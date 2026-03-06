"""Azure plugin registration loader.

This module intentionally avoids hard failing when optional SDK dependencies are
missing in lightweight test environments. Successfully imported plugins still
register themselves via the global registry.
"""

from __future__ import annotations

import importlib

import structlog

logger = structlog.get_logger()

_PLUGIN_MODULES: tuple[str, ...] = (
    "compute",
    "storage",
    "network",
    "database",
    "containers",
    "ai",
    "rightsizing",
)


def load_plugins() -> None:
    for module_name in _PLUGIN_MODULES:
        try:
            importlib.import_module(f"{__name__}.{module_name}")
        except (ModuleNotFoundError, ImportError, AttributeError) as exc:
            logger.debug(
                "azure_plugin_module_skipped",
                module=module_name,
                error=str(exc),
            )


__all__ = ("load_plugins",)
