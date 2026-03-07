from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from app.shared.adapters.platform import PlatformAdapter
from app.shared.core.exceptions import ExternalAPIError
from tests.unit.services.adapters.platform_additional_test_helpers import _conn


@pytest.mark.asyncio
async def test_platform_verify_datadog_and_strict_pricing_branch() -> None:
    adapter = PlatformAdapter(
        _conn(
            vendor="datadog",
            auth_method="api_key",
            connector_config={"site": "datadoghq.com", "unit_prices_usd": {"hosts": 2.0}},
        )
    )
    with patch.object(
        adapter,
        "_get_json",
        new=AsyncMock(
            return_value={"usage": [{"billing_dimension": "hosts", "usage": 1, "unit": "host"}]}
        ),
    ):
        await adapter._verify_datadog()

    strict_adapter = PlatformAdapter(
        _conn(
            vendor="datadog",
            auth_method="api_key",
            connector_config={
                "site": "datadoghq.com",
                "strict_pricing": True,
                "unit_prices_usd": {"hosts": 2.0},
            },
        )
    )
    with patch.object(
        strict_adapter,
        "_get_json",
        new=AsyncMock(return_value={"usage": [{"billing_dimension": "apm", "usage": 4}]}),
    ):
        with pytest.raises(ExternalAPIError, match="Missing unit price"):
            _ = [
                row
                async for row in strict_adapter._stream_datadog_cost_and_usage(
                    datetime(2026, 1, 1, tzinfo=timezone.utc),
                    datetime(2026, 1, 31, tzinfo=timezone.utc),
                )
            ]


@pytest.mark.asyncio
async def test_platform_newrelic_helpers_and_error_paths() -> None:
    adapter = PlatformAdapter(
        _conn(
            vendor="newrelic",
            auth_method="api_key",
            connector_config={
                "account_id": "123",
                "nrql_query": "SELECT latest(gigabytes) AS gigabytes SINCE '{start}' UNTIL '{end}'",
                "unit_prices_usd": {"gigabytes": 0.5},
            },
        )
    )
    assert adapter._resolve_newrelic_account_id() == 123
    assert "latest(gigabytes)" in adapter._resolve_newrelic_nrql_template()

    with patch.object(adapter, "_post_json", new=AsyncMock(return_value=[])):
        with pytest.raises(ExternalAPIError, match="invalid payload"):
            await adapter._verify_newrelic()

    with patch.object(adapter, "_post_json", new=AsyncMock(return_value={"data": "bad"})):
        with pytest.raises(ExternalAPIError, match="missing data"):
            await adapter._verify_newrelic()

    with patch.object(adapter, "_post_json", new=AsyncMock(return_value={"data": {"actor": "bad"}})):
        with pytest.raises(ExternalAPIError, match="missing actor"):
            await adapter._verify_newrelic()

    with patch.object(
        adapter,
        "_post_json",
        new=AsyncMock(return_value={"data": {"actor": {"requestContext": {}}}}),
    ):
        with pytest.raises(ExternalAPIError, match="validation failed"):
            await adapter._verify_newrelic()


@pytest.mark.asyncio
async def test_platform_stream_newrelic_invalid_shapes() -> None:
    adapter = PlatformAdapter(
        _conn(
            vendor="newrelic",
            auth_method="api_key",
            connector_config={
                "account_id": 123,
                "nrql_template": "FROM X SELECT latest(gigabytes) AS gigabytes SINCE '{start}' UNTIL '{end}'",
                "unit_prices_usd": {"gigabytes": 0.5},
            },
        )
    )
    bad_payloads: list[object] = [
        [],
        {"data": None},
        {"data": {"actor": None}},
        {"data": {"actor": {"account": None}}},
        {"data": {"actor": {"account": {"nrql": None}}}},
        {"data": {"actor": {"account": {"nrql": {"results": {}}}}}},
    ]
    for payload in bad_payloads:
        with patch.object(adapter, "_post_json", new=AsyncMock(return_value=payload)):
            with pytest.raises(ExternalAPIError):
                await anext(
                    adapter._stream_newrelic_cost_and_usage(
                        datetime(2026, 1, 1, tzinfo=timezone.utc),
                        datetime(2026, 1, 31, tzinfo=timezone.utc),
                    )
                )


