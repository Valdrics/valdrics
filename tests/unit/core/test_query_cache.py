import json
from unittest.mock import AsyncMock
from unittest.mock import patch

import pytest

from app.shared.core.cache import QueryCache


@pytest.mark.asyncio
async def test_make_cache_key_includes_tenant_prefix():
    cache = QueryCache(backend_client=AsyncMock())
    key = cache._make_cache_key("query_fn", {"a": 1}, tenant_id="t-1")
    assert key.startswith("query_cache:tenant:t-1:")


def test_make_cache_key_deterministic():
    cache = QueryCache(backend_client=AsyncMock())
    key1 = cache._make_cache_key("query_fn", {"a": 1, "b": 2}, tenant_id="t-1")
    key2 = cache._make_cache_key("query_fn", {"b": 2, "a": 1}, tenant_id="t-1")
    assert key1 == key2


@pytest.mark.asyncio
async def test_cached_query_returns_cached_result():
    backend_client = AsyncMock()
    cached = {"ok": True}
    backend_client.get.return_value = json.dumps(cached)
    cache = QueryCache(backend_client=backend_client)

    async def handler(db, tenant_id):
        return {"ok": False}

    wrapped = cache.cached_query()(handler)
    result = await wrapped("db", "tenant-1")

    assert result == cached


@pytest.mark.asyncio
async def test_cached_query_sets_on_miss():
    backend_client = AsyncMock()
    backend_client.get.return_value = None
    cache = QueryCache(backend_client=backend_client, default_ttl=123)

    async def handler(db, tenant_id, extra=None):
        return {"value": 42, "extra": extra}

    wrapped = cache.cached_query()(handler)
    result = await wrapped("db", "tenant-1", extra="x")

    assert result == {"value": 42, "extra": "x"}
    backend_client.set.assert_awaited()


@pytest.mark.asyncio
async def test_get_cached_result_invalid_json_returns_none():
    backend_client = AsyncMock()
    backend_client.get.return_value = "{broken"
    cache = QueryCache(backend_client=backend_client)
    assert await cache.get_cached_result("bad-key") is None


@pytest.mark.asyncio
async def test_invalidate_tenant_cache_scans_and_deletes():
    backend_client = AsyncMock()
    backend_client.scan = AsyncMock(side_effect=[(1, ["k1", "k2"]), (0, ["k3"])])
    cache = QueryCache(backend_client=backend_client)

    await cache.invalidate_tenant_cache("tenant-1")

    backend_client.scan.assert_awaited()
    backend_client.delete.assert_any_await("k1", "k2")
    backend_client.delete.assert_any_await("k3")


@pytest.mark.asyncio
async def test_cached_query_waits_for_locked_result_and_avoids_duplicate_execution():
    backend_client = AsyncMock()
    cached = {"ok": True}
    # 1st get: initial cache miss
    # 2nd get: still missing while waiting on lock owner
    # 3rd get: lock owner has populated cache
    backend_client.get = AsyncMock(side_effect=[None, None, json.dumps(cached)])
    backend_client.set = AsyncMock(return_value=False)  # lock acquisition denied
    cache = QueryCache(backend_client=backend_client)

    handler = AsyncMock(return_value={"ok": False})
    wrapped = cache.cached_query()(handler)

    with patch("app.shared.core.cache.asyncio.sleep", new=AsyncMock(return_value=None)):
        result = await wrapped("db", "tenant-1")

    assert result == cached
    handler.assert_not_awaited()
    # Should not release lock it never acquired.
    backend_client.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_cached_query_does_not_release_foreign_lock_on_timeout_fallback():
    backend_client = AsyncMock()
    backend_client.get = AsyncMock(return_value=None)

    async def set_side_effect(*args, **kwargs):
        # Lock acquisition and re-acquisition attempts fail.
        if kwargs.get("nx"):
            return False
        # Cache set (non-lock write) succeeds.
        return True

    backend_client.set = AsyncMock(side_effect=set_side_effect)
    cache = QueryCache(backend_client=backend_client)

    handler = AsyncMock(return_value={"value": 7})
    wrapped = cache.cached_query()(handler)

    with patch("app.shared.core.cache.asyncio.sleep", new=AsyncMock(return_value=None)):
        result = await wrapped("db", "tenant-1")

    assert result == {"value": 7}
    handler.assert_awaited_once()
    # Critical: lock release must happen only when lock is owned.
    backend_client.delete.assert_not_awaited()
