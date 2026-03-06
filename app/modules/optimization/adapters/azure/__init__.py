"""Azure adapter exports with lazy loading."""

from __future__ import annotations

from typing import Any

__all__ = ("AzureZombieDetector",)


def __getattr__(name: str) -> Any:
    if name == "AzureZombieDetector":
        from .detector import AzureZombieDetector

        return AzureZombieDetector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
