from __future__ import annotations

from typing import Any, Iterable

from app.shared.analysis.usage_analyzer_numeric import safe_float


def resource_id_from_records(records: list[dict[str, Any]], fallback: str) -> str:
    if records:
        first = records[0]
        value = first.get("ResourceId") or first.get("resource_id")
        if value:
            return str(value)
    return fallback


def resource_name_from_id(resource_id: str) -> str:
    return resource_id.split("/")[-1] if "/" in resource_id else resource_id


def record_contains_terms(
    record: dict[str, Any],
    *,
    terms: Iterable[str],
    fields: Iterable[str],
) -> bool:
    normalized_terms = tuple(term.lower() for term in terms)
    for field in fields:
        value = str(record.get(field, "")).lower()
        if any(term in value for term in normalized_terms):
            return True
    return False


def sum_cost(records: list[dict[str, Any]]) -> float:
    return sum(safe_float(record.get("PreTaxCost", 0)) for record in records)


def sum_cost_for_terms(
    records: list[dict[str, Any]],
    *,
    terms: Iterable[str],
    fields: Iterable[str],
) -> float:
    total = 0.0
    for record in records:
        if record_contains_terms(record, terms=terms, fields=fields):
            total += safe_float(record.get("PreTaxCost", 0))
    return total


def sum_usage_for_terms(
    records: list[dict[str, Any]],
    *,
    terms: Iterable[str],
    fields: Iterable[str],
) -> float:
    total = 0.0
    for record in records:
        if record_contains_terms(record, terms=terms, fields=fields):
            total += safe_float(record.get("UsageQuantity", 0))
    return total


def projected_monthly_cost(total_cost: float, days: int) -> float:
    return round(total_cost * (30 / max(days, 1)), 2)
