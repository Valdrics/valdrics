import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.cloud import CloudAccount, CostRecord
from app.models.tenant import Tenant, User
from app.modules.reporting.api.v1 import costs as costs_api
from app.shared.core.auth import CurrentUser, UserRole, get_current_user
from app.shared.core.pricing import PricingTier
@pytest.mark.asyncio
async def test_get_acceptance_kpis_includes_ledger_quality_metrics_when_data_exists(
    async_client: AsyncClient, app, db
):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="acceptance-kpi-ledger@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.PRO,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        db.add(Tenant(id=tenant_id, name="Acceptance KPI Ledger", plan=PricingTier.PRO.value))
        db.add(
            User(id=user_id, tenant_id=tenant_id, email=mock_user.email, role=UserRole.ADMIN)
        )

        account_id = uuid.uuid4()
        db.add(
            CloudAccount(
                id=account_id,
                tenant_id=tenant_id,
                provider="aws",
                name="Prod AWS",
                is_active=True,
            )
        )

        # 4 rows in-window:
        # - 2 normalized + mapped
        # - 1 unknown service + unmapped
        # - 1 usage_amount present but missing usage_unit (normalization failure)
        record_days = [date(2026, 1, d) for d in (10, 11, 12, 13)]
        db.add_all(
            [
                CostRecord(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    account_id=account_id,
                    service="AmazonEC2",
                    region="us-east-1",
                    usage_type="BoxUsage:t3.micro",
                    resource_id="i-123",
                    usage_amount=Decimal("1"),
                    usage_unit="Hrs",
                    canonical_charge_category="compute",
                    canonical_charge_subcategory="runtime",
                    canonical_mapping_version="focus-1.3-v1",
                    cost_usd=Decimal("10.00"),
                    amount_raw=Decimal("10.00"),
                    currency="USD",
                    carbon_kg=None,
                    is_preliminary=False,
                    cost_status="FINAL",
                    reconciliation_run_id=None,
                    ingestion_metadata={},
                    tags=None,
                    attribution_id=None,
                    allocated_to=None,
                    recorded_at=record_days[0],
                    timestamp=datetime(
                        record_days[0].year,
                        record_days[0].month,
                        record_days[0].day,
                        tzinfo=timezone.utc,
                    ),
                ),
                CostRecord(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    account_id=account_id,
                    service="AmazonS3",
                    region="us-east-1",
                    usage_type="TimedStorage-ByteHrs",
                    resource_id="bucket-abc",
                    usage_amount=None,
                    usage_unit=None,
                    canonical_charge_category="storage",
                    canonical_charge_subcategory="capacity",
                    canonical_mapping_version="focus-1.3-v1",
                    cost_usd=Decimal("5.00"),
                    amount_raw=Decimal("5.00"),
                    currency="USD",
                    carbon_kg=None,
                    is_preliminary=False,
                    cost_status="FINAL",
                    reconciliation_run_id=None,
                    ingestion_metadata={},
                    tags=None,
                    attribution_id=None,
                    allocated_to=None,
                    recorded_at=record_days[1],
                    timestamp=datetime(
                        record_days[1].year,
                        record_days[1].month,
                        record_days[1].day,
                        tzinfo=timezone.utc,
                    ),
                ),
                CostRecord(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    account_id=account_id,
                    service="Unknown",
                    region="us-east-1",
                    usage_type="Usage",
                    resource_id="unknown",
                    usage_amount=None,
                    usage_unit=None,
                    canonical_charge_category="unmapped",
                    canonical_charge_subcategory=None,
                    canonical_mapping_version="focus-1.3-v1",
                    cost_usd=Decimal("1.00"),
                    amount_raw=Decimal("1.00"),
                    currency="USD",
                    carbon_kg=None,
                    is_preliminary=False,
                    cost_status="FINAL",
                    reconciliation_run_id=None,
                    ingestion_metadata={},
                    tags=None,
                    attribution_id=None,
                    allocated_to=None,
                    recorded_at=record_days[2],
                    timestamp=datetime(
                        record_days[2].year,
                        record_days[2].month,
                        record_days[2].day,
                        tzinfo=timezone.utc,
                    ),
                ),
                CostRecord(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    account_id=account_id,
                    service="AmazonRDS",
                    region="us-east-1",
                    usage_type="InstanceUsage:db.t3.micro",
                    resource_id="db-xyz",
                    usage_amount=Decimal("3"),
                    usage_unit=None,  # normalization failure
                    canonical_charge_category="database",
                    canonical_charge_subcategory="managed",
                    canonical_mapping_version="focus-1.3-v1",
                    cost_usd=Decimal("7.00"),
                    amount_raw=Decimal("7.00"),
                    currency="USD",
                    carbon_kg=None,
                    is_preliminary=False,
                    cost_status="FINAL",
                    reconciliation_run_id=None,
                    ingestion_metadata={},
                    tags=None,
                    attribution_id=None,
                    allocated_to=None,
                    recorded_at=record_days[3],
                    timestamp=datetime(
                        record_days[3].year,
                        record_days[3].month,
                        record_days[3].day,
                        tzinfo=timezone.utc,
                    ),
                ),
            ]
        )
        await db.commit()

        with (
            patch(
                "app.modules.reporting.api.v1.costs._compute_ingestion_sla_metrics",
                new=AsyncMock(
                    return_value=costs_api.IngestionSLAResponse(
                        window_hours=168,
                        target_success_rate_percent=95.0,
                        total_jobs=1,
                        successful_jobs=1,
                        failed_jobs=0,
                        success_rate_percent=100.0,
                        meets_sla=True,
                        latest_completed_at="2026-02-13T10:00:00+00:00",
                        avg_duration_seconds=60.0,
                        p95_duration_seconds=60.0,
                        records_ingested=4,
                    )
                ),
            ),
            patch(
                "app.modules.reporting.api.v1.costs._compute_provider_recency_summaries",
                new=AsyncMock(
                    return_value=[
                        costs_api.ProviderRecencyResponse(
                            provider="aws",
                            active_connections=1,
                            recently_ingested=1,
                            stale_connections=0,
                            never_ingested=0,
                            latest_ingested_at="2026-02-13T09:00:00+00:00",
                            recency_target_hours=48,
                            meets_recency_target=True,
                        )
                    ]
                ),
            ),
            patch(
                "app.modules.reporting.domain.attribution_engine.AttributionEngine.get_allocation_coverage",
                new=AsyncMock(
                    return_value={
                        "target_percentage": 90.0,
                        "coverage_percentage": 94.0,
                        "meets_target": True,
                        "status": "ok",
                        "allocated_cost": 94.0,
                        "unallocated_cost": 6.0,
                        "total_cost": 100.0,
                    }
                ),
            ),
            patch(
                "app.modules.reporting.api.v1.costs._get_or_create_unit_settings",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        default_request_volume=1000,
                        default_workload_volume=100,
                        default_customer_volume=20,
                        anomaly_threshold_percent=20.0,
                    )
                ),
            ),
            patch(
                "app.modules.reporting.api.v1.costs._window_total_cost",
                new=AsyncMock(side_effect=[Decimal("100"), Decimal("90")]),
            ),
        ):
            response = await async_client.get(
                "/api/v1/costs/acceptance/kpis",
                params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
            )

        assert response.status_code == 200
        payload = response.json()
        by_key = {item["key"]: item for item in payload["metrics"]}

        assert by_key["ledger_normalization_coverage"]["available"] is True
        assert by_key["canonical_mapping_coverage"]["available"] is True
        assert by_key["ledger_normalization_coverage"]["actual"] == "50.00%"
        assert by_key["canonical_mapping_coverage"]["actual"] == "75.00%"
        assert by_key["ledger_normalization_coverage"]["meets_target"] is False
        assert by_key["canonical_mapping_coverage"]["meets_target"] is False
        assert payload["all_targets_met"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_acceptance_kpis_marks_unavailable_features(
    async_client: AsyncClient, app
):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="q2-kpi-starter@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        with (
            patch(
                "app.modules.reporting.api.v1.costs._compute_ingestion_sla_metrics",
                new=AsyncMock(
                    return_value=costs_api.IngestionSLAResponse(
                        window_hours=168,
                        target_success_rate_percent=95.0,
                        total_jobs=2,
                        successful_jobs=1,
                        failed_jobs=1,
                        success_rate_percent=50.0,
                        meets_sla=False,
                        latest_completed_at="2026-02-13T10:00:00+00:00",
                        avg_duration_seconds=200.0,
                        p95_duration_seconds=300.0,
                        records_ingested=12,
                    )
                ),
            ),
            patch(
                "app.modules.reporting.api.v1.costs._compute_provider_recency_summaries",
                new=AsyncMock(
                    return_value=[
                        costs_api.ProviderRecencyResponse(
                            provider="aws",
                            active_connections=1,
                            recently_ingested=0,
                            stale_connections=1,
                            never_ingested=0,
                            latest_ingested_at="2026-02-10T09:00:00+00:00",
                            recency_target_hours=48,
                            meets_recency_target=False,
                        )
                    ]
                ),
            ),
            patch(
                "app.modules.reporting.api.v1.costs._get_or_create_unit_settings",
                new=AsyncMock(
                    return_value=SimpleNamespace(
                        default_request_volume=1000,
                        default_workload_volume=100,
                        default_customer_volume=20,
                        anomaly_threshold_percent=20.0,
                    )
                ),
            ),
            patch(
                "app.modules.reporting.api.v1.costs._window_total_cost",
                new=AsyncMock(side_effect=[Decimal("500"), Decimal("300")]),
            ),
        ):
            response = await async_client.get(
                "/api/v1/costs/acceptance/kpis",
                params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
            )

        assert response.status_code == 200
        payload = response.json()
        by_key = {item["key"]: item for item in payload["metrics"]}
        assert by_key["chargeback_coverage"]["available"] is False
        assert "Growth tier" in by_key["chargeback_coverage"]["target"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


