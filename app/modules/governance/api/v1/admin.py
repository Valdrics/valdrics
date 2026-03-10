from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, Depends, Query
from app.shared.core.config import get_settings
from app.shared.db.session import get_db, get_system_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import case, func, select
import secrets
import structlog
from uuid import UUID
from app.shared.core.rate_limit import auth_limit
from app.shared.core.proxy_headers import resolve_client_ip
from app.shared.core.logging import audit_log_async
from pydantic import BaseModel, Field

from app.models.landing_telemetry_rollup import LandingTelemetryDailyRollup
from app.models.tenant_growth_funnel_snapshot import TenantGrowthFunnelSnapshot
from app.modules.governance.api.v1.health_dashboard_models import (
    LandingFunnelHealthAlert,
    LandingFunnelWeeklyDelta,
    LandingFunnelWindowSummary,
)
from app.modules.governance.api.v1.landing_funnel_health_ops import (
    get_landing_funnel_health as _get_landing_funnel_health,
    build_window_summary as _build_window_summary,
    load_funnel_window_summary as _load_funnel_window_summary,
    load_rollup_window_summary as _load_rollup_window_summary,
    window_stage_count as _window_stage_count,
)
from app.shared.core.auth import CurrentUser, requires_role

router = APIRouter(tags=["Admin Utilities"])
logger = structlog.get_logger()


def _resolve_admin_audit_tenant_id(request: Request) -> str | None:
    candidate = getattr(getattr(request, "state", None), "tenant_id", None)
    if candidate is None:
        candidate = getattr(request, "path_params", {}).get("tenant_id")
    if candidate is None:
        return None
    try:
        return str(UUID(str(candidate)))
    except (TypeError, ValueError, AttributeError):
        return None


async def validate_admin_key(
    request: Request, x_admin_key: str = Header(..., alias="X-Admin-Key")
) -> bool:
    """Dependency to validate the admin API key with production hardening."""
    settings = get_settings()

    if not settings.ADMIN_API_KEY:
        logger.error("admin_key_not_configured")
        raise HTTPException(
            status_code=503, detail="Admin endpoint not configured. Set ADMIN_API_KEY."
        )

    # Item 11: Prevent weak keys in production
    if settings.ENVIRONMENT == "production" and len(settings.ADMIN_API_KEY) < 32:
        logger.critical("admin_key_too_weak_for_production")
        raise HTTPException(
            status_code=500,
            detail="ADMIN_API_KEY must be at least 32 characters in production.",
        )

    if not secrets.compare_digest(x_admin_key, settings.ADMIN_API_KEY):
        client_host = resolve_client_ip(request, settings_obj=settings)
        audit_tenant_id = _resolve_admin_audit_tenant_id(request)
        audit_details = {
            "path": request.url.path,
            "client_ip": client_host,
            "tenant_scope_known": audit_tenant_id is not None,
        }
        await audit_log_async(
            "admin_auth_failed",
            "admin_portal",
            audit_tenant_id,
            audit_details,
            db=None,
            resource_type="admin_auth",
            resource_id=request.url.path,
            success=False,
            error_message="Invalid admin key",
            request_method=getattr(request, "method", None),
            request_path=request.url.path,
            isolated=True,
        )

        logger.warning("admin_auth_failed", client_ip=client_host)
        raise HTTPException(status_code=403, detail="Forbidden")

    return True


@router.post("/trigger-analysis")
@auth_limit  # Item 11: Rate limit admin key checks
async def trigger_analysis(
    request: Request, _: bool = Depends(validate_admin_key)
) -> dict[str, str]:
    """Manually trigger a scheduled analysis job."""

    logger.info("manual_trigger_requested")
    # Access scheduler from app state (passed via request.app)
    await request.app.state.scheduler.daily_analysis_job()
    return {"status": "triggered", "message": "Daily analysis job executed."}


