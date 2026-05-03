from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from app.models.attribution import CostAllocation
from app.models.cloud import CloudAccount, CostRecord
from app.models.llm import LLMUsage
from app.modules.reporting.domain.focus_export_helpers import (
    _focus_charge_category,
    _focus_charge_frequency,
    _focus_service_category,
    _focus_service_subcategory,
    _humanize_vendor,
    _service_provider_display,
)

FOCUS_EXPORT_COST_PARSE_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    InvalidOperation,
    TypeError,
    ValueError,
)
FOCUS_EXPORT_TAG_SERIALIZATION_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    TypeError,
    ValueError,
)
AI_FOCUS_PROVIDER = "ai"
AI_FOCUS_SERVICE_CATEGORY = "AI and Machine Learning"
AI_FOCUS_SERVICE_SUBCATEGORY = "Generative AI"

# FOCUS 1.3 core export: high-value columns that are fully derivable from our
# normalized ledger without pretending to include SKU or unit-price fields we do
# not store yet.
FOCUS_V13_CORE_COLUMNS: list[str] = [
    "AllocatedMethodDetails",
    "AllocatedMethodId",
    "AllocatedResourceId",
    "AllocatedResourceName",
    "AllocatedTags",
    "BilledCost",
    "BillingAccountId",
    "BillingAccountName",
    "BillingCurrency",
    "BillingPeriodStart",
    "BillingPeriodEnd",
    "ChargeCategory",
    "ChargeClass",
    "ChargeDescription",
    "ChargeFrequency",
    "ChargePeriodStart",
    "ChargePeriodEnd",
    "ConsumedQuantity",
    "ConsumedUnit",
    "ContractedCost",
    "EffectiveCost",
    "HostProviderName",
    "InvoiceIssuerName",
    "ListCost",
    "PricingCurrency",
    "PricingQuantity",
    "PricingUnit",
    "ProviderName",
    "PublisherName",
    "RegionId",
    "RegionName",
    "ResourceId",
    "ServiceProviderName",
    "ServiceCategory",
    "ServiceSubcategory",
    "ServiceName",
    "Tags",
]


@dataclass(frozen=True)
class FocusAccountContext:
    provider_key: str
    billing_account_id: str
    billing_account_name: str
    provider_name: str
    publisher_name: str
    service_provider_name: str
    invoice_issuer_name: str


@dataclass(frozen=True)
class FocusSyntheticAllocation:
    id: str
    rule_id: None
    allocated_to: str
    amount: Decimal
    percentage: Decimal | None


FocusAllocation = CostAllocation | FocusSyntheticAllocation
FocusAllocationKey = tuple[UUID, date]


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _focus_datetime(dt: datetime) -> str:
    # RFC 3339 / ISO 8601 with Z suffix (timezone-agnostic and stable in CSV).
    return _as_utc(dt).strftime("%Y-%m-%dT%H:%M:%SZ")


def _month_start(day: date) -> datetime:
    return datetime(day.year, day.month, 1, tzinfo=timezone.utc)


