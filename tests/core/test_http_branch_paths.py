from __future__ import annotations

from unittest.mock import patch

import pytest

import app.shared.core.http as http_module


@pytest.fixture(autouse=True)
async def _cleanup_clients() -> None:
    await http_module.close_http_client()
    yield
    await http_module.close_http_client()


@pytest.mark.asyncio
async def test_get_http_client_insecure_lazy_initializes_separate_pool() -> None:
    with patch(
        "app.shared.core.outbound_tls.get_settings",
        return_value=type(
            "_Settings",
            (),
            {
                "is_strict_environment": False,
                "ALLOW_INSECURE_OUTBOUND_TLS": False,
            },
        )(),
    ):
        secure_client = http_module.get_http_client(verify=True)
        insecure_client = http_module.get_http_client(verify=False)

    assert secure_client is not insecure_client
    assert insecure_client.is_closed is False


@pytest.mark.asyncio
async def test_get_http_client_rejects_insecure_tls_in_strict_environment() -> None:
    with patch(
        "app.shared.core.outbound_tls.get_settings",
        return_value=type(
            "_Settings",
            (),
            {
                "is_strict_environment": True,
                "ALLOW_INSECURE_OUTBOUND_TLS": False,
            },
        )(),
    ), pytest.raises(ValueError, match="verify_ssl=false is forbidden"):
        http_module.get_http_client(verify=False)


@pytest.mark.asyncio
async def test_get_http_client_allows_insecure_tls_with_break_glass() -> None:
    with patch(
        "app.shared.core.outbound_tls.get_settings",
        return_value=type(
            "_Settings",
            (),
            {
                "is_strict_environment": True,
                "ALLOW_INSECURE_OUTBOUND_TLS": True,
            },
        )(),
    ):
        insecure_client = http_module.get_http_client(verify=False)

    assert insecure_client.is_closed is False


@pytest.mark.asyncio
async def test_get_http_client_reinitializes_when_event_loop_marker_changes() -> None:
    with patch(
        "app.shared.core.outbound_tls.get_settings",
        return_value=type(
            "_Settings",
            (),
            {
                "is_strict_environment": False,
                "ALLOW_INSECURE_OUTBOUND_TLS": False,
            },
        )(),
    ):
        client1 = http_module.get_http_client()
        setattr(client1, "_valdrics_loop_marker", 1)
        with patch.object(http_module, "_current_loop_marker", return_value=2):
            client2 = http_module.get_http_client()

    assert client2 is not client1
    assert client2.is_closed is False


@pytest.mark.asyncio
async def test_init_http_client_warns_when_already_initialized() -> None:
    await http_module.init_http_client()
    with patch("app.shared.core.http.logger.warning") as warning:
        await http_module.init_http_client()
    warning.assert_called_once_with("http_client_already_initialized")


class _SyncCloseClient:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _NoCloseClient:
    pass


@pytest.mark.asyncio
async def test_close_http_client_handles_sync_close_and_missing_close_methods() -> None:
    sync_client = _SyncCloseClient()
    no_close_client = _NoCloseClient()
    http_module._client = sync_client  # type: ignore[assignment]
    http_module._insecure_client = no_close_client  # type: ignore[assignment]

    await http_module.close_http_client()

    assert sync_client.closed is True
    assert http_module._client is None
    assert http_module._insecure_client is None
