import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.shared.core.cache import CacheService, QueryCache


@pytest.mark.asyncio
async def test_delete_pattern_no_keys():
    async def empty_scan_iter(match=None):
        if False:
            yield match  # pragma: no cover

    mock_cache_client = AsyncMock()
    mock_cache_client.scan_iter = MagicMock(side_effect=empty_scan_iter)

    with patch(
        "app.shared.core.cache._get_async_client", return_value=mock_cache_client
    ):
        service = CacheService()
        result = await service.delete_pattern("missing:*")

    assert result is True
    mock_cache_client.delete.assert_not_called()


def test_get_async_client_returns_none_for_managed_profile():
    with patch("app.shared.core.cache.get_settings") as mock_settings:
        mock_settings.return_value.ENVIRONMENT = "production"
        mock_settings.return_value.PLATFORM_RUNTIME_PROFILE = "gcp"
        from app.shared.core.cache import _get_async_client

        assert _get_async_client() is None


@pytest.mark.asyncio
async def test_cached_query_tenant_aware_false_does_not_use_tenant():
    cache_client = AsyncMock()
    cache = QueryCache(backend_client=cache_client)

    async def handler(db, tenant_id, extra=None):
        return {"ok": True, "extra": extra}

    with patch.object(
        cache, "_make_cache_key", wraps=cache._make_cache_key
    ) as mock_key:
        wrapped = cache.cached_query(tenant_aware=False)(handler)
        await wrapped("db", "tenant-1", extra="x")

    _, kwargs = mock_key.call_args
    assert kwargs["tenant_id"] is None
