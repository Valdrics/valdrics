"""Shared landing funnel health calculations for internal analytics and health dashboards."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.landing_telemetry_rollup import LandingTelemetryDailyRollup
from app.models.tenant_growth_funnel_snapshot import TenantGrowthFunnelSnapshot
from app.modules.governance.api.v1.health_dashboard_models import (
    LandingFunnelHealth,
    LandingFunnelHealthAlert,
    LandingFunnelWeeklyDelta,
    LandingFunnelWindowSummary,
)
from app.shared.core.ops_metrics import record_landing_funnel_health_snapshot

SIGNUP_TO_CONNECTION_MIN_RATE = 0.35
CONNECTION_TO_FIRST_VALUE_MIN_RATE = 0.40
FUNNEL_RATE_WATCH_DELTA = -0.10


def window_stage_count(column: Any, start_at: datetime, end_at: datetime) -> Any:
    return func.sum(
        case(
            (and_(column.is_not(None), column >= start_at, column < end_at), 1),
            else_=0,
        )
    )


def safe_rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return numerator / denominator


def build_window_summary(
    *,
    total_events: int = 0,
    cta_events: int = 0,
    signup_intent_events: int = 0,
    onboarded_tenants: int = 0,
    connected_tenants: int = 0,
    first_value_tenants: int = 0,
    pql_tenants: int = 0,
    pricing_view_tenants: int = 0,
    checkout_started_tenants: int = 0,
    paid_tenants: int = 0,
) -> LandingFunnelWindowSummary:
    return LandingFunnelWindowSummary(
        total_events=total_events,
        cta_events=cta_events,
        signup_intent_events=signup_intent_events,
        onboarded_tenants=onboarded_tenants,
        connected_tenants=connected_tenants,
        first_value_tenants=first_value_tenants,
        pql_tenants=pql_tenants,
        pricing_view_tenants=pricing_view_tenants,
        checkout_started_tenants=checkout_started_tenants,
        paid_tenants=paid_tenants,
        signup_to_connection_rate=safe_rate(connected_tenants, onboarded_tenants),
        connection_to_first_value_rate=safe_rate(first_value_tenants, connected_tenants),
    )


def build_weekly_delta(
    current: LandingFunnelWindowSummary,
    previous: LandingFunnelWindowSummary,
) -> LandingFunnelWeeklyDelta:
    return LandingFunnelWeeklyDelta(
        total_events=current.total_events - previous.total_events,
        signup_intent_events=current.signup_intent_events - previous.signup_intent_events,
        onboarded_tenants=current.onboarded_tenants - previous.onboarded_tenants,
        connected_tenants=current.connected_tenants - previous.connected_tenants,
        first_value_tenants=current.first_value_tenants - previous.first_value_tenants,
        pql_tenants=current.pql_tenants - previous.pql_tenants,
        pricing_view_tenants=current.pricing_view_tenants - previous.pricing_view_tenants,
        checkout_started_tenants=current.checkout_started_tenants - previous.checkout_started_tenants,
        paid_tenants=current.paid_tenants - previous.paid_tenants,
        signup_to_connection_rate=None
        if current.signup_to_connection_rate is None or previous.signup_to_connection_rate is None
        else current.signup_to_connection_rate - previous.signup_to_connection_rate,
        connection_to_first_value_rate=None
        if current.connection_to_first_value_rate is None
        or previous.connection_to_first_value_rate is None
        else current.connection_to_first_value_rate - previous.connection_to_first_value_rate,
    )


def build_funnel_health_alert(
    *,
    key: str,
    label: str,
    threshold_rate: float,
    current_rate: float | None,
    previous_rate: float | None,
    current_numerator: int,
    current_denominator: int,
) -> LandingFunnelHealthAlert:
    weekly_delta = None
    if current_rate is not None and previous_rate is not None:
        weekly_delta = current_rate - previous_rate

    status: Literal["healthy", "watch", "critical", "insufficient_data"]
    if current_rate is None:
        status = "insufficient_data"
        message = "Not enough weekly volume to evaluate this funnel step."
    elif current_rate < threshold_rate:
        status = "critical"
        message = f"Current weekly conversion is below the {threshold_rate:.0%} operating floor."
    elif weekly_delta is not None and weekly_delta <= FUNNEL_RATE_WATCH_DELTA:
        status = "watch"
        message = "Conversion stayed above floor but deteriorated sharply versus the prior week."
    else:
        status = "healthy"
        message = "Weekly conversion is within the expected operating band."

    return LandingFunnelHealthAlert(
        key=key,
        label=label,
        status=status,
        threshold_rate=threshold_rate,
        current_rate=current_rate,
        previous_rate=previous_rate,
        weekly_delta=weekly_delta,
        current_numerator=current_numerator,
        current_denominator=current_denominator,
        message=message,
    )


async def load_rollup_window_summary(
    db: AsyncSession,
    *,
    start_date: date,
    end_date: date,
) -> dict[str, int]:
    row = (
        await db.execute(
            select(
                func.sum(LandingTelemetryDailyRollup.event_count).label("total_events"),
                func.sum(
                    case(
                        (
                            LandingTelemetryDailyRollup.funnel_stage == "cta",
                            LandingTelemetryDailyRollup.event_count,
                        ),
                        else_=0,
                    )
                ).label("cta_events"),
                func.sum(
                    case(
                        (
                            LandingTelemetryDailyRollup.funnel_stage == "signup_intent",
                            LandingTelemetryDailyRollup.event_count,
                        ),
                        else_=0,
                    )
                ).label("signup_intent_events"),
            )
            .where(LandingTelemetryDailyRollup.event_date >= start_date)
            .where(LandingTelemetryDailyRollup.event_date <= end_date)
        )
    ).one()
    return {
        "total_events": int(row.total_events or 0),
        "cta_events": int(row.cta_events or 0),
        "signup_intent_events": int(row.signup_intent_events or 0),
    }


async def load_funnel_window_summary(
    db: AsyncSession,
    *,
    start_at: datetime,
    end_at: datetime,
) -> dict[str, int]:
    row = (
        await db.execute(
            select(
                window_stage_count(
                    TenantGrowthFunnelSnapshot.tenant_onboarded_at,
                    start_at,
                    end_at,
                ).label("onboarded_tenants"),
                window_stage_count(
                    TenantGrowthFunnelSnapshot.first_connection_verified_at,
                    start_at,
                    end_at,
                ).label("connected_tenants"),
                window_stage_count(
                    TenantGrowthFunnelSnapshot.first_value_activated_at,
                    start_at,
                    end_at,
                ).label("first_value_tenants"),
                window_stage_count(
                    TenantGrowthFunnelSnapshot.pql_qualified_at,
                    start_at,
                    end_at,
                ).label("pql_tenants"),
                window_stage_count(
                    TenantGrowthFunnelSnapshot.pricing_viewed_at,
                    start_at,
                    end_at,
                ).label("pricing_view_tenants"),
                window_stage_count(
                    TenantGrowthFunnelSnapshot.checkout_started_at,
                    start_at,
                    end_at,
                ).label("checkout_started_tenants"),
                window_stage_count(
                    TenantGrowthFunnelSnapshot.paid_activated_at,
                    start_at,
                    end_at,
                ).label("paid_tenants"),
            ).where(TenantGrowthFunnelSnapshot.created_at < end_at)
        )
    ).one()
    return {
        "onboarded_tenants": int(row.onboarded_tenants or 0),
        "connected_tenants": int(row.connected_tenants or 0),
        "first_value_tenants": int(row.first_value_tenants or 0),
        "pql_tenants": int(row.pql_tenants or 0),
        "pricing_view_tenants": int(row.pricing_view_tenants or 0),
        "checkout_started_tenants": int(row.checkout_started_tenants or 0),
        "paid_tenants": int(row.paid_tenants or 0),
    }


async def get_landing_funnel_health(
    db: AsyncSession,
    *,
    now: datetime,
) -> LandingFunnelHealth:
    weekly_current_end = now.date()
    weekly_current_start = weekly_current_end - timedelta(days=6)
    weekly_previous_end = weekly_current_start - timedelta(days=1)
    weekly_previous_start = weekly_previous_end - timedelta(days=6)

    weekly_current_start_at = datetime.combine(
        weekly_current_start,
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    weekly_current_end_at = datetime.combine(
        weekly_current_end + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    weekly_previous_start_at = datetime.combine(
        weekly_previous_start,
        datetime.min.time(),
        tzinfo=timezone.utc,
    )
    weekly_previous_end_at = datetime.combine(
        weekly_previous_end + timedelta(days=1),
        datetime.min.time(),
        tzinfo=timezone.utc,
    )

    weekly_current_rollup = await load_rollup_window_summary(
        db,
        start_date=weekly_current_start,
        end_date=weekly_current_end,
    )
    weekly_previous_rollup = await load_rollup_window_summary(
        db,
        start_date=weekly_previous_start,
        end_date=weekly_previous_end,
    )
    weekly_current_funnel = await load_funnel_window_summary(
        db,
        start_at=weekly_current_start_at,
        end_at=weekly_current_end_at,
    )
    weekly_previous_funnel = await load_funnel_window_summary(
        db,
        start_at=weekly_previous_start_at,
        end_at=weekly_previous_end_at,
    )

    weekly_current = build_window_summary(**weekly_current_rollup, **weekly_current_funnel)
    weekly_previous = build_window_summary(
        **weekly_previous_rollup,
        **weekly_previous_funnel,
    )
    weekly_delta = build_weekly_delta(weekly_current, weekly_previous)
    alerts = [
        build_funnel_health_alert(
            key="signup_to_connection",
            label="Signup -> connection",
            threshold_rate=SIGNUP_TO_CONNECTION_MIN_RATE,
            current_rate=weekly_current.signup_to_connection_rate,
            previous_rate=weekly_previous.signup_to_connection_rate,
            current_numerator=weekly_current.connected_tenants,
            current_denominator=weekly_current.onboarded_tenants,
        ),
        build_funnel_health_alert(
            key="connection_to_first_value",
            label="Connection -> first value",
            threshold_rate=CONNECTION_TO_FIRST_VALUE_MIN_RATE,
            current_rate=weekly_current.connection_to_first_value_rate,
            previous_rate=weekly_previous.connection_to_first_value_rate,
            current_numerator=weekly_current.first_value_tenants,
            current_denominator=weekly_current.connected_tenants,
        ),
    ]
    return LandingFunnelHealth(
        weekly_current=weekly_current,
        weekly_previous=weekly_previous,
        weekly_delta=weekly_delta,
        alerts=alerts,
    )


def record_landing_funnel_health_metrics(
    health: LandingFunnelHealth,
    *,
    evaluated_at: datetime,
) -> None:
    record_landing_funnel_health_snapshot(
        evaluated_at=evaluated_at,
        alerts=health.alerts,
    )
