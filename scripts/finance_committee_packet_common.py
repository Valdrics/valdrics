"""Shared parsing and utility helpers for finance committee packet generation."""

from __future__ import annotations

import csv
import json
import math
import re
from pathlib import Path
from typing import Any

TRACKED_TIERS: tuple[str, ...] = ("starter", "growth", "pro", "enterprise")


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


def parse_non_empty_str(value: Any, *, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field} must be a non-empty string")
    return normalized


def sanitize_label(raw: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_-]+", "_", raw).strip("_") or "snapshot"


def load_json(path: Path, *, field: str) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"{field} does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{field} must be a JSON object")
    return payload


def safe_margin_percent(revenue: float, cogs: float) -> float:
    if revenue <= 0.0:
        return 100.0 if cogs <= 0.0 else 0.0
    return ((revenue - cogs) / revenue) * 100.0


def index_by_tier(rows: list[dict[str, Any]], *, field: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{field}[{idx}] must be an object")
        tier = parse_non_empty_str(row.get("tier"), field=f"{field}[{idx}].tier").lower()
        indexed[tier] = row
    return indexed


def parse_tier_float_map(
    payload: dict[str, Any],
    *,
    field: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> dict[str, float]:
    raw = payload.get(field)
    if not isinstance(raw, dict):
        raise ValueError(f"{field} must be an object")
    values: dict[str, float] = {}
    for tier in TRACKED_TIERS:
        values[tier] = parse_float(
            raw.get(tier),
            field=f"{field}.{tier}",
            min_value=min_value,
            max_value=max_value,
        )
    return values


def parse_thresholds(payload: dict[str, Any]) -> dict[str, float | int]:
    thresholds = payload.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("thresholds must be an object")
    return {
        "min_blended_gross_margin_percent": parse_float(
            thresholds.get("min_blended_gross_margin_percent"),
            field="thresholds.min_blended_gross_margin_percent",
            min_value=0.0,
            max_value=100.0,
        ),
        "max_p95_tenant_llm_cogs_pct_mrr": parse_float(
            thresholds.get("max_p95_tenant_llm_cogs_pct_mrr"),
            field="thresholds.max_p95_tenant_llm_cogs_pct_mrr",
            min_value=0.0,
        ),
        "max_annual_discount_impact_percent": parse_float(
            thresholds.get("max_annual_discount_impact_percent"),
            field="thresholds.max_annual_discount_impact_percent",
            min_value=0.0,
            max_value=100.0,
        ),
        "min_growth_to_pro_conversion_mom_delta_percent": parse_float(
            thresholds.get("min_growth_to_pro_conversion_mom_delta_percent"),
            field="thresholds.min_growth_to_pro_conversion_mom_delta_percent",
        ),
        "min_pro_to_enterprise_conversion_mom_delta_percent": parse_float(
            thresholds.get("min_pro_to_enterprise_conversion_mom_delta_percent"),
            field="thresholds.min_pro_to_enterprise_conversion_mom_delta_percent",
        ),
        "min_stress_margin_percent": parse_float(
            thresholds.get("min_stress_margin_percent"),
            field="thresholds.min_stress_margin_percent",
            min_value=0.0,
            max_value=100.0,
        ),
        "required_consecutive_margin_closes": parse_int(
            thresholds.get("required_consecutive_margin_closes", 2),
            field="thresholds.required_consecutive_margin_closes",
            min_value=1,
        ),
    }


def parse_close_history(payload: dict[str, Any]) -> list[dict[str, Any]]:
    raw = payload.get("close_history")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("close_history must be an array")

    parsed: list[dict[str, Any]] = []
    for idx, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"close_history[{idx}] must be an object")
        parsed.append(
            {
                "month": parse_non_empty_str(
                    item.get("month"),
                    field=f"close_history[{idx}].month",
                ),
                "blended_gross_margin_percent": parse_float(
                    item.get("blended_gross_margin_percent"),
                    field=f"close_history[{idx}].blended_gross_margin_percent",
                    min_value=0.0,
                    max_value=100.0,
                ),
            }
        )
    return parsed


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return

    fieldnames = list(rows[0].keys())
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
