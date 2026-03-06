"""GCP plugin registration loader with optional dependency tolerance."""

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
    "search",
    "rightsizing",
)


def load_plugins() -> None:
    for module_name in _PLUGIN_MODULES:
        try:
            importlib.import_module(f"{__name__}.{module_name}")
        except (ModuleNotFoundError, ImportError, AttributeError) as exc:
            logger.debug(
                "gcp_plugin_module_skipped",
                module=module_name,
                error=str(exc),
            )


__all__ = ("load_plugins",)
