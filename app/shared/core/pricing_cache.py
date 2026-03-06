from __future__ import annotations

import time
import uuid
from threading import Lock
from typing import Union

from sqlalchemy.exc import SQLAlchemyError

from app.shared.core.pricing_types import PricingTier

__all__ = [
    "TENANT_TIER_LOOKUP_RECOVERABLE_EXCEPTIONS",
    "runtime_cache_get",
    "runtime_cache_set",
    "clear_tenant_tier_cache",
]

_TENANT_TIER_CACHE_TTL_SECONDS = 60.0
_TENANT_TIER_CACHE_MAX_ENTRIES = 4096
_tenant_tier_runtime_cache: dict[str, tuple[float, PricingTier]] = {}
_tenant_tier_runtime_cache_lock = Lock()

TENANT_TIER_LOOKUP_RECOVERABLE_EXCEPTIONS = (
    RuntimeError,
    ValueError,
    TypeError,
    SQLAlchemyError,
)


def runtime_cache_get(tenant_key: str, *, now: float | None = None) -> PricingTier | None:
    with _tenant_tier_runtime_cache_lock:
        cached_entry = _tenant_tier_runtime_cache.get(tenant_key)
        if cached_entry is None:
            return None
        cached_at, cached_tier = cached_entry
        current = time.monotonic() if now is None else now
        if current - cached_at > _TENANT_TIER_CACHE_TTL_SECONDS:
            _tenant_tier_runtime_cache.pop(tenant_key, None)
            return None
        return cached_tier


def runtime_cache_set(tenant_key: str, tier: PricingTier, *, now: float | None = None) -> None:
    current = time.monotonic() if now is None else now
    with _tenant_tier_runtime_cache_lock:
        _tenant_tier_runtime_cache[tenant_key] = (current, tier)
        if len(_tenant_tier_runtime_cache) <= _TENANT_TIER_CACHE_MAX_ENTRIES:
            return

        expiry_cutoff = current - _TENANT_TIER_CACHE_TTL_SECONDS
        for key, (cached_at, _) in list(_tenant_tier_runtime_cache.items()):
            if cached_at <= expiry_cutoff:
                _tenant_tier_runtime_cache.pop(key, None)

        while len(_tenant_tier_runtime_cache) > _TENANT_TIER_CACHE_MAX_ENTRIES:
            oldest_key = next(iter(_tenant_tier_runtime_cache))
            _tenant_tier_runtime_cache.pop(oldest_key, None)


def clear_tenant_tier_cache(tenant_id: Union[str, uuid.UUID, None] = None) -> None:
    """
    Clear process-level tenant tier cache.

    `tenant_id=None` clears all entries. Supplying a tenant id removes one entry.
    """
    with _tenant_tier_runtime_cache_lock:
        if tenant_id is None:
            _tenant_tier_runtime_cache.clear()
            return
        _tenant_tier_runtime_cache.pop(str(tenant_id), None)
