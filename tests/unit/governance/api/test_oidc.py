import pytest
import pytest_asyncio
from httpx import AsyncClient
from httpx import ASGITransport
from unittest.mock import patch, AsyncMock

from app.main import app as valdrics_app


@pytest_asyncio.fixture
async def oidc_client():
    """Use a minimal ASGI client to avoid full DB/bootstrap fixtures for public OIDC routes."""
    transport = ASGITransport(app=valdrics_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_oidc_discovery(oidc_client: AsyncClient):
    """Test standard OIDC discovery endpoint."""
    mock_discovery = {
        "issuer": "https://auth.valdrics.ai",
        "jwks_uri": "https://auth.valdrics.ai/.well-known/jwks.json",
        "workload_identity_profile": "signed_jwks_identity_tokens",
    }

    with patch(
        "app.shared.connections.oidc.OIDCService.get_discovery_doc",
        new_callable=AsyncMock,
    ) as mock_get:
        mock_get.return_value = mock_discovery

        response = await oidc_client.get("/.well-known/openid-configuration")

        assert response.status_code == 200
        assert response.json() == mock_discovery


@pytest.mark.asyncio
async def test_jwks_endpoint(oidc_client: AsyncClient):
    """Test JWKS endpoint."""
    mock_jwks = {
        "keys": [
            {"kty": "RSA", "kid": "test-key-id", "use": "sig", "n": "...", "e": "AQAB"}
        ]
    }

    with patch(
        "app.shared.connections.oidc.OIDCService.get_jwks", new_callable=AsyncMock
    ) as mock_get:
        mock_get.return_value = mock_jwks

        response = await oidc_client.get("/.well-known/jwks.json")

        assert response.status_code == 200
        assert response.json() == mock_jwks
