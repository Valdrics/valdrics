import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient

from app.models.background_job import BackgroundJob, JobStatus, JobType
from app.models.cloud import CloudAccount, CostRecord
from app.models.tenant import Tenant
from app.modules.reporting.api.v1 import costs as costs_api
from app.shared.core.auth import CurrentUser, UserRole, get_current_user
from app.shared.core.pricing import PricingTier
async def test_window_total_cost_provider_filter_and_missing_rows(db):
    tenant_id = uuid.uuid4()
    account = CloudAccount(
        tenant_id=tenant_id,
        provider="aws",
        name="Provider Filter",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    db.add(
        CostRecord(
            tenant_id=tenant_id,
            account_id=account.id,
            service="AmazonEC2",
            region="us-east-1",
            usage_type="BoxUsage",
            cost_usd=Decimal("12.50"),
            currency="USD",
            canonical_charge_category="compute",
            canonical_mapping_version="focus-1.3-v1",
            recorded_at=date(2026, 2, 1),
            timestamp=datetime(2026, 2, 1, 10, 0, tzinfo=timezone.utc),
        )
    )
    await db.commit()

    aws_total = await costs_api._window_total_cost(
        db=db,
        tenant_id=tenant_id,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 1),
        provider="aws",
    )
    gcp_total = await costs_api._window_total_cost(
        db=db,
        tenant_id=tenant_id,
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 1),
        provider="gcp",
    )
    assert aws_total == Decimal("12.50")
    assert gcp_total == Decimal("0")


def test_build_unit_metrics_handles_zero_denominator_and_zero_baseline():
    metrics = costs_api._build_unit_metrics(
        total_cost=Decimal("25.0"),
        baseline_total_cost=Decimal("0"),
        threshold_percent=10.0,
        request_volume=0.0,
        workload_volume=5.0,
        customer_volume=2.5,
    )
    assert len(metrics) == 2
    assert all(metric.delta_percent == 0.0 for metric in metrics)
    assert all(metric.is_anomalous is False for metric in metrics)


def test_csv_cell_sanitization_and_anomaly_severity_validation() -> None:
    assert costs_api._sanitize_csv_cell(None) == ""
    assert costs_api._sanitize_csv_cell("") == ""
    assert costs_api._sanitize_csv_cell("=2+2") == "'=2+2"
    assert costs_api._sanitize_csv_cell("+sum(a1:a2)") == "'+sum(a1:a2)"
    assert costs_api._sanitize_csv_cell("@cmd") == "'@cmd"
    assert costs_api._sanitize_csv_cell("\tformula") == "'\tformula"
    assert costs_api._sanitize_csv_cell("-safe-value") == "-safe-value"

    assert costs_api._validate_anomaly_severity(" HIGH ") == "high"
    with pytest.raises(HTTPException, match="Unsupported severity"):
        costs_api._validate_anomaly_severity("emergency")


def test_anomaly_to_response_item_maps_decimal_fields() -> None:
    anomaly = costs_api.CostAnomaly(
        day=date(2026, 2, 27),
        provider="aws",
        account_id=uuid.uuid4(),
        account_name="prod-account",
        service="AmazonEC2",
        actual_cost_usd=Decimal("150"),
        expected_cost_usd=Decimal("100"),
        delta_cost_usd=Decimal("50"),
        percent_change=50.0,
        kind="spike",
        probable_cause="spend_spike",
        confidence=0.9,
        severity="high",
    )

    item = costs_api._anomaly_to_response_item(anomaly)
    assert item.day == "2026-02-27"
    assert item.provider == "aws"
    assert item.service == "AmazonEC2"
    assert item.actual_cost_usd == 150.0
    assert item.expected_cost_usd == 100.0
    assert item.delta_cost_usd == 50.0
    assert item.percent_change == 50.0


@pytest.mark.asyncio
async def test_get_ingestion_sla_metrics(async_client: AsyncClient, app, db):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="sla@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        now = datetime.now(timezone.utc)
        db.add(Tenant(id=tenant_id, name="SLA Tenant", plan="pro"))
        db.add_all(
            [
                BackgroundJob(
                    tenant_id=tenant_id,
                    job_type=JobType.COST_INGESTION.value,
                    status=JobStatus.COMPLETED.value,
                    payload={},
                    result={"ingested": 120},
                    scheduled_for=now,
                    created_at=now,
                    started_at=now,
                    completed_at=now + timedelta(seconds=300),
                ),
                BackgroundJob(
                    tenant_id=tenant_id,
                    job_type=JobType.COST_INGESTION.value,
                    status=JobStatus.COMPLETED.value,
                    payload={},
                    result={"ingested": 40},
                    scheduled_for=now,
                    created_at=now,
                    started_at=now,
                    completed_at=now + timedelta(seconds=120),
                ),
                BackgroundJob(
                    tenant_id=tenant_id,
                    job_type=JobType.COST_INGESTION.value,
                    status=JobStatus.FAILED.value,
                    payload={},
                    result={},
                    scheduled_for=now,
                    created_at=now,
                    started_at=now,
                    completed_at=now + timedelta(seconds=60),
                ),
            ]
        )
        await db.commit()

        response = await async_client.get(
            "/api/v1/costs/ingestion/sla",
            params={"window_hours": 24, "target_success_rate_percent": 60},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["window_hours"] == 24
        assert data["total_jobs"] == 3
        assert data["successful_jobs"] == 2
        assert data["failed_jobs"] == 1
        assert data["success_rate_percent"] == pytest.approx(66.67, rel=0.01)
        assert data["meets_sla"] is True
        assert data["records_ingested"] == 160
        assert data["avg_duration_seconds"] == pytest.approx(160.0, rel=0.01)
        assert data["p95_duration_seconds"] == pytest.approx(300.0, rel=0.01)
        assert data["latest_completed_at"] is not None
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_ingestion_sla_no_jobs(async_client: AsyncClient, app, db):
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="sla-empty@valdrics.io",
        role=UserRole.MEMBER,
        tier=PricingTier.STARTER,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        db.add(Tenant(id=tenant_id, name="SLA Empty", plan="pro"))
        await db.commit()

        response = await async_client.get("/api/v1/costs/ingestion/sla")
        assert response.status_code == 200
        data = response.json()
        assert data["total_jobs"] == 0
        assert data["successful_jobs"] == 0
        assert data["failed_jobs"] == 0
        assert data["success_rate_percent"] == 0.0
        assert data["meets_sla"] is False
        assert data["records_ingested"] == 0
    finally:
        app.dependency_overrides.pop(get_current_user, None)

