from __future__ import annotations

import importlib
import sys


def _reload_without_children(package_name: str, child_modules: list[str]):
    for child in child_modules:
        sys.modules.pop(child, None)
    package = importlib.import_module(package_name)
    return importlib.reload(package)


def test_optimization_module_init_is_lazy() -> None:
    module = _reload_without_children(
        "app.modules.optimization",
        [
            "app.modules.optimization.domain.remediation",
            "app.modules.optimization.domain.service",
            "app.modules.optimization.domain.factory",
        ],
    )

    assert "app.modules.optimization.domain.service" not in sys.modules
    _ = module.ZombieService
    assert "app.modules.optimization.domain.service" in sys.modules


def test_reporting_module_init_is_lazy() -> None:
    module = _reload_without_children(
        "app.modules.reporting",
        [
            "app.modules.reporting.domain.aggregator",
            "app.modules.reporting.domain.calculator",
            "app.modules.reporting.domain.service",
            "app.modules.reporting.domain.attribution_engine",
        ],
    )

    assert "app.modules.reporting.domain.service" not in sys.modules
    _ = module.ReportingService
    assert "app.modules.reporting.domain.service" in sys.modules
