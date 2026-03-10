from __future__ import annotations

from typing import Any, Callable


async def refresh_landing_funnel_health_logic(
    *,
    open_db_session_fn: Callable[[], Any],
    scheduler_span_fn: Callable[..., Any],
    logger: Any,
    datetime_cls: Any,
    timezone_obj: Any,
) -> None:
    from app.modules.governance.api.v1.landing_funnel_health_ops import (
        get_landing_funnel_health,
        record_landing_funnel_health_metrics,
    )

    job_name = "landing_funnel_health_refresh"
    with scheduler_span_fn(
        "scheduler.refresh_landing_funnel_health",
        job_name=job_name,
    ):
        async with open_db_session_fn() as db:
            now = datetime_cls.now(timezone_obj.utc)
            health = await get_landing_funnel_health(db, now=now)
            record_landing_funnel_health_metrics(health, evaluated_at=now)

            critical_alerts = [
                alert.key for alert in health.alerts if str(alert.status) == "critical"
            ]
            watch_alerts = [
                alert.key for alert in health.alerts if str(alert.status) == "watch"
            ]
            logger.info(
                "landing_funnel_health_metrics_refreshed",
                signup_to_connection_rate=health.weekly_current.signup_to_connection_rate,
                connection_to_first_value_rate=health.weekly_current.connection_to_first_value_rate,
                critical_alerts=critical_alerts,
                watch_alerts=watch_alerts,
                onboarded_tenants=health.weekly_current.onboarded_tenants,
                connected_tenants=health.weekly_current.connected_tenants,
                first_value_tenants=health.weekly_current.first_value_tenants,
            )
