"""Shared utilities for optimization cloud adapters."""

from __future__ import annotations


def resolve_google_api_error_base() -> type[Exception]:
    try:
        from google.api_core.exceptions import GoogleAPIError
    except ImportError:  # pragma: no cover - fallback for SDK-mocked test envs
        return Exception
    return GoogleAPIError


def build_google_recoverable_exceptions() -> tuple[type[Exception], ...]:
    return (
        resolve_google_api_error_base(),
        OSError,
        TimeoutError,
        ValueError,
    )
