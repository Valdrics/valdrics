from __future__ import annotations

import pytest

from scripts.finance_committee_packet_assumptions_engine import (
    derive_assumptions_inputs,
)
from scripts.finance_committee_packet_common import TRACKED_TIERS


def _telemetry_payload() -> dict[str, object]:
    pricing_reference = {
        "free": {"monthly_price_usd": 0.0, "annual_monthly_factor": 1.0},
        "starter": {"monthly_price_usd": 49.0, "annual_monthly_factor": 0.84},
        "growth": {"monthly_price_usd": 149.0, "annual_monthly_factor": 0.83},
        "pro": {"monthly_price_usd": 299.0, "annual_monthly_factor": 0.82},
        "enterprise": {"monthly_price_usd": 799.0, "annual_monthly_factor": 0.81},
    }
    tier_subscription_snapshot = []
    tier_llm_usage = []
    for index, tier in enumerate(TRACKED_TIERS):
        tier_subscription_snapshot.append(
            {
                "tier": tier,
                "active_subscriptions": 20 + (index * 10),
                "dunning_events": index,
            }
        )
        tier_llm_usage.append(
            {
                "tier": tier,
                "total_cost_usd": 100.0 + (index * 25.0),
                "tenant_monthly_cost_percentiles_usd": {
                    "p50": 1.0 + index,
                    "p95": 3.0 + index,
                    "p99": 5.0 + index,
                },
            }
        )
    return {
        "pricing_reference": pricing_reference,
        "tier_subscription_snapshot": tier_subscription_snapshot,
        "tier_llm_usage": tier_llm_usage,
        "window": {"label": "2026-03"},
        "free_tier_margin_watch": {
            "free_total_tenants": 100,
            "free_active_subscriptions": 20,
            "free_total_llm_cost_usd": 100.0,
            "free_p95_tenant_monthly_cost_usd": 5.0,
            "starter_gross_mrr_usd": 1000.0,
            "free_llm_cost_pct_of_starter_gross_mrr": 10.0,
            "max_allowed_pct_of_starter_gross_mrr": 100.0,
        },
    }


def test_derive_assumptions_inputs_emits_expected_shape() -> None:
    payload = derive_assumptions_inputs(telemetry=_telemetry_payload())

    assert payload["source_window_label"] == "2026-03"
    assert payload["thresholds"]["required_consecutive_margin_closes"] == 2
    assert set(payload["annual_mix_by_tier"]) == set(TRACKED_TIERS)
    assert set(payload["infra_cogs_percent_of_effective_mrr_by_tier"]) == set(TRACKED_TIERS)
    assert set(payload["support_cogs_per_active_subscription_usd_by_tier"]) == set(TRACKED_TIERS)
    assert len(payload["scenario_models"]["price_sensitivity"]) == 3


def test_derive_assumptions_inputs_rejects_invalid_subscription_rows() -> None:
    telemetry = _telemetry_payload()
    telemetry["tier_subscription_snapshot"] = ["invalid-row"]
    with pytest.raises(
        ValueError,
        match=r"telemetry\.tier_subscription_snapshot\[0\] must be an object",
    ):
        derive_assumptions_inputs(telemetry=telemetry)
