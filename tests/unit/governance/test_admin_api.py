import pytest
from fastapi import Request, HTTPException
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone
from app.modules.governance.api.v1.admin import (
    validate_admin_key,
    trigger_analysis,
    reconcile_tenant_costs,
    get_landing_campaign_metrics,
)
from app.models.landing_telemetry_rollup import LandingTelemetryDailyRollup


@pytest.mark.asyncio
async def test_validate_admin_key_missing():
    request = MagicMock(spec=Request)
    # Mock settings with no key
    with patch("app.modules.governance.api.v1.admin.get_settings") as mock_settings:
        mock_settings.return_value.ADMIN_API_KEY = None

        with pytest.raises(HTTPException) as exc:
            await validate_admin_key(request, x_admin_key="anything")
        assert exc.value.status_code == 503


@pytest.mark.asyncio
async def test_validate_admin_key_weak_prod():
    request = MagicMock(spec=Request)
    with patch("app.modules.governance.api.v1.admin.get_settings") as mock_settings:
        mock_settings.return_value.ADMIN_API_KEY = "weak"
        mock_settings.return_value.ENVIRONMENT = "production"

        with pytest.raises(HTTPException) as exc:
            await validate_admin_key(request, x_admin_key="weak")
        assert exc.value.status_code == 500


@pytest.mark.asyncio
async def test_validate_admin_key_invalid():
    request = MagicMock(spec=Request)
    request.url.path = "/admin"
    request.client.host = "1.2.3.4"

    with patch("app.modules.governance.api.v1.admin.get_settings") as mock_settings:
        mock_settings.return_value.ADMIN_API_KEY = (
            "strong-key-for-testing-purposes-only"
        )
        mock_settings.return_value.ENVIRONMENT = "production"

        with pytest.raises(HTTPException) as exc:
            await validate_admin_key(request, x_admin_key="wrong-key")
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_validate_admin_key_success():
    request = MagicMock(spec=Request)
    with patch("app.modules.governance.api.v1.admin.get_settings") as mock_settings:
        mock_settings.return_value.ADMIN_API_KEY = (
            "strong-key-for-testing-purposes-only"
        )

        result = await validate_admin_key(
            request, x_admin_key="strong-key-for-testing-purposes-only"
        )
        assert result is True


@pytest.mark.asyncio
async def test_trigger_analysis_success():
    request = MagicMock(spec=Request)
    request.app.state.scheduler.daily_analysis_job = AsyncMock()

    resp = await trigger_analysis(request, True)
    assert resp["status"] == "triggered"
    request.app.state.scheduler.daily_analysis_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_reconcile_tenant_costs_success(db):
    request = MagicMock(spec=Request)
    tenant_id = "123e4567-e89b-12d3-a456-426614174000"
    start_date = "2023-01-01"
    end_date = "2023-01-31"

    with patch(
        "app.modules.reporting.domain.reconciliation.CostReconciliationService"
    ) as MockService:
        service = MockService.return_value
        service.compare_explorer_vs_cur = AsyncMock(return_value={"diff": 0})

        from uuid import UUID
        from datetime import date

        result = await reconcile_tenant_costs(
            request,
            UUID(tenant_id),
            date.fromisoformat(start_date),
            date.fromisoformat(end_date),
            db,
            True,
        )
        assert result["diff"] == 0


@pytest.mark.asyncio
async def test_get_landing_campaign_metrics_aggregates_by_campaign(db):
    request = MagicMock(spec=Request)
    now = datetime.now(timezone.utc)
    today = now.date()

    db.add_all(
        [
            LandingTelemetryDailyRollup(
                event_date=today,
                event_name="landing_view",
                section="landing",
                funnel_stage="view",
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="launch",
                event_count=11,
                first_seen_at=now,
                last_seen_at=now,
            ),
            LandingTelemetryDailyRollup(
                event_date=today,
                event_name="cta_click",
                section="hero",
                funnel_stage="cta",
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="launch",
                event_count=7,
                first_seen_at=now,
                last_seen_at=now,
            ),
            LandingTelemetryDailyRollup(
                event_date=today,
                event_name="signup_intent",
                section="hero",
                funnel_stage="signup_intent",
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="launch",
                event_count=2,
                first_seen_at=now,
                last_seen_at=now,
            ),
            LandingTelemetryDailyRollup(
                event_date=today,
                event_name="landing_view",
                section="landing",
                funnel_stage="view",
                utm_source="linkedin",
                utm_medium="paid_social",
                utm_campaign="retarget",
                event_count=3,
                first_seen_at=now,
                last_seen_at=now,
            ),
        ]
    )
    await db.commit()

    result = await get_landing_campaign_metrics(
        request=request,
        days=30,
        limit=10,
        db=db,
        user=MagicMock(),
    )

    assert result.total_events == 23
    assert len(result.items) == 2
    assert result.items[0].utm_campaign == "launch"
    assert result.items[0].total_events == 20
    assert result.items[0].cta_events == 7
    assert result.items[0].signup_intent_events == 2
