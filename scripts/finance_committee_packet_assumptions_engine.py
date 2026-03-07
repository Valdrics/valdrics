"""Core assumptions derivation for finance committee packet generation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from scripts.finance_committee_packet_common import TRACKED_TIERS
from scripts.finance_committee_packet_engine import (
    build_tier_unit_economics,
    compute_metrics,
)


def _clamp(value: float, *, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _safe_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _safe_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _index_rows(rows: Any, *, field: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        raise ValueError(f"{field} must be an array")
    indexed: dict[str, dict[str, Any]] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f"{field}[{idx}] must be an object")
        tier = str(row.get("tier", "")).strip().lower()
        if not tier:
            continue
        indexed[tier] = row
    return indexed


def derive_assumptions_inputs(
    *,
    telemetry: dict[str, Any],
) -> dict[str, Any]:
    pricing_reference = telemetry.get("pricing_reference")
    if not isinstance(pricing_reference, dict):
        raise ValueError("telemetry.pricing_reference must be an object")

    subscriptions = _index_rows(
        telemetry.get("tier_subscription_snapshot"),
        field="telemetry.tier_subscription_snapshot",
    )
    llm_usage = _index_rows(
        telemetry.get("tier_llm_usage"),
        field="telemetry.tier_llm_usage",
    )

    annual_mix_by_tier: dict[str, float] = {}
    infra_cogs_pct_by_tier: dict[str, float] = {}
    support_cogs_per_active_sub_by_tier: dict[str, float] = {}
    active_subscriptions_by_tier: dict[str, int] = {}

    total_llm_cogs = 0.0
    total_gross_mrr = 0.0

    for tier in TRACKED_TIERS:
        pricing = pricing_reference.get(tier)
        if not isinstance(pricing, dict):
            raise ValueError(f"telemetry.pricing_reference.{tier} must be an object")

        monthly_price = _safe_float(pricing.get("monthly_price_usd"), default=0.0)
        annual_factor = _safe_float(pricing.get("annual_monthly_factor"), default=1.0)
        annual_factor = _clamp(annual_factor, minimum=0.5, maximum=1.0)

        subscription = subscriptions.get(tier, {})
        active_subscriptions = max(
            0,
            _safe_int(subscription.get("active_subscriptions"), default=0),
        )
        dunning_events = max(0, _safe_int(subscription.get("dunning_events"), default=0))
        active_subscriptions_by_tier[tier] = active_subscriptions

        llm = llm_usage.get(tier, {})
        llm_cogs = max(0.0, _safe_float(llm.get("total_cost_usd"), default=0.0))
        gross_mrr = max(0.0, monthly_price * float(active_subscriptions))
        llm_cogs_pct_of_mrr = (llm_cogs / gross_mrr * 100.0) if gross_mrr > 0.0 else 0.0

        discount = max(0.0, 1.0 - annual_factor)
        base_mix = 0.42 + min(0.25, active_subscriptions / 400.0) + min(0.12, discount * 0.8)
        if tier == "enterprise":
            base_mix -= 0.12
        annual_mix_by_tier[tier] = round(
            _clamp(base_mix, minimum=0.25, maximum=0.82),
            2,
        )

        infra_base = 5.0 + (llm_cogs_pct_of_mrr * 0.35)
        if tier in {"starter", "growth"}:
            infra_base += 0.3
        infra_cogs_pct_by_tier[tier] = round(
            _clamp(infra_base, minimum=4.5, maximum=15.0),
            2,
        )

        dunning_rate = float(dunning_events) / max(float(active_subscriptions), 1.0)
        support_base = 4.0 + (monthly_price * 0.018) + (dunning_rate * 6.0)
        tier_lift = {
            "starter": 1.0,
            "growth": 1.2,
            "pro": 1.5,
            "enterprise": 1.8,
        }[tier]
        support_cogs_per_active_sub_by_tier[tier] = round(
            _clamp(support_base * tier_lift, minimum=4.0, maximum=42.0),
            2,
        )

        total_llm_cogs += llm_cogs
        total_gross_mrr += gross_mrr

    mean_support = sum(support_cogs_per_active_sub_by_tier.values()) / float(len(TRACKED_TIERS))
    support_cogs_per_dunning_event_usd = round(
        _clamp(mean_support * 1.4, minimum=12.0, maximum=45.0),
        2,
    )

    growth_active = float(active_subscriptions_by_tier["growth"])
    pro_active = float(active_subscriptions_by_tier["pro"])
    enterprise_active = float(active_subscriptions_by_tier["enterprise"])
    growth_to_pro_ratio = pro_active / max(growth_active, 1.0)
    pro_to_enterprise_ratio = enterprise_active / max(pro_active, 1.0)

    conversion_signals = {
        "growth_to_pro_conversion_mom_delta_percent": round(
            _clamp((growth_to_pro_ratio - 0.25) * 0.8, minimum=-3.0, maximum=3.0),
            4,
        ),
        "pro_to_enterprise_conversion_mom_delta_percent": round(
            _clamp((pro_to_enterprise_ratio - 0.15) * 0.8, minimum=-3.0, maximum=3.0),
            4,
        ),
    }

    llm_cogs_share = total_llm_cogs / max(total_gross_mrr, 1.0)
    stress_infra_multiplier = round(
        _clamp(1.5 + (llm_cogs_share * 2.0), minimum=1.4, maximum=2.5),
        2,
    )

    tier_unit_economics = build_tier_unit_economics(
        telemetry=telemetry,
        annual_mix_by_tier=annual_mix_by_tier,
        infra_cogs_pct_by_tier=infra_cogs_pct_by_tier,
        support_cogs_per_subscription_by_tier=support_cogs_per_active_sub_by_tier,
        support_cogs_per_dunning_event_usd=support_cogs_per_dunning_event_usd,
    )
    metrics, totals = compute_metrics(
        tier_unit_economics=tier_unit_economics,
        telemetry=telemetry,
        conversion_signals=conversion_signals,
        stress_infra_multiplier=stress_infra_multiplier,
    )

    min_blended = round(
        _clamp(
            metrics["blended_gross_margin_percent"] - 2.5,
            minimum=60.0,
            maximum=86.0,
        ),
        2,
    )
    thresholds = {
        "min_blended_gross_margin_percent": min_blended,
        "max_p95_tenant_llm_cogs_pct_mrr": round(
            _clamp(
                max(
                    metrics["p95_tenant_llm_cogs_pct_mrr"] + 2.0,
                    metrics["p95_tenant_llm_cogs_pct_mrr"] * 1.2,
                ),
                minimum=6.0,
                maximum=35.0,
            ),
            2,
        ),
        "max_annual_discount_impact_percent": round(
            _clamp(
                max(metrics["annual_discount_impact_percent"] + 3.0, 12.0),
                minimum=10.0,
                maximum=35.0,
            ),
            2,
        ),
        "min_growth_to_pro_conversion_mom_delta_percent": round(
            _clamp(
                metrics["growth_to_pro_conversion_mom_delta_percent"] - 0.2,
                minimum=-5.0,
                maximum=5.0,
            ),
            4,
        ),
        "min_pro_to_enterprise_conversion_mom_delta_percent": round(
            _clamp(
                metrics["pro_to_enterprise_conversion_mom_delta_percent"] - 0.2,
                minimum=-5.0,
                maximum=5.0,
            ),
            4,
        ),
        "min_stress_margin_percent": round(
            _clamp(metrics["stress_margin_percent"] - 3.0, minimum=45.0, maximum=86.0),
            2,
        ),
        "required_consecutive_margin_closes": 2,
    }

    window = telemetry.get("window")
    if not isinstance(window, dict):
        raise ValueError("telemetry.window must be an object")
    now_utc = datetime.now(timezone.utc)
    current_label = str(window.get("label", "")).strip() or now_utc.date().isoformat()
    previous_month = (now_utc.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
    close_history = [
        {
            "month": previous_month,
            "blended_gross_margin_percent": round(
                _clamp(
                    max(metrics["blended_gross_margin_percent"] + 1.0, min_blended + 0.5),
                    minimum=45.0,
                    maximum=95.0,
                ),
                2,
            ),
        }
    ]

    scenario_models = {
        "price_sensitivity": [
            {
                "name": "baseline",
                "subscription_multipliers_by_tier": {tier: 1.0 for tier in TRACKED_TIERS},
                "monthly_price_multipliers_by_tier": {tier: 1.0 for tier in TRACKED_TIERS},
            },
            {
                "name": "pro_price_plus_15_growth_retention",
                "subscription_multipliers_by_tier": {
                    "starter": 1.0,
                    "growth": 0.99,
                    "pro": 0.96,
                    "enterprise": 1.02,
                },
                "monthly_price_multipliers_by_tier": {
                    "starter": 1.0,
                    "growth": 1.0,
                    "pro": 1.15,
                    "enterprise": 1.0,
                },
            },
            {
                "name": "enterprise_expansion_signal",
                "subscription_multipliers_by_tier": {
                    "starter": 1.0,
                    "growth": 1.01,
                    "pro": 1.03,
                    "enterprise": 1.08,
                },
                "monthly_price_multipliers_by_tier": {tier: 1.0 for tier in TRACKED_TIERS},
            },
        ]
    }

    hosted_arr_run_rate = totals["total_effective_mrr_usd"] * 12.0
    self_hosted_tco_inputs = {
        "annual_staffing_usd": round(max(220_000.0, hosted_arr_run_rate * 0.28), 2),
        "annual_oncall_usd": round(max(70_000.0, hosted_arr_run_rate * 0.055), 2),
        "annual_security_compliance_usd": round(
            max(45_000.0, hosted_arr_run_rate * 0.035), 2
        ),
        "annual_infra_ops_usd": round(max(55_000.0, hosted_arr_run_rate * 0.045), 2),
        "annual_tooling_usd": round(max(22_000.0, hosted_arr_run_rate * 0.018), 2),
    }

    return {
        "captured_at": now_utc.replace(microsecond=0).isoformat(),
        "source_window_label": current_label,
        "thresholds": thresholds,
        "annual_mix_by_tier": annual_mix_by_tier,
        "infra_cogs_percent_of_effective_mrr_by_tier": infra_cogs_pct_by_tier,
        "support_cogs_per_active_subscription_usd_by_tier": (
            support_cogs_per_active_sub_by_tier
        ),
        "support_cogs_per_dunning_event_usd": support_cogs_per_dunning_event_usd,
        "conversion_signals": conversion_signals,
        "stress_scenario": {
            "infra_cost_multiplier": stress_infra_multiplier,
        },
        "close_history": close_history,
        "scenario_models": scenario_models,
        "self_hosted_tco_inputs": self_hosted_tco_inputs,
    }
