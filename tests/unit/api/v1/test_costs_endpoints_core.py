import inspect
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.params import Depends
from httpx import AsyncClient

from app.models.attribution import CostAllocation
from app.models.cloud import CloudAccount, CostRecord
from app.models.llm import LLMUsage
from app.models.tenant import Tenant
from app.modules.reporting.api.v1 import costs as costs_api
from app.modules.reporting.api.v1 import costs_core_endpoints, costs_http_routes_core
from app.shared.core.auth import (
    CurrentUser,
    UserRole,
    get_current_user,
    get_current_user_with_db_context,
    requires_role_with_db_context,
)
from app.shared.core.pricing import PricingTier


def _override_reporting_auth(app: object, mock_user: CurrentUser) -> None:
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_current_user_with_db_context] = lambda: mock_user


def _clear_reporting_auth_overrides(app: object) -> None:
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_current_user_with_db_context, None)


def _dependency_for(function: object, parameter_name: str) -> object:
    default = inspect.signature(function).parameters[parameter_name].default
    assert isinstance(default, Depends)
    return default.dependency


def test_cost_routes_bind_db_context_dependencies() -> None:
    assert (
        _dependency_for(costs_http_routes_core.get_costs, "current_user")
        is get_current_user_with_db_context
    )
    assert (
        _dependency_for(costs_http_routes_core.get_cost_breakdown, "current_user")
        is get_current_user_with_db_context
    )
    assert (
        _dependency_for(costs_http_routes_core.get_canonical_quality, "current_user")
        is get_current_user_with_db_context
    )
    assert (
        _dependency_for(costs_http_routes_core.get_cost_forecast, "current_user")
        is get_current_user_with_db_context
    )
    assert (
        _dependency_for(costs_http_routes_core.trigger_ingest, "current_user")
        is requires_role_with_db_context("admin")
    )
    assert (
        _dependency_for(costs_core_endpoints.get_costs, "current_user")
        is get_current_user_with_db_context
    )


@pytest.mark.asyncio
async def test_get_costs_root_delegates_to_get_costs_wrapper() -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="root-costs@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )
    response = MagicMock()
    db = AsyncMock()
    payload = {"total_cost": 12.34}

    with patch.object(costs_api, "get_costs", new=AsyncMock(return_value=payload)) as mock_get_costs:
        out = await costs_api.get_costs_root(
            response=response,
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            provider="aws",
            db=db,
            current_user=user,
        )

    assert out == payload
    mock_get_costs.assert_awaited_once_with(
        response=response,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        provider="aws",
        db=db,
        current_user=user,
    )


