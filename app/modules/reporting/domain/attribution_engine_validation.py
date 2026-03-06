"""Validation and normalization helpers for attribution rules."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

VALID_RULE_TYPES = {"DIRECT", "PERCENTAGE", "FIXED"}
ATTRIBUTION_DECIMAL_PARSE_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    InvalidOperation,
    TypeError,
    ValueError,
)


def normalize_rule_type(rule_type: str) -> str:
    """Normalize rule type to uppercase for consistent matching."""
    return (rule_type or "").strip().upper()


def allocation_entries(allocation: Any) -> list[dict[str, Any]]:
    """Normalize allocation payload to a list of dict entries."""
    if isinstance(allocation, list):
        return [item for item in allocation if isinstance(item, dict)]
    if isinstance(allocation, dict):
        return [allocation]
    return []


def validate_rule_payload(rule_type: str, allocation: Any) -> list[str]:
    """
    Validate allocation payload shape for a rule type.

    Returns a list of validation error messages; empty list means valid.
    """
    errors: list[str] = []
    normalized_type = normalize_rule_type(rule_type)
    if normalized_type not in VALID_RULE_TYPES:
        errors.append(f"rule_type must be one of {sorted(VALID_RULE_TYPES)}")
        return errors

    entries = allocation_entries(allocation)

    if normalized_type == "DIRECT":
        if len(entries) != 1:
            errors.append("DIRECT allocation must define exactly one bucket.")
        elif not entries[0].get("bucket"):
            errors.append("DIRECT allocation requires a non-empty 'bucket'.")

    elif normalized_type == "PERCENTAGE":
        if not entries:
            errors.append("PERCENTAGE allocation requires at least one split entry.")
        total_percentage = Decimal("0")
        for split in entries:
            if not split.get("bucket"):
                errors.append("Each PERCENTAGE split requires a non-empty 'bucket'.")
            percentage_raw = split.get("percentage")
            try:
                percentage = Decimal(str(percentage_raw))
            except ATTRIBUTION_DECIMAL_PARSE_RECOVERABLE_EXCEPTIONS:
                errors.append("Each PERCENTAGE split requires numeric 'percentage'.")
                continue
            if percentage < 0:
                errors.append("PERCENTAGE split cannot be negative.")
            total_percentage += percentage
        if entries and total_percentage != Decimal("100"):
            errors.append("PERCENTAGE split percentages must sum to 100.")

    elif normalized_type == "FIXED":
        if not entries:
            errors.append("FIXED allocation requires at least one split entry.")
        for split in entries:
            if not split.get("bucket"):
                errors.append("Each FIXED split requires a non-empty 'bucket'.")
            amount_raw = split.get("amount")
            try:
                amount = Decimal(str(amount_raw))
            except ATTRIBUTION_DECIMAL_PARSE_RECOVERABLE_EXCEPTIONS:
                errors.append("Each FIXED split requires numeric 'amount'.")
                continue
            if amount < 0:
                errors.append("FIXED split amount cannot be negative.")

    return errors
