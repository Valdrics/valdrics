import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.models.tenant import Tenant, User
from app.modules.reporting.api.v1 import costs as costs_api
from app.shared.core.auth import CurrentUser, UserRole, get_current_user
from app.shared.core.pricing import PricingTier
@pytest.mark.asyncio
async def test_get_acceptance_kpis_csv_export(async_client: AsyncClient, app):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="q2-kpi-csv@valdrics.io",
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
                        total_jobs=10,
                        successful_jobs=9,
                        failed_jobs=1,
                        success_rate_percent=90.0,
                        meets_sla=False,
                        latest_completed_at="2026-02-13T10:00:00+00:00",
                        avg_duration_seconds=120.0,
                        p95_duration_seconds=200.0,
                        records_ingested=400,
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
                        "coverage_percentage": 91.0,
                        "meets_target": True,
                        "status": "ok",
                        "allocated_cost": 910.0,
                        "unallocated_cost": 90.0,
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
                new=AsyncMock(side_effect=[Decimal("1000"), Decimal("800")]),
            ),
        ):
            response = await async_client.get(
                "/api/v1/costs/acceptance/kpis",
                params={
                    "start_date": "2026-01-01",
                    "end_date": "2026-01-31",
                    "response_format": "csv",
                },
            )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment; filename=" in response.headers.get(
            "content-disposition", ""
        )
        assert "metric,key,label,available,target,actual,meets_target" in response.text
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_capture_acceptance_kpis_persists_audit_evidence(
    async_client: AsyncClient, app, db
):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="kpi-capture-admin@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.PRO,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        db.add(Tenant(id=tenant_id, name="KPI Evidence Tenant", plan=PricingTier.PRO.value))
        db.add(
            User(id=user_id, tenant_id=tenant_id, email=mock_user.email, role=UserRole.ADMIN)
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
            response = await async_client.post(
                "/api/v1/costs/acceptance/kpis/capture",
                params={"start_date": "2026-01-01", "end_date": "2026-01-31"},
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "captured"
        assert payload["event_id"]
        assert payload["run_id"]
        assert payload["acceptance_kpis"]["start_date"] == "2026-01-01"

        list_response = await async_client.get("/api/v1/costs/acceptance/kpis/evidence")
        assert list_response.status_code == 200
        evidence = list_response.json()
        assert evidence["total"] >= 1
        assert evidence["items"][0]["event_id"] == payload["event_id"]
        assert evidence["items"][0]["acceptance_kpis"]["end_date"] == "2026-01-31"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
