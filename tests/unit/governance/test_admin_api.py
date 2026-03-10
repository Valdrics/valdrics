import pytest
import pytest_asyncio
from fastapi import Request, HTTPException
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool
from app.modules.governance.api.v1.admin import (
    _resolve_admin_audit_tenant_id,
    validate_admin_key,
    trigger_analysis,
    reconcile_tenant_costs,
    get_landing_campaign_metrics,
)
from app.models.landing_telemetry_rollup import LandingTelemetryDailyRollup
from app.models.tenant import Tenant
from app.models.tenant_growth_funnel_snapshot import TenantGrowthFunnelSnapshot
from app.shared.core.pricing import PricingTier


@pytest_asyncio.fixture
async def campaign_db() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Tenant.__table__.create)
        await conn.run_sync(LandingTelemetryDailyRollup.__table__.create)
        await conn.run_sync(TenantGrowthFunnelSnapshot.__table__.create)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
    await engine.dispose()


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
    request.method = "POST"
    request.client.host = "1.2.3.4"

    with (
        patch("app.modules.governance.api.v1.admin.get_settings") as mock_settings,
        patch(
            "app.modules.governance.api.v1.admin.audit_log_async",
            new_callable=AsyncMock,
        ),
    ):
        mock_settings.return_value.ADMIN_API_KEY = (
            "strong-key-for-testing-purposes-only"
        )
        mock_settings.return_value.ENVIRONMENT = "production"

        with pytest.raises(HTTPException) as exc:
            await validate_admin_key(request, x_admin_key="wrong-key")
        assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_validate_admin_key_invalid_persists_tenant_scoped_audit():
    request = MagicMock(spec=Request)
    request.url.path = "/admin/reconcile/123e4567-e89b-12d3-a456-426614174000"
    request.method = "POST"
    request.client.host = "1.2.3.4"
    request.path_params = {"tenant_id": "123e4567-e89b-12d3-a456-426614174000"}
    request.state.tenant_id = None

    with (
        patch("app.modules.governance.api.v1.admin.get_settings") as mock_settings,
        patch(
            "app.modules.governance.api.v1.admin.audit_log_async",
            new_callable=AsyncMock,
        ) as mock_audit_async,
    ):
        mock_settings.return_value.ADMIN_API_KEY = (
            "strong-key-for-testing-purposes-only"
        )
        mock_settings.return_value.ENVIRONMENT = "production"

        with pytest.raises(HTTPException) as exc:
            await validate_admin_key(request, x_admin_key="wrong-key")

    assert exc.value.status_code == 403
    mock_audit_async.assert_awaited_once()
    assert mock_audit_async.await_args.args[:3] == (
        "admin_auth_failed",
        "admin_portal",
        "123e4567-e89b-12d3-a456-426614174000",
    )
    assert mock_audit_async.await_args.kwargs["isolated"] is True
    assert mock_audit_async.await_args.kwargs["db"] is None


@pytest.mark.asyncio
async def test_validate_admin_key_invalid_persists_system_scope_audit_when_tenant_unknown():
    request = MagicMock(spec=Request)
    request.url.path = "/admin"
    request.method = "POST"
    request.client.host = "1.2.3.4"
    request.path_params = {}
    request.state.tenant_id = None

    with (
        patch("app.modules.governance.api.v1.admin.get_settings") as mock_settings,
        patch(
            "app.modules.governance.api.v1.admin.audit_log_async",
            new_callable=AsyncMock,
        ) as mock_audit_async,
    ):
        mock_settings.return_value.ADMIN_API_KEY = (
            "strong-key-for-testing-purposes-only"
        )
        mock_settings.return_value.ENVIRONMENT = "production"

        with pytest.raises(HTTPException) as exc:
            await validate_admin_key(request, x_admin_key="wrong-key")

    assert exc.value.status_code == 403
    mock_audit_async.assert_awaited_once()
    assert mock_audit_async.await_args.args[:3] == (
        "admin_auth_failed",
        "admin_portal",
        None,
    )
    assert mock_audit_async.await_args.kwargs["isolated"] is True
    assert mock_audit_async.await_args.kwargs["db"] is None


