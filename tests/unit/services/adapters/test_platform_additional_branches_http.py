from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.shared.adapters.platform import PlatformAdapter
from app.shared.core.exceptions import ExternalAPIError
from tests.unit.services.adapters.platform_additional_test_helpers import (
    _conn,
    _FakeAsyncClient,
    _FakeResponse,
    _http_status_error,
    _InvalidJSONResponse,
)


@pytest.mark.asyncio
async def test_platform_post_json_retry_and_error_branches() -> None:
    adapter = PlatformAdapter(_conn(vendor="newrelic", auth_method="api_key"))

    retry_then_ok = _FakeAsyncClient([_http_status_error(500, method="POST"), _FakeResponse({"ok": True})])
    with patch("app.shared.adapters.platform.httpx.AsyncClient", return_value=retry_then_ok):
        payload = await adapter._post_json(
            "https://example.invalid",
            headers={"API-Key": "x"},
            json={"query": "ok"},
        )
    assert payload == {"ok": True}

    non_retry = _FakeAsyncClient([_http_status_error(401, method="POST")])
    with patch("app.shared.adapters.platform.httpx.AsyncClient", return_value=non_retry):
        with pytest.raises(ExternalAPIError, match="failed with status 401"):
            await adapter._post_json(
                "https://example.invalid",
                headers={"API-Key": "x"},
                json={"query": "ok"},
            )

    bad_json = _FakeAsyncClient([_InvalidJSONResponse({})])
    with patch("app.shared.adapters.platform.httpx.AsyncClient", return_value=bad_json):
        with pytest.raises(ExternalAPIError, match="invalid JSON"):
            await adapter._post_json(
                "https://example.invalid",
                headers={"API-Key": "x"},
                json={"query": "ok"},
            )

    transport_fail = _FakeAsyncClient(
        [httpx.ConnectError("c1"), httpx.ConnectError("c2"), httpx.ConnectError("c3")]
    )
    with patch("app.shared.adapters.platform.httpx.AsyncClient", return_value=transport_fail):
        with pytest.raises(ExternalAPIError, match="request failed"):
            await adapter._post_json(
                "https://example.invalid",
                headers={"API-Key": "x"},
                json={"query": "ok"},
            )


@pytest.mark.asyncio
async def test_platform_get_json_and_post_json_unexpected_retry_exhaustion_branch() -> None:
    adapter = PlatformAdapter(_conn(vendor="ledger", auth_method="api_key"))
    with patch("app.shared.adapters.platform._NATIVE_MAX_RETRIES", 0):
        with pytest.raises(ExternalAPIError, match="failed unexpectedly"):
            await adapter._get_json("https://example.invalid", headers={})
        with pytest.raises(ExternalAPIError, match="failed unexpectedly"):
            await adapter._post_json(
                "https://example.invalid",
                headers={},
                json={},
            )


@pytest.mark.asyncio
async def test_platform_get_json_retry_and_error_paths() -> None:
    adapter = PlatformAdapter(_conn(vendor="ledger", auth_method="api_key"))

    retry_then_ok = _FakeAsyncClient([_http_status_error(500), _FakeResponse({"ok": True})])
    with patch("app.shared.adapters.platform.httpx.AsyncClient", return_value=retry_then_ok):
        payload = await adapter._get_json("https://example.invalid", headers={})
    assert payload == {"ok": True}

    non_retry = _FakeAsyncClient([_http_status_error(401)])
    with patch("app.shared.adapters.platform.httpx.AsyncClient", return_value=non_retry):
        with pytest.raises(ExternalAPIError, match="status 401"):
            await adapter._get_json("https://example.invalid", headers={})

    bad_json = _FakeAsyncClient([_InvalidJSONResponse({})])
    with patch("app.shared.adapters.platform.httpx.AsyncClient", return_value=bad_json):
        with pytest.raises(ExternalAPIError, match="invalid JSON"):
            await adapter._get_json("https://example.invalid", headers={})

    transport_fail = _FakeAsyncClient(
        [httpx.ConnectError("c1"), httpx.ConnectError("c2"), httpx.ConnectError("c3")]
    )
    with patch("app.shared.adapters.platform.httpx.AsyncClient", return_value=transport_fail):
        with pytest.raises(ExternalAPIError, match="request failed"):
            await adapter._get_json("https://example.invalid", headers={})


@pytest.mark.asyncio
async def test_platform_get_json_and_post_json_fallthrough_raise_last_error() -> None:
    adapter = PlatformAdapter(_conn(vendor="ledger", auth_method="api_key"))

    get_transport_fail = _FakeAsyncClient([httpx.ConnectError("c1"), httpx.ConnectError("c2")])
    with (
        patch("app.shared.adapters.platform.httpx.AsyncClient", return_value=get_transport_fail),
        patch("app.shared.adapters.http_retry.range", return_value=[1, 2]),
    ):
        with pytest.raises(ExternalAPIError, match="Platform request failed:"):
            await adapter._get_json("https://example.invalid", headers={})

    post_transport_fail = _FakeAsyncClient([httpx.ConnectError("p1"), httpx.ConnectError("p2")])
    with (
        patch("app.shared.adapters.platform.httpx.AsyncClient", return_value=post_transport_fail),
        patch("app.shared.adapters.http_retry.range", return_value=[1, 2]),
    ):
        with pytest.raises(ExternalAPIError, match="Platform native request failed:"):
            await adapter._post_json(
                "https://example.invalid",
                headers={"API-Key": "x"},
                json={"query": "ok"},
            )