@pytest.mark.asyncio
async def test_platform_ledger_helpers_extract_and_conversion_fallback() -> None:
    adapter = PlatformAdapter(
        _conn(
            vendor="ledger",
            auth_method="api_key",
            connector_config={
                "base_url": "https://ledger.example.com",
                "path": "finops/costs",
                "api_key_header": "X-API-Key",
            },
        )
    )
    assert adapter._resolve_ledger_http_costs_path() == "/finops/costs"
    assert adapter._resolve_ledger_http_headers() == {"X-API-Key": "token-123"}

    assert adapter._extract_ledger_records([{"x": 1}, "skip"]) == [{"x": 1}]
    assert adapter._extract_ledger_records({"records": None}) == []
    with pytest.raises(ExternalAPIError, match="missing a list of records"):
        adapter._extract_ledger_records({"records": {"bad": True}})
    with pytest.raises(ExternalAPIError, match="invalid payload shape"):
        adapter._extract_ledger_records("bad")  # type: ignore[arg-type]

    with patch.object(adapter, "_get_json", new=AsyncMock(return_value={"records": []})):
        await adapter._verify_ledger_http()

    with (
        patch.object(
            adapter,
            "_get_json",
            new=AsyncMock(
                return_value={
                    "records": [
                        {
                            "date": "2026-01-10T00:00:00Z",
                            "service": "Ledger Service",
                            "amount_raw": 92.0,
                            "currency": "EUR",
                        }
                    ]
                }
            ),
        ),
        patch(
            "app.shared.adapters.platform.convert_to_usd",
            new=AsyncMock(side_effect=RuntimeError("fx down")),
        ),
    ):
        rows = [
            row
            async for row in adapter._stream_ledger_http_cost_and_usage(
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
            )
        ]
    assert len(rows) == 1
    assert rows[0]["cost_usd"] == 92.0
    assert rows[0]["currency"] == "EUR"


@pytest.mark.asyncio
async def test_platform_native_stream_success_rows() -> None:
    datadog = PlatformAdapter(
        _conn(
            vendor="datadog",
            auth_method="api_key",
            connector_config={"site": "datadoghq.com", "unit_prices_usd": {"hosts": 2.0}},
        )
    )
    with patch.object(
        datadog,
        "_get_json",
        new=AsyncMock(
            side_effect=[
                {"usage": [{"billing_dimension": "hosts", "usage": 3}]},
                {"usage": [{"billing_dimension": "apm", "usage": 4}]},
            ]
        ),
    ):
        rows = [
            row
            async for row in datadog._stream_datadog_cost_and_usage(
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 2, 28, tzinfo=timezone.utc),
            )
        ]
    assert len(rows) == 2
    assert rows[0]["cost_usd"] == 6.0
    assert rows[1]["tags"]["unpriced"] is True

    newrelic = PlatformAdapter(
        _conn(
            vendor="newrelic",
            auth_method="api_key",
            connector_config={
                "account_id": 123,
                "nrql_template": "FROM X SELECT latest(gigabytes) AS gigabytes SINCE '{start}' UNTIL '{end}'",
                "unit_prices_usd": {"gigabytes": 0.5},
            },
        )
    )
    with patch.object(
        newrelic,
        "_post_json",
        new=AsyncMock(
            return_value={
                "data": {
                    "actor": {
                        "account": {"nrql": {"results": [{"gigabytes": 8, "noise": "x"}]}}
                    }
                }
            }
        ),
    ):
        rows = [
            row
            async for row in newrelic._stream_newrelic_cost_and_usage(
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
            )
        ]
    assert len(rows) == 1
    assert rows[0]["cost_usd"] == 4.0


