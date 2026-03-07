from __future__ import annotations

from unittest.mock import patch

import pytest

import httpx

from app.shared.adapters.license import LicenseAdapter
from app.shared.core.exceptions import ExternalAPIError
from tests.unit.services.adapters.license_verification_stream_test_helpers import (
    FakeAsyncClient,
    FakeGetClient,
    FakeResponse,
    build_connection,
    http_status_error,
)


def test_license_manual_feed_validation_error_branches() -> None:
    adapter = LicenseAdapter(build_connection(vendor="custom", auth_method="manual"))
    assert adapter._validate_manual_feed("bad") is False  # type: ignore[arg-type]
    assert "at least one record" in (adapter.last_error or "")

    assert adapter._validate_manual_feed(["bad-entry"]) is False
    assert "must be a JSON object" in (adapter.last_error or "")

    assert adapter._validate_manual_feed([{"cost_usd": 1.0}]) is False
    assert "missing timestamp/date" in (adapter.last_error or "")

    assert (
        adapter._validate_manual_feed(
            [{"timestamp": "2026-01-01T00:00:00Z", "cost_usd": "bad"}]
        )
        is False
    )
    assert "must include numeric cost_usd" in (adapter.last_error or "")


@pytest.mark.asyncio
async def test_get_json_returns_empty_dict_for_204() -> None:
    adapter = LicenseAdapter(build_connection())
    request = httpx.Request("GET", "https://example.invalid")
    response = httpx.Response(204, request=request)

    with patch(
        "app.shared.adapters.license.httpx.AsyncClient",
        return_value=FakeGetClient(response),
    ):
        payload = await adapter._get_json("https://example.invalid", headers={})
    assert payload == {}


@pytest.mark.asyncio
async def test_license_get_json_retry_and_shape_branches() -> None:
    adapter = LicenseAdapter(build_connection(vendor="custom", auth_method="oauth"))

    list_payload_client = FakeAsyncClient([FakeResponse([{"id": "u1"}])])
    with patch(
        "app.shared.adapters.license.httpx.AsyncClient",
        return_value=list_payload_client,
    ):
        payload = await adapter._get_json("https://example.invalid", headers={})
    assert payload == {"value": [{"id": "u1"}]}

    bad_shape_client = FakeAsyncClient([FakeResponse("bad-shape")])
    with patch(
        "app.shared.adapters.license.httpx.AsyncClient",
        return_value=bad_shape_client,
    ):
        with pytest.raises(ExternalAPIError, match="invalid payload shape"):
            await adapter._get_json("https://example.invalid", headers={})

    retry_then_ok_client = FakeAsyncClient(
        [http_status_error(500), FakeResponse({"ok": True})]
    )
    with patch(
        "app.shared.adapters.license.httpx.AsyncClient",
        return_value=retry_then_ok_client,
    ):
        payload = await adapter._get_json("https://example.invalid", headers={})
    assert payload == {"ok": True}

    non_retry_client = FakeAsyncClient([http_status_error(401)])
    with patch(
        "app.shared.adapters.license.httpx.AsyncClient",
        return_value=non_retry_client,
    ):
        with pytest.raises(ExternalAPIError, match="status 401"):
            await adapter._get_json("https://example.invalid", headers={})

    transport_client = FakeAsyncClient(
        [httpx.ConnectError("c1"), httpx.ConnectError("c2"), httpx.ConnectError("c3")]
    )
    with patch(
        "app.shared.adapters.license.httpx.AsyncClient",
        return_value=transport_client,
    ):
        with pytest.raises(ExternalAPIError, match="request failed"):
            await adapter._get_json("https://example.invalid", headers={})


@pytest.mark.asyncio
async def test_license_get_json_fallthrough_raises_last_error_and_unexpected() -> None:
    adapter = LicenseAdapter(build_connection(vendor="custom", auth_method="oauth"))

    fallthrough_client = FakeAsyncClient([httpx.ConnectError("c1"), httpx.ConnectError("c2")])
    with (
        patch("app.shared.adapters.license.httpx.AsyncClient", return_value=fallthrough_client),
        patch("app.shared.adapters.http_retry.range", return_value=[1, 2]),
    ):
        with pytest.raises(ExternalAPIError, match="License connector API request failed:"):
            await adapter._get_json("https://example.invalid", headers={})

    with patch("app.shared.adapters.license._NATIVE_MAX_RETRIES", 0):
        with pytest.raises(ExternalAPIError, match="failed unexpectedly"):
            await adapter._get_json("https://example.invalid", headers={})
