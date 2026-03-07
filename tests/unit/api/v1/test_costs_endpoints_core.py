import uuid
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.shared.core.auth import CurrentUser, UserRole, get_current_user
from app.shared.core.pricing import PricingTier
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

    app.dependency_overrides[get_current_user] = lambda: mock_user
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
        app.dependency_overrides.pop(get_current_user, None)


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

    app.dependency_overrides[get_current_user] = lambda: mock_user
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
        app.dependency_overrides.pop(get_current_user, None)


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

    app.dependency_overrides[get_current_user] = lambda: mock_user
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
        app.dependency_overrides.pop(get_current_user, None)


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

    app.dependency_overrides[get_current_user] = lambda: mock_user
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
        app.dependency_overrides.pop(get_current_user, None)


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

    app.dependency_overrides[get_current_user] = lambda: mock_user
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
        app.dependency_overrides.pop(get_current_user, None)


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

    app.dependency_overrides[get_current_user] = lambda: mock_user
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
        app.dependency_overrides.pop(get_current_user, None)


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

    app.dependency_overrides[get_current_user] = lambda: mock_user
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
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_cost_anomalies_requires_growth(async_client: AsyncClient, app):
    mock_user = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="anomalies-denied@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.STARTER,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.get(
            "/api/v1/costs/anomalies",
            params={"target_date": "2026-02-12"},
        )
        assert response.status_code == 403
        assert "requires" in response.json()["error"].lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


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

    app.dependency_overrides[get_current_user] = lambda: mock_user
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
        app.dependency_overrides.pop(get_current_user, None)


