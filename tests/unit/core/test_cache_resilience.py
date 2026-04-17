import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from app.shared.core.cache import CacheService


@pytest.mark.asyncio
async def test_cache_service_graceful_failure():
    """Verify that CacheService doesn't crash if cache operations fail."""
    mock_cache_client = AsyncMock()
    mock_cache_client.get.side_effect = RuntimeError("cache read failed")
    mock_cache_client.set.side_effect = RuntimeError("cache write failed")

    with patch(
        "app.shared.core.cache._get_async_client", return_value=mock_cache_client
    ):
        service = CacheService()
        tenant_id = uuid4()

        # 1. Test GET failure
        result = await service.get_analysis(tenant_id)
        assert result is None  # Should return None instead of raising

        # 2. Test SET failure
        success = await service.set_analysis(tenant_id, {"data": "test"})
        assert success is False  # Should return False instead of raising


@pytest.mark.asyncio
async def test_cache_service_disabled_logic():
    """Verify behavior when caching is disabled."""
    with patch("app.shared.core.cache._get_async_client", return_value=None):
        service = CacheService()
        assert service.enabled is False

        result = await service.get_analysis(uuid4())
        assert result is None

        success = await service.set_analysis(uuid4(), {})
        assert success is False
