import uuid
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.license_connection import LicenseConnection
from app.models.remediation import (
    RemediationAction,
    RemediationRequest,
    RemediationStatus,
)
from app.models.tenant import Tenant, User
from app.modules.reporting.api.v1 import costs as costs_api
from app.shared.core.auth import CurrentUser, UserRole, get_current_user
from app.shared.core.pricing import PricingTier
@pytest.mark.asyncio
async def test_get_acceptance_kpis(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="q2-kpi@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.PRO,
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
                        total_jobs=12,
                        successful_jobs=12,
                        failed_jobs=0,
                        success_rate_percent=100.0,
                        meets_sla=True,
                        latest_completed_at="2026-02-13T10:00:00+00:00",
                        avg_duration_seconds=120.0,
                        p95_duration_seconds=180.0,
                        records_ingested=1250,
                    )
                ),
            ),
            patch(
                "app.modules.reporting.api.v1.costs._compute_provider_recency_summaries",
                new=AsyncMock(
                    return_value=[
                        costs_api.ProviderRecencyResponse(
                            provider="aws",
                            active_connections=2,
                            recently_ingested=2,
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
                        "allocated_cost": 940.0,
                        "unallocated_cost": 60.0,
                        "total_cost": 1000.0,
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
                new=AsyncMock(side_effect=[Decimal("1000"), Decimal("900")]),
            ),
        ):
            response = await async_client.get(
                "/api/v1/costs/acceptance/kpis",
                params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["all_targets_met"] is True
        assert payload["available_metrics"] >= 3
        by_key = {item["key"]: item for item in payload["metrics"]}
        assert by_key["ingestion_reliability"]["meets_target"] is True
        assert by_key["chargeback_coverage"]["actual"] == "94.00%"
        assert by_key["unit_economics_stability"]["meets_target"] is True
        assert "license_governance_reliability" in by_key
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_acceptance_kpis_includes_license_governance_metrics(
    async_client: AsyncClient, app, db
):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="acceptance-kpi-license@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.PRO,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        db.add(Tenant(id=tenant_id, name="Acceptance KPI License", plan=PricingTier.PRO.value))
        db.add(
            User(id=user_id, tenant_id=tenant_id, email=mock_user.email, role=UserRole.ADMIN)
        )
        db.add(
            LicenseConnection(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                name="M365 Seats",
                vendor="microsoft_365",
                auth_method="api_key",
                api_key=None,
                connector_config={},
                license_feed=[],
                is_active=True,
            )
        )
        db.add_all(
            [
                RemediationRequest(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    resource_id="user-1",
                    resource_type="license_seat",
                    provider="license",
                    region="global",
                    action=RemediationAction.RECLAIM_LICENSE_SEAT,
                    status=RemediationStatus.COMPLETED,
                    requested_by_user_id=user_id,
                    created_at=datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc),
                    executed_at=datetime(2026, 1, 10, 12, 0, tzinfo=timezone.utc),
                ),
                RemediationRequest(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    resource_id="user-2",
                    resource_type="license_seat",
                    provider="license",
                    region="global",
                    action=RemediationAction.RECLAIM_LICENSE_SEAT,
                    status=RemediationStatus.FAILED,
                    requested_by_user_id=user_id,
                    created_at=datetime(2026, 1, 11, 10, 0, tzinfo=timezone.utc),
                ),
                RemediationRequest(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    resource_id="user-3",
                    resource_type="license_seat",
                    provider="license",
                    region="global",
                    action=RemediationAction.RECLAIM_LICENSE_SEAT,
                    status=RemediationStatus.SCHEDULED,
                    requested_by_user_id=user_id,
                    created_at=datetime(2026, 1, 12, 10, 0, tzinfo=timezone.utc),
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
                        total_jobs=12,
                        successful_jobs=12,
                        failed_jobs=0,
                        success_rate_percent=100.0,
                        meets_sla=True,
                        latest_completed_at="2026-02-13T10:00:00+00:00",
                        avg_duration_seconds=120.0,
                        p95_duration_seconds=180.0,
                        records_ingested=1250,
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
        license_metric = by_key["license_governance_reliability"]
        assert license_metric["available"] is True
        assert license_metric["details"]["active_license_connections"] == 1
        assert license_metric["details"]["total_requests"] == 3
        assert license_metric["details"]["completed_requests"] == 1
        assert license_metric["details"]["failed_requests"] == 1
        assert license_metric["details"]["in_flight_requests"] == 1
        assert license_metric["meets_target"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


