from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from starlette.datastructures import Headers
from app.shared.core.rate_limit import (
    context_aware_key,
    global_limit_key,
    global_rate_limit,
    get_analysis_limit,
    setup_rate_limiting,
)


def mock_request(headers=None, state_attrs=None):
    req = MagicMock()
    req.headers = Headers(headers or {})
    # Properly configure state mock
    state = MagicMock()
    # Explicitly set defaults to None so getattr(state, "tenant_id", None) works as expected
    state.tenant_id = None
    state.tier = None

    if state_attrs:
        for k, v in state_attrs.items():
            setattr(state, k, v)
    req.state = state
    req.client = MagicMock()
    req.client.host = "127.0.0.1"
    return req


def test_context_aware_key():
    """Test rate limit key generation strategies."""
    # 1. Tenant ID (Highest priority)
    req1 = mock_request(state_attrs={"tenant_id": "tenant-123"})
    assert context_aware_key(req1) == "tenant:tenant-123"

    # 2. Auth Token Hash
    req2 = mock_request(headers={"Authorization": "Bearer some-token-value"})
    # Patch WHERE IT IS IMPORTED
    with patch(
        "app.shared.core.rate_limit.resolve_client_ip", return_value="127.0.0.1"
    ):
        key = context_aware_key(req2)
        assert key.startswith("token:")
        assert key != "token:some-token-value"  # Should be hashed

    # 3. IP Fallback
    req3 = mock_request(headers={})
    with patch("app.shared.core.rate_limit.resolve_client_ip", return_value="10.0.0.1"):
        assert context_aware_key(req3) == "10.0.0.1"


def test_get_analysis_limit():
    """Test dynamic rate limits based on tier."""
    # Starter default
    req_default = mock_request()
    limit = get_analysis_limit(req_default)
    # The default for requests with no tier is "starter" -> 2/hour
    assert limit == "2/hour"

    # Tier mapping
    assert get_analysis_limit(mock_request(state_attrs={"tier": "starter"})) == "2/hour"
    assert get_analysis_limit(mock_request(state_attrs={"tier": "pro"})) == "50/hour"
    assert (
        get_analysis_limit(mock_request(state_attrs={"tier": "enterprise"}))
        == "200/hour"
    )

    # Invalid tier -> default
    assert get_analysis_limit(mock_request(state_attrs={"tier": "invalid"})) == "1/hour"
    assert get_analysis_limit(None) == "1/hour"


def test_get_analysis_limit_uses_settings_overrides() -> None:
    settings = SimpleNamespace(
        ANALYSIS_RATE_LIMIT_FREE_PER_HOUR=3,
        ANALYSIS_RATE_LIMIT_STARTER_PER_HOUR=7,
        ANALYSIS_RATE_LIMIT_GROWTH_PER_HOUR=11,
        ANALYSIS_RATE_LIMIT_PRO_PER_HOUR=21,
        ANALYSIS_RATE_LIMIT_ENTERPRISE_PER_HOUR=99,
    )

    with patch("app.shared.core.rate_limit.get_settings", return_value=settings):
        assert (
            get_analysis_limit(mock_request(state_attrs={"tier": "free"})) == "3/hour"
        )
        assert (
            get_analysis_limit(mock_request(state_attrs={"tier": "starter"}))
            == "7/hour"
        )
        assert (
            get_analysis_limit(mock_request(state_attrs={"tier": "growth"}))
            == "11/hour"
        )
        assert (
            get_analysis_limit(mock_request(state_attrs={"tier": "pro"})) == "21/hour"
        )
        assert (
            get_analysis_limit(mock_request(state_attrs={"tier": "enterprise"}))
            == "99/hour"
        )


def test_global_limit_key_is_stable_across_requests() -> None:
    key_func = global_limit_key("enforcement_gate")
    req_a = mock_request(state_attrs={"tenant_id": "tenant-a"})
    req_b = mock_request(state_attrs={"tenant_id": "tenant-b"})
    assert key_func(req_a) == "global:enforcement_gate"
    assert key_func(req_b) == "global:enforcement_gate"


@pytest.mark.asyncio
async def test_global_rate_limit_throttles_cross_tenant_requests() -> None:
    settings = SimpleNamespace(
        ENVIRONMENT="development",
        ALLOW_IN_MEMORY_RATE_LIMITS=False,
        RATELIMIT_ENABLED=True,
        TESTING=False,
    )
    with patch("app.shared.core.rate_limit.get_settings", return_value=settings):
        with patch("app.shared.core.rate_limit._limiter", None):
            app = FastAPI()
            setup_rate_limiting(app)

            @app.get("/global-limit")
            @global_rate_limit("2/minute", namespace="enforcement_gate")
            async def global_limit_route(request: Request) -> dict[str, bool]:
                request.state.tenant_id = request.headers.get("x-tenant-id")
                return {"ok": True}

            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                first = await client.get(
                    "/global-limit",
                    headers={"x-tenant-id": "tenant-a"},
                )
                second = await client.get(
                    "/global-limit",
                    headers={"x-tenant-id": "tenant-b"},
                )
                third = await client.get(
                    "/global-limit",
                    headers={"x-tenant-id": "tenant-c"},
                )

            assert first.status_code == 200
            assert second.status_code == 200
            assert third.status_code == 429