@pytest.mark.asyncio
async def test_platform_ledger_resolution_and_stream_fields() -> None:
    with pytest.raises(ExternalAPIError, match="Missing connector_config.base_url"):
        PlatformAdapter(
            _conn(vendor="ledger", auth_method="api_key", connector_config={})
        )._resolve_ledger_http_base_url()
    with pytest.raises(ExternalAPIError, match="must be an http"):
        PlatformAdapter(
            _conn(
                vendor="ledger",
                auth_method="api_key",
                connector_config={"base_url": "ledger.local"},
            )
        )._resolve_ledger_http_base_url()

    adapter = PlatformAdapter(
        _conn(
            vendor="ledger",
            auth_method="api_key",
            connector_config={"base_url": "https://ledger.example.com"},
        )
    )
    assert adapter._resolve_ledger_http_costs_path() == "/api/v1/finops/costs"
    assert adapter._resolve_ledger_http_headers() == {"Authorization": "Bearer token-123"}

    with (
        patch.object(
            adapter,
            "_get_json",
            new=AsyncMock(
                return_value={
                    "records": [
                        {"timestamp": "2025-12-01T00:00:00Z", "cost_usd": 1},
                        {
                            "timestamp": "2026-01-10T00:00:00Z",
                            "cost_usd": 4.5,
                            "amount_raw": 4.7,
                            "resource_id": "res-1",
                            "usage_amount": 2,
                            "usage_unit": "hour",
                            "tags": {"team": "plat"},
                        },
                        {
                            "timestamp": "2026-01-12T00:00:00Z",
                            "amount_raw": 3.0,
                            "currency": "EUR",
                            "id": "",
                            "usage_amount": "x",
                            "usage_unit": "",
                        },
                    ]
                }
            ),
        ),
        patch(
            "app.shared.adapters.platform.convert_to_usd",
            new=AsyncMock(return_value=6.6),
        ),
    ):
        rows = [
            row
            async for row in adapter._stream_ledger_http_cost_and_usage(
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
            )
        ]

    assert len(rows) == 2
    assert rows[0]["resource_id"] == "res-1"
    assert rows[0]["usage_amount"] == 2.0
    assert rows[0]["usage_unit"] == "hour"
    assert rows[1]["resource_id"] is None
    assert rows[1]["usage_amount"] is None
    assert rows[1]["usage_unit"] is None
    assert rows[1]["cost_usd"] == 6.6


@pytest.mark.asyncio
async def test_platform_newrelic_verify_success_and_stream_skip_branches() -> None:
    adapter = PlatformAdapter(
        _conn(
            vendor="newrelic",
            auth_method="api_key",
            connector_config={
                "account_id": 123,
                "nrql_template": "FROM X SELECT latest(gigabytes) AS gigabytes SINCE '{start}' UNTIL '{end}'",
                "unit_prices_usd": {"gigabytes": 0.5},
            },
        )
    )
    with patch.object(
        adapter,
        "_post_json",
        new=AsyncMock(
            return_value={
                "data": {"actor": {"requestContext": {"userId": "u-1"}, "account": {}}}
            }
        ),
    ):
        await adapter._verify_newrelic()

    with patch.object(
        adapter,
        "_post_json",
        new=AsyncMock(
            return_value={
                "data": {
                    "actor": {
                        "account": {
                            "nrql": {"results": ["skip", {"gigabytes": "x"}, {"gigabytes": 4}]}
                        }
                    }
                }
            }
        ),
    ):
        rows = [
            row
            async for row in adapter._stream_newrelic_cost_and_usage(
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
            )
        ]
    assert len(rows) == 1
    assert rows[0]["cost_usd"] == 2.0


@pytest.mark.asyncio
async def test_platform_ledger_path_and_currency_branches() -> None:
    adapter = PlatformAdapter(
        _conn(
            vendor="ledger",
            auth_method="api_key",
            connector_config={"base_url": "https://ledger.example.com", "costs_path": 123},
        )
    )
    assert adapter._resolve_ledger_http_costs_path() == "/api/v1/finops/costs"

    with (
        patch.object(
            adapter,
            "_get_json",
            new=AsyncMock(
                return_value={
                    "records": [
                        {"timestamp": "2026-01-10T00:00:00Z", "amount_raw": 5.0, "currency": "USD"}
                    ]
                }
            ),
        ),
        patch("app.shared.adapters.platform.convert_to_usd", new=AsyncMock(return_value=99.0)),
    ):
        rows = [
            row
            async for row in adapter._stream_ledger_http_cost_and_usage(
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 31, tzinfo=timezone.utc),
            )
        ]
    assert len(rows) == 1
    assert rows[0]["cost_usd"] == 5.0

