from __future__ import annotations

from typing import Any


def coerce_positive_int(
    value: Any,
    *,
    default: int,
    minimum: int,
) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= minimum else default


def extract_deleted_count(result: Any, *, fallback: int = 0) -> int:
    rowcount = getattr(result, "rowcount", fallback)
    if isinstance(rowcount, int) and rowcount >= 0:
        return rowcount
    return fallback if fallback >= 0 else 0
