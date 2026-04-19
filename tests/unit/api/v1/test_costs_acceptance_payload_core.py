from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.modules.reporting.api.v1 import costs as costs_api
from app.modules.reporting.api.v1 import costs_acceptance_payload as acceptance_payload
from tests.unit.api.v1.costs_acceptance_test_helpers import (
    ExecResult,
    FakeDB,
    event_time,
    free_user,
    standard_allocation_coverage,
    standard_ingestion_response,
    standard_license_metric,
    standard_recency_response,
    standard_unit_settings,
    unavailable_license_metric,
    user,
)


def _audit_event(*, success: bool = True) -> SimpleNamespace:
    return SimpleNamespace(
        id="audit-event-1",
        success=success,
        event_timestamp=event_time(),
        correlation_id="run-1",
    )


def test_as_naive_utc_normalizes_aware_datetimes_for_db_filters() -> None:
    aware = datetime(2026, 3, 19, 0, 0, tzinfo=timezone.utc)

    normalized = acceptance_payload._as_naive_utc(aware)

    assert normalized == datetime(2026, 3, 19, 0, 0)
    assert normalized.tzinfo is None


@pytest.mark.asyncio
async def test_compute_acceptance_payload_handles_zero_ledger_records() -> None:
    db = FakeDB(scalar_values=[_audit_event(), 1, 0])

    with (
        patch.object(
            costs_api,
            "_compute_ingestion_sla_metrics",
            new=AsyncMock(return_value=standard_ingestion_response()),
        ),
        patch.object(
            costs_api,
            "_compute_provider_recency_summaries",
            new=AsyncMock(return_value=standard_recency_response()),
        ),
        patch.object(
            costs_api,
            "_compute_license_governance_kpi",
            new=AsyncMock(return_value=standard_license_metric()),
        ),
        patch(
            "app.modules.reporting.domain.attribution_engine.AttributionEngine.get_allocation_coverage",
            new=AsyncMock(return_value=standard_allocation_coverage()),
        ),
        patch.object(
            costs_api,
            "_get_unit_settings_snapshot",
            new=AsyncMock(return_value=standard_unit_settings()),
        ),
        patch.object(
            costs_api,
            "_window_total_cost",
            new=AsyncMock(side_effect=[Decimal("1000"), Decimal("900")]),
        ),
        patch.object(
            costs_api,
            "get_settings",
            return_value=SimpleNamespace(ENCRYPTION_KEY="k", KDF_SALT="s"),
        ),
    ):
        payload = await costs_api._compute_acceptance_kpis_payload(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            ingestion_window_hours=168,
            ingestion_target_success_rate_percent=95.0,
            recency_target_hours=48,
            chargeback_target_percent=90.0,
            max_unit_anomalies=0,
            current_user=user(),
            db=db,  # type: ignore[arg-type]
        )

    by_key = {metric.key: metric for metric in payload.metrics}
    assert by_key["tenant_isolation_proof"].available is True
    assert by_key["tenant_isolation_proof"].meets_target is True
    assert by_key["encryption_health_proof"].meets_target is True
    assert by_key["user_access_review_proof"].available is False
    assert (
        "No automated user-access review evidence source"
        in by_key["user_access_review_proof"].actual
    )
    assert by_key["ledger_normalization_coverage"].available is False
    assert by_key["canonical_mapping_coverage"].actual == "No cost records in window"