@pytest.mark.asyncio
async def test_get_costs_and_breakdown(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="costs@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )

    _override_reporting_auth(app, mock_user)
    try:
        with (
            patch(
                "app.modules.reporting.api.v1.costs.CostAggregator.get_dashboard_summary",
                new=AsyncMock(),
            ) as mock_summary,
            patch(
                "app.modules.reporting.api.v1.costs.CostAggregator.get_basic_breakdown",
                new=AsyncMock(),
            ) as mock_breakdown,
        ):
            mock_summary.return_value = {"total_cost": 123.45}
            mock_breakdown.return_value = {"services": []}

            response = await async_client.get(
                "/api/v1/costs",
                params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
            )
            assert response.status_code == 200
            assert response.json()["total_cost"] == 123.45

            response = await async_client.get(
                "/api/v1/costs/breakdown",
                params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
            )
            assert response.status_code == 200
            assert response.json()["services"] == []
    finally:
        _clear_reporting_auth_overrides(app)


@pytest.mark.asyncio
async def test_get_cost_attribution_summary(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="allocation@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.GROWTH,
    )

    _override_reporting_auth(app, mock_user)
    try:
        with patch(
            "app.modules.reporting.domain.attribution_engine.AttributionEngine.get_allocation_summary",
            new=AsyncMock(),
        ) as mock_summary:
            mock_summary.return_value = {
                "buckets": [
                    {"name": "Platform", "total_amount": 123.45, "record_count": 2}
                ],
                "total": 123.45,
            }

            response = await async_client.get(
                "/api/v1/costs/attribution/summary",
                params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["total"] == 123.45
            assert data["buckets"][0]["name"] == "Platform"
            assert mock_summary.await_count == 1
    finally:
        _clear_reporting_auth_overrides(app)


@pytest.mark.asyncio
async def test_get_cost_attribution_coverage(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="coverage@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.GROWTH,
    )

    _override_reporting_auth(app, mock_user)
    try:
        with patch(
            "app.modules.reporting.domain.attribution_engine.AttributionEngine.get_allocation_coverage",
            new=AsyncMock(),
        ) as mock_coverage:
            mock_coverage.return_value = {
                "target_percentage": 90.0,
                "coverage_percentage": 93.5,
                "meets_target": True,
                "status": "ok",
            }

            response = await async_client.get(
                "/api/v1/costs/attribution/coverage",
                params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["coverage_percentage"] == 93.5
            assert data["meets_target"] is True
            assert mock_coverage.await_count == 1
    finally:
        _clear_reporting_auth_overrides(app)


@pytest.mark.asyncio
async def test_get_spend_ledger_wrapper_preserves_models_and_validates_payloads() -> None:
    tenant_id = uuid.uuid4()
    user = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="ledger-wrapper@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.PRO,
    )
    ledger = costs_api.SpendLedgerResponse(
        start_date="2026-01-01",
        end_date="2026-01-31",
        provider="aws",
        include_preliminary=False,
        limit=100,
        offset=0,
        record_count=0,
        total_cost_usd="0.00000000",
        total_allocated_usd="0.00000000",
        total_unallocated_usd="0.00000000",
        entries=[],
    )

    with patch.object(
        costs_api,
        "get_spend_ledger_impl",
        new=AsyncMock(side_effect=[ledger, ledger.model_dump()]),
    ) as mock_impl:
        first = await costs_api.get_spend_ledger(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            provider="aws",
            db=AsyncMock(),
            current_user=user,
        )
        second = await costs_api.get_spend_ledger(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            provider="aws",
            db=AsyncMock(),
            current_user=user,
        )

    assert first is ledger
    assert second == ledger
    assert mock_impl.await_count == 2
    assert mock_impl.await_args_list[0].kwargs["require_tenant_id"] is (
        costs_api._require_tenant_id
    )
    assert mock_impl.await_args_list[0].kwargs["normalize_provider_filter"] is (
        costs_api._normalize_spend_ledger_provider_filter
    )


@pytest.mark.asyncio
async def test_get_spend_ledger_returns_origin_rows_with_canonical_allocations(
    async_client: AsyncClient,
    app,
    db,
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    account_id = uuid.uuid4()
    record_id = uuid.uuid4()

    db.add(Tenant(id=tenant_id, name="Ledger Tenant", plan=PricingTier.PRO.value))
    db.add(
        CloudAccount(
            id=account_id,
            tenant_id=tenant_id,
            provider="saas",
            name="SaaS Spend",
            is_active=True,
        )
    )
    db.add(
        CostRecord(
            id=record_id,
            tenant_id=tenant_id,
            account_id=account_id,
            service="Slack",
            region="global",
            usage_type="Seats",
            resource_id="workspace-1",
            usage_amount=Decimal("20"),
            usage_unit="Seat",
            cost_usd=Decimal("100.00"),
            amount_raw=Decimal("100.00"),
            currency="USD",
            cost_status="FINAL",
            is_preliminary=False,
            canonical_charge_category="saas",
            canonical_charge_subcategory="subscription",
            canonical_mapping_version="focus-1.3-v1",
            tags={"department": "shared"},
            recorded_at=date(2026, 1, 15),
            timestamp=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
        )
    )
    db.add_all(
        [
            CostAllocation(
                cost_record_id=record_id,
                recorded_at=date(2026, 1, 15),
                allocated_to="Engineering",
                amount=Decimal("60.00"),
                percentage=Decimal("60.00"),
                timestamp=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
            ),
            CostAllocation(
                cost_record_id=record_id,
                recorded_at=date(2026, 1, 15),
                allocated_to="Finance",
                amount=Decimal("40.00"),
                percentage=Decimal("40.00"),
                timestamp=datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc),
            ),
        ]
    )
    await db.commit()

    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="ledger@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.PRO,
    )

    _override_reporting_auth(app, mock_user)
    try:
        response = await async_client.get(
            "/api/v1/costs/ledger",
            params={
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "provider": "saas",
            },
        )
    finally:
        _clear_reporting_auth_overrides(app)

    assert response.status_code == 200
    payload = response.json()
    assert payload["record_count"] == 1
    assert payload["total_cost_usd"] == "100.00000000"
    assert payload["total_allocated_usd"] == "100.00000000"
    assert payload["total_unallocated_usd"] == "0.00000000"
    assert payload["entries"][0]["allocation_status"] == "allocated"
    assert payload["entries"][0]["resource_id"] == "workspace-1"
    assert payload["entries"][0]["usage_amount"] == "20.00000000"
    assert [item["allocated_to"] for item in payload["entries"][0]["allocations"]] == [
        "Engineering",
        "Finance",
    ]


@pytest.mark.asyncio
async def test_get_spend_ledger_includes_ai_usage_provider_filter(
    async_client: AsyncClient,
    app,
    db,
) -> None:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    usage_id = uuid.uuid4()
    db.add(Tenant(id=tenant_id, name="AI Ledger Tenant", plan=PricingTier.PRO.value))
    db.add(
        LLMUsage(
            id=usage_id,
            tenant_id=tenant_id,
            user_id=user_id,
            provider="groq",
            model="llama-3.3-70b-versatile",
            input_tokens=125,
            output_tokens=75,
            total_tokens=200,
            cost_usd=Decimal("0.0042"),
            request_type="daily_analysis",
            operation_id="op-ai-ledger-1",
            is_byok=True,
            created_at=datetime(2026, 1, 16, 9, 30, tzinfo=timezone.utc),
        )
    )
    await db.commit()

    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="ai-ledger@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.PRO,
    )

    _override_reporting_auth(app, mock_user)
    try:
        response = await async_client.get(
            "/api/v1/costs/ledger",
            params={
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "provider": "ai",
            },
        )
    finally:
        _clear_reporting_auth_overrides(app)

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "ai"
    assert payload["record_count"] == 1
    assert payload["total_cost_usd"] == "0.00420000"
    assert payload["total_allocated_usd"] == "0.00000000"
    assert payload["total_unallocated_usd"] == "0.00420000"
    entry = payload["entries"][0]
    assert entry["provider"] == "ai"
    assert entry["account_id"] == "ai:groq"
    assert entry["service"] == "LLM"
    assert entry["usage_type"] == "daily_analysis"
    assert entry["resource_id"] == "op-ai-ledger-1"
    assert entry["usage_amount"] == "200.00000000"
    assert entry["usage_unit"] == "tokens"
    assert entry["canonical_charge_category"] == "ai"
    assert entry["canonical_charge_subcategory"] == "llm_inference"
    assert entry["allocation_status"] == "unallocated"
    assert entry["tags"]["model"] == "llama-3.3-70b-versatile"
    assert entry["tags"]["is_byok"] is True


