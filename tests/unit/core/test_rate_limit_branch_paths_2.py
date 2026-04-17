from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.shared.core import rate_limit as rl


def _settings(**overrides):
    base = {
        "ENVIRONMENT": "development",
        "PLATFORM_RUNTIME_PROFILE": "gcp",
        "RATELIMIT_ENABLED": True,
        "PUBLIC_API_RATE_LIMITING_BACKEND": "cloudflare",
        "TESTING": False,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _request(*, tenant_id=None, auth_header=None):
    headers = {}
    if auth_header is not None:
        headers["Authorization"] = auth_header
    return SimpleNamespace(state=SimpleNamespace(tenant_id=tenant_id), headers=headers)


def test_context_aware_key_falls_back_to_ip_when_hashing_fails() -> None:
    request = _request(auth_header="Bearer abc")
    with (
        patch(
            "app.shared.core.rate_limit.hashlib.sha256",
            side_effect=RuntimeError("boom"),
        ),
        patch("app.shared.core.rate_limit.resolve_client_ip", return_value="10.0.0.7"),
    ):
        assert rl.context_aware_key(request) == "10.0.0.7"


def test_global_limit_key_sanitizes_namespace_and_defaults_to_global() -> None:
    assert (
        rl.global_limit_key("Enforcement Gate/Prod!")(None)
        == "global:enforcement_gate_prod_"
    )
    assert rl.global_limit_key("   ")(None) == "global:global"


def test_get_limiter_logs_cloudflare_delegation_for_managed_profile() -> None:
    with (
        patch("app.shared.core.rate_limit._limiter", None),
        patch("app.shared.core.rate_limit._limiter_enabled", None),
        patch(
            "app.shared.core.rate_limit.get_settings",
            return_value=_settings(
                ENVIRONMENT="production",
                RATELIMIT_ENABLED=False,
                PUBLIC_API_RATE_LIMITING_BACKEND="cloudflare",
            ),
        ),
        patch("app.shared.core.rate_limit.logger") as logger,
    ):
        limiter = rl.get_limiter()

    assert limiter is not None
    logger.info.assert_called_once()


def test_get_limiter_recreates_when_enabled_state_changes() -> None:
    with (
        patch("app.shared.core.rate_limit._limiter", None),
        patch("app.shared.core.rate_limit._limiter_enabled", None),
        patch(
            "app.shared.core.rate_limit.get_settings",
            side_effect=[
                _settings(RATELIMIT_ENABLED=True),
                _settings(RATELIMIT_ENABLED=False),
            ],
        ),
    ):
        first = rl.get_limiter()
        second = rl.get_limiter()

    assert first is not second


def test_reset_rate_limit_runtime_clears_singletons() -> None:
    limiter = MagicMock()

    with (
        patch("app.shared.core.rate_limit._limiter", limiter),
        patch("app.shared.core.rate_limit._limiter_enabled", True),
    ):
        asyncio.run(rl.reset_rate_limit_runtime())
        assert rl._limiter is None
        assert rl._limiter_enabled is None


def test_analysis_limit_returns_original_function_during_testing() -> None:
    def sample() -> str:
        return "ok"

    with patch(
        "app.shared.core.rate_limit.get_settings", return_value=_settings(TESTING=True)
    ):
        decorated = rl.analysis_limit(sample)
    assert decorated is sample


def test_analysis_limit_delegates_to_limiter_when_not_testing() -> None:
    def sample() -> str:
        return "ok"

    limiter = MagicMock()

    def _decorator(func):
        return lambda: f"decorated:{func()}"

    limiter.limit.return_value = _decorator

    with (
        patch(
            "app.shared.core.rate_limit.get_settings",
            return_value=_settings(TESTING=False),
        ),
        patch("app.shared.core.rate_limit.get_limiter", return_value=limiter),
    ):
        decorated = rl.analysis_limit(sample)

    limiter.limit.assert_called_once_with(rl.get_analysis_limit)
    assert decorated() == "decorated:ok"
