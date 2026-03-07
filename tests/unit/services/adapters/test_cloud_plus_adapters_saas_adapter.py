from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.adapters.saas import SaaSAdapter
from app.shared.core.exceptions import ExternalAPIError


from tests.unit.services.adapters.cloud_plus_test_helpers import (
    FakeAsyncClient as _FakeAsyncClient,
    FakeResponse as _FakeResponse,
    raise_external_api_error as _raise_external_api_error,
)


@pytest.mark.asyncio
async def test_saas_adapter_normalizes_feed() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.spend_feed = [
        {
            "date": "2026-01-10T00:00:00Z",
            "vendor": "Slack",
            "amount_usd": 25.5,
            "tags": {"team": "platform"},
        }
    ]
    adapter = SaaSAdapter(conn)
    rows = await adapter.get_cost_and_usage(
        start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
    )

    assert len(rows) == 1
    assert rows[0]["provider"] == "saas"
    assert rows[0]["service"] == "Slack"
    assert rows[0]["cost_usd"] == 25.5
    assert rows[0]["resource_id"] is None
    assert rows[0]["usage_amount"] is None
    assert rows[0]["usage_unit"] is None


@pytest.mark.asyncio
async def test_saas_adapter_native_stripe_normalizes_invoices() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "stripe"
    conn.api_key = "sk_test_123"
    conn.spend_feed = []
    conn.connector_config = {}

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "data": [
                        {
                            "id": "in_123",
                            "created": int(
                                datetime(2026, 1, 12, tzinfo=timezone.utc).timestamp()
                            ),
                            "amount_paid": 1299,
                            "currency": "usd",
                            "description": "Stripe Platform",
                            "customer": "cus_123",
                        }
                    ],
                    "has_more": False,
                }
            )
        ]
    )
    adapter = SaaSAdapter(conn)
    with patch("app.shared.adapters.saas.httpx.AsyncClient", return_value=fake_client):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["source_adapter"] == "saas_stripe_api"
    assert rows[0]["cost_usd"] == 12.99
    assert rows[0]["currency"] == "USD"
    assert rows[0]["resource_id"] == "in_123"
    assert rows[0]["usage_amount"] == 1.0
    assert rows[0]["usage_unit"] == "invoice"


