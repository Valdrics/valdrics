from __future__ import annotations

import copy
import re
from datetime import date, datetime, timedelta
from typing import Any, Callable, TYPE_CHECKING

from app.shared.core.pricing import PricingTier

if TYPE_CHECKING:
    from langchain_core.language_models.chat_models import BaseChatModel
    from app.schemas.costs import CloudUsageSummary


def strip_markdown(text: str) -> str:
    """Remove markdown code fence wrappers from model output."""
    pattern = r"^```(?:\w+)?\s*\n?(.*?)\n?```$"
    match = re.match(pattern, text.strip(), re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def resolve_output_token_ceiling(raw_limit: Any) -> int | None:
    if raw_limit is None:
        return None
    try:
        parsed = int(raw_limit)
    except (TypeError, ValueError):
        return None
    if parsed <= 0:
        return None
    return max(128, min(parsed, 32768))


def resolve_positive_limit(
    raw_limit: Any,
    *,
    minimum: int = 1,
    maximum: int = 1_000_000,
) -> int | None:
    if raw_limit is None:
        return None
    try:
        parsed = int(raw_limit)
    except (TypeError, ValueError):
        return None
    if parsed < minimum:
        return None
    return min(parsed, maximum)


def record_to_date(value: Any) -> date | None:
    raw = value
    if isinstance(value, dict):
        raw = value.get("date")
    else:
        raw = getattr(value, "date", None)

    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            return None
    return None


def apply_tier_analysis_shape_limits(
    usage_summary: "CloudUsageSummary",
    *,
    tenant_tier: PricingTier,
    get_tier_limit_fn: Callable[[PricingTier, str], Any],
) -> tuple["CloudUsageSummary", dict[str, int]]:
    """
    Enforce deterministic tier-based analysis shape limits.

    Order:
    1. Date window bound.
    2. Prompt-token-derived record bound.
    3. Explicit max-records bound.
    """
    limits: dict[str, int] = {}
    records = list(usage_summary.records)
    original_count = len(records)

    max_window_days = resolve_positive_limit(
        get_tier_limit_fn(tenant_tier, "llm_analysis_max_window_days"),
        maximum=3650,
    )
    if max_window_days:
        dated_records = [(record, record_to_date(record)) for record in records]
        valid_dates = [record_date for _, record_date in dated_records if record_date]
        if valid_dates:
            latest_date = max(valid_dates)
            cutoff = latest_date - timedelta(days=max_window_days - 1)
            records = [
                record
                for record, record_date in dated_records
                if record_date is None or record_date >= cutoff
            ]
            limits["max_window_days"] = max_window_days

    prompt_max_tokens = resolve_positive_limit(
        get_tier_limit_fn(tenant_tier, "llm_prompt_max_input_tokens"),
        minimum=256,
        maximum=131_072,
    )
    if prompt_max_tokens:
        limits["max_prompt_tokens"] = prompt_max_tokens

    max_records = resolve_positive_limit(
        get_tier_limit_fn(tenant_tier, "llm_analysis_max_records"),
        maximum=50_000,
    )
    if prompt_max_tokens:
        prompt_record_cap = max(1, prompt_max_tokens // 20)
        max_records = (
            prompt_record_cap if max_records is None else min(max_records, prompt_record_cap)
        )
    if max_records and len(records) > max_records:
        sortable_records = [(record, record_to_date(record) or date.min, idx) for idx, record in enumerate(records)]
        sortable_records.sort(key=lambda item: (item[1], item[2]))
        records = [record for record, _, _ in sortable_records[-max_records:]]
        limits["max_records"] = max_records

    if len(records) == original_count:
        limits["records_before"] = original_count
        limits["records_after"] = original_count
        return usage_summary, limits

    updated_summary = copy.copy(usage_summary)
    updated_summary.records = records
    limits["records_before"] = original_count
    limits["records_after"] = len(records)
    return updated_summary, limits


def bind_output_token_ceiling(llm: "BaseChatModel", max_output_tokens: int) -> Any:
    bind_fn = getattr(llm, "bind", None)
    if not callable(bind_fn):
        return None

    for kwargs in (
        {"max_tokens": max_output_tokens},
        {"max_output_tokens": max_output_tokens},
    ):
        try:
            return bind_fn(**kwargs)
        except TypeError:
            continue
        except (AttributeError, ValueError, RuntimeError):
            return None
    return None


def normalize_analysis_payload(llm_result: dict[str, Any]) -> dict[str, Any]:
    insights = llm_result.get("insights", [])
    recommendations = llm_result.get("recommendations", [])
    anomalies = llm_result.get("anomalies", [])
    forecast = llm_result.get("forecast", {})
    return {
        "insights": insights if isinstance(insights, list) else [],
        "recommendations": recommendations if isinstance(recommendations, list) else [],
        "anomalies": anomalies if isinstance(anomalies, list) else [],
        "forecast": forecast if isinstance(forecast, dict) else {},
    }
