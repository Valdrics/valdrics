from __future__ import annotations

from typing import Any

from app.modules.reporting.domain.pricing.service import PricingQuote


def serialize_pricing_quote(quote: PricingQuote) -> dict[str, Any]:
    metadata = dict(quote.pricing_metadata or {})
    covered_regions = metadata.get("covered_regions")
    if isinstance(covered_regions, tuple):
        metadata["covered_regions"] = list(covered_regions)

    return {
        "source": quote.source,
        "requested_region": quote.requested_region,
        "effective_region": quote.effective_region,
        "hourly_rate_usd": round(float(quote.hourly_rate_usd), 6),
        "monthly_cost_usd": round(float(quote.monthly_cost_usd), 2),
        "coverage_scope": metadata.get("coverage_scope"),
        "pricing_confidence": metadata.get("pricing_confidence"),
        "match_strategy": metadata.get("match_strategy"),
        "catalog_probe": metadata.get("catalog_probe"),
        "coverage_limitations": metadata.get("coverage_limitations"),
        "metadata": metadata,
    }


def build_pricing_fields(quote: PricingQuote) -> dict[str, Any]:
    return {
        "monthly_cost": round(float(quote.monthly_cost_usd), 2),
        "pricing_evidence": serialize_pricing_quote(quote),
    }