def _next_month_start(day: date) -> datetime:
    if day.month == 12:
        return datetime(day.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(day.year, day.month + 1, 1, tzinfo=timezone.utc)


def _format_cost(value: Any) -> str:
    if value is None:
        return "0"
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except FOCUS_EXPORT_COST_PARSE_RECOVERABLE_EXCEPTIONS as exc:
        raise ValueError("FOCUS export cost must be numeric") from exc
    if not amount.is_finite():
        raise ValueError("FOCUS export cost must be finite")
    return format(amount, "f")


def _to_decimal(value: Any, *, field_name: str) -> Decimal:
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except FOCUS_EXPORT_COST_PARSE_RECOVERABLE_EXCEPTIONS as exc:
        raise ValueError(f"FOCUS export {field_name} must be numeric") from exc
    if not amount.is_finite():
        raise ValueError(f"FOCUS export {field_name} must be finite")
    return amount


def _format_optional_decimal(value: Any) -> str:
    if value is None:
        return ""
    return format(_to_decimal(value, field_name="numeric value"), "f")


def _format_currency(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        return "USD"
    return value.strip().upper()


def _tags_json(value: Any) -> str:
    if not isinstance(value, dict):
        return ""
    # Stable JSON for diffs and deterministic exports.
    try:
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    except FOCUS_EXPORT_TAG_SERIALIZATION_RECOVERABLE_EXCEPTIONS:
        return ""


def _stable_json(value: dict[str, Any] | None) -> str:
    if not value:
        return ""
    try:
        return json.dumps(value, separators=(",", ":"), sort_keys=True)
    except FOCUS_EXPORT_TAG_SERIALIZATION_RECOVERABLE_EXCEPTIONS:
        return ""


def _allocation_bucket(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()


def _date_window_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


def row_to_focus(
    cost_record: CostRecord,
    account: CloudAccount,
    contexts: dict[UUID, FocusAccountContext],
    allocation: FocusAllocation | None = None,
) -> dict[str, str]:
    recorded_day = getattr(cost_record, "recorded_at", None) or date.today()
    billing_start = _month_start(recorded_day)
    billing_end = _next_month_start(recorded_day)

    provider_key = str(getattr(account, "provider", "") or "").strip().lower()
    charge_start: datetime
    charge_end: datetime
    ts = getattr(cost_record, "timestamp", None)
    if isinstance(ts, datetime):
        ts = _as_utc(ts)
    if provider_key in {"aws", "azure", "gcp"} and isinstance(ts, datetime):
        charge_start = ts
        charge_end = ts + timedelta(hours=1)
    else:
        charge_start = datetime.combine(recorded_day, time.min, tzinfo=timezone.utc)
        charge_end = charge_start + timedelta(days=1)

    service = getattr(cost_record, "service", None)
    usage_type = getattr(cost_record, "usage_type", None)
    charge_category = _focus_charge_category(service, usage_type)
    service_category = _focus_service_category(
        getattr(cost_record, "canonical_charge_category", None)
    )
    service_subcategory = _focus_service_subcategory(service_category)

    raw_tags = getattr(cost_record, "tags", None)
    if not isinstance(raw_tags, dict) or not raw_tags:
        meta = getattr(cost_record, "ingestion_metadata", None)
        if isinstance(meta, dict):
            raw_tags = meta.get("tags")

    ctx = contexts.get(account.id)
    if ctx is None:
        display = _service_provider_display(provider_key)
        ctx = FocusAccountContext(
            provider_key=provider_key,
            billing_account_id=str(account.id),
            billing_account_name=str(getattr(account, "name", "") or ""),
            provider_name=display,
            publisher_name=display,
            service_provider_name=display,
            invoice_issuer_name=display,
        )

    region_value = str(getattr(cost_record, "region", "") or "").strip()
    cost_value = _format_cost(
        getattr(allocation, "amount", None)
        if allocation is not None
        else getattr(cost_record, "cost_usd", None)
    )
    # Our ledger stores `cost_usd` in USD. For exports, keep currency aligned with the cost value.
    currency_value = "USD"
    usage_quantity = _format_optional_decimal(getattr(cost_record, "usage_amount", None))
    usage_unit = str(getattr(cost_record, "usage_unit", "") or "").strip()
    resource_id = str(getattr(cost_record, "resource_id", "") or "").strip()
    pricing_currency = _format_currency(getattr(cost_record, "currency", None))
    allocation_field_values = allocation_fields(cost_record, allocation)

    focus_row = {
        **allocation_field_values,
        "BilledCost": cost_value,
        "BillingAccountId": ctx.billing_account_id,
        "BillingAccountName": ctx.billing_account_name,
        "BillingCurrency": currency_value,
        "BillingPeriodStart": _focus_datetime(billing_start),
        "BillingPeriodEnd": _focus_datetime(billing_end),
        "ChargeCategory": charge_category,
        "ChargeClass": "Regular",
        "ChargeDescription": str(usage_type or service or "").strip(),
        "ChargeFrequency": _focus_charge_frequency(charge_category),
        "ChargePeriodStart": _focus_datetime(charge_start),
        "ChargePeriodEnd": _focus_datetime(charge_end),
        "ConsumedQuantity": usage_quantity,
        "ConsumedUnit": usage_unit,
        "ContractedCost": cost_value,
        "EffectiveCost": cost_value,
        "HostProviderName": ctx.service_provider_name,
        "InvoiceIssuerName": ctx.invoice_issuer_name,
        "ListCost": cost_value,
        "PricingCurrency": pricing_currency,
        "PricingQuantity": usage_quantity,
        "PricingUnit": usage_unit,
        "ProviderName": ctx.provider_name,
        "PublisherName": ctx.publisher_name,
        "RegionId": region_value,
        "RegionName": region_value,
        "ResourceId": resource_id,
        "ServiceProviderName": ctx.service_provider_name,
        "ServiceCategory": service_category,
        "ServiceSubcategory": service_subcategory,
        "ServiceName": str(service or "Unknown").strip() or "Unknown",
        "Tags": _tags_json(raw_tags),
    }

    # Ensure stable presence for all expected columns (avoid accidental KeyError).
    return {col: str(focus_row.get(col, "")) for col in FOCUS_V13_CORE_COLUMNS}


def llm_usage_to_focus(usage: LLMUsage) -> dict[str, str]:
    created_at = _as_utc(getattr(usage, "created_at", datetime.now(timezone.utc)))
    provider_key = (getattr(usage, "provider", None) or "unknown").strip().lower()
    provider_display = _humanize_vendor(provider_key) or provider_key.upper()
    model = str(getattr(usage, "model", "") or "LLM").strip() or "LLM"
    request_type = str(getattr(usage, "request_type", "") or "inference").strip()
    cost_value = _format_cost(getattr(usage, "cost_usd", None))
    tokens = _format_optional_decimal(getattr(usage, "total_tokens", None))
    charge_end = created_at + timedelta(seconds=1)
    tags = {
        "source": "llm_usage",
        "llm_provider": provider_key,
        "model": model,
        "request_type": request_type,
        "is_byok": bool(getattr(usage, "is_byok", False)),
    }
    focus_row = {
        "AllocatedMethodDetails": "",
        "AllocatedMethodId": "",
        "AllocatedResourceId": "",
        "AllocatedResourceName": "",
        "AllocatedTags": "",
        "BilledCost": cost_value,
        "BillingAccountId": f"ai:{provider_key}",
        "BillingAccountName": f"AI Spend ({provider_display})",
        "BillingCurrency": "USD",
        "BillingPeriodStart": _focus_datetime(_month_start(created_at.date())),
        "BillingPeriodEnd": _focus_datetime(_next_month_start(created_at.date())),
        "ChargeCategory": "Usage",
        "ChargeClass": "Regular",
        "ChargeDescription": request_type,
        "ChargeFrequency": "Usage-Based",
        "ChargePeriodStart": _focus_datetime(created_at),
        "ChargePeriodEnd": _focus_datetime(charge_end),
        "ConsumedQuantity": tokens,
        "ConsumedUnit": "tokens",
        "ContractedCost": cost_value,
        "EffectiveCost": cost_value,
        "HostProviderName": provider_display,
        "InvoiceIssuerName": provider_display,
        "ListCost": cost_value,
        "PricingCurrency": "USD",
        "PricingQuantity": tokens,
        "PricingUnit": "tokens",
        "ProviderName": provider_display,
        "PublisherName": provider_display,
        "RegionId": "",
        "RegionName": "",
        "ResourceId": str(getattr(usage, "operation_id", "") or "").strip(),
        "ServiceProviderName": provider_display,
        "ServiceCategory": AI_FOCUS_SERVICE_CATEGORY,
        "ServiceSubcategory": AI_FOCUS_SERVICE_SUBCATEGORY,
        "ServiceName": model,
        "Tags": _tags_json(tags),
    }
    return {col: str(focus_row.get(col, "")) for col in FOCUS_V13_CORE_COLUMNS}


def allocation_fields(
    cost_record: CostRecord,
    allocation: FocusAllocation | None,
) -> dict[str, str]:
    empty = {
        "AllocatedMethodDetails": "",
        "AllocatedMethodId": "",
        "AllocatedResourceId": "",
        "AllocatedResourceName": "",
        "AllocatedTags": "",
    }
    if allocation is None:
        return empty

    bucket = _allocation_bucket(allocation.allocated_to)
    is_unallocated_remainder = bucket.lower() == "unallocated"
    method_id = "valdrics-rule-based-allocation-v1"
    origin_cost = _to_decimal(
        getattr(cost_record, "cost_usd", None),
        field_name="origin cost",
    )
    allocation_amount = _to_decimal(
        getattr(allocation, "amount", None),
        field_name="allocation amount",
    )
    percentage = getattr(allocation, "percentage", None)
    if percentage is not None:
        ratio = _to_decimal(percentage, field_name="allocation percentage") / Decimal(
            "100"
        )
    elif origin_cost == Decimal("0"):
        ratio = Decimal("0")
    else:
        ratio = allocation_amount / origin_cost

    details: dict[str, Any] = {
        "Elements": [
            {
                "AllocatedRatio": float(ratio),
            }
        ],
        "x_ValdricsAllocationId": str(allocation.id),
    }
    if allocation.rule_id is not None:
        details["x_ValdricsRuleId"] = str(allocation.rule_id)

    return {
        **empty,
        "AllocatedMethodDetails": _stable_json(details),
        "AllocatedMethodId": method_id,
        "AllocatedResourceId": "" if is_unallocated_remainder else bucket,
        "AllocatedResourceName": "" if is_unallocated_remainder else bucket,
    }
