"""Shared rightsizing evaluation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Sequence


@dataclass(frozen=True)
class UtilizationEvaluation:
    has_data: bool
    below_threshold: bool
    max_observed: float


def utc_window(days: int) -> tuple[datetime, datetime]:
    end_time = datetime.now(timezone.utc)
    return end_time - timedelta(days=days), end_time


def is_small_shape(shape_name: str, *, tokens: Sequence[str]) -> bool:
    normalized = shape_name.strip().lower()
    return any(token.lower() in normalized for token in tokens)


def evaluate_max_samples(
    samples: Iterable[float],
    *,
    threshold: float,
) -> UtilizationEvaluation:
    has_data = False
    below_threshold = True
    max_observed = 0.0
    for raw_value in samples:
        try:
            value = float(raw_value)
        except (TypeError, ValueError):
            continue
        has_data = True
        if value > max_observed:
            max_observed = value
        if value >= threshold:
            below_threshold = False
            break
    return UtilizationEvaluation(
        has_data=has_data,
        below_threshold=below_threshold,
        max_observed=max_observed,
    )


def build_rightsizing_finding(
    *,
    resource_id: str,
    resource_type: str,
    resource_name: str,
    region: str,
    monthly_cost: float,
    current_size: str,
    max_cpu_percent: float,
    threshold_percent: float,
    action: str,
    confidence_score: float = 0.85,
) -> dict[str, Any]:
    return {
        "resource_id": resource_id,
        "resource_type": resource_type,
        "resource_name": resource_name,
        "region": region,
        "monthly_cost": monthly_cost,
        "recommendation": f"Resize {current_size} (Max CPU {max_cpu_percent:.1f}%)",
        "action": action,
        "utilization_percent": max_cpu_percent,
        "confidence_score": confidence_score,
        "explainability_notes": (
            f"Resource {current_size} had Max CPU of {max_cpu_percent:.1f}% "
            f"over the last 7 days (Threshold: {threshold_percent:.1f}%)."
        ),
    }
