"""
Cost result caching for tenant-scoped cost and analysis responses.

Repo-owned runtime support is process-local only:
1. Process-local in-memory cache
2. Automatic TTL management
3. Targeted cache invalidation support

The supported managed Cloud Run profile remains cacheless by default, so this
adapter intentionally avoids shared external cache dependencies.
"""

import json
import hashlib
import asyncio
from abc import ABC, abstractmethod
from datetime import date, timedelta, datetime, timezone
from typing import Any, Optional
import structlog

logger = structlog.get_logger()


def _safe_json_loads(raw_payload: Any, *, key: str) -> Any | None:
    """Decode cached JSON defensively to avoid malformed payload crashes."""
    if raw_payload is None:
        return None

    if isinstance(raw_payload, bytes):
        try:
            raw_payload = raw_payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            logger.warning(
                "cost_cache_payload_invalid_encoding", key=key, error=str(exc)
            )
            return None

    if not isinstance(raw_payload, str):
        logger.warning(
            "cost_cache_payload_unexpected_type",
            key=key,
            payload_type=type(raw_payload).__name__,
        )
        return None

    try:
        return json.loads(raw_payload)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("cost_cache_payload_invalid_json", key=key, error=str(exc))
        return None


class CacheBackend(ABC):
    """Abstract base class for cache backends."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache."""
        ...

    @abstractmethod
    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        """Set value in cache with TTL."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        ...

    @abstractmethod
    async def delete_pattern(self, pattern: str) -> int:
        """Delete keys matching pattern. Returns count deleted."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if backend is healthy."""
        ...


