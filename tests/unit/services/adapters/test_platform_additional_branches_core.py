from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.shared.adapters.platform import PlatformAdapter
from app.shared.core.exceptions import ExternalAPIError
from tests.unit.services.adapters.platform_additional_test_helpers import (
    _conn,
    _raise_external_api_error,
    _single_row_gen,
)


@pytest.mark.asyncio
async def test_platform_verify_connection_additional_native_and_manual_paths() -> None:
    manual = PlatformAdapter(
        _conn(
            vendor="custom",
            auth_method="manual",
            spend_feed=[{"timestamp": "2026-01-01T00:00:00Z", "cost_usd": 1.0}],
        )
    )
    assert await manual.verify_connection() is True

    ledger = PlatformAdapter(_conn(vendor="ledger", auth_method="api_key"))
    with patch.object(
        ledger, "_verify_ledger_http", new=AsyncMock(side_effect=ExternalAPIError("ledger down"))
    ):
        assert await ledger.verify_connection() is False
    assert "ledger down" in (ledger.last_error or "")

    datadog = PlatformAdapter(_conn(vendor="datadog", auth_method="api_key"))
    with patch.object(
        datadog, "_verify_datadog", new=AsyncMock(side_effect=ExternalAPIError("dd down"))
    ):
        assert await datadog.verify_connection() is False
    assert "dd down" in (datadog.last_error or "")

    newrelic = PlatformAdapter(_conn(vendor="newrelic", auth_method="api_key"))
    with patch.object(
        newrelic, "_verify_newrelic", new=AsyncMock(side_effect=ExternalAPIError("nr down"))
    ):
        assert await newrelic.verify_connection() is False
    assert "nr down" in (newrelic.last_error or "")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("vendor", "method_name"),
    [
        ("ledger", "_stream_ledger_http_cost_and_usage"),
        ("datadog", "_stream_datadog_cost_and_usage"),
        ("newrelic", "_stream_newrelic_cost_and_usage"),
    ],
)
async def test_platform_stream_fallback_for_native_vendors(vendor: str, method_name: str) -> None:
    adapter = PlatformAdapter(
        _conn(
            vendor=vendor,
            auth_method="api_key",
            spend_feed=[{"timestamp": "2026-01-15T00:00:00Z", "service": "fallback", "cost_usd": 3}],
        )
    )
    with patch.object(adapter, method_name, new=_raise_external_api_error):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["source_adapter"] == "platform_feed"
    assert "native upstream down" in (adapter.last_error or "")


@pytest.mark.asyncio
async def test_platform_discover_and_resource_usage_defaults() -> None:
    adapter = PlatformAdapter(_conn())
    assert await adapter.discover_resources("any") == []
    assert await adapter.get_resource_usage("service", "id-1") == []


@pytest.mark.asyncio
async def test_platform_get_resource_usage_projects_manual_feed_rows() -> None:
    now = datetime.now(timezone.utc)
    adapter = PlatformAdapter(
        _conn(
            auth_method="manual",
            spend_feed=[
                {
                    "timestamp": (now - timedelta(days=2)).isoformat(),
                    "service": "Shared Platform",
                    "resource_id": "svc-1",
                    "usage_amount": 2,
                    "usage_unit": "unit",
                    "cost_usd": 5.0,
                },
                {
                    "timestamp": (now - timedelta(days=1)).isoformat(),
                    "service": "Shared Platform",
                    "resource_id": "svc-2",
                    "usage_amount": 3,
                    "cost_usd": 9.0,
                },
            ],
        )
    )
    rows = await adapter.get_resource_usage("platform", "svc-1")
    assert len(rows) == 1
    assert rows[0]["provider"] == "platform"
    assert rows[0]["resource_id"] == "svc-1"
    assert rows[0]["usage_unit"] == "unit"

    defaulted_unit_rows = await adapter.get_resource_usage("platform", "svc-2")
    assert len(defaulted_unit_rows) == 1
    assert defaulted_unit_rows[0]["usage_unit"] == "unit"


