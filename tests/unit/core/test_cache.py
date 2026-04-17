import pytest
import json
from datetime import timedelta
from unittest.mock import MagicMock, AsyncMock, patch
from app.shared.core.cache import get_cache_service


@pytest.fixture(autouse=True)
def reset_cache_singleton():
    """Reset the global cache service singleton before each test."""
    import app.shared.core.cache as cache_mod

    cache_mod._cache_service = None
    cache_mod._async_client = None
    # Patch get_settings globally to keep a non-managed profile with cache enabled.
    with patch("app.shared.core.cache.get_settings") as mock_settings:
        mock_settings.return_value.ENVIRONMENT = "development"
        mock_settings.return_value.PLATFORM_RUNTIME_PROFILE = "gcp"
        yield


@pytest.fixture
def mock_cache_client():
    cache_client = AsyncMock()
    return cache_client


@pytest.mark.asyncio
async def test_cache_get_set(mock_cache_client):
    """Test basic get/set operations."""
    with patch(
        "app.shared.core.cache._get_async_client", return_value=mock_cache_client
    ):
        from app.shared.core.cache import CacheService

        service = CacheService()

        # Test Set
        await service.set("test-key", {"foo": "bar"}, ttl=timedelta(seconds=60))
        mock_cache_client.set.assert_called()  # Check call

        # Test Get Hit
        mock_cache_client.get.return_value = json.dumps({"foo": "bar"})
        val = await service.get("test-key")
        assert val == {"foo": "bar"}

        # Test Get Miss
        mock_cache_client.get.return_value = None
        val = await service.get("missing")
        assert val is None


@pytest.mark.asyncio
async def test_cache_delete_pattern(mock_cache_client):
    """Test deleting by pattern."""

    # Properly mock scan_iter as an async iterator
    async def mock_scan_iter(match=None):
        for k in ["key1", "key2"]:
            yield k

    mock_cache_client.scan_iter = MagicMock(side_effect=mock_scan_iter)

    with patch(
        "app.shared.core.cache._get_async_client", return_value=mock_cache_client
    ):
        from app.shared.core.cache import CacheService

        service = CacheService()
        await service.delete_pattern("prefix:*")

    mock_cache_client.delete.assert_called_with("key1", "key2")


@pytest.mark.asyncio
async def test_cache_raw_primitives_delegate_to_client(mock_cache_client):
    """Raw coordination helpers delegate directly to the configured backend."""
    with patch(
        "app.shared.core.cache._get_async_client", return_value=mock_cache_client
    ):
        from app.shared.core.cache import CacheService

        service = CacheService()

        mock_cache_client.get.return_value = b"raw-value"
        mock_cache_client.set.return_value = True
        mock_cache_client.incr.return_value = 2
        mock_cache_client.decr.return_value = 1
        mock_cache_client.expire.return_value = 1

        assert await service.get_raw("raw-key") == "raw-value"
        assert await service.set_raw("raw-key", "value", ex=30, nx=True) is True
        assert await service.increment("raw-key") == 2
        assert await service.decrement("raw-key") == 1
        assert await service.expire("raw-key", 30) is True

    mock_cache_client.set.assert_called_with("raw-key", "value", ex=30, nx=True)
    mock_cache_client.expire.assert_called_with("raw-key", 30)


def test_singleton_getter():
    """Test get_cache_service singleton."""
    with patch("app.shared.core.cache._get_async_client", return_value=AsyncMock()):
        s1 = get_cache_service()
        s2 = get_cache_service()
        assert s1 is s2
