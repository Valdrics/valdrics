from __future__ import annotations

from contextlib import asynccontextmanager, nullcontext
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.tasks.scheduler_funnel_ops import refresh_landing_funnel_health_logic
from app.tasks import scheduler_tasks as st


@asynccontextmanager
async def _db_cm(db: AsyncMock):
    yield db


@pytest.mark.asyncio
async def test_refresh_landing_funnel_health_logic_records_metrics_and_logs() -> None:
    db = AsyncMock()
    now = datetime(2026, 3, 10, 10, 0, tzinfo=timezone.utc)
    health = SimpleNamespace(
        weekly_current=SimpleNamespace(
            signup_to_connection_rate=0.5,
            connection_to_first_value_rate=0.75,
            onboarded_tenants=4,
            connected_tenants=2,
            first_value_tenants=1,
        ),
        alerts=[
            SimpleNamespace(key="signup_to_connection", status="critical"),
            SimpleNamespace(key="connection_to_first_value", status="watch"),
        ],
    )
    mock_datetime = MagicMock()
    mock_datetime.now.return_value = now
    logger = MagicMock()

    with (
        patch(
            "app.modules.governance.api.v1.landing_funnel_health_ops.get_landing_funnel_health",
            new=AsyncMock(return_value=health),
        ) as mock_health,
        patch(
            "app.modules.governance.api.v1.landing_funnel_health_ops.record_landing_funnel_health_metrics"
        ) as mock_record,
    ):
        await refresh_landing_funnel_health_logic(
            open_db_session_fn=lambda: _db_cm(db),
            scheduler_span_fn=lambda *args, **kwargs: nullcontext(),
            logger=logger,
            datetime_cls=mock_datetime,
            timezone_obj=timezone,
        )

    mock_health.assert_awaited_once_with(db, now=now)
    mock_record.assert_called_once_with(health, evaluated_at=now)
    logger.info.assert_called_once_with(
        "landing_funnel_health_metrics_refreshed",
        signup_to_connection_rate=0.5,
        connection_to_first_value_rate=0.75,
        critical_alerts=["signup_to_connection"],
        watch_alerts=["connection_to_first_value"],
        onboarded_tenants=4,
        connected_tenants=2,
        first_value_tenants=1,
    )


@pytest.mark.asyncio
async def test_refresh_landing_funnel_health_task_records_success_metrics() -> None:
    with (
        patch(
            "app.tasks.scheduler_tasks._refresh_landing_funnel_health_logic_impl",
            new=AsyncMock(),
        ) as mock_impl,
        patch("app.tasks.scheduler_tasks.SCHEDULER_JOB_RUNS") as mock_runs,
        patch("app.tasks.scheduler_tasks.SCHEDULER_JOB_DURATION") as mock_duration,
    ):
        await st._refresh_landing_funnel_health_logic()

    mock_impl.assert_awaited_once()
    mock_runs.labels.assert_any_call(
        job_name="landing_funnel_health_refresh",
        status="success",
    )
    mock_duration.labels.return_value.observe.assert_called_once()


@pytest.mark.asyncio
async def test_refresh_landing_funnel_health_task_records_failure_and_raises() -> None:
    with (
        patch(
            "app.tasks.scheduler_tasks._refresh_landing_funnel_health_logic_impl",
            new=AsyncMock(side_effect=RuntimeError("db unavailable")),
        ),
        patch("app.tasks.scheduler_tasks.SCHEDULER_JOB_RUNS") as mock_runs,
        patch("app.tasks.scheduler_tasks.SCHEDULER_JOB_DURATION") as mock_duration,
        patch("app.tasks.scheduler_tasks.logger") as mock_logger,
    ):
        with pytest.raises(RuntimeError, match="db unavailable"):
            await st._refresh_landing_funnel_health_logic()

    mock_runs.labels.assert_any_call(
        job_name="landing_funnel_health_refresh",
        status="failure",
    )
    mock_duration.labels.return_value.observe.assert_called_once()
    mock_logger.error.assert_called_once_with(
        "landing_funnel_health_refresh_failed",
        error="db unavailable",
        error_type="RuntimeError",
    )
