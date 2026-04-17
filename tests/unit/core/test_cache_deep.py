import pytest
import json
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from app.shared.core.cache import CacheService, get_cache_service


class TestCacheDeep:
    @pytest.fixture
    def mock_settings(self):
        with patch("app.shared.core.cache.get_settings") as mock:
            mock.return_value.ENVIRONMENT = "development"
            mock.return_value.PLATFORM_RUNTIME_PROFILE = "gcp"
            yield mock

    @pytest.fixture
    def mock_cache_client(self):
        with patch("app.shared.core.cache._async_client", new=None):  # Reset singleton
            client = AsyncMock()
            client.get = AsyncMock()
            client.set = AsyncMock()
            client.delete = AsyncMock()
            yield client

    @pytest.mark.asyncio
    async def test_init_disabled(self):
        with patch("app.shared.core.cache.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "production"
            mock_settings.return_value.PLATFORM_RUNTIME_PROFILE = "gcp"
            with patch("app.shared.core.cache._async_client", new=None):
                service = CacheService()
                assert service.enabled is False
                assert await service.get_analysis(uuid4()) is None
                assert await service.set_analysis(uuid4(), {}) is False

    @pytest.mark.asyncio
    async def test_init_enabled(self, mock_settings, mock_cache_client):
        with patch(
            "app.shared.core.cache._get_async_client", return_value=mock_cache_client
        ):
            service = CacheService()
        assert service.enabled is True

    @pytest.mark.asyncio
    async def test_get_analysis_hit(self, mock_settings, mock_cache_client):
        with patch(
            "app.shared.core.cache._get_async_client", return_value=mock_cache_client
        ):
            service = CacheService()
        mock_cache_client.get.return_value = json.dumps({"result": "ok"})

        res = await service.get_analysis(uuid4())
        assert res == {"result": "ok"}

    @pytest.mark.asyncio
    async def test_get_analysis_miss(self, mock_settings, mock_cache_client):
        with patch(
            "app.shared.core.cache._get_async_client", return_value=mock_cache_client
        ):
            service = CacheService()
        mock_cache_client.get.return_value = None

        res = await service.get_analysis(uuid4())
        assert res is None

    @pytest.mark.asyncio
    async def test_set_analysis(self, mock_settings, mock_cache_client):
        with patch(
            "app.shared.core.cache._get_async_client", return_value=mock_cache_client
        ):
            service = CacheService()
        tid = uuid4()
        data = {"result": "ok"}

        assert await service.set_analysis(tid, data) is True
        mock_cache_client.set.assert_called()
        # Verify TTL is passed (24h = 86400s)
        call_args = mock_cache_client.set.call_args
        assert call_args.kwargs["ex"] == 86400

    @pytest.mark.asyncio
    async def test_invalidate_tenant(self, mock_settings, mock_cache_client):
        with patch(
            "app.shared.core.cache._get_async_client", return_value=mock_cache_client
        ):
            service = CacheService()
        tid = uuid4()

        assert await service.invalidate_tenant(tid) is True
        mock_cache_client.delete.assert_called()

    @pytest.mark.asyncio
    async def test_error_handling_get(self, mock_settings, mock_cache_client):
        with patch(
            "app.shared.core.cache._get_async_client", return_value=mock_cache_client
        ):
            service = CacheService()
        mock_cache_client.get.side_effect = RuntimeError("cache down")

        assert await service.get_analysis(uuid4()) is None

    @pytest.mark.asyncio
    async def test_invalid_json_payload_returns_none(
        self, mock_settings, mock_cache_client
    ):
        with patch(
            "app.shared.core.cache._get_async_client", return_value=mock_cache_client
        ):
            service = CacheService()
        mock_cache_client.get.return_value = "{bad-json"
        assert await service.get_analysis(uuid4()) is None

    @pytest.mark.asyncio
    async def test_invalid_json_payload_returns_none(
        self, mock_settings, mock_cache_client
    ):
        with patch(
            "app.shared.core.cache._get_async_client", return_value=mock_cache_client
        ):
            service = CacheService()
        mock_cache_client.get.return_value = "{bad-json"
        assert await service.get_analysis(uuid4()) is None

    @pytest.mark.asyncio
    async def test_error_handling_set(self, mock_settings, mock_cache_client):
        with patch(
            "app.shared.core.cache._get_async_client", return_value=mock_cache_client
        ):
            service = CacheService()
        mock_cache_client.set.side_effect = RuntimeError("cache down")

        assert await service.set_analysis(uuid4(), {}) is False

    def test_get_cache_service_singleton(self, mock_settings, mock_cache_client):
        with (
            patch("app.shared.core.cache._cache_service", new=None),
            patch(
                "app.shared.core.cache._get_async_client",
                return_value=mock_cache_client,
            ),
        ):
            s1 = get_cache_service()
            s2 = get_cache_service()
            assert s1 is s2
