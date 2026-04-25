from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


def parse_required_timestamp(value: Any) -> datetime:
    """
    Strict timestamp normalization for records that must carry a valid event time.

    Raises ValueError/TypeError on invalid inputs instead of fabricating a timestamp.
    """
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    raise TypeError("timestamp must be datetime, ISO string, or unix timestamp")


def parse_timestamp(value: Any) -> datetime:
    """
    Best-effort timestamp normalization.

    Accepts:
    - datetime (naive treated as UTC)
    - ISO8601 strings (Z supported)
    - unix timestamps (int/float)

    Falls back to "now" on invalid inputs to keep ingestion resilient, but callers
    should validate required fields before relying on this.
    """
    try:
        return parse_required_timestamp(value)
    except (TypeError, ValueError):
        return datetime.now(timezone.utc)


def as_float(value: Any, default: float = 0.0, *, divisor: int = 1) -> float:
    if value is None:
        return default
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("value must be numeric") from exc
    if not amount.is_finite():
        raise ValueError("value must be finite")
    if divisor <= 0:
        divisor = 1
    return float(amount / Decimal(divisor))


def is_number(value: Any) -> bool:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return amount.is_finite()
