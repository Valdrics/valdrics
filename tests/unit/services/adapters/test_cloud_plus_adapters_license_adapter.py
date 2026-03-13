from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import app.shared.adapters.license_native_dispatch as native_dispatch
from app.shared.adapters.license import LicenseAdapter
from app.shared.core.exceptions import ExternalAPIError


from tests.unit.services.adapters.cloud_plus_test_helpers import (
    FakeAsyncClient as _FakeAsyncClient,
    FakeResponse as _FakeResponse,
    raise_external_api_error as _raise_external_api_error,
)


@pytest.mark.asyncio
async def test_license_adapter_normalizes_feed() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.license_feed = [
        {
            "timestamp": "2026-01-15T00:00:00+00:00",
            "service": "Microsoft E5",
            "cost_usd": 120.0,
        }
    ]
    adapter = LicenseAdapter(conn)
    rows = await adapter.get_cost_and_usage(
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
    )

    assert len(rows) == 1
    assert rows[0]["provider"] == "license"
    assert rows[0]["service"] == "Microsoft E5"
    assert rows[0]["cost_usd"] == 120.0
    assert rows[0]["resource_id"] is None
    assert rows[0]["usage_amount"] is None
    assert rows[0]["usage_unit"] is None


@pytest.mark.asyncio
async def test_license_adapter_native_microsoft_365_costs() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "microsoft_365"
    conn.api_key = "m365-token"
    conn.connector_config = {
        "default_seat_price_usd": 20,
        "sku_prices": {"SPE_E5": 57},
    }
    conn.license_feed = []

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "value": [
                        {
                            "skuId": "sku-1",
                            "skuPartNumber": "SPE_E5",
                            "consumedUnits": 10,
                        }
                    ]
                }
            )
        ]
    )
    adapter = LicenseAdapter(conn)
    with patch(
        "app.shared.adapters.license.get_http_client", return_value=fake_client
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["source_adapter"] == "license_microsoft_graph"
    assert rows[0]["cost_usd"] == 570.0
    assert rows[0]["usage_type"] == "seat_license"
    assert rows[0]["resource_id"] == "sku-1"
    assert rows[0]["usage_amount"] == 10.0
    assert rows[0]["usage_unit"] == "seat"


@pytest.mark.asyncio
async def test_license_adapter_native_rejects_unsupported_vendor() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "flexera"
    conn.api_key = "token"
    conn.connector_config = {}
    conn.license_feed = []

    adapter = LicenseAdapter(conn)
    success = await adapter.verify_connection()

    assert success is False
    assert adapter.last_error is not None
    assert "not supported" in adapter.last_error.lower()


@pytest.mark.asyncio
async def test_license_adapter_manual_requires_non_empty_feed() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.license_feed = []
    conn.connector_config = {}

    adapter = LicenseAdapter(conn)
    success = await adapter.verify_connection()

    assert success is False
    assert "at least one record" in (adapter.last_error or "").lower()


@pytest.mark.asyncio
async def test_license_verify_connection_native_success_and_failure() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "microsoft_365"
    conn.api_key = "token_12345678901234567890"
    conn.connector_config = {}

    adapter = LicenseAdapter(conn)
    with patch.dict(
        native_dispatch._VERIFY_FN_BY_VENDOR,
        {"microsoft_365": AsyncMock(return_value=None)},
        clear=False,
    ):
        assert await adapter.verify_connection() is True

    with patch.dict(
        native_dispatch._VERIFY_FN_BY_VENDOR,
        {"microsoft_365": AsyncMock(side_effect=ExternalAPIError("verify failed"))},
        clear=False,
    ):
        assert await adapter.verify_connection() is False
        assert adapter.last_error is not None


@pytest.mark.asyncio
async def test_license_stream_native_error_falls_back_to_feed() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "microsoft_365"
    conn.api_key = "token_12345678901234567890"
    conn.license_feed = [
        {"date": "2026-01-15T00:00:00Z", "service": "Fallback", "cost_usd": 9.0}
    ]
    conn.connector_config = {}

    adapter = LicenseAdapter(conn)
    with patch.dict(
        native_dispatch._STREAM_FN_BY_VENDOR,
        {"microsoft_365": _raise_external_api_error},
        clear=False,
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["source_adapter"] == "license_feed"
    assert adapter.last_error is not None


@pytest.mark.asyncio
async def test_license_native_uses_prepaid_fallback_and_default_price() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "m365"
    conn.api_key = "token_12345678901234567890"
    conn.connector_config = {"default_seat_price_usd": 12.5, "currency": "usd"}
    conn.license_feed = []

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "value": [
                        {
                            "skuId": "sku-x",
                            "skuPartNumber": "SKU_X",
                            "consumedUnits": 0,
                            "prepaidUnits": {"enabled": 3},
                        }
                    ]
                }
            )
        ]
    )

    adapter = LicenseAdapter(conn)
    with patch(
        "app.shared.adapters.license.get_http_client", return_value=fake_client
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["cost_usd"] == 37.5
    assert rows[0]["currency"] == "USD"
    assert rows[0]["tags"]["consumed_units"] == 3.0