@pytest.mark.asyncio
async def test_platform_feed_stream_non_list_and_fallback_values() -> None:
    non_list = PlatformAdapter(_conn(auth_method="manual", spend_feed={"bad": True}))
    rows = [
        row
        async for row in non_list.stream_cost_and_usage(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 31, tzinfo=timezone.utc),
        )
    ]
    assert rows == []

    adapter = PlatformAdapter(
        _conn(
            auth_method="manual",
            spend_feed=[
                {"timestamp": "2025-12-01T00:00:00Z", "cost_usd": 1.0},
                {
                    "timestamp": "2026-01-10T00:00:00Z",
                    "cost_usd": "nan-value",
                    "currency": "eur",
                    "tags": "bad-shape",
                },
            ],
        )
    )
    rows = [
        row
        async for row in adapter.stream_cost_and_usage(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 31, tzinfo=timezone.utc),
        )
    ]
    assert len(rows) == 1
    assert rows[0]["service"] == "Internal Platform"
    assert rows[0]["cost_usd"] == 0.0
    assert rows[0]["tags"] == {}
    assert rows[0]["currency"] == "EUR"


@pytest.mark.asyncio
async def test_platform_verify_connection_unsupported_and_native_success_paths() -> None:
    unsupported_vendor = PlatformAdapter(
        _conn(vendor="custom", auth_method="api_key", spend_feed=[])
    )
    assert await unsupported_vendor.verify_connection() is False
    assert "not supported for vendor" in (unsupported_vendor.last_error or "")

    unsupported_auth = PlatformAdapter(
        _conn(vendor="datadog", auth_method="oauth", spend_feed=[])
    )
    assert await unsupported_auth.verify_connection() is False
    assert "must be one of" in (unsupported_auth.last_error or "")

    ledger = PlatformAdapter(_conn(vendor="ledger", auth_method="api_key"))
    with patch.object(ledger, "_verify_ledger_http", new=AsyncMock(return_value=None)):
        assert await ledger.verify_connection() is True

    datadog = PlatformAdapter(_conn(vendor="datadog", auth_method="api_key"))
    with patch.object(datadog, "_verify_datadog", new=AsyncMock(return_value=None)):
        assert await datadog.verify_connection() is True

    newrelic = PlatformAdapter(_conn(vendor="newrelic", auth_method="api_key"))
    with patch.object(newrelic, "_verify_newrelic", new=AsyncMock(return_value=None)):
        assert await newrelic.verify_connection() is True

    manual_bad = PlatformAdapter(_conn(vendor="custom", auth_method="manual", spend_feed=[]))
    assert await manual_bad.verify_connection() is False
    assert "at least one record" in (manual_bad.last_error or "")

    manual_default_error = PlatformAdapter(
        _conn(vendor="custom", auth_method="manual", spend_feed=[])
    )
    with patch.object(manual_default_error, "_validate_manual_feed", return_value=False):
        assert await manual_default_error.verify_connection() is False
    assert "missing or invalid" in (manual_default_error.last_error or "").lower()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("vendor", "method_name"),
    [
        ("ledger", "_stream_ledger_http_cost_and_usage"),
        ("datadog", "_stream_datadog_cost_and_usage"),
        ("newrelic", "_stream_newrelic_cost_and_usage"),
    ],
)
async def test_platform_stream_native_success_short_circuit(vendor: str, method_name: str) -> None:
    adapter = PlatformAdapter(_conn(vendor=vendor, auth_method="api_key", spend_feed=[]))
    expected_row = {"provider": "platform", "service": "native"}
    with patch.object(adapter, method_name, new=_single_row_gen(expected_row)):
        rows = [
            row
            async for row in adapter.stream_cost_and_usage(
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 2, tzinfo=timezone.utc),
            )
        ]
    assert rows == [expected_row]