@pytest.mark.asyncio
async def test_compute_acceptance_payload_builds_ledger_breakdown_and_unmapped_signatures() -> (
    None
):
    db = FakeDB(
        scalar_values=[_audit_event(), 1, 10],
        execute_values=[
            ExecResult(
                one_row=SimpleNamespace(
                    total_records=10,
                    normalized_records=8,
                    mapped_records=7,
                    unknown_service_records=1,
                    invalid_currency_records=1,
                    usage_unit_missing_records=0,
                )
            ),
            ExecResult(
                all_rows=[
                    SimpleNamespace(
                        provider="aws",
                        total_records=6,
                        normalized_records=5,
                        mapped_records=5,
                    ),
                    SimpleNamespace(
                        provider="saas",
                        total_records=4,
                        normalized_records=3,
                        mapped_records=2,
                    ),
                ]
            ),
            ExecResult(
                all_rows=[
                    SimpleNamespace(
                        provider="aws",
                        service="AmazonEC2",
                        usage_type="BoxUsage:t3.micro",
                        record_count=3,
                        first_seen=datetime(2026, 1, 3, tzinfo=timezone.utc),
                        last_seen=datetime(2026, 1, 20, tzinfo=timezone.utc),
                    )
                ]
            ),
        ],
    )

    with (
        patch.object(
            costs_api,
            "_compute_ingestion_sla_metrics",
            new=AsyncMock(return_value=standard_ingestion_response()),
        ),
        patch.object(
            costs_api,
            "_compute_provider_recency_summaries",
            new=AsyncMock(return_value=standard_recency_response()),
        ),
        patch.object(
            costs_api,
            "_compute_license_governance_kpi",
            new=AsyncMock(return_value=standard_license_metric()),
        ),
        patch(
            "app.modules.reporting.domain.attribution_engine.AttributionEngine.get_allocation_coverage",
            new=AsyncMock(return_value=standard_allocation_coverage()),
        ),
        patch.object(
            costs_api,
            "_get_unit_settings_snapshot",
            new=AsyncMock(return_value=standard_unit_settings()),
        ),
        patch.object(
            costs_api,
            "_window_total_cost",
            new=AsyncMock(side_effect=[Decimal("1000"), Decimal("900")]),
        ),
        patch.object(
            costs_api,
            "get_settings",
            return_value=SimpleNamespace(ENCRYPTION_KEY="k", KDF_SALT="s"),
        ),
    ):
        payload = await costs_api._compute_acceptance_kpis_payload(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            ingestion_window_hours=168,
            ingestion_target_success_rate_percent=95.0,
            recency_target_hours=48,
            chargeback_target_percent=90.0,
            max_unit_anomalies=0,
            current_user=user(),
            db=db,  # type: ignore[arg-type]
        )

    by_key = {metric.key: metric for metric in payload.metrics}
    ledger = by_key["ledger_normalization_coverage"]
    canonical = by_key["canonical_mapping_coverage"]
    assert ledger.available is True
    assert ledger.actual == "80.00%"
    assert ledger.details["provider_breakdown"][0]["provider"] == "aws"
    assert canonical.actual == "70.00%"
    assert canonical.details["top_unmapped_signatures"][0]["service"] == "AmazonEC2"


@pytest.mark.asyncio
async def test_compute_acceptance_payload_handles_ledger_query_exception() -> None:
    db = FakeDB(scalar_values=[None, 0, RuntimeError("ledger query failed")])

    with (
        patch.object(
            costs_api,
            "_compute_ingestion_sla_metrics",
            new=AsyncMock(
                return_value=standard_ingestion_response(
                    window_hours=1,
                    total_jobs=1,
                    successful_jobs=1,
                    records_ingested=1,
                    avg_duration_seconds=10.0,
                    p95_duration_seconds=10.0,
                )
            ),
        ),
        patch.object(
            costs_api,
            "_compute_provider_recency_summaries",
            new=AsyncMock(return_value=standard_recency_response()),
        ),
        patch.object(
            costs_api,
            "_compute_license_governance_kpi",
            new=AsyncMock(return_value=unavailable_license_metric()),
        ),
        patch(
            "app.modules.reporting.domain.attribution_engine.AttributionEngine.get_allocation_coverage",
            new=AsyncMock(
                return_value=standard_allocation_coverage(
                    coverage_percentage=0,
                    meets_target=False,
                )
            ),
        ),
        patch.object(
            costs_api,
            "_get_unit_settings_snapshot",
            new=AsyncMock(
                return_value=standard_unit_settings(
                    default_request_volume=1.0,
                    default_workload_volume=1.0,
                    default_customer_volume=1.0,
                )
            ),
        ),
        patch.object(
            costs_api,
            "_window_total_cost",
            new=AsyncMock(side_effect=[Decimal("1"), Decimal("1")]),
        ),
        patch.object(
            costs_api,
            "get_settings",
            return_value=SimpleNamespace(ENCRYPTION_KEY="", KDF_SALT=""),
        ),
    ):
        payload = await costs_api._compute_acceptance_kpis_payload(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            ingestion_window_hours=1,
            ingestion_target_success_rate_percent=95.0,
            recency_target_hours=48,
            chargeback_target_percent=90.0,
            max_unit_anomalies=0,
            current_user=user(),
            db=db,  # type: ignore[arg-type]
        )

    by_key = {metric.key: metric for metric in payload.metrics}
    assert by_key["ledger_normalization_coverage"].available is False
    assert by_key["encryption_health_proof"].actual == "Degraded"
    assert by_key["tenant_isolation_proof"].meets_target is False


