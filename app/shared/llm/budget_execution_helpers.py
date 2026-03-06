"""Helper coercion/normalization utilities for LLM budget execution."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


def coerce_decimal(value: Any) -> Decimal | None:
    """Return Decimal for supported scalar types, otherwise None."""
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float, str)):
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
    return None


def coerce_bool(value: Any, *, default: bool = False) -> bool:
    """Normalize mixed scalar/string values into booleans."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float, Decimal)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def coerce_threshold_percent(value: Any) -> Decimal:
    """Clamp threshold percent into [0,100], defaulting to 80."""
    threshold = coerce_decimal(value)
    if threshold is None:
        return Decimal("80")
    if threshold < 0:
        return Decimal("0")
    if threshold > 100:
        return Decimal("100")
    return threshold


def normalize_actor_type(value: Any) -> str:
    """Normalize actor type to supported values (`user`/`system`)."""
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"user", "system"}:
            return normalized
    return "system"


def compose_request_type(actor_type: str, request_type: str) -> str:
    """Compose namespaced request type while preserving pre-namespaced values."""
    normalized_actor = normalize_actor_type(actor_type)
    raw = str(request_type or "unknown").strip()
    if not raw:
        raw = "unknown"
    if raw.startswith("user:") or raw.startswith("system:"):
        return raw
    return f"{normalized_actor}:{raw}"


__all__ = [
    "coerce_bool",
    "coerce_decimal",
    "coerce_threshold_percent",
    "compose_request_type",
    "normalize_actor_type",
]
