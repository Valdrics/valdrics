"""
Process-local cache service for non-managed runtimes.

The supported managed GCP profile remains cacheless by default. Outside that
profile, callers can still use a best-effort in-memory cache without carrying
an external Redis contract or dependency in the active runtime surface.
"""

import asyncio
from fnmatch import fnmatchcase
import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Optional
from uuid import UUID

import structlog

from app.shared.core.config import get_settings

logger = structlog.get_logger()

# Cache TTLs
ANALYSIS_TTL = timedelta(hours=24)
COST_DATA_TTL = timedelta(hours=6)
METADATA_TTL = timedelta(hours=1)

# Key Prefixes
PREFIX_ANALYSIS = "analysis"
PREFIX_COSTS = "costs"

# Singleton instances
_async_client: Optional["_InMemoryAsyncCacheClient"] = None

CACHE_RECOVERABLE_ERRORS = (
    OSError,
    RuntimeError,
    TimeoutError,
    TypeError,
    ValueError,
)


class _InMemoryAsyncCacheClient:
    """Async in-memory cache backend for local and non-managed execution."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, datetime | None]] = {}

    def _now(self) -> datetime:
        return datetime.now(timezone.utc)

    def _purge_if_expired(self, key: str) -> None:
        record = self._store.get(key)
        if record is None:
            return
        _, expires_at = record
        if expires_at is not None and self._now() >= expires_at:
            self._store.pop(key, None)

    def _matching_keys(self, pattern: str) -> list[str]:
        for key in list(self._store):
            self._purge_if_expired(key)
        return sorted(key for key in self._store if fnmatchcase(key, pattern))

    async def get(self, key: str) -> Any:
        self._purge_if_expired(key)
        record = self._store.get(key)
        if record is None:
            return None
        return record[0]

    async def set(
        self,
        key: str,
        value: Any,
        *,
        ex: int | None = None,
        nx: bool | None = None,
    ) -> bool:
        self._purge_if_expired(key)
        if nx and key in self._store:
            return False
        expires_at = self._now() + timedelta(seconds=ex) if ex is not None else None
        self._store[key] = (value, expires_at)
        return True

    async def delete(self, *keys: str) -> int:
        deleted = 0
        for key in keys:
            if key in self._store:
                deleted += 1
                self._store.pop(key, None)
        return deleted

    async def scan(
        self, cursor: int, *, match: str, count: int = 100
    ) -> tuple[int, list[str]]:
        keys = self._matching_keys(match)
        start = max(int(cursor), 0)
        end = start + max(int(count), 1)
        batch = keys[start:end]
        next_cursor = 0 if end >= len(keys) else end
        return next_cursor, batch

    async def incr(self, key: str) -> int:
        current = await self.get(key)
        value = int(current) if current is not None else 0
        value += 1
        await self.set(key, value)
        return value

    async def decr(self, key: str) -> int:
        current = await self.get(key)
        value = int(current) if current is not None else 0
        value -= 1
        await self.set(key, value)
        return value

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        self._purge_if_expired(key)
        record = self._store.get(key)
        if record is None:
            return False
        value, _ = record
        self._store[key] = (
            value,
            self._now() + timedelta(seconds=max(int(ttl_seconds), 0)),
        )
        return True

    async def scan_iter(self, *, match: str):
        for key in self._matching_keys(match):
            yield key


def _managed_cacheless_profile(settings: object) -> bool:
    environment = str(getattr(settings, "ENVIRONMENT", "") or "").strip().lower()
    runtime_profile = (
        str(getattr(settings, "PLATFORM_RUNTIME_PROFILE", "gcp") or "gcp")
        .strip()
        .lower()
    )
    return environment in {"staging", "production"} and runtime_profile == "gcp"


def _safe_json_loads(payload: str, key: str) -> Optional[Any]:
    """Strict JSON decode with bounded-failure behavior."""
    try:
        return json.loads(payload)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("cache_payload_invalid_json", key=key, error=str(exc))
        return None


def _get_async_client() -> Optional[_InMemoryAsyncCacheClient]:
    """Get or create the process-local cache backend for non-managed runtimes."""
    global _async_client
    settings = get_settings()
    if _managed_cacheless_profile(settings):
        _async_client = None
        return None

    if _async_client is None:
        _async_client = _InMemoryAsyncCacheClient()
        logger.debug("process_local_cache_client_created")

    return _async_client


class CacheService:
    """
    Best-effort async cache service.

    Falls back gracefully when the backend is unavailable or disabled for the
    active runtime profile.
    """

    def __init__(self, client: _InMemoryAsyncCacheClient | Any | None = None) -> None:
        self._client = _get_async_client() if client is None else client
        self.enabled = self._client is not None

    @property
    def client(self) -> _InMemoryAsyncCacheClient | Any | None:
        """Expose the resolved backend for read-only inspection."""
        return self._client

    async def get_analysis(self, tenant_id: UUID) -> Optional[dict[str, Any]]:
        """Get cached LLM analysis for a tenant."""
        key = f"{PREFIX_ANALYSIS}:{tenant_id}"
        return await self._get(key)

    async def set_analysis(self, tenant_id: UUID, analysis: dict[str, Any]) -> bool:
        """Cache LLM analysis with 24h TTL."""
        key = f"{PREFIX_ANALYSIS}:{tenant_id}"
        return await self._set(key, analysis, ANALYSIS_TTL)

    async def get_cost_data(
        self, tenant_id: UUID, date_range: str
    ) -> Optional[list[Any]]:
        """Get cached cost data for a tenant and date range."""
        key = f"{PREFIX_COSTS}:{tenant_id}:{date_range}"
        return await self._get(key)

    async def set_cost_data(
        self, tenant_id: UUID, date_range: str, costs: list[Any]
    ) -> bool:
        """Cache cost data with 6h TTL."""
        key = f"{PREFIX_COSTS}:{tenant_id}:{date_range}"
        return await self._set(key, costs, COST_DATA_TTL)

    async def invalidate_tenant(self, tenant_id: UUID) -> bool:
        """Invalidate all cache entries for a tenant."""
        if not self.enabled or self._client is None:
            return False
        try:
            await self._client.delete(f"{PREFIX_ANALYSIS}:{tenant_id}")
            logger.info("cache_invalidated", tenant_id=str(tenant_id))
            return True
        except CACHE_RECOVERABLE_ERRORS as exc:
            logger.warning("cache_invalidate_error", error=str(exc))
            return False

    async def get(self, key: str) -> Optional[Any]:
        """Public helper for backend GET."""
        return await self._get(key)

    async def set(self, key: str, value: Any, ttl: Optional[timedelta] = None) -> bool:
        """Public helper for backend SET."""
        return await self._set(key, value, ttl or ANALYSIS_TTL)

    async def get_raw(self, key: str) -> Any:
        """
        Public raw GET primitive for coordination paths.

        Unlike `get`, this intentionally propagates backend exceptions so callers
        can keep fail-open or fail-closed behavior explicit at the call site.
        """
        if not self.enabled or self._client is None:
            return None
        data = await self._client.get(key)
        if isinstance(data, bytes):
            return data.decode("utf-8")
        return data

    async def set_raw(
        self,
        key: str,
        value: Any,
        *,
        ex: int | None = None,
        nx: bool | None = None,
    ) -> Any:
        """
        Public raw SET primitive for coordination paths.

        This bypasses JSON serialization and propagates backend exceptions.
        """
        if not self.enabled or self._client is None:
            return False
        kwargs: dict[str, Any] = {}
        if ex is not None:
            kwargs["ex"] = ex
        if nx is not None:
            kwargs["nx"] = nx
        return await self._client.set(key, value, **kwargs)

    async def increment(self, key: str) -> int | None:
        """Public raw INCR primitive for coordination paths."""
        if not self.enabled or self._client is None:
            return None
        return int(await self._client.incr(key))

    async def decrement(self, key: str) -> int | None:
        """Public raw DECR primitive for coordination paths."""
        if not self.enabled or self._client is None:
            return None
        return int(await self._client.decr(key))

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        """Public raw EXPIRE primitive for coordination paths."""
        if not self.enabled or self._client is None:
            return False
        return bool(await self._client.expire(key, ttl_seconds))

    async def delete_pattern(self, pattern: str) -> bool:
        """Delete keys matching pattern."""
        if not self.enabled or self._client is None:
            return False
        try:
            scan_iter = getattr(self._client, "scan_iter", None)
            if callable(scan_iter):
                keys = [key async for key in scan_iter(match=pattern)]
                if keys:
                    await self._client.delete(*keys)
                    logger.info(
                        "cache_pattern_deleted", pattern=pattern, count=len(keys)
                    )
                return True

            cursor = 0
            total_deleted = 0
            while True:
                next_cursor, keys = await self._client.scan(
                    cursor, match=pattern, count=100
                )
                if keys:
                    await self._client.delete(*keys)
                    total_deleted += len(keys)
                cursor = int(next_cursor)
                if cursor == 0:
                    break
            if total_deleted > 0:
                logger.info(
                    "cache_pattern_deleted", pattern=pattern, count=total_deleted
                )
            return True
        except CACHE_RECOVERABLE_ERRORS as exc:
            logger.warning(
                "cache_delete_pattern_error", pattern=pattern, error=str(exc)
            )
            return False

    async def _get(self, key: str) -> Optional[Any]:
        """Internal helper for backend GET with error handling."""
        if not self.enabled or self._client is None:
            return None
        try:
            data = await self._client.get(key)
            if data is not None:
                logger.debug("cache_hit", key=key)
                if isinstance(data, bytes):
                    try:
                        data = data.decode("utf-8")
                    except UnicodeDecodeError as exc:
                        logger.warning(
                            "cache_payload_invalid_encoding", key=key, error=str(exc)
                        )
                        return None
                if isinstance(data, str):
                    return _safe_json_loads(data, key=key)
                if isinstance(data, (dict, list, int, float, bool)):
                    return data
                if data is None:
                    return None
                logger.warning(
                    "cache_payload_unexpected_type",
                    key=key,
                    payload_type=type(data).__name__,
                )
                return None
        except CACHE_RECOVERABLE_ERRORS as exc:
            logger.warning("cache_get_error", key=key, error=str(exc))
        return None

    async def _set(self, key: str, value: Any, ttl: timedelta) -> bool:
        """Internal helper for backend SET with error handling."""
        if not self.enabled or self._client is None:
            return False
        try:
            await self._client.set(
                key, json.dumps(value, default=str), ex=int(ttl.total_seconds())
            )
            logger.debug("cache_set", key=key, ttl_seconds=int(ttl.total_seconds()))
            return True
        except CACHE_RECOVERABLE_ERRORS as exc:
            logger.warning("cache_set_error", key=key, error=str(exc))
            return False


class QueryCache:
    """Query result caching with automatic invalidation."""

    def __init__(self, backend_client: Any = None, default_ttl: int = 300) -> None:
        self.backend_client = backend_client
        self.default_ttl = default_ttl
        self.enabled = backend_client is not None

    def _make_cache_key(
        self, query: str, params: dict[str, Any], tenant_id: Optional[str] = None
    ) -> str:
        """Generate deterministic cache key from query and parameters."""
        key_data = {"query": query, "params": params, "tenant_id": tenant_id}
        key_str = json.dumps(key_data, sort_keys=True, default=str)
        digest = hashlib.sha256(key_str.encode()).hexdigest()
        if tenant_id:
            return f"query_cache:tenant:{tenant_id}:{digest}"
        return f"query_cache:{digest}"

    async def get_cached_result(self, cache_key: str) -> Optional[Any]:
        """Retrieve cached query result."""
        if not self.enabled or self.backend_client is None:
            return None

        try:
            cached_data = await self.backend_client.get(cache_key)
            if cached_data is not None:
                logger.debug("cache_hit", key=cache_key)
                if isinstance(cached_data, bytes):
                    try:
                        cached_data = cached_data.decode("utf-8")
                    except UnicodeDecodeError as exc:
                        logger.warning(
                            "cache_payload_invalid_encoding",
                            key=cache_key,
                            error=str(exc),
                        )
                        return None
                if isinstance(cached_data, str):
                    return _safe_json_loads(cached_data, key=cache_key)
                if isinstance(cached_data, (dict, list, int, float, bool)):
                    return cached_data
                logger.warning(
                    "cache_payload_unexpected_type",
                    key=cache_key,
                    payload_type=type(cached_data).__name__,
                )
                return None
            logger.debug("cache_miss", key=cache_key)
            return None
        except CACHE_RECOVERABLE_ERRORS as exc:
            logger.warning("cache_get_error", error=str(exc), key=cache_key)
            return None

    async def set_cached_result(
        self, cache_key: str, result: Any, ttl: Optional[int] = None
    ) -> None:
        """Cache query result with TTL."""
        if not self.enabled or self.backend_client is None:
            return

        try:
            ttl = ttl or self.default_ttl
            await self.backend_client.set(
                cache_key, json.dumps(result, default=str), ex=ttl
            )
            logger.debug("cache_set", key=cache_key, ttl=ttl)
        except CACHE_RECOVERABLE_ERRORS as exc:
            logger.warning("cache_set_error", error=str(exc), key=cache_key)

    async def invalidate_tenant_cache(self, tenant_id: str) -> None:
        """Invalidate all cached queries for a tenant."""
        if not self.enabled or self.backend_client is None:
            return

        try:
            # Use backend SCAN semantics to find tenant-related keys
            pattern = f"query_cache:tenant:{tenant_id}:*"
            cursor = 0
            while True:
                cursor, keys = await self.backend_client.scan(
                    cursor, match=pattern, count=100
                )
                if keys:
                    # Delete the batch directly when the backend supports variadic delete.
                    await self.backend_client.delete(*keys)
                    logger.info(
                        "cache_invalidated", tenant_id=tenant_id, keys_deleted=len(keys)
                    )
                if cursor == 0:
                    break
        except CACHE_RECOVERABLE_ERRORS as exc:
            logger.warning(
                "cache_invalidation_error", error=str(exc), tenant_id=tenant_id
            )

    def cached_query(
        self,
        ttl: Optional[int] = None,
        tenant_aware: bool = True,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """
        Decorator for caching SQLAlchemy query results.

        Usage:
            @cache.cached_query(ttl=300, tenant_aware=True)
            async def get_tenant_connections(db, tenant_id):
                return await db.execute(select(AWSConnection).where(...))
        """

        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> Any:
                if not self.enabled:
                    return await func(*args, **kwargs)

                # Extract tenant_id for tenant-aware caching
                tenant_id = None
                if tenant_aware:
                    # Look for tenant_id in kwargs or as second positional arg (after db)
                    tenant_id = kwargs.get("tenant_id") or (
                        args[1] if len(args) > 1 else None
                    )

                # Generate cache key from function name and arguments
                cache_key = self._make_cache_key(
                    query=func.__name__,
                    params={
                        "args": args[2:],
                        "kwargs": {k: v for k, v in kwargs.items() if k != "tenant_id"},
                    },
                    tenant_id=str(tenant_id) if tenant_id else None,
                )

                # Try cache first
                cached_result = await self.get_cached_result(cache_key)
                if cached_result is not None:
                    return cached_result

                # SEC: Dogpile/Stampede Protection (BE-CORE-1)
                # Use a short-lived lock to ensure only one worker executes the query.
                lock_key = f"lock:{cache_key}"
                lock_acquired = False
                if self.backend_client:
                    lock_ttl_seconds = 30
                    wait_step_seconds = 0.25
                    max_wait_seconds = 2.0
                    try:
                        # SET NX (if not exists) EX (expire)
                        lock_acquired = bool(
                            await self.backend_client.set(
                                lock_key,
                                "locked",
                                ex=lock_ttl_seconds,
                                nx=True,
                            )
                        )
                    except CACHE_RECOVERABLE_ERRORS as exc:
                        logger.warning(
                            "cache_lock_acquire_error",
                            key=lock_key,
                            error=str(exc),
                        )
                        lock_acquired = False

                    # If another worker holds the lock, wait for cache fill and retry once.
                    if not lock_acquired:
                        waited = 0.0
                        while waited < max_wait_seconds:
                            await asyncio.sleep(wait_step_seconds)
                            waited += wait_step_seconds
                            cached_result = await self.get_cached_result(cache_key)
                            if cached_result is not None:
                                return cached_result
                        try:
                            lock_acquired = bool(
                                await self.backend_client.set(
                                    lock_key,
                                    "locked",
                                    ex=lock_ttl_seconds,
                                    nx=True,
                                )
                            )
                        except CACHE_RECOVERABLE_ERRORS as exc:
                            logger.warning(
                                "cache_lock_reacquire_error",
                                key=lock_key,
                                error=str(exc),
                            )
                            lock_acquired = False
                        if not lock_acquired:
                            logger.warning(
                                "cache_lock_wait_timeout_fallback",
                                key=cache_key,
                                wait_seconds=max_wait_seconds,
                            )

                try:
                    # Execute query
                    result = await func(*args, **kwargs)

                    # Cache result
                    await self.set_cached_result(cache_key, result, ttl)
                finally:
                    # Release lock
                    if self.backend_client and lock_acquired:
                        try:
                            await self.backend_client.delete(lock_key)
                        except CACHE_RECOVERABLE_ERRORS as exc:
                            logger.warning(
                                "cache_lock_release_error",
                                key=lock_key,
                                error=str(exc),
                            )

                return result

            return wrapper

        return decorator


# Singleton cache service
_cache_service: Optional[CacheService] = None


def reset_cache_service_state() -> None:
    """Clear the process-local cache backend and singleton service."""
    global _async_client, _cache_service
    _cache_service = None
    _async_client = None


def get_cache_service() -> CacheService:
    """Get or create the global cache service."""
    global _cache_service
    current_client = _get_async_client()
    if (
        _cache_service is None
        or _cache_service.client is not current_client
        or _cache_service.enabled is not (current_client is not None)
    ):
        _cache_service = CacheService()
    return _cache_service
