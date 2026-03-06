"""Optimization domain exports with lazy loading."""

from __future__ import annotations

from typing import Any

from .registry import registry as plugins

__all__ = (
    "ZombieService",
    "OptimizationService",
    "ZombieDetector",
    "ZombieDetectorFactory",
    "RemediationService",
    "plugins",
)


def __getattr__(name: str) -> Any:
    if name == "ZombieService":
        from .service import ZombieService

        return ZombieService
    if name == "OptimizationService":
        from .service import OptimizationService

        return OptimizationService
    if name == "ZombieDetectorFactory":
        from .factory import ZombieDetectorFactory

        return ZombieDetectorFactory
    if name == "RemediationService":
        from .remediation import RemediationService

        return RemediationService
    if name == "ZombieDetector":
        from app.modules.optimization.adapters.aws.detector import AWSZombieDetector

        return AWSZombieDetector
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
