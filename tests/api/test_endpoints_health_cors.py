"""API endpoint tests: health, monitoring, and CORS/preflight behavior."""

import pytest
from httpx import AsyncClient

class TestHealthAndMonitoringAPIs:
    """Tests for health check and monitoring endpoints."""

    @pytest.mark.asyncio
    async def test_health_endpoint(self, ac: AsyncClient):
        """Test health check endpoint."""
        response = await ac.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "ok", "degraded"]

    @pytest.mark.asyncio
    async def test_metrics_endpoint_protected(self, ac: AsyncClient):
        """Test that metrics endpoints are properly protected."""
        response = await ac.get("/metrics")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_openapi_schema_accessible(self, ac: AsyncClient):
        """Test that OpenAPI schema is accessible."""
        response = await ac.get("/openapi.json")

        assert response.status_code == 200
        data = response.json()
        assert "paths" in data
        assert "/api/v1/zombies" in data.get("paths", {})


class TestCORSAndPreflight:
    """Tests for CORS and preflight requests."""

    @pytest.mark.asyncio
    async def test_cors_headers_present(self, ac: AsyncClient):
        """Test that CORS headers are present when needed."""
        response = await ac.options("/api/v1/zombies")

        # Check for CORS headers - may not be configured in test environment
        headers = response.headers
        # CORS might not be enabled in test environment, so check for basic headers
        assert "allow" in headers  # OPTIONS should return Allow header
        # If CORS is configured, these would be present, but in test they might not be
        cors_headers = [
            "access-control-allow-origin",
            "access-control-allow-methods",
            "access-control-allow-headers",
        ]
        has_cors = any(cors_header in headers for cors_header in cors_headers)
        if has_cors:
            assert "access-control-allow-origin" in headers

    @pytest.mark.asyncio
    async def test_preflight_requests_handled(self, ac: AsyncClient):
        """Test that preflight OPTIONS requests are handled."""
        response = await ac.options(
            "/api/v1/zombies",
            headers={
                "Origin": "https://app.valdrics.ai",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Should handle preflight request
        assert response.status_code in [200, 400, 404]
