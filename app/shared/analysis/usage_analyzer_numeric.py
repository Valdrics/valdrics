from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to float, returning default on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_decimal(value: Any) -> Decimal:
    """Convert values to Decimal safely, defaulting to 0 on invalid input."""
    if value is None or value == "":
        return Decimal("0")
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")


def safe_int(value: Any) -> int:
    """Convert values to int safely, defaulting to 0 on invalid input."""
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except (TypeError, ValueError, OverflowError):
        return 0


__all__ = ["safe_decimal", "safe_float", "safe_int"]