class InMemoryCache(CacheBackend):
    """
    Process-local cache for tests, local development, and cacheless fallback.

    Note: Not suitable for multi-instance shared-state deployments.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, datetime | None]] = {}

    async def get(self, key: str) -> Optional[str]:
        if key not in self._store:
            return None

        value, expires_at = self._store[key]
        if expires_at and datetime.now(timezone.utc) > expires_at:
            del self._store[key]
            return None

        return value

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
        self._store[key] = (value, expires_at)

    async def delete(self, key: str) -> None:
        self._store.pop(key, None)

    async def delete_pattern(self, pattern: str) -> int:
        # Simple pattern matching (prefix only)
        prefix = pattern.rstrip("*")
        to_delete = [k for k in self._store if k.startswith(prefix)]
        for k in to_delete:
            del self._store[k]
        return len(to_delete)

    async def health_check(self) -> bool:
        return True


class CostCache:
    """
    High-level caching API for cost data.

    Usage:
        cache = await get_cost_cache()

        # Check cache first
        cached = await cache.get_daily_costs(tenant_id, start, end)
        if cached:
            return cached

        # Fetch from API
        costs = await adapter.get_daily_costs(start, end)

        # Store in cache
        await cache.set_daily_costs(tenant_id, start, end, costs)
    """

    # Cache TTLs
    TTL_DAILY_COSTS = 3600  # 1 hour
    TTL_ZOMBIES = 1800  # 30 minutes
    TTL_ANALYSIS = 7200  # 2 hours

    def __init__(self, backend: CacheBackend):
        self.backend = backend

    def _generate_key(self, prefix: str, tenant_id: str, *args: object) -> str:
        """Generate a unique cache key."""
        key_parts = [prefix, tenant_id] + [str(a) for a in args]
        key_string = ":".join(key_parts)
        # Switch from MD5 to SHA256 for stronger collision resistance (SEC-05)
        digest = hashlib.sha256(key_string.encode()).hexdigest()
        # Keep tenant and prefix in plaintext to allow precise invalidation patterns.
        return f"valdrics:{tenant_id}:{prefix}:{digest}"

    def _tenant_pattern(self, tenant_id: str) -> str:
        """Generate pattern for all tenant keys."""
        return f"valdrics:{tenant_id}:*"

    # Daily Costs
    async def get_daily_costs(
        self, tenant_id: str, start_date: date, end_date: date
    ) -> Optional[list[dict[str, Any]]]:
        """Get cached daily costs if available."""
        key = self._generate_key("costs", tenant_id, start_date, end_date)
        cached = await self.backend.get(key)

        if cached is not None:
            logger.debug("cache_hit", type="daily_costs", tenant_id=tenant_id)
            return _safe_json_loads(cached, key=key)

        logger.debug("cache_miss", type="daily_costs", tenant_id=tenant_id)
        return None

    async def set_daily_costs(
        self,
        tenant_id: str,
        start_date: date,
        end_date: date,
        costs: list[dict[str, Any]],
    ) -> None:
        """Cache daily costs."""
        key = self._generate_key("costs", tenant_id, start_date, end_date)
        await self.backend.set(key, json.dumps(costs), self.TTL_DAILY_COSTS)
        logger.debug("cache_set", type="daily_costs", records=len(costs))

    # Zombie Scans
    async def get_zombie_scan(
        self, tenant_id: str, region: str
    ) -> Optional[dict[str, Any]]:
        """Get cached zombie scan if available."""
        key = self._generate_key("zombies", tenant_id, region)
        cached = await self.backend.get(key)

        if cached is not None:
            logger.debug("cache_hit", type="zombie_scan", region=region)
            return _safe_json_loads(cached, key=key)
        return None

    async def set_zombie_scan(
        self, tenant_id: str, region: str, zombies: dict[str, Any]
    ) -> None:
        """Cache zombie scan results."""
        key = self._generate_key("zombies", tenant_id, region)
        await self.backend.set(key, json.dumps(zombies), self.TTL_ZOMBIES)

    # LLM Analysis
    async def get_analysis(
        self, tenant_id: str, analysis_hash: str
    ) -> Optional[dict[str, Any]]:
        """Get cached LLM analysis if available."""
        key = self._generate_key("analysis", tenant_id, analysis_hash)
        cached = await self.backend.get(key)

        if cached is not None:
            logger.debug("cache_hit", type="analysis")
            return _safe_json_loads(cached, key=key)
        return None

    async def set_analysis(
        self, tenant_id: str, analysis_hash: str, result: dict[str, Any]
    ) -> None:
        """Cache LLM analysis results."""
        key = self._generate_key("analysis", tenant_id, analysis_hash)
        await self.backend.set(key, json.dumps(result), self.TTL_ANALYSIS)

    # Invalidation
    async def invalidate_tenant(self, tenant_id: str) -> int:
        """
        Invalidate all cache entries for a tenant.

        Use on:
        - AWS connection change
        - Settings update
        - Manual refresh request
        """
        pattern = self._tenant_pattern(tenant_id)
        deleted = await self.backend.delete_pattern(pattern)
        logger.info("cache_invalidated", tenant_id=tenant_id, keys_deleted=deleted)
        return deleted

    async def invalidate_zombies(self, tenant_id: str) -> int:
        """Invalidate zombie scan cache for fresh scan."""
        pattern = f"valdrics:{tenant_id}:zombies:*"
        deleted = await self.backend.delete_pattern(pattern)
        logger.debug("zombie_cache_invalidated", tenant_id=tenant_id, keys=deleted)
        return deleted

    # Health
    async def health_check(self) -> dict[str, Any]:
        """Check cache health for monitoring."""
        healthy = await self.backend.health_check()
        return {
            "healthy": healthy,
            "backend": "memory",
            "ttl_costs": self.TTL_DAILY_COSTS,
            "ttl_zombies": self.TTL_ZOMBIES,
        }


# Factory
_cache_instance: Optional[CostCache] = None
_cache_instance_lock = asyncio.Lock()


async def get_cost_cache() -> CostCache:
    """
    Factory to get cache instance.

    The repo-owned runtime contract is process-local only. Keep a singleton
    in-memory backend to avoid unnecessary object churn in hot paths.
    """
    global _cache_instance

    cache = _cache_instance
    if cache is not None:
        return cache

    async with _cache_instance_lock:
        cache = _cache_instance
        if cache is not None:
            return cache

        backend = InMemoryCache()
        logger.info("cost_cache_initialized", backend="memory")
        _cache_instance = CostCache(backend)

    return _cache_instance
