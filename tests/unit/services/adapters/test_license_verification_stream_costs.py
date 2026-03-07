from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

import app.shared.adapters.feed_utils as feed_utils
import app.shared.adapters.license_native_dispatch as native_dispatch
import app.shared.adapters.license_vendor_google as vendor_google
import app.shared.adapters.license_vendor_microsoft as vendor_microsoft
from app.shared.adapters.license import LicenseAdapter
from app.shared.core.exceptions import ExternalAPIError
from tests.unit.services.adapters.license_verification_stream_test_helpers import (
    build_connection,
    row_generator,
)


@pytest.mark.asyncio
async def test_stream_cost_and_usage_google_fallback_and_feed_window_filter() -> None:
    adapter = LicenseAdapter(
        build_connection(
            vendor="google_workspace",
            auth_method="oauth",
            license_feed=[
                {"timestamp": "2025-12-31T00:00:00Z", "cost_usd": 2, "service": "old"},
                {"timestamp": "2026-01-15T00:00:00Z", "cost_usd": 3, "service": "in-range"},
            ],
        )
    )

    async def _raise_google(*_: object, **__: object):  # type: ignore[no-untyped-def]
        raise ExternalAPIError("google down")
        yield {}

    with patch.dict(
        native_dispatch._STREAM_FN_BY_VENDOR,
        {"google_workspace": _raise_google},
        clear=False,
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["service"] == "in-range"
    assert "google down" in (adapter.last_error or "")


@pytest.mark.asyncio
async def test_stream_cost_and_usage_microsoft_native_short_circuit() -> None:
    adapter = LicenseAdapter(
        build_connection(
            vendor="microsoft_365",
            auth_method="oauth",
            license_feed=[{"timestamp": "2026-01-15T00:00:00Z", "cost_usd": 3}],
        )
    )
    expected_row = {"provider": "license", "service": "native-m365"}
    with patch.dict(
        native_dispatch._STREAM_FN_BY_VENDOR,
        {"microsoft_365": row_generator(expected_row)},
        clear=False,
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )
    assert rows == [expected_row]


@pytest.mark.asyncio
async def test_stream_google_workspace_costs_error_and_out_of_range_branches() -> None:
    adapter = LicenseAdapter(
        build_connection(
            vendor="google_workspace",
            auth_method="oauth",
            connector_config={"sku_prices": {"sku-a": 12.5}},
        )
    )

    with patch.object(adapter, "_get_json", new=AsyncMock(side_effect=ExternalAPIError("bad sku"))):
        with pytest.raises(ExternalAPIError, match="failed for all configured SKUs"):
            _ = [
                row
                async for row in vendor_google.stream_google_workspace_license_costs(
                    adapter,
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 31, tzinfo=timezone.utc),
                    as_float_fn=feed_utils.as_float,
                )
            ]

    with patch.object(adapter, "_get_json", new=AsyncMock(return_value={"totalUnits": 2})):
        rows = [
            row
            async for row in vendor_google.stream_google_workspace_license_costs(
                adapter,
                datetime(2026, 2, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                as_float_fn=feed_utils.as_float,
            )
        ]
    assert rows == []

    non_dict_prices = LicenseAdapter(
        build_connection(
            vendor="google_workspace",
            auth_method="oauth",
            connector_config={"sku_prices": ["bad-shape"]},
        )
    )
    with patch.object(non_dict_prices, "_get_json", new=AsyncMock(return_value={"totalUnits": 1})):
        rows = [
            row
            async for row in vendor_google.stream_google_workspace_license_costs(
                non_dict_prices,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
                as_float_fn=feed_utils.as_float,
            )
        ]
    assert len(rows) == 2


@pytest.mark.asyncio
async def test_stream_microsoft_costs_skips_non_dict_entries_and_out_of_range() -> None:
    adapter = LicenseAdapter(build_connection(vendor="microsoft_365", auth_method="oauth"))
    payload = {
        "value": [
            "skip-me",
            {
                "skuId": "abc",
                "skuPartNumber": "M365_X",
                "consumedUnits": 7,
            },
        ]
    }

    with patch.object(adapter, "_get_json", new=AsyncMock(return_value=payload)):
        rows = [
            row
            async for row in vendor_microsoft.stream_microsoft_365_license_costs(
                adapter,
                datetime(2026, 2, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                as_float_fn=feed_utils.as_float,
            )
        ]
    assert rows == []


@pytest.mark.asyncio
async def test_license_stream_fallback_and_native_short_circuit_paths() -> None:
    m365 = LicenseAdapter(
        build_connection(vendor="microsoft_365", auth_method="oauth", license_feed={"bad": True})
    )

    async def _raise_m365(*_args, **_kwargs):
        raise ExternalAPIError("m365 down")
        yield {}

    with patch.dict(
        native_dispatch._STREAM_FN_BY_VENDOR,
        {"microsoft_365": _raise_m365},
        clear=False,
    ):
        rows = [
            row
            async for row in m365.stream_cost_and_usage(
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
                "DAILY",
            )
        ]
    assert rows == []
    assert "m365 down" in (m365.last_error or "")

    google = LicenseAdapter(
        build_connection(vendor="google_workspace", auth_method="oauth", license_feed=[])
    )
    expected = {"provider": "license", "service": "native-google"}
    with patch.dict(
        native_dispatch._STREAM_FN_BY_VENDOR,
        {"google_workspace": row_generator(expected)},
        clear=False,
    ):
        rows = [
            row
            async for row in google.stream_cost_and_usage(
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
                "DAILY",
            )
        ]
    assert rows == [expected]


@pytest.mark.asyncio
async def test_license_stream_fail_closed_for_unsupported_native_auth_vendor() -> None:
    adapter = LicenseAdapter(
        build_connection(
            vendor="custom",
            auth_method="oauth",
            license_feed=[{"timestamp": "2026-01-15T00:00:00Z", "cost_usd": 99.0}],
        )
    )

    rows = [
        row
        async for row in adapter.stream_cost_and_usage(
            datetime(2026, 1, 1, tzinfo=timezone.utc),
            datetime(2026, 1, 31, tzinfo=timezone.utc),
            "DAILY",
        )
    ]

    assert rows == []
    assert "not supported for vendor" in str(adapter.last_error or "")


@pytest.mark.asyncio
async def test_license_verify_native_vendor_http_calls_and_stream_branches() -> None:
    adapter = LicenseAdapter(
        build_connection(
            vendor="google_workspace",
            auth_method="oauth",
            connector_config={
                "sku_prices": {"sku-a": 10.0, 123: 4},
                "currency": "USD",
            },
        )
    )
    with patch.object(adapter, "_get_json", new=AsyncMock(return_value={"ok": True})) as get_mock:
        await native_dispatch._VERIFY_FN_BY_VENDOR["microsoft_365"](adapter)
        await native_dispatch._VERIFY_FN_BY_VENDOR["google_workspace"](adapter)
        await native_dispatch._VERIFY_FN_BY_VENDOR["github"](adapter)
    assert get_mock.await_count == 3

    with patch.object(
        adapter,
        "_get_json",
        new=AsyncMock(return_value={"totalUnits": 3}),
    ):
        rows = [
            row
            async for row in vendor_google.stream_google_workspace_license_costs(
                adapter,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
                as_float_fn=feed_utils.as_float,
            )
        ]
    assert len(rows) == 1
    assert rows[0]["usage_amount"] == 3.0

    bad_m365 = LicenseAdapter(build_connection(vendor="microsoft_365", auth_method="oauth"))
    with patch.object(bad_m365, "_get_json", new=AsyncMock(return_value={"value": {}})):
        with pytest.raises(ExternalAPIError, match="Invalid Microsoft Graph"):
            _ = [
                row
                async for row in vendor_microsoft.stream_microsoft_365_license_costs(
                    bad_m365,
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 31, tzinfo=timezone.utc),
                    as_float_fn=feed_utils.as_float,
                )
            ]

    good_m365 = LicenseAdapter(
        build_connection(
            vendor="microsoft_365",
            auth_method="oauth",
            connector_config={"sku_prices": {"M365_X": 5.0}},
        )
    )
    with patch.object(
        good_m365,
        "_get_json",
        new=AsyncMock(
            return_value={
                "value": [
                    {
                        "skuId": "abc",
                        "skuPartNumber": "m365_x",
                        "consumedUnits": 0,
                        "prepaidUnits": {"enabled": 2},
                    }
                ]
            }
        ),
    ):
        rows = [
            row
            async for row in vendor_microsoft.stream_microsoft_365_license_costs(
                good_m365,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
                as_float_fn=feed_utils.as_float,
            )
        ]
    assert len(rows) == 1
    assert rows[0]["cost_usd"] == 10.0

    non_string_sku_key = LicenseAdapter(
        build_connection(
            vendor="microsoft_365",
            auth_method="oauth",
            connector_config={"sku_prices": {123: 9.0, "M365_Z": 3.0}},
        )
    )
    with patch.object(
        non_string_sku_key,
        "_get_json",
        new=AsyncMock(
            return_value={
                "value": [
                    {
                        "skuId": "abc",
                        "skuPartNumber": "m365_z",
                        "consumedUnits": 1,
                    }
                ]
            }
        ),
    ):
        rows = [
            row
            async for row in vendor_microsoft.stream_microsoft_365_license_costs(
                non_string_sku_key,
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
                as_float_fn=feed_utils.as_float,
            )
        ]
    assert len(rows) == 1
    assert rows[0]["cost_usd"] == 3.0
