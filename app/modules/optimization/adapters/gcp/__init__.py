"""GCP adapter exports with lazy loading."""

from __future__ import annotations

from typing import Any

__all__ = ("GCPZombieDetector",)


def __getattr__(name: str) -> Any:
    if name == "GCPZombieDetector":
        from .detector import GCPZombieDetector

        return GCPZombieDetector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
