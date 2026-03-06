"""Reporting module exports with lazy loading to avoid import cascades."""

from __future__ import annotations

from typing import Any

__all__ = (
    "CostAggregator",
    "CarbonCalculator",
    "ReportingService",
    "AttributionEngine",
)


def __getattr__(name: str) -> Any:
    if name == "CostAggregator":
        from .domain.aggregator import CostAggregator

        return CostAggregator
    if name == "CarbonCalculator":
        from .domain.calculator import CarbonCalculator

        return CarbonCalculator
    if name == "ReportingService":
        from .domain.service import ReportingService

        return ReportingService
    if name == "AttributionEngine":
        from .domain.attribution_engine import AttributionEngine

        return AttributionEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
