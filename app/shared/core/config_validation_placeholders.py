"""Helpers for detecting unresolved managed-environment placeholder values."""

from __future__ import annotations

PLACEHOLDER_PREFIX = "REPLACE_WITH_"


def contains_managed_placeholder(value: object) -> bool:
    """Return True when a value still contains a managed scaffold placeholder."""
    if value is None:
        return False
    if isinstance(value, dict):
        return any(contains_managed_placeholder(item) for item in value.values())
    if isinstance(value, (list, tuple, set, frozenset)):
        return any(contains_managed_placeholder(item) for item in value)
    return PLACEHOLDER_PREFIX in str(value)


def require_no_managed_placeholder(value: object, *, name: str) -> None:
    """Raise when a runtime setting still contains a scaffold placeholder."""
    if contains_managed_placeholder(value):
        raise ValueError(f"{name} contains unresolved placeholder values.")


__all__ = [
    "PLACEHOLDER_PREFIX",
    "contains_managed_placeholder",
    "require_no_managed_placeholder",
]
