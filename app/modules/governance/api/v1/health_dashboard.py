"""Internal health dashboard API for operational metrics."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gcp_connection import GCPConnection
from app.models.hybrid_connection import HybridConnection
from app.models.license_connection import LicenseConnection
from app.models.platform_connection import PlatformConnection
from app.models.saas_connection import SaaSConnection
from app.models.azure_connection import AzureConnection
from app.modules.governance.api.v1.health_dashboard_models import (
    CloudConnectionHealth,
    CloudPlusConnectionHealth,
    CloudPlusProviderHealth,
    InvestorHealthDashboard,
    JobQueueHealth,
    LLMFairUseRuntime,
    LLMFairUseThresholds,
    LLMUsageMetrics,
    LicenseGovernanceHealth,
    LandingFunnelHealth,
    SystemHealth,
    TenantMetrics,
)
from app.modules.governance.api.v1.health_dashboard_ops import (
    get_aws_provider_health as _get_aws_provider_health_impl,
    get_cloud_plus_provider_health as _get_cloud_plus_provider_health_impl,
    get_job_queue_health as _get_job_queue_health_impl,
    get_license_governance_health as _get_license_governance_health_impl,
    get_llm_usage_metrics as _get_llm_usage_metrics_impl,
    get_tenant_metrics as _get_tenant_metrics_impl,
)
from app.modules.governance.api.v1.landing_funnel_health_ops import (
    get_landing_funnel_health as _get_landing_funnel_health_impl,
)
from app.shared.core.auth import CurrentUser, requires_role
from app.shared.core.cache import get_cache_service
from app.shared.core.config import get_settings
from app.shared.core.ops_metrics import LLM_BUDGET_BURN_RATE
from app.shared.core.pricing import PricingTier, get_tenant_tier
from app.shared.db.session import get_db

logger = structlog.get_logger()
router = APIRouter(tags=["Internal Health"])
HEALTH_DASHBOARD_CACHE_RECOVERABLE_EXCEPTIONS = (
    ValidationError,
    RuntimeError,
    TypeError,
    ValueError,
)
HEALTH_DASHBOARD_TIER_LOOKUP_RECOVERABLE_EXCEPTIONS = (
    SQLAlchemyError,
    RuntimeError,
    TypeError,
    ValueError,
)

# Track startup time
_startup_time = datetime.now(timezone.utc)
HEALTH_DASHBOARD_CACHE_TTL = timedelta(seconds=20)
FAIR_USE_RUNTIME_CACHE_TTL = timedelta(seconds=20)


@router.get("", response_model=InvestorHealthDashboard)
async def get_investor_health_dashboard(
    _user: Annotated[CurrentUser, Depends(requires_role("admin"))],
    db: AsyncSession = Depends(get_db),
) -> InvestorHealthDashboard:
    """
    Get comprehensive internal health dashboard for operations visibility.

    Shows:
    - System uptime and availability
    - Tenant growth and engagement metrics
    - Job queue health
    - LLM usage and costs
    - Cloud + Cloud+ connection reliability
    """
    now = datetime.now(timezone.utc)
    tenant_scope = str(_user.tenant_id) if _user.tenant_id else "global"
    cache_key = f"api:health-dashboard:{tenant_scope}"
    cache = get_cache_service()
    if cache.enabled:
        cached_payload = await cache.get(cache_key)
        if isinstance(cached_payload, dict):
            try:
                return InvestorHealthDashboard.model_validate(cached_payload)
            except HEALTH_DASHBOARD_CACHE_RECOVERABLE_EXCEPTIONS as exc:
                logger.warning("health_dashboard_cache_decode_failed", error=str(exc))

    uptime = now - _startup_time
    system = SystemHealth(
        status="healthy",
        uptime_hours=round(uptime.total_seconds() / 3600, 2),
        last_check=now.isoformat(),
    )

    tenants = await _get_tenant_metrics(db, now)
    job_queue = await _get_job_queue_health(db, now)
    llm_usage = await _get_llm_usage_metrics(db, now)
    cloud_connections = await _get_cloud_connection_health(db)
    cloud_plus_connections = await _get_cloud_plus_connection_health(db)
    license_governance = await _get_license_governance_health(db, now)
    landing_funnel = await _get_landing_funnel_health(db, now=now)

    payload = InvestorHealthDashboard(
        generated_at=now.isoformat(),
        system=system,
        tenants=tenants,
        job_queue=job_queue,
        llm_usage=llm_usage,
        cloud_connections=cloud_connections,
        cloud_plus_connections=cloud_plus_connections,
        license_governance=license_governance,
        landing_funnel=landing_funnel,
    )
    if cache.enabled:
        await cache.set(
            cache_key,
            payload.model_dump(mode="json"),
            ttl=HEALTH_DASHBOARD_CACHE_TTL,
        )
    return payload


def _positive_int_or_none(value: Any) -> int | None:
    """Normalize optional integer settings and treat non-positive values as disabled."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _coerce_int_with_minimum(value: Any, *, default: int, minimum: int) -> int:
    """Parse integer settings defensively and enforce a minimum bound."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(parsed, minimum)


@router.get("/fair-use", response_model=LLMFairUseRuntime)
async def get_llm_fair_use_runtime(
    _user: Annotated[CurrentUser, Depends(requires_role("admin"))],
    db: AsyncSession = Depends(get_db),
) -> LLMFairUseRuntime:
    """
    Return tenant-scoped fair-use runtime status and configured thresholds.

    This endpoint is intended for operations visibility in admin health.
    """
    now = datetime.now(timezone.utc)
    tenant_scope = str(_user.tenant_id) if _user.tenant_id else "global"
    cache_key = f"api:health-dashboard:fair-use:{tenant_scope}"
    cache = get_cache_service()
    if cache.enabled:
        cached_payload = await cache.get(cache_key)
        if isinstance(cached_payload, dict):
            try:
                return LLMFairUseRuntime.model_validate(cached_payload)
            except HEALTH_DASHBOARD_CACHE_RECOVERABLE_EXCEPTIONS as exc:
                logger.warning(
                    "health_dashboard_fair_use_cache_decode_failed", error=str(exc)
                )

    settings = get_settings()
    tenant_tier = PricingTier.FREE
    if _user.tenant_id:
        try:
            tenant_tier = await get_tenant_tier(_user.tenant_id, db)
        except HEALTH_DASHBOARD_TIER_LOOKUP_RECOVERABLE_EXCEPTIONS as exc:
            logger.warning(
                "health_dashboard_fair_use_tier_lookup_failed",
                tenant_id=str(_user.tenant_id),
                error=str(exc),
            )

    guards_enabled = bool(settings.LLM_FAIR_USE_GUARDS_ENABLED)
    tier_eligible = tenant_tier in {PricingTier.PRO, PricingTier.ENTERPRISE}
    active_for_tenant = guards_enabled and tier_eligible

    threshold_payload = LLMFairUseThresholds(
        pro_daily_soft_cap=_positive_int_or_none(settings.LLM_FAIR_USE_PRO_DAILY_SOFT_CAP),
        enterprise_daily_soft_cap=_positive_int_or_none(
            settings.LLM_FAIR_USE_ENTERPRISE_DAILY_SOFT_CAP
        ),
        per_minute_cap=_positive_int_or_none(settings.LLM_FAIR_USE_PER_MINUTE_CAP),
        per_tenant_concurrency_cap=_positive_int_or_none(
            settings.LLM_FAIR_USE_PER_TENANT_CONCURRENCY_CAP
        ),
        concurrency_lease_ttl_seconds=_coerce_int_with_minimum(
            settings.LLM_FAIR_USE_CONCURRENCY_LEASE_TTL_SECONDS,
            default=180,
            minimum=30,
        ),
        enforced_tiers=[PricingTier.PRO.value, PricingTier.ENTERPRISE.value],
    )

    payload = LLMFairUseRuntime(
        generated_at=now.isoformat(),
        guards_enabled=guards_enabled,
        tenant_tier=tenant_tier.value,
        tier_eligible=tier_eligible,
        active_for_tenant=active_for_tenant,
        thresholds=threshold_payload,
    )
    if cache.enabled:
        await cache.set(
            cache_key,
            payload.model_dump(mode="json"),
            ttl=FAIR_USE_RUNTIME_CACHE_TTL,
        )
    return payload


async def _get_tenant_metrics(db: AsyncSession, now: datetime) -> TenantMetrics:
    return await _get_tenant_metrics_impl(db, now)


async def _get_job_queue_health(db: AsyncSession, now: datetime) -> JobQueueHealth:
    return await _get_job_queue_health_impl(db, now)


async def _get_llm_usage_metrics(db: AsyncSession, now: datetime) -> LLMUsageMetrics:
    return await _get_llm_usage_metrics_impl(
        db,
        now,
        burn_rate_metric=LLM_BUDGET_BURN_RATE,
    )


async def _get_cloud_plus_provider_health(
    db: AsyncSession, model: Any
) -> CloudPlusProviderHealth:
    return await _get_cloud_plus_provider_health_impl(db, model)


async def _get_aws_provider_health(db: AsyncSession) -> CloudPlusProviderHealth:
    return await _get_aws_provider_health_impl(db)


async def _get_cloud_connection_health(db: AsyncSession) -> CloudConnectionHealth:
    providers: dict[str, CloudPlusProviderHealth] = {
        "aws": await _get_aws_provider_health(db),
        "azure": await _get_cloud_plus_provider_health(db, AzureConnection),
        "gcp": await _get_cloud_plus_provider_health(db, GCPConnection),
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


async def _get_cloud_plus_connection_health(db: AsyncSession) -> CloudPlusConnectionHealth:
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
        snapshot = await _get_cloud_plus_provider_health(db, model)
        providers[provider] = snapshot
        totals["total_connections"] += snapshot.total_connections
        totals["active_connections"] += snapshot.active_connections
        totals["inactive_connections"] += snapshot.inactive_connections
        totals["errored_connections"] += snapshot.errored_connections

    return CloudPlusConnectionHealth(providers=providers, **totals)


async def _get_license_governance_health(
    db: AsyncSession, now: datetime, *, window_hours: int = 24
) -> LicenseGovernanceHealth:
    return await _get_license_governance_health_impl(
        db,
        now,
        window_hours=window_hours,
    )


async def _get_landing_funnel_health(
    db: AsyncSession,
    now: datetime,
) -> LandingFunnelHealth:
    return await _get_landing_funnel_health_impl(db, now=now)
