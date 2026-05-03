from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4
from unittest.mock import AsyncMock

import pytest

from app.models.attribution import CostAllocation
from app.modules.reporting.domain import focus_export as focus_export_module
from app.modules.reporting.domain.focus_export import (
    FocusAccountContext,
    FocusV13ExportService,
)


class _RowsResult:
    def __init__(self, rows: list[tuple[object, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[object, ...]]:
        return self._rows

    def __iter__(self):
        return iter(self._rows)


def _service_with_mock_db() -> FocusV13ExportService:
    db = SimpleNamespace()
    db.stream = AsyncMock()
    db.execute = AsyncMock()
    return FocusV13ExportService(db=db)


def test_focus_export_helper_branches() -> None:
    assert focus_export_module._next_month_start(date(2026, 12, 31)) == datetime(
        2027, 1, 1, tzinfo=timezone.utc
    )
    assert focus_export_module._humanize_vendor("  microsoft_365  ") == "Microsoft 365"
    assert focus_export_module._humanize_vendor("new-relic") == "New Relic"
    assert focus_export_module._humanize_vendor(None) is None
    assert focus_export_module._focus_service_category("ai") == "AI and Machine Learning"

    assert (
        focus_export_module._service_provider_display("saas", "salesforce")
        == "Salesforce"
    )
    assert (
        focus_export_module._focus_charge_category("invoice tax", "x")
        == "Tax"
    )
    assert (
        focus_export_module._focus_charge_category("refund", "credit")
        == "Credit"
    )
    assert (
        focus_export_module._focus_charge_category("marketplace fee", None)
        == "Adjustment"
    )
    assert focus_export_module._focus_charge_frequency("Adjustment") == "One-Time"
    assert focus_export_module._format_cost(None) == "0"
    with pytest.raises(ValueError, match="FOCUS export cost must be numeric"):
        focus_export_module._format_cost(object())
    with pytest.raises(ValueError, match="FOCUS export cost must be finite"):
        focus_export_module._format_cost(Decimal("NaN"))
    assert focus_export_module._format_optional_decimal(None) == ""
    assert focus_export_module._format_optional_decimal("1.25") == "1.25"
    with pytest.raises(ValueError, match="FOCUS export numeric value must be finite"):
        focus_export_module._format_optional_decimal(Decimal("Infinity"))
    assert focus_export_module._format_currency(" eur ") == "EUR"
    assert focus_export_module._format_currency(None) == "USD"
    assert focus_export_module._tags_json([]) == ""
    assert focus_export_module._tags_json({"bad": {1, 2}}) == ""


@pytest.mark.asyncio
async def test_export_rows_falls_back_to_execute_when_stream_fails() -> None:
    service = _service_with_mock_db()
    account_id = uuid4()
    service._load_account_contexts = AsyncMock(return_value={})  # type: ignore[attr-defined]
    service.db.stream.side_effect = RuntimeError("stream unavailable")

    cost_record = SimpleNamespace(
        id=uuid4(),
        recorded_at=date(2026, 1, 3),
        timestamp=datetime(2026, 1, 3, 1, 0, tzinfo=timezone.utc),
        service="AmazonEC2",
        usage_type="BoxUsage:t3.micro",
        canonical_charge_category="compute",
        tags={"env": "prod"},
        ingestion_metadata=None,
        cost_usd=Decimal("12.34"),
        region="us-east-1",
    )
    account = SimpleNamespace(id=account_id, provider="aws", name="Prod AWS")
    service.db.execute.return_value = _RowsResult([(cost_record, account, None)])

    rows = [
        row
        async for row in service.export_rows(
            tenant_id=uuid4(),
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 31),
            provider="aws",
            include_preliminary=True,
        )
    ]

    assert len(rows) == 1
    assert rows[0]["ProviderName"] == "Amazon Web Services"
    assert rows[0]["BillingCurrency"] == "USD"
    assert rows[0]["Tags"] == '{"env":"prod"}'


@pytest.mark.asyncio
async def test_load_account_contexts_handles_provider_and_preliminary_paths() -> None:
    service = _service_with_mock_db()
    service.db.execute.return_value = _RowsResult([])
    service._enrich_cloud_accounts = AsyncMock()  # type: ignore[attr-defined]
    service._enrich_cloud_plus_accounts = AsyncMock()  # type: ignore[attr-defined]

    contexts = await service._load_account_contexts(
        tenant_id=uuid4(),
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        provider="aws",
        include_preliminary=True,
    )

    assert contexts == {}
    service.db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_enrich_cloud_accounts_updates_known_contexts_and_skips_unknown() -> None:
    service = _service_with_mock_db()
    aws_id = uuid4()
    azure_id = uuid4()
    gcp_id = uuid4()
    unknown_id = uuid4()
    contexts = {
        aws_id: FocusAccountContext(
            provider_key="aws",
            billing_account_id=str(aws_id),
            billing_account_name="aws",
            provider_name="aws",
            publisher_name="aws",
            service_provider_name="aws",
            invoice_issuer_name="aws",
        ),
        azure_id: FocusAccountContext(
            provider_key="azure",
            billing_account_id=str(azure_id),
            billing_account_name="",
            provider_name="azure",
            publisher_name="azure",
            service_provider_name="azure",
            invoice_issuer_name="azure",
        ),
        gcp_id: FocusAccountContext(
            provider_key="gcp",
            billing_account_id=str(gcp_id),
            billing_account_name="",
            provider_name="gcp",
            publisher_name="gcp",
            service_provider_name="gcp",
            invoice_issuer_name="gcp",
        ),
    }
    service.db.execute.side_effect = [
        _RowsResult([(unknown_id, "111111111111"), (aws_id, "123456789012")]),
        _RowsResult([(azure_id, "sub-123")]),
        _RowsResult([(gcp_id, "project-abc")]),
    ]

    await service._enrich_cloud_accounts(contexts, [aws_id, azure_id, gcp_id])

    assert contexts[aws_id].billing_account_id == "123456789012"
    assert contexts[azure_id].billing_account_id == "sub-123"
    assert contexts[gcp_id].billing_account_id == "project-abc"
    assert contexts[gcp_id].provider_name == "Google Cloud"


@pytest.mark.asyncio
async def test_enrich_cloud_plus_accounts_handles_unknown_provider_and_context_filter() -> None:
    service = _service_with_mock_db()
    known_id = uuid4()
    unknown_id = uuid4()
    contexts = {
        known_id: FocusAccountContext(
            provider_key="saas",
            billing_account_id=str(known_id),
            billing_account_name="SaaS Acct",
            provider_name="saas",
            publisher_name="saas",
            service_provider_name="saas",
            invoice_issuer_name="saas",
        )
    }

    await service._enrich_cloud_plus_accounts(contexts, "unknown", [known_id])
    service.db.execute.assert_not_awaited()

    service.db.execute.return_value = _RowsResult(
        [(known_id, "microsoft_365"), (unknown_id, "zoom")]
    )
    await service._enrich_cloud_plus_accounts(contexts, "saas", [known_id, unknown_id])

    assert contexts[known_id].provider_name == "Microsoft 365"
    assert contexts[known_id].billing_account_name == "SaaS Acct"


def test_row_to_focus_uses_context_fallback_for_non_cloud_records() -> None:
    service = _service_with_mock_db()
    account_id = uuid4()
    account = SimpleNamespace(id=account_id, provider="platform", name="Ops Platform")
    cost_record = SimpleNamespace(
        recorded_at=date(2026, 2, 14),
        timestamp=None,
        service=None,
        usage_type=None,
        canonical_charge_category=None,
        region="",
        tags=[],
        ingestion_metadata={"tags": {"owner": "finops"}},
        cost_usd=Decimal("0.25"),
        currency=None,
    )

    row = service._row_to_focus(cost_record, account, contexts={})

    assert row["ServiceName"] == "Unknown"
    assert row["ChargeCategory"] == "Usage"
    assert row["ChargeFrequency"] == "Usage-Based"
    assert row["Tags"] == '{"owner":"finops"}'
    assert row["ProviderName"] == "PLATFORM"
    assert row["HostProviderName"] == "PLATFORM"
    assert row["PricingCurrency"] == "USD"


def test_llm_usage_to_focus_exports_ai_service_category() -> None:
    service = _service_with_mock_db()
    usage = SimpleNamespace(
        id=uuid4(),
        provider="groq",
        model="llama-3.3-70b-versatile",
        total_tokens=200,
        cost_usd=Decimal("0.0042"),
        request_type="daily_analysis",
        operation_id="op-ai-focus-1",
        is_byok=True,
        created_at=datetime(2026, 1, 16, 9, 30, tzinfo=timezone.utc),
    )

    row = service._llm_usage_to_focus(usage)

    assert row["BillingAccountId"] == "ai:groq"
    assert row["ProviderName"] == "Groq"
    assert row["ServiceCategory"] == "AI and Machine Learning"
    assert row["ServiceSubcategory"] == "Generative AI"
    assert row["ServiceName"] == "llama-3.3-70b-versatile"
    assert row["ConsumedQuantity"] == "200"
    assert row["ConsumedUnit"] == "tokens"
    assert row["BilledCost"] == "0.0042"
    assert row["ResourceId"] == "op-ai-focus-1"


def test_row_to_focus_handles_non_dict_metadata_tags_and_cloud_hour_window() -> None:
    service = _service_with_mock_db()
    account_id = uuid4()
    account = SimpleNamespace(id=account_id, provider="aws", name="AWS")
    timestamp = datetime(2026, 2, 14, 6, 30, tzinfo=timezone.utc)
    cost_record = SimpleNamespace(
        recorded_at=date(2026, 2, 14),
        timestamp=timestamp,
        service="AmazonS3",
        usage_type="Requests",
        canonical_charge_category="storage",
        region="us-east-1",
        resource_id="arn:aws:s3:::example",
        usage_amount=Decimal("42"),
        usage_unit="Requests",
        tags=None,
        ingestion_metadata=["bad-shape"],
        cost_usd=Decimal("4.5"),
        currency="usd",
    )

    row = service._row_to_focus(cost_record, account, contexts={})

    assert row["ChargePeriodStart"] == "2026-02-14T06:30:00Z"
    assert row["ChargePeriodEnd"] == "2026-02-14T07:30:00Z"
    assert row["ConsumedQuantity"] == "42"
    assert row["ConsumedUnit"] == "Requests"
    assert row["PricingQuantity"] == "42"
    assert row["PricingUnit"] == "Requests"
    assert row["ResourceId"] == "arn:aws:s3:::example"
    assert row["PricingCurrency"] == "USD"
    assert row["Tags"] == ""


def test_row_to_focus_rejects_non_finite_cost() -> None:
    service = _service_with_mock_db()
    account_id = uuid4()
    account = SimpleNamespace(id=account_id, provider="aws", name="AWS")
    cost_record = SimpleNamespace(
        recorded_at=date(2026, 2, 14),
        timestamp=datetime(2026, 2, 14, 6, 30, tzinfo=timezone.utc),
        service="AmazonS3",
        usage_type="Requests",
        canonical_charge_category="storage",
        region="us-east-1",
        tags={"env": "prod"},
        ingestion_metadata=None,
        cost_usd=Decimal("Infinity"),
        currency="USD",
    )

    with pytest.raises(ValueError, match="FOCUS export cost must be finite"):
        service._row_to_focus(cost_record, account, contexts={})


def test_rows_for_cost_record_expands_canonical_split_allocations() -> None:
    service = _service_with_mock_db()
    record_id = uuid4()
    account_id = uuid4()
    rule_id = uuid4()
    allocation_a = CostAllocation(
        id=uuid4(),
        cost_record_id=record_id,
        recorded_at=date(2026, 3, 1),
        rule_id=rule_id,
        allocated_to="Engineering",
        amount=Decimal("60.00"),
        percentage=Decimal("60.00"),
        timestamp=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    allocation_b = CostAllocation(
        id=uuid4(),
        cost_record_id=record_id,
        recorded_at=date(2026, 3, 1),
        rule_id=rule_id,
        allocated_to="Finance",
        amount=Decimal("40.00"),
        percentage=Decimal("40.00"),
        timestamp=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    cost_record = SimpleNamespace(
        id=record_id,
        recorded_at=date(2026, 3, 1),
        timestamp=datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc),
        service="Slack",
        usage_type="Seats",
        canonical_charge_category="saas",
        region="global",
        resource_id="slack-workspace-1",
        usage_amount=Decimal("20"),
        usage_unit="Seat",
        tags={"department": "shared"},
        ingestion_metadata=None,
        cost_usd=Decimal("100.00"),
        currency="USD",
    )
    account = SimpleNamespace(id=account_id, provider="saas", name="SaaS")

    rows = service._rows_for_cost_record(
        cost_record,
        account,
        contexts={},
        allocations_by_record_key={
            (record_id, date(2026, 3, 1)): [allocation_a, allocation_b]
        },
    )

    assert [row["BilledCost"] for row in rows] == ["60.00", "40.00"]
    assert [row["AllocatedResourceId"] for row in rows] == [
        "Engineering",
        "Finance",
    ]
    assert rows[0]["AllocatedMethodId"] == "valdrics-rule-based-allocation-v1"
    assert rows[0]["AllocatedMethodDetails"] == (
        '{"Elements":[{"AllocatedRatio":0.6}],'
        f'"x_ValdricsAllocationId":"{allocation_a.id}",'
        f'"x_ValdricsRuleId":"{rule_id}"'
        "}"
    )
    assert rows[0]["ConsumedQuantity"] == "20"
    assert rows[0]["ConsumedUnit"] == "Seat"


def test_rows_for_cost_record_keeps_synthetic_unallocated_row_as_origin_charge() -> None:
    service = _service_with_mock_db()
    record_id = uuid4()
    account_id = uuid4()
    allocation = CostAllocation(
        id=uuid4(),
        cost_record_id=record_id,
        recorded_at=date(2026, 3, 1),
        rule_id=None,
        allocated_to="Unallocated",
        amount=Decimal("100.00"),
        percentage=Decimal("100.00"),
        timestamp=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    cost_record = SimpleNamespace(
        id=record_id,
        recorded_at=date(2026, 3, 1),
        timestamp=datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc),
        service="AmazonEC2",
        usage_type="BoxUsage:t3.micro",
        canonical_charge_category="compute",
        region="us-east-1",
        resource_id="i-123",
        usage_amount=None,
        usage_unit=None,
        tags={},
        ingestion_metadata=None,
        cost_usd=Decimal("100.00"),
        currency="USD",
    )
    account = SimpleNamespace(id=account_id, provider="aws", name="AWS")

    rows = service._rows_for_cost_record(
        cost_record,
        account,
        contexts={},
        allocations_by_record_key={(record_id, date(2026, 3, 1)): [allocation]},
    )

    assert len(rows) == 1
    assert rows[0]["BilledCost"] == "100.00"
    assert rows[0]["AllocatedMethodId"] == ""


def test_rows_for_cost_record_keys_allocations_by_record_id_and_recorded_date() -> None:
    service = _service_with_mock_db()
    record_id = uuid4()
    account = SimpleNamespace(id=uuid4(), provider="aws", name="AWS")
    allocation = CostAllocation(
        id=uuid4(),
        cost_record_id=record_id,
        recorded_at=date(2026, 3, 2),
        rule_id=uuid4(),
        allocated_to="Engineering",
        amount=Decimal("80.00"),
        percentage=Decimal("100.00"),
        timestamp=datetime(2026, 3, 2, tzinfo=timezone.utc),
    )
    cost_record = SimpleNamespace(
        id=record_id,
        recorded_at=date(2026, 3, 1),
        timestamp=datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc),
        service="AmazonEC2",
        usage_type="BoxUsage:t3.micro",
        canonical_charge_category="compute",
        region="us-east-1",
        resource_id="i-123",
        usage_amount=None,
        usage_unit=None,
        tags={},
        ingestion_metadata=None,
        cost_usd=Decimal("80.00"),
        currency="USD",
    )

    rows = service._rows_for_cost_record(
        cost_record,
        account,
        contexts={},
        allocations_by_record_key={(record_id, date(2026, 3, 2)): [allocation]},
    )

    assert len(rows) == 1
    assert rows[0]["BilledCost"] == "80.00"
    assert rows[0]["AllocatedMethodId"] == ""


def test_rows_for_cost_record_adds_unallocated_remainder_for_partial_allocations() -> None:
    service = _service_with_mock_db()
    record_id = uuid4()
    account = SimpleNamespace(id=uuid4(), provider="saas", name="SaaS")
    allocation = CostAllocation(
        id=uuid4(),
        cost_record_id=record_id,
        recorded_at=date(2026, 3, 1),
        rule_id=uuid4(),
        allocated_to="Engineering",
        amount=Decimal("60.00"),
        percentage=Decimal("60.00"),
        timestamp=datetime(2026, 3, 1, tzinfo=timezone.utc),
    )
    cost_record = SimpleNamespace(
        id=record_id,
        recorded_at=date(2026, 3, 1),
        timestamp=datetime(2026, 3, 1, 1, 0, tzinfo=timezone.utc),
        service="Slack",
        usage_type="Seats",
        canonical_charge_category="saas",
        region="global",
        resource_id="slack-workspace-1",
        usage_amount=Decimal("20"),
        usage_unit="Seat",
        tags={"department": "shared"},
        ingestion_metadata=None,
        cost_usd=Decimal("100.00"),
        currency="USD",
    )

    rows = service._rows_for_cost_record(
        cost_record,
        account,
        contexts={},
        allocations_by_record_key={(record_id, date(2026, 3, 1)): [allocation]},
    )

    assert [row["BilledCost"] for row in rows] == ["60.00", "40.00"]
    assert sum(Decimal(row["BilledCost"]) for row in rows) == Decimal("100.00")
    assert rows[1]["AllocatedResourceId"] == ""
    assert rows[1]["AllocatedMethodId"] == "valdrics-rule-based-allocation-v1"
