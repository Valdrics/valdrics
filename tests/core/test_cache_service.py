"""
Tests for CacheService with the optional remote cache backend.

Tests behavior when:
1. The backend is not configured (graceful fallback)
2. The backend is configured (mocked operations)
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
import json

from app.shared.core.cache import CacheService, get_cache_service, reset_cache_service_state


class TestCacheServiceDisabled:
    """Tests for cache service when the managed profile disables caching."""

    def test_disabled_for_managed_profile(self):
        """Cache is disabled for the supported managed GCP runtime profile."""
        with patch("app.shared.core.cache.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "production"
            mock_settings.return_value.PLATFORM_RUNTIME_PROFILE = "gcp"

            # Reset singleton
            import app.shared.core.cache as cache_module

            cache_module._async_client = None
            cache_module._cache_service = None

            service = CacheService()
            assert service.enabled is False

    @pytest.mark.asyncio
    async def test_get_analysis_returns_none_when_disabled(self):
        """get_analysis returns None when cache is disabled."""
        with patch("app.shared.core.cache.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "production"
            mock_settings.return_value.PLATFORM_RUNTIME_PROFILE = "gcp"

            import app.shared.core.cache as cache_module

            cache_module._async_client = None
            cache_module._cache_service = None

            service = CacheService()
            result = await service.get_analysis(uuid4())
            assert result is None

    @pytest.mark.asyncio
    async def test_set_analysis_returns_false_when_disabled(self):
        """set_analysis returns False when cache is disabled."""
        with patch("app.shared.core.cache.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "production"
            mock_settings.return_value.PLATFORM_RUNTIME_PROFILE = "gcp"

            import app.shared.core.cache as cache_module

            cache_module._async_client = None
            cache_module._cache_service = None

            service = CacheService()
            result = await service.set_analysis(uuid4(), {"test": "data"})
            assert result is False


class TestCacheServiceEnabled:
    """Tests for cache service when the remote backend is configured (mocked)."""

    @pytest.mark.asyncio
    async def test_get_analysis_returns_cached_data(self):
        """get_analysis returns parsed JSON when data exists."""
        tenant_id = uuid4()
        cached_data = {"anomalies": [], "recommendations": []}
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=json.dumps(cached_data))
        service = CacheService(client=mock_client)

        result = await service.get_analysis(tenant_id)
        assert result == cached_data
        mock_client.get.assert_called_once_with(f"analysis:{tenant_id}")

    @pytest.mark.asyncio
    async def test_set_analysis_stores_data_with_ttl(self):
        """set_analysis stores JSON with 24h TTL."""
        tenant_id = uuid4()
        analysis_data = {
            "anomalies": [],
            "summary": {"total_estimated_savings": "$0/month"},
        }

        mock_client = AsyncMock()
        mock_client.set = AsyncMock(return_value=True)

        service = CacheService(client=mock_client)

        result = await service.set_analysis(tenant_id, analysis_data)

        assert result is True
        mock_client.set.assert_called_once()
        call_args = mock_client.set.call_args
        assert call_args[0][0] == f"analysis:{tenant_id}"
        assert json.loads(call_args[0][1]) == analysis_data
        assert call_args[1]["ex"] == 86400  # 24 hours in seconds

    @pytest.mark.asyncio
    async def test_get_analysis_handles_errors_gracefully(self):
        """get_analysis returns None on backend errors."""
        tenant_id = uuid4()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=RuntimeError("Connection failed"))

        service = CacheService(client=mock_client)

        result = await service.get_analysis(tenant_id)
        assert result is None  # Graceful fallback on error


class TestCacheServiceSingleton:
    """Tests for singleton behavior."""

    def test_get_cache_service_returns_same_instance(self):
        """get_cache_service returns the same instance."""
        with patch("app.shared.core.cache.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "production"
            mock_settings.return_value.PLATFORM_RUNTIME_PROFILE = "gcp"

            import app.shared.core.cache as cache_module

            cache_module._cache_service = None

            service1 = get_cache_service()
            service2 = get_cache_service()

            assert service1 is service2

    @pytest.mark.asyncio
    async def test_reset_cache_service_state_clears_process_local_singletons(self):
        """Reset helper drops the singleton and clears in-memory cached payloads."""
        with patch("app.shared.core.cache.get_settings") as mock_settings:
            mock_settings.return_value.ENVIRONMENT = "development"
            mock_settings.return_value.PLATFORM_RUNTIME_PROFILE = "gcp"

            import app.shared.core.cache as cache_module

            reset_cache_service_state()
            service = get_cache_service()
            assert service.enabled is True

            assert await service.set("test-key", {"ok": True}) is True
            assert await service.get("test-key") == {"ok": True}

            reset_cache_service_state()

            assert cache_module._cache_service is None
            assert cache_module._async_client is None
            fresh_service = get_cache_service()
            assert await fresh_service.get("test-key") is None