@pytest.mark.asyncio
async def test_saas_adapter_native_stripe_converts_non_usd_currency() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "stripe"
    conn.api_key = "sk_test_123"
    conn.spend_feed = []
    conn.connector_config = {}

    # 92 EUR at USD->EUR=0.92 => 100 USD
    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "data": [
                        {
                            "id": "in_234",
                            "created": int(
                                datetime(2026, 1, 12, tzinfo=timezone.utc).timestamp()
                            ),
                            "amount_paid": 9200,
                            "currency": "eur",
                            "description": "Stripe Platform",
                            "customer": "cus_234",
                        }
                    ],
                    "has_more": False,
                }
            )
        ]
    )
    adapter = SaaSAdapter(conn)
    with (
        patch("app.shared.adapters.saas.httpx.AsyncClient", return_value=fake_client),
        patch(
            "app.shared.core.currency.get_exchange_rate",
            new=AsyncMock(return_value=Decimal("0.92")),
        ),
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["currency"] == "EUR"
    assert rows[0]["amount_raw"] == 92.0
    assert rows[0]["cost_usd"] == pytest.approx(100.0, abs=0.0001)
    assert rows[0]["resource_id"] == "in_234"
    assert rows[0]["usage_amount"] == 1.0
    assert rows[0]["usage_unit"] == "invoice"


@pytest.mark.asyncio
async def test_saas_adapter_native_salesforce_requires_instance_url() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "salesforce"
    conn.api_key = "token"
    conn.connector_config = {}
    conn.spend_feed = []

    adapter = SaaSAdapter(conn)
    success = await adapter.verify_connection()

    assert success is False
    assert adapter.last_error is not None
    assert "instance_url" in adapter.last_error


@pytest.mark.asyncio
async def test_saas_adapter_native_rejects_unsupported_vendor() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "hubspot"
    conn.api_key = "token"
    conn.connector_config = {}
    conn.spend_feed = []

    adapter = SaaSAdapter(conn)
    success = await adapter.verify_connection()

    assert success is False
    assert adapter.last_error is not None
    assert "not supported" in adapter.last_error.lower()


@pytest.mark.asyncio
async def test_saas_adapter_manual_requires_non_empty_feed() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.spend_feed = []
    conn.connector_config = {}

    adapter = SaaSAdapter(conn)
    success = await adapter.verify_connection()

    assert success is False
    assert "at least one record" in (adapter.last_error or "").lower()


@pytest.mark.asyncio
async def test_saas_verify_connection_native_success_and_failure() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "stripe"
    conn.api_key = "sk_test_12345678901234567890"
    conn.connector_config = {}

    adapter = SaaSAdapter(conn)
    with patch.object(adapter, "_verify_stripe", new=AsyncMock(return_value=None)):
        assert await adapter.verify_connection() is True

    with patch.object(
        adapter,
        "_verify_stripe",
        new=AsyncMock(side_effect=ExternalAPIError("boom")),
    ):
        assert await adapter.verify_connection() is False
        assert adapter.last_error is not None


@pytest.mark.asyncio
async def test_saas_stream_native_error_falls_back_to_feed() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "stripe"
    conn.api_key = "sk_test_12345678901234567890"
    conn.spend_feed = [
        {"timestamp": "2026-01-03T00:00:00Z", "service": "Fallback", "cost_usd": 5.0}
    ]
    conn.connector_config = {}

    adapter = SaaSAdapter(conn)
    with patch.object(
        adapter,
        "_stream_stripe_cost_and_usage",
        new=_raise_external_api_error,
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["source_adapter"] == "saas_feed"
    assert adapter.last_error is not None


@pytest.mark.asyncio
async def test_saas_stream_stripe_pagination() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "stripe"
    conn.api_key = "sk_test_12345678901234567890"
    conn.spend_feed = []
    conn.connector_config = {}

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "data": [
                        {
                            "id": "in_1",
                            "created": int(
                                datetime(2026, 1, 11, tzinfo=timezone.utc).timestamp()
                            ),
                            "total": 1000,
                            "currency": "usd",
                        }
                    ],
                    "has_more": True,
                }
            ),
            _FakeResponse(
                {
                    "data": [
                        {
                            "id": "in_2",
                            "created": int(
                                datetime(2026, 1, 12, tzinfo=timezone.utc).timestamp()
                            ),
                            "amount_paid": 500,
                            "currency": "eur",
                        }
                    ],
                    "has_more": False,
                }
            ),
        ]
    )

    adapter = SaaSAdapter(conn)
    with (
        patch("app.shared.adapters.saas.httpx.AsyncClient", return_value=fake_client),
        patch(
            "app.shared.core.currency.get_exchange_rate",
            new=AsyncMock(return_value=Decimal("0.92")),
        ),
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 2
    assert rows[0]["cost_usd"] == 10.0
    assert rows[1]["cost_usd"] == pytest.approx(5.4347826, abs=0.0001)
    assert rows[1]["currency"] == "EUR"
    assert fake_client.calls[1]["params"]["starting_after"] == "in_1"  # type: ignore[index]


@pytest.mark.asyncio
async def test_saas_stream_salesforce_pagination() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "salesforce"
    conn.api_key = "token_12345678901234567890"
    conn.connector_config = {"instance_url": "https://example.my.salesforce.com"}
    conn.spend_feed = []

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "records": [
                        {
                            "Id": "a01",
                            "Description": "Contract A",
                            "ServiceDate": "2026-01-10",
                            "TotalPrice": "12.5",
                            "CurrencyIsoCode": "usd",
                        }
                    ],
                    "nextRecordsUrl": "/services/data/v60.0/query/next",
                }
            ),
            _FakeResponse(
                {
                    "records": [
                        {
                            "Id": "a02",
                            "Description": "Contract B",
                            "ServiceDate": "2026-01-11",
                            "TotalPrice": "7.5",
                            "CurrencyIsoCode": "usd",
                        }
                    ]
                }
            ),
        ]
    )

    adapter = SaaSAdapter(conn)
    with patch("app.shared.adapters.saas.httpx.AsyncClient", return_value=fake_client):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 2
    assert rows[0]["source_adapter"] == "saas_salesforce_api"


@pytest.mark.asyncio
async def test_saas_stream_salesforce_converts_non_usd_currency() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "salesforce"
    conn.api_key = "token"
    conn.connector_config = {"instance_url": "https://example.my.salesforce.com"}
    conn.spend_feed = []

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "records": [
                        {
                            "Id": "a01",
                            "Description": "Salesforce Contract",
                            "ServiceDate": "2026-01-10",
                            "TotalPrice": "92.0",
                            "CurrencyIsoCode": "eur",
                        }
                    ]
                }
            )
        ]
    )

    adapter = SaaSAdapter(conn)
    with (
        patch("app.shared.adapters.saas.httpx.AsyncClient", return_value=fake_client),
        patch(
            "app.shared.core.currency.get_exchange_rate",
            new=AsyncMock(return_value=Decimal("0.92")),
        ),
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["currency"] == "EUR"
    assert rows[0]["amount_raw"] == 92.0
    assert rows[0]["cost_usd"] == pytest.approx(100.0, abs=0.0001)


@pytest.mark.asyncio
async def test_saas_verify_salesforce_success() -> None:
    conn = MagicMock()
    conn.auth_method = "oauth"
    conn.vendor = "salesforce"
    conn.api_key = "token_12345678901234567890"
    conn.connector_config = {"instance_url": "https://example.my.salesforce.com"}
    conn.spend_feed = []
    adapter = SaaSAdapter(conn)

    fake_client = _FakeAsyncClient([_FakeResponse({"ok": True})])
    with patch("app.shared.adapters.saas.httpx.AsyncClient", return_value=fake_client):
        assert await adapter.verify_connection() is True
