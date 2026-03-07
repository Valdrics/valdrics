"""Parsing and payload loading helpers for PKG/FIN evidence verification."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.pkg_fin_policy_decisions_constants import PLACEHOLDER_TOKEN_RE


def parse_iso_utc(value: Any, *, field: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(f"{field} must be a non-empty ISO-8601 datetime")
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone information")
    return parsed.astimezone(timezone.utc)


def parse_float(
    value: Any,
    *,
    field: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    if min_value is not None and parsed < min_value:
        raise ValueError(f"{field} must be >= {min_value}")
    if max_value is not None and parsed > max_value:
        raise ValueError(f"{field} must be <= {max_value}")
    return parsed


def parse_int(value: Any, *, field: str, min_value: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be integer-like") from exc
    if min_value is not None and parsed < min_value:
        raise ValueError(f"{field} must be >= {min_value}")
    return parsed


def parse_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field} must be boolean")


def parse_non_empty_str(value: Any, *, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field} must be a non-empty string")
    if PLACEHOLDER_TOKEN_RE.search(normalized):
        raise ValueError(f"{field} must not contain placeholder tokens")
    return normalized


def parse_date(value: Any, *, field: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(f"{field} must be a non-empty YYYY-MM-DD date")
    try:
        parsed = datetime.fromisoformat(f"{raw}T00:00:00+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc
    return parsed


def load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"PKG/FIN policy decision evidence file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"PKG/FIN policy decision evidence JSON is invalid: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("PKG/FIN policy decision payload must be a JSON object")
    return payload
