"""Scenario modeling for finance committee packet generation."""

from __future__ import annotations

from typing import Any

from scripts.finance_committee_packet_common import (
    TRACKED_TIERS,
    parse_float,
    parse_non_empty_str,
    safe_margin_percent,
)


def compute_scenario_rows(
    *,
    baseline_rows: list[dict[str, Any]],
    annual_mix_by_tier: dict[str, float],
    assumptions: dict[str, Any],
) -> list[dict[str, Any]]:
    scenario_models = assumptions.get("scenario_models")
    if not isinstance(scenario_models, dict):
        return []
    scenario_rows_raw = scenario_models.get("price_sensitivity")
    if not isinstance(scenario_rows_raw, list):
        return []

    baseline_by_tier = {str(row["tier"]): row for row in baseline_rows}
    output: list[dict[str, Any]] = []
    for idx, scenario in enumerate(scenario_rows_raw):
        if not isinstance(scenario, dict):
            raise ValueError(f"scenario_models.price_sensitivity[{idx}] must be an object")

        name = parse_non_empty_str(
            scenario.get("name"),
            field=f"scenario_models.price_sensitivity[{idx}].name",
        )
        sub_mults = scenario.get("subscription_multipliers_by_tier")
        if not isinstance(sub_mults, dict):
            raise ValueError(
                "scenario_models.price_sensitivity[{idx}].subscription_multipliers_by_tier "
                "must be an object".format(idx=idx)
            )
        price_mults = scenario.get("monthly_price_multipliers_by_tier")
        if not isinstance(price_mults, dict):
            raise ValueError(
                "scenario_models.price_sensitivity[{idx}].monthly_price_multipliers_by_tier "
                "must be an object".format(idx=idx)
            )

        total_effective = 0.0
        total_cogs = 0.0
        for tier in TRACKED_TIERS:
            baseline = baseline_by_tier[tier]
            sub_mult = parse_float(
                sub_mults.get(tier),
                field=(
                    "scenario_models.price_sensitivity[{idx}]."
                    "subscription_multipliers_by_tier.{tier}"
                ).format(idx=idx, tier=tier),
                min_value=0.0,
            )
            price_mult = parse_float(
                price_mults.get(tier),
                field=(
                    "scenario_models.price_sensitivity[{idx}]."
                    "monthly_price_multipliers_by_tier.{tier}"
                ).format(idx=idx, tier=tier),
                min_value=0.0,
            )
            active = float(baseline["active_subscriptions"]) * sub_mult
            monthly_price = (
                float(baseline["mrr_usd"]) / max(float(baseline["active_subscriptions"]), 1.0)
            ) * price_mult
            gross_mrr = active * monthly_price
            annual_factor = 1.0 - annual_mix_by_tier[tier] * (
                1.0
                - parse_float(
                    assumptions["telemetry_pricing_factors"][tier],
                    field=f"telemetry_pricing_factors.{tier}",
                    min_value=0.0,
                    max_value=1.0,
                )
            )
            effective_mrr = gross_mrr * annual_factor

            llm_per_sub = float(baseline["llm_cogs_usd"]) / max(
                float(baseline["active_subscriptions"]), 1.0
            )
            infra_per_effective = float(baseline["infra_cogs_usd"]) / max(
                float(baseline["effective_mrr_usd"]), 1.0
            )
            support_per_sub = float(baseline["support_cogs_usd"]) / max(
                float(baseline["active_subscriptions"]), 1.0
            )

            llm_cogs = llm_per_sub * active
            infra_cogs = infra_per_effective * effective_mrr
            support_cogs = support_per_sub * active

            total_effective += effective_mrr
            total_cogs += llm_cogs + infra_cogs + support_cogs

        output.append(
            {
                "scenario": name,
                "effective_mrr_usd": round(total_effective, 2),
                "projected_margin_percent": round(
                    safe_margin_percent(total_effective, total_cogs), 2
                ),
            }
        )
    return output
