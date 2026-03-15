from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import date, datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import structlog
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reporting.api.v1.costs_acceptance_ledger_quality import (
    build_ledger_quality_metrics,
)
from app.modules.reporting.api.v1.costs_helpers import build_unit_metrics
from app.modules.reporting.api.v1.costs_metrics import (
    compute_ingestion_sla_metrics,
    compute_license_governance_kpi,
    compute_provider_recency_summaries,
    get_unit_settings_snapshot,
    window_total_cost,
)
from app.modules.reporting.api.v1.costs_models import (
    AcceptanceKpiMetric,
    AcceptanceKpisResponse,
)
from app.shared.core.auth import CurrentUser
from app.shared.core.config import get_settings
from app.shared.core.pricing import (
    FeatureFlag,
    PricingTier,
    is_feature_enabled,
    normalize_tier,
)

logger = structlog.get_logger()


def require_tenant_id(user: CurrentUser) -> UUID:
    if user.tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context is required")
    return user.tenant_id


def resolve_user_tier(user: CurrentUser) -> PricingTier:
    return normalize_tier(getattr(user, "tier", PricingTier.FREE))


def _window_bounds(
    start_date: date,
    end_date: date,
) -> tuple[datetime, datetime]:
    start_dt = datetime.combine(start_date, datetime.min.time()).replace(
        tzinfo=timezone.utc
    )
    end_dt_exclusive = datetime.combine(
        end_date + timedelta(days=1),
        datetime.min.time(),
    ).replace(tzinfo=timezone.utc)
    return start_dt, end_dt_exclusive


