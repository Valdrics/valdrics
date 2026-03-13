from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

import app.shared.adapters.license as license_module
import app.shared.adapters.license_vendor_microsoft as vendor_microsoft
from app.shared.adapters.license import LicenseAdapter
from app.shared.core.exceptions import ExternalAPIError


from tests.unit.services.adapters.cloud_plus_test_helpers import (
    FakeAsyncClient as _FakeAsyncClient,
    FakeResponse as _FakeResponse,
    InvalidJSONResponse as _InvalidJSONResponse,
    http_status_error as _http_status_error,
)


@pytest.mark.asyncio
async def test_license_get_json_error_paths_and_discover_resources() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    adapter = LicenseAdapter(conn)

    http_error_client = _FakeAsyncClient(
        [
            _FakeResponse({}, status_code=500),
            _FakeResponse({}, status_code=500),
            _FakeResponse({}, status_code=500),
        ]
    )
    with patch(
        "app.shared.adapters.license.get_http_client", return_value=http_error_client
    ):
        with pytest.raises(Exception):
            await adapter._get_json("https://example.invalid", headers={})

    invalid_json_client = _FakeAsyncClient([_InvalidJSONResponse({})])
    with patch(
        "app.shared.adapters.license.get_http_client",
        return_value=invalid_json_client,
    ):
        with pytest.raises(Exception):
            await adapter._get_json("https://example.invalid", headers={})

    non_dict_client = _FakeAsyncClient([_FakeResponse([])])  # type: ignore[list-item]
    with patch(
        "app.shared.adapters.license.get_http_client", return_value=non_dict_client
    ):
        payload = await adapter._get_json("https://example.invalid", headers={})
    assert payload == {"value": []}

    assert await adapter.discover_resources("any") == []


def test_license_helper_branches() -> None:
    now = datetime.now(timezone.utc)
    assert license_module.parse_timestamp(now) == now
    assert license_module.parse_timestamp("invalid").tzinfo == timezone.utc
    assert license_module.parse_timestamp(1700000000).tzinfo == timezone.utc
    assert license_module.as_float(None, default=8.8) == 8.8
    assert license_module.as_float("bad", default=2.4) == 2.4
    assert license_module.is_number("12.5") is True
    assert license_module.is_number("not-a-number") is False


@pytest.mark.asyncio
async def test_license_manual_feed_validation_error_branches() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.connector_config = {}
    adapter = LicenseAdapter(conn)

    conn.license_feed = ["not-dict"]
    assert await adapter.verify_connection() is False
    assert "json object" in (adapter.last_error or "").lower()

    conn.license_feed = [{"cost_usd": 1}]
    assert await adapter.verify_connection() is False
    assert "missing timestamp/date" in (adapter.last_error or "").lower()

    conn.license_feed = [{"timestamp": "2026-01-01", "cost_usd": "x"}]
    assert await adapter.verify_connection() is False
    assert "numeric cost_usd" in (adapter.last_error or "").lower()


@pytest.mark.asyncio
async def test_license_stream_ignores_non_list_feed() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.license_feed = "bad-feed"
    conn.cost_feed = "bad-feed"
    conn.connector_config = {}
    adapter = LicenseAdapter(conn)

    rows = await adapter.get_cost_and_usage(
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
    )
    assert rows == []


@pytest.mark.asyncio
async def test_license_get_json_retry_branches() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    adapter = LicenseAdapter(conn)

    retry_then_success = _FakeAsyncClient(
        [_http_status_error(500), _FakeResponse({"ok": True})]
    )
    with patch(
        "app.shared.adapters.license.get_http_client", return_value=retry_then_success
    ):
        payload = await adapter._get_json("https://example.invalid", headers={})
    assert payload == {"ok": True}

    non_retryable = _FakeAsyncClient([_http_status_error(401)])
    with patch(
        "app.shared.adapters.license.get_http_client", return_value=non_retryable
    ):
        with pytest.raises(ExternalAPIError):
            await adapter._get_json("https://example.invalid", headers={})

    transport_retry = _FakeAsyncClient(
        [httpx.ConnectError("connect"), _FakeResponse({"ok": True})]
    )
    with patch(
        "app.shared.adapters.license.get_http_client", return_value=transport_retry
    ):
        payload = await adapter._get_json("https://example.invalid", headers={})
    assert payload == {"ok": True}

    transport_fail = _FakeAsyncClient(
        [httpx.ConnectError("c1"), httpx.ConnectError("c2"), httpx.ConnectError("c3")]
    )
    with patch(
        "app.shared.adapters.license.get_http_client", return_value=transport_fail
    ):
        with pytest.raises(ExternalAPIError):
            await adapter._get_json("https://example.invalid", headers={})


@pytest.mark.asyncio
async def test_license_stream_invalid_payload_raises() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "microsoft_365"
    conn.api_key = "token_12345678901234567890"
    conn.connector_config = {}
    adapter = LicenseAdapter(conn)

    fake_client = _FakeAsyncClient([_FakeResponse({"value": {"bad": "shape"}})])
    with patch(
        "app.shared.adapters.license.get_http_client", return_value=fake_client
    ):
        with pytest.raises(ExternalAPIError):
            await anext(
                vendor_microsoft.stream_microsoft_365_license_costs(
                    adapter,
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 31, tzinfo=timezone.utc),
                    as_float_fn=license_module.as_float,
                )
            )


@pytest.mark.asyncio
async def test_license_get_json_retries_retryable_status() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    adapter = LicenseAdapter(conn)

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse({}, status_code=429),
            _FakeResponse({"value": []}, status_code=200),
        ]
    )
    with patch(
        "app.shared.adapters.license.get_http_client", return_value=fake_client
    ):
        payload = await adapter._get_json("https://example.invalid", headers={})

    assert payload == {"value": []}
    assert len(fake_client.calls) == 2