@pytest.mark.asyncio
async def test_compute_acceptance_payload_invalid_window_and_unavailable_feature_branches() -> (
    None
):
    with pytest.raises(costs_api.HTTPException) as exc_info:
        await costs_api._compute_acceptance_kpis_payload(
            start_date=date(2026, 2, 1),
            end_date=date(2026, 1, 1),
            ingestion_window_hours=24,
            ingestion_target_success_rate_percent=95.0,
            recency_target_hours=48,
            chargeback_target_percent=90.0,
            max_unit_anomalies=0,
            current_user=free_user(),
            db=FakeDB(),  # type: ignore[arg-type]
        )
    assert exc_info.value.status_code == 400

    db = FakeDB(scalar_values=[None, 0, 0])

    def _feature_disabled_for_analytics(_tier, feature):
        return feature not in {
            costs_api.FeatureFlag.INGESTION_SLA,
            costs_api.FeatureFlag.CHARGEBACK,
            costs_api.FeatureFlag.UNIT_ECONOMICS,
        }

    with (
        patch.object(
            costs_api,
            "_compute_license_governance_kpi",
            new=AsyncMock(return_value=unavailable_license_metric()),
        ),
        patch.object(
            costs_api,
            "get_settings",
            return_value=SimpleNamespace(ENCRYPTION_KEY="k", KDF_SALT="s"),
        ),
        patch.object(
            costs_api,
            "is_feature_enabled",
            side_effect=_feature_disabled_for_analytics,
        ),
    ):
        payload = await costs_api._compute_acceptance_kpis_payload(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            ingestion_window_hours=24,
            ingestion_target_success_rate_percent=95.0,
            recency_target_hours=48,
            chargeback_target_percent=90.0,
            max_unit_anomalies=0,
            current_user=free_user(),
            db=db,  # type: ignore[arg-type]
        )

    by_key = {metric.key: metric for metric in payload.metrics}
    assert by_key["ingestion_reliability"].available is False
    assert by_key["chargeback_coverage"].available is False
    assert by_key["unit_economics_stability"].available is False


@pytest.mark.asyncio
async def test_compute_acceptance_payload_bounds_change_governance_window() -> None:
    db = AsyncMock()
    db.scalar.side_effect = [_audit_event(), 2, 0]

    with (
        patch.object(
            costs_api,
            "_compute_ingestion_sla_metrics",
            new=AsyncMock(return_value=standard_ingestion_response()),
        ),
        patch.object(
            costs_api,
            "_compute_provider_recency_summaries",
            new=AsyncMock(return_value=standard_recency_response()),
        ),
        patch.object(
            costs_api,
            "_compute_license_governance_kpi",
            new=AsyncMock(return_value=standard_license_metric()),
        ),
        patch(
            "app.modules.reporting.domain.attribution_engine.AttributionEngine.get_allocation_coverage",
            new=AsyncMock(return_value=standard_allocation_coverage()),
        ),
        patch.object(
            costs_api,
            "_get_unit_settings_snapshot",
            new=AsyncMock(return_value=standard_unit_settings()),
        ),
        patch.object(
            costs_api,
            "_window_total_cost",
            new=AsyncMock(side_effect=[Decimal("1000"), Decimal("900")]),
        ),
        patch.object(
            costs_api,
            "get_settings",
            return_value=SimpleNamespace(ENCRYPTION_KEY="k", KDF_SALT="s"),
        ),
    ):
        payload = await costs_api._compute_acceptance_kpis_payload(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            ingestion_window_hours=168,
            ingestion_target_success_rate_percent=95.0,
            recency_target_hours=48,
            chargeback_target_percent=90.0,
            max_unit_anomalies=0,
            current_user=user(),
            db=db,
        )

    remediation_stmt = db.scalar.await_args_list[1].args[0]
    compiled = str(remediation_stmt.compile(compile_kwargs={"literal_binds": True}))

    assert "2026-01-01 00:00:00" in compiled
    assert "2026-02-01 00:00:00" in compiled
    assert "+00:00" not in compiled
    assert "event_timestamp <" in compiled
    assert {metric.key: metric for metric in payload.metrics}[
        "change_governance_proof"
    ].meets_target is True