async def compute_acceptance_kpis_payload(
    *,
    start_date: date,
    end_date: date,
    ingestion_window_hours: int,
    ingestion_target_success_rate_percent: float,
    recency_target_hours: int,
    chargeback_target_percent: float,
    max_unit_anomalies: int,
    ledger_normalization_target_percent: float = 95.0,
    canonical_mapping_target_percent: float = 90.0,
    current_user: CurrentUser,
    db: AsyncSession,
    compute_ingestion_sla_metrics_fn: Callable[..., Awaitable[Any]] = (
        compute_ingestion_sla_metrics
    ),
    compute_provider_recency_summaries_fn: Callable[..., Awaitable[Any]] = (
        compute_provider_recency_summaries
    ),
    compute_license_governance_kpi_fn: Callable[
        ..., Awaitable[AcceptanceKpiMetric]
    ] = compute_license_governance_kpi,
    get_unit_settings_snapshot_fn: Callable[..., Awaitable[Any]] = (
        get_unit_settings_snapshot
    ),
    window_total_cost_fn: Callable[..., Awaitable[Any]] = (window_total_cost),
    get_settings_fn: Callable[[], Any] = get_settings,
    is_feature_enabled_fn: Callable[..., bool] = is_feature_enabled,
) -> AcceptanceKpisResponse:
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must be <= end_date")

    tenant_id = require_tenant_id(current_user)
    tier = resolve_user_tier(current_user)
    metrics: list[AcceptanceKpiMetric] = []
    window_start, window_end_exclusive = _window_bounds(start_date, end_date)

    if is_feature_enabled_fn(tier, FeatureFlag.INGESTION_SLA):
        ingestion = await compute_ingestion_sla_metrics_fn(
            db=db,
            tenant_id=tenant_id,
            window_hours=ingestion_window_hours,
            target_success_rate_percent=ingestion_target_success_rate_percent,
        )
        recency = await compute_provider_recency_summaries_fn(
            db=db,
            tenant_id=tenant_id,
            recency_target_hours=recency_target_hours,
        )
        active_connections = sum(item.active_connections for item in recency)
        stale_connections = sum(
            item.stale_connections + item.never_ingested for item in recency
        )
        recency_met = active_connections > 0 and stale_connections == 0
        meets_target = ingestion.meets_sla and recency_met
        metrics.append(
            AcceptanceKpiMetric(
                key="ingestion_reliability",
                label="Ingestion Reliability + Recency",
                available=True,
                target=(
                    f">={ingestion_target_success_rate_percent:.2f}% success and "
                    f"0 stale active connections (>{recency_target_hours}h)"
                ),
                actual=(
                    f"{ingestion.success_rate_percent:.2f}% success, "
                    f"stale/never {stale_connections}/{active_connections}"
                ),
                meets_target=meets_target,
                details={
                    "ingestion_sla": ingestion.model_dump(),
                    "provider_recency": [item.model_dump() for item in recency],
                },
            )
        )
    else:
        metrics.append(
            AcceptanceKpiMetric(
                key="ingestion_reliability",
                label="Ingestion Reliability + Recency",
                available=False,
                target="Growth tier or higher",
                actual="Feature unavailable on current tier",
                meets_target=False,
            )
        )

    if is_feature_enabled_fn(tier, FeatureFlag.CHARGEBACK):
        from app.modules.reporting.domain.attribution_engine import AttributionEngine

        attribution_engine = AttributionEngine(db)
        coverage = await attribution_engine.get_allocation_coverage(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            target_percentage=chargeback_target_percent,
        )
        coverage_percentage = float(coverage.get("coverage_percentage", 0.0))
        metrics.append(
            AcceptanceKpiMetric(
                key="chargeback_coverage",
                label="Chargeback Allocation Coverage",
                available=True,
                target=f">={chargeback_target_percent:.2f}%",
                actual=f"{coverage_percentage:.2f}%",
                meets_target=bool(coverage.get("meets_target", False)),
                details=coverage,
            )
        )
    else:
        metrics.append(
            AcceptanceKpiMetric(
                key="chargeback_coverage",
                label="Chargeback Allocation Coverage",
                available=False,
                target="Growth tier or higher",
                actual="Feature unavailable on current tier",
                meets_target=False,
            )
        )

    metrics.append(
        await compute_license_governance_kpi_fn(
            db=db, tenant_id=tenant_id, start_date=start_date, end_date=end_date
        )
    )

    from app.modules.governance.domain.security.audit_log import (
        AuditEventType,
        AuditLog,
    )

    latest_isolation_verification = await db.scalar(
        select(AuditLog)
        .where(
            AuditLog.tenant_id == tenant_id,
            AuditLog.event_type
            == AuditEventType.TENANCY_ISOLATION_VERIFICATION_CAPTURED.value,
            AuditLog.event_timestamp >= window_start,
            AuditLog.event_timestamp < window_end_exclusive,
        )
        .order_by(AuditLog.event_timestamp.desc())
        .limit(1)
    )
    if latest_isolation_verification is None:
        isolation_actual = (
            "No tenant-isolation verification evidence captured in window"
        )
        isolation_meets_target = False
        isolation_details: dict[str, Any] = {
            "verification_status": "MISSING",
            "window_start": window_start.isoformat(),
            "window_end_exclusive": window_end_exclusive.isoformat(),
        }
    else:
        observed_at = latest_isolation_verification.event_timestamp
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=timezone.utc)
        isolation_meets_target = bool(
            getattr(latest_isolation_verification, "success", False)
        )
        isolation_actual = (
            f"Verified at {observed_at.isoformat()}"
            if isolation_meets_target
            else f"Latest verification failed at {observed_at.isoformat()}"
        )
        isolation_details = {
            "verification_status": "PASS" if isolation_meets_target else "FAILED",
            "event_id": str(getattr(latest_isolation_verification, "id", "")),
            "captured_at": observed_at.isoformat(),
            "correlation_id": getattr(
                latest_isolation_verification, "correlation_id", None
            ),
            "window_start": window_start.isoformat(),
            "window_end_exclusive": window_end_exclusive.isoformat(),
        }

    metrics.append(
        AcceptanceKpiMetric(
            key="tenant_isolation_proof",
            label="Tenant Isolation Verification Evidence",
            available=True,
            target="Successful tenant-isolation verification captured in requested window",
            actual=isolation_actual,
            meets_target=isolation_meets_target,
            details=isolation_details,
        )
    )

    settings = get_settings_fn()
    encryption_ready = bool(settings.ENCRYPTION_KEY and settings.KDF_SALT)
    metrics.append(
        AcceptanceKpiMetric(
            key="encryption_health_proof",
            label="Encryption & Key Management Health",
            available=True,
            target="Encryption keys and KDF salt configured",
            actual="Healthy" if encryption_ready else "Degraded",
            meets_target=encryption_ready,
            details={
                "fernet_ready": bool(settings.ENCRYPTION_KEY),
                "kdf_salt_ready": bool(settings.KDF_SALT),
                "blind_indexing_active": True,
            },
        )
    )

    metrics.append(
        AcceptanceKpiMetric(
            key="user_access_review_proof",
            label="User Access Review Evidence",
            available=False,
            target="Operator-captured user access review evidence in requested window",
            actual="No automated user-access review evidence source is available",
            meets_target=False,
            details={
                "requires_manual_evidence": True,
                "window_start": window_start.isoformat(),
                "window_end_exclusive": window_end_exclusive.isoformat(),
            },
        )
    )

    remediation_stmt = select(func.count(AuditLog.id)).where(
        AuditLog.tenant_id == tenant_id,
        AuditLog.event_type == AuditEventType.REMEDIATION_EXECUTED.value,
        AuditLog.event_timestamp >= window_start,
        AuditLog.event_timestamp < window_end_exclusive,
        AuditLog.success,
    )
    remediation_count = await db.scalar(remediation_stmt) or 0

    metrics.append(
        AcceptanceKpiMetric(
            key="change_governance_proof",
            label="Change Governance Audit Evidence",
            available=True,
            target=">=1 successful remediation execution audit event in requested window",
            actual=f"{remediation_count} successful remediation execution events",
            meets_target=remediation_count > 0,
            details={
                "period_remediations": remediation_count,
                "evidence_type": "AuditLog.remediation.executed",
                "window_start": window_start.isoformat(),
                "window_end_exclusive": window_end_exclusive.isoformat(),
            },
        )
    )

    if is_feature_enabled_fn(tier, FeatureFlag.UNIT_ECONOMICS):
        unit_settings = await get_unit_settings_snapshot_fn(db, tenant_id)
        total_cost = await window_total_cost_fn(db, tenant_id, start_date, end_date)
        window_days = (end_date - start_date).days + 1
        baseline_end = start_date - timedelta(days=1)
        baseline_start = baseline_end - timedelta(days=window_days - 1)
        baseline_total_cost = await window_total_cost_fn(
            db, tenant_id, baseline_start, baseline_end
        )
        unit_metrics = build_unit_metrics(
            total_cost=total_cost,
            baseline_total_cost=baseline_total_cost,
            threshold_percent=float(unit_settings.anomaly_threshold_percent),
            request_volume=float(unit_settings.default_request_volume),
            workload_volume=float(unit_settings.default_workload_volume),
            customer_volume=float(unit_settings.default_customer_volume),
        )
        anomaly_count = sum(1 for metric in unit_metrics if metric.is_anomalous)
        metrics.append(
            AcceptanceKpiMetric(
                key="unit_economics_stability",
                label="Unit Economics Stability",
                available=True,
                target=f"<= {max_unit_anomalies} anomalous metrics",
                actual=f"{anomaly_count} anomalous metrics",
                meets_target=anomaly_count <= max_unit_anomalies,
                details={
                    "threshold_percent": float(unit_settings.anomaly_threshold_percent),
                    "metrics": [metric.model_dump() for metric in unit_metrics],
                },
            )
        )
    else:
        metrics.append(
            AcceptanceKpiMetric(
                key="unit_economics_stability",
                label="Unit Economics Stability",
                available=False,
                target="Starter tier or higher",
                actual="Feature unavailable on current tier",
                meets_target=False,
            )
        )

    metrics.extend(
        await build_ledger_quality_metrics(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            ledger_normalization_target_percent=ledger_normalization_target_percent,
            canonical_mapping_target_percent=canonical_mapping_target_percent,
            logger=logger,
        )
    )

    available_metrics = [metric for metric in metrics if metric.available]
    informational_keys = {
        "tenant_isolation_proof",
        "encryption_health_proof",
        "user_access_review_proof",
        "change_governance_proof",
    }
    gating_metrics = [
        metric for metric in available_metrics if metric.key not in informational_keys
    ]
    all_targets_met = bool(gating_metrics) and all(
        metric.meets_target for metric in gating_metrics
    )

    return AcceptanceKpisResponse(
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        tier=tier.value,
        all_targets_met=all_targets_met,
        available_metrics=len(available_metrics),
        metrics=metrics,
    )
