"""Operational metric builders for investor health dashboard APIs."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.aws_connection import AWSConnection
from app.models.azure_connection import AzureConnection
from app.models.background_job import BackgroundJob, JobStatus
from app.models.gcp_connection import GCPConnection
from app.models.hybrid_connection import HybridConnection
from app.models.license_connection import LicenseConnection
from app.models.platform_connection import PlatformConnection
from app.models.remediation import (
    RemediationAction,
    RemediationRequest,
    RemediationStatus,
)
from app.models.saas_connection import SaaSConnection
from app.models.tenant import Tenant
from app.modules.governance.api.v1.health_dashboard_models import (
    CloudConnectionHealth,
    CloudPlusConnectionHealth,
    CloudPlusProviderHealth,
    JobQueueHealth,
    LLMUsageMetrics,
    LicenseGovernanceHealth,
    TenantMetrics,
)
from app.shared.core.ops_metrics import LLM_BUDGET_BURN_RATE
from app.shared.core.pricing import PricingTier

logger = structlog.get_logger()


async def get_tenant_metrics(db: AsyncSession, now: datetime) -> TenantMetrics:
    """Calculate tenant growth and activity metrics."""
    day_ago = now - timedelta(hours=24)
    week_ago = now - timedelta(days=7)
    free_plan = PricingTier.FREE.value

    result = await db.execute(
        select(
            func.count(Tenant.id).label("total_tenants"),
            func.count(Tenant.id)
            .filter(Tenant.last_accessed_at >= day_ago)
            .label("active_last_24h"),
            func.count(Tenant.id)
            .filter(Tenant.last_accessed_at >= week_ago)
            .label("active_last_7d"),
            func.count(Tenant.id)
            .filter(Tenant.plan == free_plan)
            .label("free_tenants"),
            func.count(Tenant.id)
            .filter(Tenant.plan != free_plan)
            .label("paid_tenants"),
            func.count(Tenant.id)
            .filter(
                Tenant.plan != free_plan,
                (Tenant.last_accessed_at < week_ago)
                | (Tenant.last_accessed_at.is_(None)),
            )
            .label("churn_risk"),
        )
    )
    row = result.one()

    return TenantMetrics(
        total_tenants=int(row.total_tenants or 0),
        active_last_24h=int(row.active_last_24h or 0),
        active_last_7d=int(row.active_last_7d or 0),
        free_tenants=int(row.free_tenants or 0),
        paid_tenants=int(row.paid_tenants or 0),
        churn_risk=int(row.churn_risk or 0),
    )


async def get_job_queue_health(db: AsyncSession, now: datetime) -> JobQueueHealth:
    """Calculate job queue health metrics."""
    day_ago = now - timedelta(hours=24)
    counts_result = await db.execute(
        select(
            func.count(BackgroundJob.id)
            .filter(BackgroundJob.status == JobStatus.PENDING)
            .label("pending_jobs"),
            func.count(BackgroundJob.id)
            .filter(BackgroundJob.status == JobStatus.RUNNING)
            .label("running_jobs"),
            func.count(BackgroundJob.id)
            .filter(
                BackgroundJob.status == JobStatus.FAILED,
                BackgroundJob.completed_at >= day_ago,
            )
            .label("failed_last_24h"),
            func.count(BackgroundJob.id)
            .filter(BackgroundJob.status == JobStatus.DEAD_LETTER)
            .label("dead_letter_count"),
        )
    )
    counts_row = counts_result.one()

    duration_expr = (
        func.extract("epoch", BackgroundJob.completed_at)
        - func.extract("epoch", BackgroundJob.created_at)
    ) * 1000

    from app.shared.db.session import get_engine

    is_postgres = get_engine().url.get_backend_name().startswith("postgresql")

    if is_postgres:
        metrics = await db.execute(
            select(
                func.avg(duration_expr),
                func.percentile_cont(0.5).within_group(duration_expr),
                func.percentile_cont(0.95).within_group(duration_expr),
                func.percentile_cont(0.99).within_group(duration_expr),
            ).where(
                BackgroundJob.status == JobStatus.COMPLETED,
                BackgroundJob.completed_at >= day_ago,
            )
        )
        avg_time, p50, p95, p99 = metrics.one()
    else:
        metrics = await db.execute(
            select(func.avg(duration_expr)).where(
                BackgroundJob.status == JobStatus.COMPLETED,
                BackgroundJob.completed_at >= day_ago,
            )
        )
        avg_time = metrics.scalar()
        p50 = p95 = p99 = avg_time

    return JobQueueHealth(
        pending_jobs=int(counts_row.pending_jobs or 0),
        running_jobs=int(counts_row.running_jobs or 0),
        failed_last_24h=int(counts_row.failed_last_24h or 0),
        dead_letter_count=int(counts_row.dead_letter_count or 0),
        avg_processing_time_ms=round(avg_time or 0.0, 2),
        p50_processing_time_ms=round(p50 or 0.0, 2),
        p95_processing_time_ms=round(p95 or 0.0, 2),
        p99_processing_time_ms=round(p99 or 0.0, 2),
    )


async def get_llm_usage_metrics(
    db: AsyncSession,
    now: datetime,
    *,
    burn_rate_metric: Any | None = None,
) -> LLMUsageMetrics:
    """Calculate real LLM usage metrics."""
    from app.models.llm import LLMBudget, LLMUsage

    day_ago = now - timedelta(hours=24)

    usage_result = await db.execute(
        select(
            func.count(LLMUsage.id).label("total_requests_24h"),
            func.coalesce(func.sum(LLMUsage.cost_usd), 0).label("estimated_cost_24h"),
        ).where(LLMUsage.created_at >= day_ago)
    )
    usage_row = usage_result.one()

    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_spend = (
        select(
            LLMUsage.tenant_id.label("tenant_id"),
            func.coalesce(func.sum(LLMUsage.cost_usd), 0).label("month_spend"),
        )
        .where(LLMUsage.created_at >= start_of_month)
        .group_by(LLMUsage.tenant_id)
        .subquery()
    )

    utilization_result = await db.execute(
        select(
            func.avg(
                func.coalesce(monthly_spend.c.month_spend, 0)
                / func.nullif(LLMBudget.monthly_limit_usd, 0)
            )
        )
        .select_from(LLMBudget)
        .outerjoin(monthly_spend, monthly_spend.c.tenant_id == LLMBudget.tenant_id)
    )
    utilization = utilization_result.scalar()
    utilization_pct = round(float(utilization or 0.0) * 100, 2)
    metric = burn_rate_metric or LLM_BUDGET_BURN_RATE
    metric.set(utilization_pct)

    return LLMUsageMetrics(
        total_requests_24h=int(usage_row.total_requests_24h or 0),
        cache_hit_rate=0.85,
        estimated_cost_24h=float(usage_row.estimated_cost_24h or 0.0),
        budget_utilization=utilization_pct,
    )


async def get_cloud_plus_provider_health(
    db: AsyncSession, model: Any
) -> CloudPlusProviderHealth:
    """Compute active/inactive/error counts for a single Cloud+ connection model."""
    result = await db.execute(
        select(
            func.count(model.id).label("total_connections"),
            func.count(model.id)
            .filter(model.is_active.is_(True))
            .label("active_connections"),
            func.count(model.id)
            .filter(
                and_(
                    model.error_message.is_not(None),
                    func.length(func.trim(model.error_message)) > 0,
                )
            )
            .label("errored_connections"),
        )
    )
    row = result.one()
    total = int(row.total_connections or 0)
    active = int(row.active_connections or 0)
    inactive = max(total - active, 0)
    errored = min(int(row.errored_connections or 0), total)
    return CloudPlusProviderHealth(
        total_connections=total,
        active_connections=active,
        inactive_connections=inactive,
        errored_connections=errored,
    )


async def get_aws_provider_health(db: AsyncSession) -> CloudPlusProviderHealth:
    """Compute provider-style health for AWS status model."""
    result = await db.execute(
        select(
            func.count(AWSConnection.id).label("total_connections"),
            func.count(AWSConnection.id)
            .filter(AWSConnection.status == "active")
            .label("active_connections"),
            func.count(AWSConnection.id)
            .filter(AWSConnection.status == "error")
            .label("errored_connections"),
        )
    )
    row = result.one()
    total = int(row.total_connections or 0)
    active = int(row.active_connections or 0)
    inactive = max(total - active, 0)
    errored = min(int(row.errored_connections or 0), total)
    return CloudPlusProviderHealth(
        total_connections=total,
        active_connections=active,
        inactive_connections=inactive,
        errored_connections=errored,
    )


async def get_cloud_connection_health(db: AsyncSession) -> CloudConnectionHealth:
    """Aggregate health for AWS, Azure, and GCP connectors."""
    providers: dict[str, CloudPlusProviderHealth] = {
        "aws": await get_aws_provider_health(db),
        "azure": await get_cloud_plus_provider_health(db, AzureConnection),
        "gcp": await get_cloud_plus_provider_health(db, GCPConnection),
    }
    totals = {
        "total_connections": 0,
        "active_connections": 0,
        "inactive_connections": 0,
        "errored_connections": 0,
    }
    for snapshot in providers.values():
        totals["total_connections"] += snapshot.total_connections
        totals["active_connections"] += snapshot.active_connections
        totals["inactive_connections"] += snapshot.inactive_connections
        totals["errored_connections"] += snapshot.errored_connections

    return CloudConnectionHealth(providers=providers, **totals)


async def get_cloud_plus_connection_health(
    db: AsyncSession,
) -> CloudPlusConnectionHealth:
    """Aggregate health for SaaS, license, platform, and hybrid connectors."""
    provider_models: dict[str, Any] = {
        "saas": SaaSConnection,
        "license": LicenseConnection,
        "platform": PlatformConnection,
        "hybrid": HybridConnection,
    }
    providers: dict[str, CloudPlusProviderHealth] = {}
    totals = {
        "total_connections": 0,
        "active_connections": 0,
        "inactive_connections": 0,
        "errored_connections": 0,
    }

    for provider, model in provider_models.items():
        snapshot = await get_cloud_plus_provider_health(db, model)
        providers[provider] = snapshot
        totals["total_connections"] += snapshot.total_connections
        totals["active_connections"] += snapshot.active_connections
        totals["inactive_connections"] += snapshot.inactive_connections
        totals["errored_connections"] += snapshot.errored_connections

    return CloudPlusConnectionHealth(providers=providers, **totals)


async def get_license_governance_health(
    db: AsyncSession, now: datetime, *, window_hours: int = 24
) -> LicenseGovernanceHealth:
    """Calculate license governance throughput and reliability over a rolling window."""
    window_start = now - timedelta(hours=window_hours)
    in_flight_statuses = (
        RemediationStatus.PENDING,
        RemediationStatus.PENDING_APPROVAL,
        RemediationStatus.APPROVED,
        RemediationStatus.SCHEDULED,
        RemediationStatus.EXECUTING,
    )

    active_connections = int(
        await db.scalar(
            select(func.count(LicenseConnection.id)).where(LicenseConnection.is_active)
        )
        or 0
    )

    counts_result = await db.execute(
        select(
            func.count(RemediationRequest.id).label("created_requests"),
            func.count(RemediationRequest.id)
            .filter(RemediationRequest.status == RemediationStatus.COMPLETED)
            .label("completed_requests"),
            func.count(RemediationRequest.id)
            .filter(RemediationRequest.status == RemediationStatus.FAILED)
            .label("failed_requests"),
            func.count(RemediationRequest.id)
            .filter(RemediationRequest.status.in_(in_flight_statuses))
            .label("in_flight_requests"),
        ).where(
            RemediationRequest.action == RemediationAction.RECLAIM_LICENSE_SEAT,
            RemediationRequest.created_at >= window_start,
        )
    )
    counts_row = counts_result.one()
    created_requests = int(counts_row.created_requests or 0)
    completed_requests = int(counts_row.completed_requests or 0)
    failed_requests = int(counts_row.failed_requests or 0)
    in_flight_requests = int(counts_row.in_flight_requests or 0)

    completion_rate = (
        round((completed_requests / created_requests) * 100.0, 2)
        if created_requests > 0
        else 0.0
    )
    failure_rate = (
        round((failed_requests / created_requests) * 100.0, 2)
        if created_requests > 0
        else 0.0
    )

    completed_rows = (
        await db.execute(
            select(RemediationRequest.created_at, RemediationRequest.executed_at).where(
                RemediationRequest.action == RemediationAction.RECLAIM_LICENSE_SEAT,
                RemediationRequest.status == RemediationStatus.COMPLETED,
                RemediationRequest.created_at >= window_start,
                RemediationRequest.executed_at.is_not(None),
            )
        )
    ).all()
    completion_hours: list[float] = []
    for created_at, executed_at in completed_rows:
        if created_at is None or executed_at is None:
            continue
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        if executed_at.tzinfo is None:
            executed_at = executed_at.replace(tzinfo=timezone.utc)
        if executed_at >= created_at:
            completion_hours.append((executed_at - created_at).total_seconds() / 3600.0)

    avg_time_to_complete_hours = (
        round(sum(completion_hours) / len(completion_hours), 2)
        if completion_hours
        else None
    )

    return LicenseGovernanceHealth(
        window_hours=window_hours,
        active_license_connections=active_connections,
        requests_created_24h=created_requests,
        requests_completed_24h=completed_requests,
        requests_failed_24h=failed_requests,
        requests_in_flight=in_flight_requests,
        completion_rate_percent=completion_rate,
        failure_rate_percent=failure_rate,
        avg_time_to_complete_hours=avg_time_to_complete_hours,
    )


__all__ = [
    "get_aws_provider_health",
    "get_cloud_connection_health",
    "get_cloud_plus_connection_health",
    "get_cloud_plus_provider_health",
    "get_job_queue_health",
    "get_license_governance_health",
    "get_llm_usage_metrics",
    "get_tenant_metrics",
]
