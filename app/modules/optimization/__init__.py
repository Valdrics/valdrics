"""Optimization module exports with lazy loading.

Avoid importing heavy domain graphs at package import time, which can trigger
unrelated adapter/provider imports and side effects in lightweight call paths.
"""

from __future__ import annotations

from typing import Any

__all__ = ("RemediationService", "ZombieService", "ZombieDetectorFactory")


def __getattr__(name: str) -> Any:
    if name == "RemediationService":
        from .domain.remediation import RemediationService

        return RemediationService
    if name == "ZombieService":
        from .domain.service import ZombieService

        return ZombieService
    if name == "ZombieDetectorFactory":
        from .domain.factory import ZombieDetectorFactory

        return ZombieDetectorFactory
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