@pytest.mark.asyncio
async def test_get_canonical_quality_with_alert(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="canonical@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )

    _override_reporting_auth(app, mock_user)
    try:
        with (
            patch(
                "app.modules.reporting.api.v1.costs.CostAggregator.get_canonical_data_quality",
                new=AsyncMock(),
            ) as mock_quality,
            patch(
                "app.modules.reporting.api.v1.costs.NotificationDispatcher.send_alert",
                new=AsyncMock(),
            ) as mock_alert,
        ):
            mock_quality.return_value = {
                "target_percentage": 99.0,
                "total_records": 100,
                "mapped_percentage": 95.0,
                "unmapped_records": 5,
                "meets_target": False,
                "status": "warning",
            }
            response = await async_client.get(
                "/api/v1/costs/canonical/quality",
                params={
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-31",
                    "provider": "saas",
                    "notify_on_breach": "true",
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["status"] == "warning"
            assert payload["alert_triggered"] is True
            assert mock_alert.await_count == 1
    finally:
        _clear_reporting_auth_overrides(app)


@pytest.mark.asyncio
async def test_get_canonical_quality_rejects_invalid_provider(
    async_client: AsyncClient, app
):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="canonical-invalid@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )

    _override_reporting_auth(app, mock_user)
    try:
        response = await async_client.get(
            "/api/v1/costs/canonical/quality",
            params={
                "start_date": "2026-01-01",
                "end_date": "2026-01-31",
                "provider": "oracle",
            },
        )
        assert response.status_code == 400
        assert "unsupported provider" in response.json()["error"].lower()
    finally:
        _clear_reporting_auth_overrides(app)


@pytest.mark.asyncio
async def test_get_cost_forecast_paths(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="forecast@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )

    _override_reporting_auth(app, mock_user)
    try:
        # Insufficient records -> 400
        with patch(
            "app.modules.reporting.api.v1.costs.CostAggregator.get_summary",
            new=AsyncMock(),
        ) as mock_summary:
            mock_summary.return_value = SimpleNamespace(records=[])
            response = await async_client.get(
                "/api/v1/costs/forecast", params={"days": 30}
            )
            assert response.status_code == 400
            assert "Insufficient cost history" in response.json()["error"]

        # Sufficient records -> forecast returned
        with (
            patch(
                "app.modules.reporting.api.v1.costs.CostAggregator.get_summary",
                new=AsyncMock(),
            ) as mock_summary,
            patch(
                "app.shared.analysis.forecaster.SymbolicForecaster.forecast",
                new=AsyncMock(),
            ) as mock_forecast,
        ):
            mock_summary.return_value = SimpleNamespace(records=[{"cost": 10.0}])
            mock_forecast.return_value = {"forecast": [1, 2, 3]}
            response = await async_client.get(
                "/api/v1/costs/forecast", params={"days": 14}
            )
            assert response.status_code == 200
            assert response.json()["forecast"] == [1, 2, 3]
    finally:
        _clear_reporting_auth_overrides(app)


@pytest.mark.asyncio
async def test_get_cost_anomalies_paths(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="anomalies@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.GROWTH,
    )

    _override_reporting_auth(app, mock_user)
    try:
        mock_item = MagicMock()
        mock_item.day = date(2026, 2, 12)
        mock_item.provider = "aws"
        mock_item.account_id = uuid.uuid4()
        mock_item.account_name = "Prod"
        mock_item.service = "AmazonEC2"
        mock_item.actual_cost_usd = Decimal("250.00")
        mock_item.expected_cost_usd = Decimal("100.00")
        mock_item.delta_cost_usd = Decimal("150.00")
        mock_item.percent_change = 150.0
        mock_item.kind = "spike"
        mock_item.probable_cause = "spend_spike"
        mock_item.confidence = 0.9
        mock_item.severity = "high"

        with (
            patch(
                "app.modules.reporting.api.v1.costs.CostAnomalyDetectionService.detect",
                new=AsyncMock(return_value=[mock_item]),
            ),
            patch(
                "app.modules.reporting.api.v1.costs.dispatch_cost_anomaly_alerts",
                new=AsyncMock(return_value=1),
            ) as mock_alert,
        ):
            response = await async_client.get(
                "/api/v1/costs/anomalies",
                params={
                    "target_date": "2026-02-12",
                    "provider": "aws",
                    "alert": "true",
                    "suppression_hours": 12,
                    "min_severity": "medium",
                },
            )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["alerted_count"] == 1
        assert body["anomalies"][0]["kind"] == "spike"
        assert body["anomalies"][0]["severity"] == "high"
        assert mock_alert.await_count == 1
    finally:
        _clear_reporting_auth_overrides(app)


@pytest.mark.asyncio
async def test_get_cost_anomalies_requires_growth(async_client: AsyncClient, app):
    mock_user = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="anomalies-denied@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.STARTER,
    )

    _override_reporting_auth(app, mock_user)
    try:
        response = await async_client.get(
            "/api/v1/costs/anomalies",
            params={"target_date": "2026-02-12"},
        )
        assert response.status_code == 403
        assert "requires" in response.json()["error"].lower()
    finally:
        _clear_reporting_auth_overrides(app)


@pytest.mark.asyncio
async def test_analyze_costs_paths(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="analyze@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.PRO,
    )

    _override_reporting_auth(app, mock_user)
    try:
        # No records -> fallback response
        with patch(
            "app.modules.reporting.api.v1.costs.CostAggregator.get_summary",
            new=AsyncMock(),
        ) as mock_summary:
            mock_summary.return_value = SimpleNamespace(records=[])
            response = await async_client.post("/api/v1/costs/analyze")
            assert response.status_code == 200
            data = response.json()
            assert data["summary"] == "No cost data available for analysis."

        # Records -> analyzer path
        with (
            patch(
                "app.modules.reporting.api.v1.costs.CostAggregator.get_summary",
                new=AsyncMock(),
            ) as mock_summary,
            patch(
                "app.modules.reporting.api.v1.costs.LLMFactory.create",
                return_value=MagicMock(),
            ) as mock_create,
            patch(
                "app.modules.reporting.api.v1.costs.FinOpsAnalyzer"
            ) as mock_analyzer_class,
        ):
            mock_summary.return_value = SimpleNamespace(records=[{"cost": 10.0}])
            mock_analyzer = mock_analyzer_class.return_value
            mock_analyzer.analyze = AsyncMock(return_value={"summary": "ok"})

            response = await async_client.post("/api/v1/costs/analyze")
            assert response.status_code == 200
            assert response.json()["summary"] == "ok"
            assert mock_create.called
            assert mock_analyzer.analyze.await_count == 1
            assert mock_analyzer.analyze.await_args.kwargs["user_id"] == user_id
            assert "client_ip" in mock_analyzer.analyze.await_args.kwargs
    finally:
        _clear_reporting_auth_overrides(app)
