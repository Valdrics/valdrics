import pytest
from unittest.mock import MagicMock, patch
from app.shared.core.rate_limit import (
    context_aware_key,
    get_analysis_limit,
    get_limiter,
)
from uuid import uuid4
from types import SimpleNamespace


@pytest.fixture
def mock_request():
    request = SimpleNamespace()
    request.state = SimpleNamespace()
    request.headers = MagicMock()
    return request


def test_context_aware_key_tenant_id(mock_request):
    """Test key extraction from tenant_id in state."""
    tenant_id = str(uuid4())

    mock_request.state.tenant_id = tenant_id

    key = context_aware_key(mock_request)
    assert key == f"tenant:{tenant_id}"


def test_context_aware_key_token_hash(mock_request):
    """Test key extraction from Authorization header token."""
    mock_request.state.tenant_id = None
    mock_request.headers = {"Authorization": "Bearer my-secret-token"}

    key = context_aware_key(mock_request)
    assert key.startswith("token:")
    assert len(key) == 6 + 16  # "token:" + 16 hex chars


def test_context_aware_key_ip_fallback(mock_request):
    """Test fallback to remote address."""
    mock_request.state.tenant_id = None
    mock_request.headers = {}

    with patch(
        "app.shared.core.rate_limit.resolve_client_ip", return_value="127.0.0.1"
    ):
        key = context_aware_key(mock_request)
        assert key == "127.0.0.1"


def test_get_analysis_limit_tiers(mock_request):
    """Test tiers return correct limit strings."""
    mock_request.state.tier = "pro"
    assert get_analysis_limit(mock_request) == "50/hour"

    mock_request.state.tier = "growth"
    assert get_analysis_limit(mock_request) == "10/hour"

    mock_request.state.tier = "unknown"
    assert get_analysis_limit(mock_request) == "1/hour"


def test_get_analysis_limit_tiers_use_configured_settings(mock_request):
    settings = SimpleNamespace(
        ANALYSIS_RATE_LIMIT_FREE_PER_HOUR=4,
        ANALYSIS_RATE_LIMIT_STARTER_PER_HOUR=8,
        ANALYSIS_RATE_LIMIT_GROWTH_PER_HOUR=12,
        ANALYSIS_RATE_LIMIT_PRO_PER_HOUR=60,
        ANALYSIS_RATE_LIMIT_ENTERPRISE_PER_HOUR=240,
    )

    with patch("app.shared.core.rate_limit.get_settings", return_value=settings):
        mock_request.state.tier = "pro"
        assert get_analysis_limit(mock_request) == "60/hour"

        mock_request.state.tier = "growth"
        assert get_analysis_limit(mock_request) == "12/hour"

        mock_request.state.tier = "free"
        assert get_analysis_limit(mock_request) == "4/hour"


def test_get_limiter_initialization():
    """Test that limiter is initialized with correct strategy."""
    with patch("app.shared.core.rate_limit._limiter", None):
        limiter = get_limiter()
        assert limiter is not None


def test_get_limiter_uses_memory_storage_in_local_runtime() -> None:
    mock_settings = SimpleNamespace(
        ENVIRONMENT="local",
        PLATFORM_RUNTIME_PROFILE="gcp",
        RATELIMIT_ENABLED=True,
        PUBLIC_API_RATE_LIMITING_BACKEND="cloudflare",
        TESTING=False,
    )
    with patch("app.shared.core.rate_limit.get_settings", return_value=mock_settings):
        with (
            patch("app.shared.core.rate_limit._limiter", None),
            patch("app.shared.core.rate_limit._limiter_enabled", None),
        ):
            limiter = get_limiter()
            assert limiter is not None
            assert limiter._storage_uri == "memory://"


def test_get_limiter_allows_disabled_cloudflare_edge_profile() -> None:
    mock_settings = SimpleNamespace(
        ENVIRONMENT="production",
        ALLOW_IN_MEMORY_RATE_LIMITS=False,
        RATELIMIT_ENABLED=False,
        PUBLIC_API_RATE_LIMITING_BACKEND="cloudflare",
        TESTING=False,
    )
    with patch("app.shared.core.rate_limit.get_settings", return_value=mock_settings):
        with patch("app.shared.core.rate_limit._limiter", None):
            limiter = get_limiter()
            assert limiter is not None


def test_setup_rate_limiting():
    """Test standard app setup for rate limiting."""
    app = MagicMock()
    app.state = MagicMock()
    with patch("app.shared.core.rate_limit.get_limiter") as mock_get:
        mock_limiter = MagicMock()
        mock_get.return_value = mock_limiter
        from app.shared.core.rate_limit import setup_rate_limiting

        setup_rate_limiting(app)
        assert app.state.limiter == mock_limiter
        app.add_exception_handler.assert_called_once()
