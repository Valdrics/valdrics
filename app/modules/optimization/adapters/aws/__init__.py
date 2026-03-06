"""AWS adapter exports with lazy loading."""

from __future__ import annotations

from typing import Any

__all__ = ("AWSZombieDetector",)


def __getattr__(name: str) -> Any:
    if name == "AWSZombieDetector":
        from .detector import AWSZombieDetector

        return AWSZombieDetector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
