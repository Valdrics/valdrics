from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import httpx
import pytest

import app.shared.adapters.saas as saas_module
from app.shared.adapters.saas import SaaSAdapter
from app.shared.core.exceptions import ExternalAPIError


from tests.unit.services.adapters.cloud_plus_test_helpers import (
    FakeAsyncClient as _FakeAsyncClient,
    FakeResponse as _FakeResponse,
    InvalidJSONResponse as _InvalidJSONResponse,
    http_status_error as _http_status_error,
)


@pytest.mark.asyncio
async def test_saas_get_json_error_paths_and_discover_resources() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    adapter = SaaSAdapter(conn)

    http_error_client = _FakeAsyncClient(
        [
            _FakeResponse({}, status_code=500),
            _FakeResponse({}, status_code=500),
            _FakeResponse({}, status_code=500),
        ]
    )
    with patch(
        "app.shared.adapters.saas.get_http_client", return_value=http_error_client
    ):
        with pytest.raises(Exception):
            await adapter._get_json("https://example.invalid", headers={})

    invalid_json_client = _FakeAsyncClient([_InvalidJSONResponse({})])
    with patch(
        "app.shared.adapters.saas.get_http_client", return_value=invalid_json_client
    ):
        with pytest.raises(Exception):
            await adapter._get_json("https://example.invalid", headers={})

    non_dict_client = _FakeAsyncClient([_FakeResponse([])])  # type: ignore[list-item]
    with patch(
        "app.shared.adapters.saas.get_http_client", return_value=non_dict_client
    ):
        with pytest.raises(Exception):
            await adapter._get_json("https://example.invalid", headers={})

    assert await adapter.discover_resources("any") == []


@pytest.mark.asyncio
async def test_saas_get_json_retries_retryable_status() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    adapter = SaaSAdapter(conn)

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse({}, status_code=429),
            _FakeResponse({"data": []}, status_code=200),
        ]
    )
    with patch("app.shared.adapters.saas.get_http_client", return_value=fake_client):
        payload = await adapter._get_json("https://example.invalid", headers={})

    assert payload == {"data": []}
    assert len(fake_client.calls) == 2


def test_saas_helper_branches() -> None:
    now = datetime.now(timezone.utc)
    assert saas_module.parse_timestamp(now) == now
    assert saas_module.parse_timestamp("invalid").tzinfo == timezone.utc
    assert saas_module.parse_timestamp(1700000000).tzinfo == timezone.utc
    assert saas_module.as_float(None, default=9.1) == 9.1
    assert saas_module.as_float("bad", default=3.2) == 3.2
    assert saas_module.as_float("10", divisor=0) == 10.0
    assert saas_module.is_number("12.5") is True
    assert saas_module.is_number("not-a-number") is False


@pytest.mark.asyncio
async def test_saas_manual_feed_validation_error_branches() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.connector_config = {}
    adapter = SaaSAdapter(conn)

    conn.spend_feed = ["not-dict"]
    assert await adapter.verify_connection() is False
    assert "json object" in (adapter.last_error or "").lower()

    conn.spend_feed = [{"cost_usd": 1}]
    assert await adapter.verify_connection() is False
    assert "missing timestamp/date" in (adapter.last_error or "").lower()

    conn.spend_feed = [{"timestamp": "2026-01-01", "cost_usd": "x"}]
    assert await adapter.verify_connection() is False
    assert "numeric cost_usd" in (adapter.last_error or "").lower()


@pytest.mark.asyncio
async def test_saas_stream_ignores_non_list_feed() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.spend_feed = "bad-feed"
    conn.cost_feed = "bad-feed"
    conn.connector_config = {}
    adapter = SaaSAdapter(conn)

    rows = await adapter.get_cost_and_usage(
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
    )
    assert rows == []


@pytest.mark.asyncio
async def test_saas_stream_stripe_invalid_payload_raises() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "stripe"
    conn.api_key = "sk_test_12345678901234567890"
    conn.connector_config = {}
    conn.spend_feed = []
    adapter = SaaSAdapter(conn)

    fake_client = _FakeAsyncClient([_FakeResponse({"data": {"not": "list"}})])
    with patch("app.shared.adapters.saas.get_http_client", return_value=fake_client):
        with pytest.raises(ExternalAPIError):
            await anext(
                adapter._stream_stripe_cost_and_usage(
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 31, tzinfo=timezone.utc),
                )
            )


@pytest.mark.asyncio
async def test_saas_stream_salesforce_invalid_payload_raises() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "salesforce"
    conn.api_key = "token_12345678901234567890"
    conn.connector_config = {"instance_url": "https://example.my.salesforce.com"}
    adapter = SaaSAdapter(conn)

    fake_client = _FakeAsyncClient([_FakeResponse({"records": {"bad": "shape"}})])
    with patch("app.shared.adapters.saas.get_http_client", return_value=fake_client):
        with pytest.raises(ExternalAPIError):
            await anext(
                adapter._stream_salesforce_cost_and_usage(
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 31, tzinfo=timezone.utc),
                )
            )


@pytest.mark.asyncio
async def test_saas_get_json_retry_branches() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    adapter = SaaSAdapter(conn)

    retry_then_success = _FakeAsyncClient(
        [_http_status_error(500), _FakeResponse({"ok": True})]
    )
    with patch(
        "app.shared.adapters.saas.get_http_client", return_value=retry_then_success
    ):
        payload = await adapter._get_json("https://example.invalid", headers={})
    assert payload == {"ok": True}

    non_retryable = _FakeAsyncClient([_http_status_error(401)])
    with patch(
        "app.shared.adapters.saas.get_http_client", return_value=non_retryable
    ):
        with pytest.raises(ExternalAPIError):
            await adapter._get_json("https://example.invalid", headers={})

    transport_retry = _FakeAsyncClient(
        [httpx.ConnectError("connect"), _FakeResponse({"ok": True})]
    )
    with patch(
        "app.shared.adapters.saas.get_http_client", return_value=transport_retry
    ):
        payload = await adapter._get_json("https://example.invalid", headers={})
    assert payload == {"ok": True}

    transport_fail = _FakeAsyncClient(
        [httpx.ConnectError("c1"), httpx.ConnectError("c2"), httpx.ConnectError("c3")]
    )
    with patch(
        "app.shared.adapters.saas.get_http_client", return_value=transport_fail
    ):
        with pytest.raises(ExternalAPIError):
            await adapter._get_json("https://example.invalid", headers={})


@pytest.mark.asyncio
async def test_saas_discover_resources_projects_from_cost_rows() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.spend_feed = [
        {
            "timestamp": "2026-02-20T00:00:00Z",
            "service": "GitHub",
            "resource_id": "gh-seat-1",
            "cost_usd": 4.2,
            "region": "global",
            "usage_type": "subscription",
        }
    ]
    conn.connector_config = {}

    adapter = SaaSAdapter(conn)
    adapter.last_error = "stale"
    resources = await adapter.discover_resources("saas")

    assert len(resources) == 1
    assert resources[0]["id"] == "gh-seat-1"
    assert resources[0]["type"] == "saas_subscription"
    assert resources[0]["provider"] == "saas"
    assert resources[0]["metadata"]["total_cost_usd"] == pytest.approx(4.2)
    assert adapter.last_error is None