def test_resolve_admin_audit_tenant_id_prefers_request_context() -> None:
    request = MagicMock(spec=Request)
    request.state.tenant_id = "d290f1ee-6c54-4b01-90e6-d701748f0851"
    request.path_params = {"tenant_id": "123e4567-e89b-12d3-a456-426614174000"}

    assert _resolve_admin_audit_tenant_id(request) == (
        "d290f1ee-6c54-4b01-90e6-d701748f0851"
    )


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
async def test_reconcile_tenant_costs_success():
    request = MagicMock(spec=Request)
    tenant_id = "123e4567-e89b-12d3-a456-426614174000"
    start_date = "2023-01-01"
    end_date = "2023-01-31"
    db = MagicMock()

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
async def test_get_landing_campaign_metrics_aggregates_by_campaign(campaign_db: AsyncSession):
    request = MagicMock(spec=Request)
    now = datetime.now(timezone.utc)
    today = now.date()

    campaign_db.add_all(
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
    await campaign_db.commit()

    result = await get_landing_campaign_metrics(
        request=request,
        days=30,
        limit=10,
        db=campaign_db,
        user=MagicMock(),
    )

    assert result.total_events == 23
    assert len(result.items) == 2
    assert result.items[0].utm_campaign == "launch"
    assert result.items[0].total_events == 20
    assert result.items[0].cta_events == 7
    assert result.items[0].signup_intent_events == 2
    assert result.weekly_current.total_events == 23
    assert result.weekly_previous.total_events == 0
    assert result.weekly_delta.total_events == 23
    assert result.funnel_alerts[0].status == "insufficient_data"
    assert result.funnel_alerts[1].status == "insufficient_data"


@pytest.mark.asyncio
async def test_get_landing_campaign_metrics_merges_authenticated_funnel_progress(
    campaign_db: AsyncSession,
):
    request = MagicMock(spec=Request)
    now = datetime.now(timezone.utc)
    today = now.date()

    launch_tenant = Tenant(id=uuid4(), name="Launch Co", plan=PricingTier.GROWTH.value)
    direct_tenant = Tenant(id=uuid4(), name="Direct Co", plan=PricingTier.PRO.value)
    campaign_db.add_all([launch_tenant, direct_tenant])
    campaign_db.add(
        LandingTelemetryDailyRollup(
            event_date=today,
            event_name="landing_view",
            section="landing",
            funnel_stage="view",
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="launch",
            event_count=5,
            first_seen_at=now,
            last_seen_at=now,
        )
    )
    campaign_db.add_all(
        [
            TenantGrowthFunnelSnapshot(
                tenant_id=launch_tenant.id,
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="launch",
                current_tier=PricingTier.GROWTH.value,
                tenant_onboarded_at=now - timedelta(hours=5),
                first_connection_verified_at=now - timedelta(hours=4),
                first_value_activated_at=now - timedelta(hours=3),
                pql_qualified_at=now - timedelta(hours=3),
                pricing_viewed_at=now - timedelta(hours=2),
                checkout_started_at=now - timedelta(hours=1),
                paid_activated_at=now - timedelta(minutes=30),
                created_at=now - timedelta(hours=5),
                updated_at=now - timedelta(minutes=30),
            ),
            TenantGrowthFunnelSnapshot(
                tenant_id=direct_tenant.id,
                current_tier=PricingTier.STARTER.value,
                tenant_onboarded_at=now - timedelta(hours=2),
                created_at=now - timedelta(hours=2),
                updated_at=now - timedelta(hours=2),
            ),
        ]
    )
    await campaign_db.commit()

    result = await get_landing_campaign_metrics(
        request=request,
        days=30,
        limit=10,
        db=campaign_db,
        user=MagicMock(),
    )

    assert result.total_events == 5
    assert result.total_onboarded_tenants == 2
    assert result.total_connected_tenants == 1
    assert result.total_first_value_tenants == 1
    assert result.total_pql_tenants == 1
    assert result.total_pricing_view_tenants == 1
    assert result.total_checkout_started_tenants == 1
    assert result.total_paid_tenants == 1
    assert result.weekly_current.onboarded_tenants == 2
    assert result.weekly_current.connected_tenants == 1
    assert result.weekly_current.first_value_tenants == 1
    assert result.weekly_current.signup_to_connection_rate == 0.5
    assert result.weekly_current.connection_to_first_value_rate == 1.0
    assert result.weekly_delta.paid_tenants == 1
    assert result.funnel_alerts[0].key == "signup_to_connection"
    assert result.funnel_alerts[0].status == "healthy"
    assert result.funnel_alerts[1].key == "connection_to_first_value"
    assert result.funnel_alerts[1].status == "healthy"

    by_campaign = {
        (item.utm_source, item.utm_medium, item.utm_campaign): item for item in result.items
    }
    launch = by_campaign[("google", "cpc", "launch")]
    assert launch.total_events == 5
    assert launch.onboarded_tenants == 1
    assert launch.connected_tenants == 1
    assert launch.first_value_tenants == 1
    assert launch.pql_tenants == 1
    assert launch.pricing_view_tenants == 1
    assert launch.checkout_started_tenants == 1
    assert launch.paid_tenants == 1

    direct = by_campaign[("direct", "direct", "direct")]
    assert direct.total_events == 0
    assert direct.onboarded_tenants == 1
    assert direct.connected_tenants == 0


@pytest.mark.asyncio
async def test_get_landing_campaign_metrics_flags_critical_funnel_dropoffs(
    campaign_db: AsyncSession,
):
    request = MagicMock(spec=Request)
    now = datetime.now(timezone.utc)

    current_tenants = [
        Tenant(id=uuid4(), name=f"Current {index}", plan=PricingTier.STARTER.value)
        for index in range(4)
    ]
    previous_tenants = [
        Tenant(id=uuid4(), name=f"Previous {index}", plan=PricingTier.STARTER.value)
        for index in range(4)
    ]
    campaign_db.add_all([*current_tenants, *previous_tenants])
    campaign_db.add_all(
        [
            TenantGrowthFunnelSnapshot(
                tenant_id=current_tenants[0].id,
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="launch",
                current_tier=PricingTier.STARTER.value,
                tenant_onboarded_at=now - timedelta(days=1),
                first_connection_verified_at=now - timedelta(days=1),
                created_at=now - timedelta(days=1),
                updated_at=now - timedelta(days=1),
            ),
            TenantGrowthFunnelSnapshot(
                tenant_id=current_tenants[1].id,
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="launch",
                current_tier=PricingTier.STARTER.value,
                tenant_onboarded_at=now - timedelta(days=2),
                created_at=now - timedelta(days=2),
                updated_at=now - timedelta(days=2),
            ),
            TenantGrowthFunnelSnapshot(
                tenant_id=current_tenants[2].id,
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="launch",
                current_tier=PricingTier.STARTER.value,
                tenant_onboarded_at=now - timedelta(days=3),
                created_at=now - timedelta(days=3),
                updated_at=now - timedelta(days=3),
            ),
            TenantGrowthFunnelSnapshot(
                tenant_id=current_tenants[3].id,
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="launch",
                current_tier=PricingTier.STARTER.value,
                tenant_onboarded_at=now - timedelta(days=4),
                created_at=now - timedelta(days=4),
                updated_at=now - timedelta(days=4),
            ),
            TenantGrowthFunnelSnapshot(
                tenant_id=previous_tenants[0].id,
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="launch",
                current_tier=PricingTier.STARTER.value,
                tenant_onboarded_at=now - timedelta(days=8),
                first_connection_verified_at=now - timedelta(days=8),
                first_value_activated_at=now - timedelta(days=8),
                created_at=now - timedelta(days=8),
                updated_at=now - timedelta(days=8),
            ),
            TenantGrowthFunnelSnapshot(
                tenant_id=previous_tenants[1].id,
                utm_source="google",
                utm_medium="cpc",
                utm_campaign="launch",
                current_tier=PricingTier.STARTER.value,
                tenant_onboarded_at=now - timedelta(days=9),
                first_connection_verified_at=now - timedelta(days=9),
                first_value_activated_at=now - timedelta(days=9),
                created_at=now - timedelta(days=9),
                updated_at=now - timedelta(days=9),
            ),
        ]
    )
    await campaign_db.commit()

    result = await get_landing_campaign_metrics(
        request=request,
        days=30,
        limit=10,
        db=campaign_db,
        user=MagicMock(),
    )

    assert result.weekly_current.onboarded_tenants == 4
    assert result.weekly_current.connected_tenants == 1
    assert result.weekly_current.first_value_tenants == 0
    assert result.weekly_current.signup_to_connection_rate == 0.25
    assert result.weekly_current.connection_to_first_value_rate == 0.0
    assert result.weekly_previous.onboarded_tenants == 2
    assert result.weekly_previous.connected_tenants == 2
    assert result.weekly_previous.first_value_tenants == 2
    assert result.funnel_alerts[0].status == "critical"
    assert result.funnel_alerts[1].status == "critical"