@router.get("/reconcile/{tenant_id}")
@auth_limit  # Item 11: Consistent rate limiting
async def reconcile_tenant_costs(
    request: Request,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    provider: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(validate_admin_key),
) -> dict[str, Any]:
    """
    Diagnostic tool to compare Explorer vs CUR data for a tenant.
    Used for investigating billing discrepancies.
    """

    from app.modules.reporting.domain.reconciliation import CostReconciliationService

    service = CostReconciliationService(db)

    try:
        result = await service.compare_explorer_vs_cur(
            tenant_id,
            start_date,
            end_date,
            provider=provider,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


class LandingCampaignMetricsRow(BaseModel):
    utm_source: str = Field(default="direct")
    utm_medium: str = Field(default="direct")
    utm_campaign: str = Field(default="direct")
    total_events: int
    cta_events: int
    signup_intent_events: int
    onboarded_tenants: int = 0
    connected_tenants: int = 0
    first_value_tenants: int = 0
    pql_tenants: int = 0
    pricing_view_tenants: int = 0
    checkout_started_tenants: int = 0
    paid_tenants: int = 0
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None


class LandingCampaignMetricsResponse(BaseModel):
    window_start: date
    window_end: date
    days: int
    total_events: int
    total_onboarded_tenants: int
    total_connected_tenants: int
    total_first_value_tenants: int
    total_pql_tenants: int
    total_pricing_view_tenants: int
    total_checkout_started_tenants: int
    total_paid_tenants: int
    weekly_current: LandingFunnelWindowSummary
    weekly_previous: LandingFunnelWindowSummary
    weekly_delta: LandingFunnelWeeklyDelta
    funnel_alerts: list[LandingFunnelHealthAlert]
    items: list[LandingCampaignMetricsRow]

@router.get("/landing/campaigns", response_model=LandingCampaignMetricsResponse)
@auth_limit
async def get_landing_campaign_metrics(
    request: Request,
    days: int = Query(default=30, ge=1, le=120),
    limit: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_system_db),
    user: CurrentUser = Depends(requires_role("admin")),
) -> LandingCampaignMetricsResponse:
    del request
    del user

    window_end = datetime.now(timezone.utc).date()
    window_start = window_end - timedelta(days=days - 1)
    window_start_at = datetime.combine(window_start, datetime.min.time(), tzinfo=timezone.utc)
    window_end_at = datetime.combine(
        window_end + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )

    total_events_expr = func.sum(LandingTelemetryDailyRollup.event_count)
    cta_events_expr = func.sum(
        case(
            (
                LandingTelemetryDailyRollup.funnel_stage == "cta",
                LandingTelemetryDailyRollup.event_count,
            ),
            else_=0,
        )
    )
    signup_intent_expr = func.sum(
        case(
            (
                LandingTelemetryDailyRollup.funnel_stage == "signup_intent",
                LandingTelemetryDailyRollup.event_count,
            ),
            else_=0,
        )
    )
    normalized_source = func.coalesce(TenantGrowthFunnelSnapshot.utm_source, "direct")
    normalized_medium = func.coalesce(TenantGrowthFunnelSnapshot.utm_medium, "direct")
    normalized_campaign = func.coalesce(TenantGrowthFunnelSnapshot.utm_campaign, "direct")

    stmt = (
        select(
            LandingTelemetryDailyRollup.utm_source,
            LandingTelemetryDailyRollup.utm_medium,
            LandingTelemetryDailyRollup.utm_campaign,
            total_events_expr.label("total_events"),
            cta_events_expr.label("cta_events"),
            signup_intent_expr.label("signup_intent_events"),
            func.min(LandingTelemetryDailyRollup.first_seen_at).label("first_seen_at"),
            func.max(LandingTelemetryDailyRollup.last_seen_at).label("last_seen_at"),
        )
        .where(LandingTelemetryDailyRollup.event_date >= window_start)
        .where(LandingTelemetryDailyRollup.event_date <= window_end)
        .group_by(
            LandingTelemetryDailyRollup.utm_source,
            LandingTelemetryDailyRollup.utm_medium,
            LandingTelemetryDailyRollup.utm_campaign,
        )
        .order_by(total_events_expr.desc())
    )
    funnel_stmt = (
        select(
            normalized_source.label("utm_source"),
            normalized_medium.label("utm_medium"),
            normalized_campaign.label("utm_campaign"),
            _window_stage_count(
                TenantGrowthFunnelSnapshot.tenant_onboarded_at,
                window_start_at,
                window_end_at,
            ).label("onboarded_tenants"),
            _window_stage_count(
                TenantGrowthFunnelSnapshot.first_connection_verified_at,
                window_start_at,
                window_end_at,
            ).label("connected_tenants"),
            _window_stage_count(
                TenantGrowthFunnelSnapshot.first_value_activated_at,
                window_start_at,
                window_end_at,
            ).label("first_value_tenants"),
            _window_stage_count(
                TenantGrowthFunnelSnapshot.pql_qualified_at,
                window_start_at,
                window_end_at,
            ).label("pql_tenants"),
            _window_stage_count(
                TenantGrowthFunnelSnapshot.pricing_viewed_at,
                window_start_at,
                window_end_at,
            ).label("pricing_view_tenants"),
            _window_stage_count(
                TenantGrowthFunnelSnapshot.checkout_started_at,
                window_start_at,
                window_end_at,
            ).label("checkout_started_tenants"),
            _window_stage_count(
                TenantGrowthFunnelSnapshot.paid_activated_at,
                window_start_at,
                window_end_at,
            ).label("paid_tenants"),
            func.min(TenantGrowthFunnelSnapshot.created_at).label("first_seen_at"),
            func.max(TenantGrowthFunnelSnapshot.updated_at).label("last_seen_at"),
        )
        .where(
            TenantGrowthFunnelSnapshot.created_at < window_end_at,
        )
        .group_by(normalized_source, normalized_medium, normalized_campaign)
    )

    rows = (await db.execute(stmt)).all()
    funnel_rows = (await db.execute(funnel_stmt)).all()
    item_map: dict[tuple[str, str, str], LandingCampaignMetricsRow] = {}

    for row in rows:
        key = (
            row.utm_source or "direct",
            row.utm_medium or "direct",
            row.utm_campaign or "direct",
        )
        item_map[key] = LandingCampaignMetricsRow(
            utm_source=key[0],
            utm_medium=key[1],
            utm_campaign=key[2],
            total_events=int(row.total_events or 0),
            cta_events=int(row.cta_events or 0),
            signup_intent_events=int(row.signup_intent_events or 0),
            first_seen_at=row.first_seen_at,
            last_seen_at=row.last_seen_at,
        )

    for row in funnel_rows:
        key = (
            row.utm_source or "direct",
            row.utm_medium or "direct",
            row.utm_campaign or "direct",
        )
        existing = item_map.get(
            key,
            LandingCampaignMetricsRow(
                utm_source=key[0],
                utm_medium=key[1],
                utm_campaign=key[2],
                total_events=0,
                cta_events=0,
                signup_intent_events=0,
                first_seen_at=row.first_seen_at,
                last_seen_at=row.last_seen_at,
            ),
        )
        existing.onboarded_tenants = int(row.onboarded_tenants or 0)
        existing.connected_tenants = int(row.connected_tenants or 0)
        existing.first_value_tenants = int(row.first_value_tenants or 0)
        existing.pql_tenants = int(row.pql_tenants or 0)
        existing.pricing_view_tenants = int(row.pricing_view_tenants or 0)
        existing.checkout_started_tenants = int(row.checkout_started_tenants or 0)
        existing.paid_tenants = int(row.paid_tenants or 0)
        existing.first_seen_at = existing.first_seen_at or row.first_seen_at
        existing.last_seen_at = row.last_seen_at or existing.last_seen_at
        item_map[key] = existing

    all_items = sorted(
        item_map.values(),
        key=lambda item: (
            item.total_events,
            item.paid_tenants,
            item.pql_tenants,
            item.checkout_started_tenants,
            item.utm_campaign,
        ),
        reverse=True,
    )
    items = all_items[:limit]

    current_rollup = await _load_rollup_window_summary(
        db,
        start_date=window_start,
        end_date=window_end,
    )
    current_funnel = await _load_funnel_window_summary(
        db,
        start_at=window_start_at,
        end_at=window_end_at,
    )
    current_summary = _build_window_summary(
        **current_rollup,
        **current_funnel,
    )
    landing_funnel_health = await _get_landing_funnel_health(
        db,
        now=datetime.combine(window_end, datetime.min.time(), tzinfo=timezone.utc),
    )

    return LandingCampaignMetricsResponse(
        window_start=window_start,
        window_end=window_end,
        days=days,
        total_events=current_summary.total_events,
        total_onboarded_tenants=current_summary.onboarded_tenants,
        total_connected_tenants=current_summary.connected_tenants,
        total_first_value_tenants=current_summary.first_value_tenants,
        total_pql_tenants=current_summary.pql_tenants,
        total_pricing_view_tenants=current_summary.pricing_view_tenants,
        total_checkout_started_tenants=current_summary.checkout_started_tenants,
        total_paid_tenants=current_summary.paid_tenants,
        weekly_current=landing_funnel_health.weekly_current,
        weekly_previous=landing_funnel_health.weekly_previous,
        weekly_delta=landing_funnel_health.weekly_delta,
        funnel_alerts=landing_funnel_health.alerts,
        items=items,
    )
