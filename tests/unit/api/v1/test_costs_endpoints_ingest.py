import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.cloud import CloudAccount, CostRecord
from app.modules.reporting.api.v1 import costs as costs_api
from app.shared.core.auth import CurrentUser, UserRole, get_current_user
from app.shared.core.pricing import PricingTier
async def test_analyze_costs_available_on_starter(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="starter@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.STARTER,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.post("/api/v1/costs/analyze")
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"] == "No cost data available for analysis."
    finally:
        app.dependency_overrides.pop(get_current_user, None)
async def test_trigger_ingest(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="ingest@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.STARTER,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        mock_job = SimpleNamespace(id=uuid.uuid4())
        with patch(
            "app.modules.governance.domain.jobs.processor.enqueue_job",
            new=AsyncMock(return_value=mock_job),
        ):
            response = await async_client.post("/api/v1/costs/ingest")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "queued"
            assert data["job_id"] == str(mock_job.id)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
async def test_trigger_ingest_with_backfill_window(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="ingest-range@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.GROWTH,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        mock_job = SimpleNamespace(id=uuid.uuid4())
        with patch(
            "app.modules.governance.domain.jobs.processor.enqueue_job",
            new=AsyncMock(return_value=mock_job),
        ) as mock_enqueue:
            response = await async_client.post(
                "/api/v1/costs/ingest",
                params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "queued"
            assert data["start_date"] == "2026-01-01"
            assert data["end_date"] == "2026-01-31"
            call_kwargs = mock_enqueue.await_args.kwargs
            assert call_kwargs["payload"]["start_date"] == "2026-01-01"
            assert call_kwargs["payload"]["end_date"] == "2026-01-31"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_trigger_ingest_backfill_requires_growth_tier(
    async_client: AsyncClient, app
):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="ingest-backfill-denied@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.STARTER,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.post(
            "/api/v1/costs/ingest",
            params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
        )
        assert response.status_code == 403
        assert "backfill" in response.json()["error"].lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_trigger_ingest_backfill_requires_both_dates(
    async_client: AsyncClient, app
):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="ingest-invalid@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.STARTER,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.post(
            "/api/v1/costs/ingest",
            params={"start_date": "2026-01-01"},
        )
        assert response.status_code == 400
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_costs_returns_data_quality_metadata(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="quality@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        with patch(
            "app.modules.reporting.api.v1.costs.CostAggregator.get_dashboard_summary",
            new=AsyncMock(),
        ) as mock_summary:
            mock_summary.return_value = {
                "total_cost": 123.45,
                "data_quality": {
                    "freshness": {"status": "mixed"},
                    "canonical_mapping": {
                        "mapped_percentage": 99.1,
                        "meets_target": True,
                    },
                },
            }

            response = await async_client.get(
                "/api/v1/costs",
                params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
            )
            assert response.status_code == 200
            data = response.json()
            assert data["data_quality"]["freshness"]["status"] == "mixed"
            assert (
                data["data_quality"]["canonical_mapping"]["mapped_percentage"] == 99.1
            )
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_costs_requires_tenant_context(async_client: AsyncClient, app):
    mock_user = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=None,
        email="no-tenant@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.get(
            "/api/v1/costs",
            params={"start_date": "2024-01-01", "end_date": "2024-01-31"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_costs_large_dataset_returns_accepted(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="large@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        mock_job = SimpleNamespace(id=uuid.uuid4())
        with (
            patch(
                "app.modules.reporting.api.v1.costs.CostAggregator.count_records",
                new=AsyncMock(return_value=costs_api.LARGE_DATASET_THRESHOLD + 1),
            ),
            patch(
                "app.modules.governance.domain.jobs.processor.enqueue_job",
                new=AsyncMock(return_value=mock_job),
            ) as mock_enqueue,
        ):
            response = await async_client.get(
                "/api/v1/costs",
                params={
                    "start_date": "2024-01-01",
                    "end_date": "2024-01-31",
                    "provider": "aws",
                },
            )

        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "accepted"
        assert body["job_id"] == str(mock_job.id)
        assert mock_enqueue.await_args.kwargs["payload"]["provider"] == "aws"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_trigger_ingest_rejects_invalid_date_order(
    async_client: AsyncClient, app
):
    mock_user = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="ingest-order@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.STARTER,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.post(
            "/api/v1/costs/ingest",
            params={"start_date": "2026-02-02", "end_date": "2026-02-01"},
        )
        assert response.status_code == 400
        assert "start_date must be <=" in response.json()["error"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_unit_economics_rejects_invalid_date_order(
    async_client: AsyncClient, app
):
    mock_user = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="unit-order@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.PRO,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.get(
            "/api/v1/costs/unit-economics",
            params={"start_date": "2026-02-02", "end_date": "2026-02-01"},
        )
        assert response.status_code == 400
        assert "start_date must be <=" in response.json()["error"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_unit_economics_alert_failure_is_non_fatal(
    async_client: AsyncClient, app, db, member_user
):
    app.dependency_overrides[get_current_user] = lambda: member_user
    try:
        account = CloudAccount(
            tenant_id=member_user.tenant_id,
            provider="aws",
            name="Alert Failure AWS",
            is_active=True,
        )
        db.add(account)
        await db.flush()
        for day in range(1, 8):
            db.add(
                CostRecord(
                    tenant_id=member_user.tenant_id,
                    account_id=account.id,
                    service="AmazonEC2",
                    region="us-east-1",
                    usage_type="BoxUsage",
                    cost_usd=Decimal("100.00"),
                    currency="USD",
                    canonical_charge_category="compute",
                    canonical_mapping_version="focus-1.3-v1",
                    recorded_at=date(2026, 2, day),
                    timestamp=datetime(2026, 2, day, 10, 0, tzinfo=timezone.utc),
                )
            )
            db.add(
                CostRecord(
                    tenant_id=member_user.tenant_id,
                    account_id=account.id,
                    service="AmazonEC2",
                    region="us-east-1",
                    usage_type="BoxUsage",
                    cost_usd=Decimal("50.00"),
                    currency="USD",
                    canonical_charge_category="compute",
                    canonical_mapping_version="focus-1.3-v1",
                    recorded_at=date(2026, 1, 24 + day),
                    timestamp=datetime(2026, 1, 24 + day, 10, 0, tzinfo=timezone.utc),
                )
            )
        await db.commit()

        with patch(
            "app.modules.reporting.api.v1.costs.NotificationDispatcher.send_alert",
            new=AsyncMock(side_effect=RuntimeError("alert failure")),
        ):
            response = await async_client.get(
                "/api/v1/costs/unit-economics",
                params={"start_date": "2026-02-01", "end_date": "2026-02-07"},
            )

        assert response.status_code == 200
        assert response.json()["alert_dispatched"] is False
        assert response.json()["anomaly_count"] >= 1
    finally:
        app.dependency_overrides.pop(get_current_user, None)
