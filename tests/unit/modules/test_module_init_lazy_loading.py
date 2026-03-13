from __future__ import annotations

import importlib
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from types import ModuleType


@contextmanager
def _reload_without_children(
    package_name: str, child_modules: list[str]
) -> Iterator[ModuleType]:
    saved_children = {
        child: sys.modules.get(child) for child in child_modules if child in sys.modules
    }
    package = importlib.import_module(package_name)

    try:
        for child in child_modules:
            sys.modules.pop(child, None)
        yield importlib.reload(package)
    finally:
        for child in child_modules:
            sys.modules.pop(child, None)
        sys.modules.update(saved_children)


def test_optimization_module_init_is_lazy() -> None:
    with _reload_without_children(
        "app.modules.optimization",
        [
            "app.modules.optimization.domain.remediation",
            "app.modules.optimization.domain.service",
            "app.modules.optimization.domain.factory",
        ],
    ) as module:
        assert "app.modules.optimization.domain.service" not in sys.modules
        _ = module.ZombieService
        assert "app.modules.optimization.domain.service" in sys.modules


def test_reporting_module_init_is_lazy() -> None:
    with _reload_without_children(
        "app.modules.reporting",
        [
            "app.modules.reporting.domain.aggregator",
            "app.modules.reporting.domain.calculator",
            "app.modules.reporting.domain.service",
            "app.modules.reporting.domain.attribution_engine",
        ],
    ) as module:
        assert "app.modules.reporting.domain.service" not in sys.modules
        _ = module.ReportingService
        assert "app.modules.reporting.domain.service" in sys.modules
