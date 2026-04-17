"""
Tests for CostCache - Caching logic for cost data
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import date, datetime, timezone, timedelta
from app.shared.adapters.cost_cache import (
    InMemoryCache,
    CostCache,
    get_cost_cache,
    CacheBackend,
)


class TestInMemoryCache:
    @pytest.mark.asyncio
    async def test_set_get(self):
        cache = InMemoryCache()
        await cache.set("key", "value", 10)
        assert await cache.get("key") == "value"

    @pytest.mark.asyncio
    async def test_get_expired(self):
        cache = InMemoryCache()
        with patch("app.shared.adapters.cost_cache.datetime") as mock_dt:
            # mock_dt is the datetime module in cost_cache
            now = datetime.now(timezone.utc)
            mock_dt.now.return_value = now
            mock_dt.timezone = timezone
            mock_dt.timedelta = timedelta

            await cache.set("key", "value", 10)

            # Move time forward
            mock_dt.now.return_value = now + timedelta(seconds=11)
            assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_delete(self):
        cache = InMemoryCache()
        await cache.set("key", "value", 10)
        await cache.delete("key")
        assert await cache.get("key") is None

    @pytest.mark.asyncio
    async def test_delete_pattern(self):
        cache = InMemoryCache()
        await cache.set("tenant:1:a", "v1", 10)
        await cache.set("tenant:1:b", "v2", 10)
        await cache.set("tenant:2:a", "v3", 10)

        count = await cache.delete_pattern("tenant:1:*")
        assert count == 2
        assert await cache.get("tenant:1:a") is None
        assert await cache.get("tenant:2:a") == "v3"

class TestCostCache:
    @pytest.mark.asyncio
    async def test_get_set_daily_costs(self):
        backend = InMemoryCache()
        cache = CostCache(backend)
        tenant_id = "tenant-1"
        start = date(2026, 1, 1)
        end = date(2026, 1, 2)
        costs = [{"service": "EC2", "amount": 10.5}]

        await cache.set_daily_costs(tenant_id, start, end, costs)
        cached = await cache.get_daily_costs(tenant_id, start, end)

        assert cached == costs

    @pytest.mark.asyncio
    async def test_get_daily_costs_invalid_json_returns_none(self):
        backend = MagicMock(spec=CacheBackend)
        backend.get = AsyncMock(return_value='{"broken":')
        cache = CostCache(backend)

        cached = await cache.get_daily_costs(
            "tenant-1", date(2026, 1, 1), date(2026, 1, 2)
        )

        assert cached is None

    @pytest.mark.asyncio
    async def test_get_set_zombie_scan(self):
        backend = InMemoryCache()
        cache = CostCache(backend)
        tenant_id = "tenant-1"
        region = "us-east-1"
        zombies = {"summary": {"count": 5}}

        await cache.set_zombie_scan(tenant_id, region, zombies)
        cached = await cache.get_zombie_scan(tenant_id, region)

        assert cached == zombies

    @pytest.mark.asyncio
    async def test_get_zombie_scan_non_utf8_payload_returns_none(self):
        backend = MagicMock(spec=CacheBackend)
        backend.get = AsyncMock(return_value=b"\xff\xfe\xfa")
        cache = CostCache(backend)

        cached = await cache.get_zombie_scan("tenant-1", "us-east-1")

        assert cached is None

    @pytest.mark.asyncio
    async def test_get_analysis_unexpected_payload_type_returns_none(self):
        backend = MagicMock(spec=CacheBackend)
        backend.get = AsyncMock(return_value=123)
        cache = CostCache(backend)

        cached = await cache.get_analysis("tenant-1", "analysis-hash")

        assert cached is None

    @pytest.mark.asyncio
    async def test_invalidate_tenant(self):
        backend = MagicMock(spec=CacheBackend)
        backend.delete_pattern = AsyncMock(return_value=5)
        cache = CostCache(backend)

        await cache.invalidate_tenant("tenant-1")
        backend.delete_pattern.assert_called_once_with("valdrics:tenant-1:*")

    @pytest.mark.asyncio
    async def test_invalidate_zombies_pattern(self):
        backend = MagicMock(spec=CacheBackend)
        backend.delete_pattern = AsyncMock(return_value=2)
        cache = CostCache(backend)

        await cache.invalidate_zombies("tenant-1")
        backend.delete_pattern.assert_called_once_with("valdrics:tenant-1:zombies:*")

    @pytest.mark.asyncio
    async def test_keys_include_tenant_and_prefix(self):
        backend = MagicMock(spec=CacheBackend)
        backend.set = AsyncMock()
        backend.get = AsyncMock(return_value="[]")
        cache = CostCache(backend)
        tenant_id = "tenant-1"
        start = date(2026, 1, 1)
        end = date(2026, 1, 2)

        await cache.set_daily_costs(tenant_id, start, end, [])
        key = backend.set.call_args[0][0]
        assert key.startswith("valdrics:tenant-1:costs:")

        await cache.get_daily_costs(tenant_id, start, end)
        key = backend.get.call_args[0][0]
        assert key.startswith("valdrics:tenant-1:costs:")


@pytest.mark.asyncio
async def test_get_cost_cache_factory():
    with patch("app.shared.adapters.cost_cache._cache_instance", None):
        cache = await get_cost_cache()
        assert isinstance(cache.backend, InMemoryCache)


@pytest.mark.asyncio
async def test_get_cost_cache_reuses_singleton_without_runtime_switching():
    with patch("app.shared.adapters.cost_cache._cache_instance", None):
        first = await get_cost_cache()
        second = await get_cost_cache()

    assert first is second
