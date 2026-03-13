from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.shared.adapters.hybrid import HybridAdapter
from app.shared.adapters.platform import PlatformAdapter


from tests.unit.services.adapters.cloud_plus_test_helpers import (
    FakeAsyncClient as _FakeAsyncClient,
    FakeResponse as _FakeResponse,
)


@pytest.mark.asyncio
async def test_platform_adapter_native_ledger_http_normalizes_records() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "ledger_http"
    conn.api_key = "token_123"
    conn.connector_config = {
        "base_url": "https://ledger.example.com",
        "costs_path": "/api/v1/finops/costs",
    }
    conn.spend_feed = []

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "records": [
                        {
                            "timestamp": "2026-01-10T00:00:00Z",
                            "service": "Kubernetes Shared",
                            "cost_usd": 55.5,
                            "currency": "USD",
                            "tags": {"team": "platform"},
                        }
                    ]
                }
            )
        ]
    )
    adapter = PlatformAdapter(conn)
    with patch(
        "app.shared.adapters.platform.get_http_client", return_value=fake_client
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["provider"] == "platform"
    assert rows[0]["service"] == "Kubernetes Shared"
    assert rows[0]["cost_usd"] == 55.5
    assert rows[0]["source_adapter"] == "platform_ledger_http"
    assert rows[0]["tags"]["team"] == "platform"
    assert fake_client.calls
    assert "start_date" in (fake_client.calls[0].get("params") or {})
    assert "end_date" in (fake_client.calls[0].get("params") or {})


@pytest.mark.asyncio
async def test_platform_adapter_native_datadog_normalizes_priced_usage() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "datadog"
    conn.api_key = "dd_api_key"
    conn.api_secret = "dd_app_key"
    conn.connector_config = {"site": "datadoghq.com", "unit_prices_usd": {"hosts": 2.0}}
    conn.spend_feed = []

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "usage": [
                        {"billing_dimension": "hosts", "usage": 3, "unit": "host"},
                    ]
                }
            )
        ]
    )

    adapter = PlatformAdapter(conn)
    with patch(
        "app.shared.adapters.platform.get_http_client", return_value=fake_client
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["provider"] == "platform"
    assert rows[0]["service"] == "Datadog hosts"
    assert rows[0]["usage_amount"] == 3.0
    assert rows[0]["usage_unit"] == "host"
    assert rows[0]["cost_usd"] == 6.0
    assert rows[0]["source_adapter"] == "platform_datadog_api"


@pytest.mark.asyncio
async def test_platform_adapter_native_newrelic_normalizes_priced_nrql_results() -> (
    None
):
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "newrelic"
    conn.api_key = "nr_api_key"
    conn.connector_config = {
        "account_id": 12345,
        "nrql_template": "FROM NrMTDConsumption SELECT latest(gigabytes) AS gigabytes SINCE '{start}' UNTIL '{end}'",
        "unit_prices_usd": {"gigabytes": 0.5},
    }
    conn.spend_feed = []

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "data": {
                        "actor": {
                            "account": {
                                "nrql": {
                                    "results": [
                                        {"gigabytes": 10},
                                    ]
                                }
                            }
                        }
                    }
                }
            )
        ]
    )
    adapter = PlatformAdapter(conn)
    with patch(
        "app.shared.adapters.platform.get_http_client", return_value=fake_client
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["provider"] == "platform"
    assert rows[0]["service"] == "New Relic gigabytes"
    assert rows[0]["usage_amount"] == 10.0
    assert rows[0]["cost_usd"] == 5.0
    assert rows[0]["source_adapter"] == "platform_newrelic_nerdgraph"


@pytest.mark.asyncio
async def test_hybrid_adapter_native_ledger_http_normalizes_records() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "cmdb_ledger"
    conn.api_key = "token_123"
    conn.connector_config = {"base_url": "https://ledger.example.com"}
    conn.spend_feed = []

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse(
                {
                    "data": [
                        {
                            "date": "2026-01-10T00:00:00Z",
                            "system": "VMware Cluster",
                            "amount_usd": 99.9,
                            "currency": "USD",
                            "tags": {"env": "prod"},
                        }
                    ]
                }
            )
        ]
    )
    adapter = HybridAdapter(conn)
    with patch(
        "app.shared.adapters.hybrid.get_http_client", return_value=fake_client
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["provider"] == "hybrid"
    assert rows[0]["service"] == "VMware Cluster"
    assert rows[0]["cost_usd"] == 99.9
    assert rows[0]["source_adapter"] == "hybrid_ledger_http"
    assert rows[0]["tags"]["env"] == "prod"


@pytest.mark.asyncio
async def test_hybrid_adapter_native_cloudkitty_normalizes_summary() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "openstack"
    conn.api_key = "app_cred_id"
    conn.api_secret = "app_cred_secret"
    conn.connector_config = {
        "auth_url": "https://keystone.example.com",
        "cloudkitty_base_url": "https://cloudkitty.example.com",
        "currency": "USD",
        "groupby": "month",
    }
    conn.spend_feed = []

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse({}, headers={"X-Subject-Token": "token-123"}),
            _FakeResponse(
                {
                    "columns": [
                        {"name": "begin", "unit": None},
                        {"name": "end", "unit": None},
                        {"name": "qty", "unit": "GB"},
                        {"name": "rate", "unit": "USD"},
                    ],
                    "results": [
                        {
                            "desc": ["2026-01-01T00:00:00Z", "2026-01-31T23:59:59Z"],
                            "qty": 2,
                            "rate": 10,
                        }
                    ],
                }
            ),
        ]
    )

    adapter = HybridAdapter(conn)
    with patch(
        "app.shared.adapters.hybrid.get_http_client", return_value=fake_client
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 31, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["provider"] == "hybrid"
    assert rows[0]["service"] == "OpenStack CloudKitty"
    assert rows[0]["currency"] == "USD"
    assert rows[0]["usage_amount"] == 2.0
    assert rows[0]["cost_usd"] == 10.0
    assert rows[0]["source_adapter"] == "hybrid_openstack_cloudkitty"


@pytest.mark.asyncio
async def test_hybrid_adapter_native_vmware_estimates_cost_from_inventory() -> None:
    conn = MagicMock()
    conn.auth_method = "api_key"
    conn.vendor = "vmware"
    conn.api_key = "administrator@vsphere.local"
    conn.api_secret = "password"
    conn.connector_config = {
        "base_url": "https://vcenter.example.com",
        "cpu_hour_usd": 0.1,
        "ram_gb_hour_usd": 0.01,
    }
    conn.spend_feed = []

    fake_client = _FakeAsyncClient(
        [
            _FakeResponse({"value": "session-123"}),
            _FakeResponse(
                {
                    "value": [
                        {
                            "name": "vm-1",
                            "cpu_count": 2,
                            "memory_size_MiB": 2048,
                            "power_state": "POWERED_ON",
                        }
                    ]
                }
            ),
        ]
    )

    adapter = HybridAdapter(conn)
    with patch(
        "app.shared.adapters.hybrid.get_http_client", return_value=fake_client
    ):
        rows = await adapter.get_cost_and_usage(
            start_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end_date=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    assert len(rows) == 1
    assert rows[0]["provider"] == "hybrid"
    assert rows[0]["service"] == "VMware vCenter (estimated)"
    assert rows[0]["usage_amount"] == 1.0
    assert rows[0]["usage_unit"] == "vm"
    # (2 vCPU * $0.1 + 2GB * $0.01) * 24h = $5.28/day
    assert rows[0]["cost_usd"] == pytest.approx(5.28, abs=0.0001)
    assert rows[0]["source_adapter"] == "hybrid_vmware_vcenter"


@pytest.mark.asyncio
async def test_platform_discover_resources_projects_from_cost_rows() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.spend_feed = [
        {
            "timestamp": "2026-02-20T00:00:00Z",
            "service": "Shared Kubernetes",
            "resource_id": "plat-svc-1",
            "cost_usd": 11.0,
            "region": "us-east-1",
            "usage_type": "shared_service",
        }
    ]
    conn.connector_config = {}

    adapter = PlatformAdapter(conn)
    adapter.last_error = "stale"
    resources = await adapter.discover_resources("platform", region="us-east-1")

    assert len(resources) == 1
    assert resources[0]["id"] == "plat-svc-1"
    assert resources[0]["type"] == "platform_service"
    assert resources[0]["provider"] == "platform"
    assert resources[0]["region"] == "us-east-1"
    assert adapter.last_error is None


@pytest.mark.asyncio
async def test_hybrid_discover_resources_projects_from_cost_rows() -> None:
    conn = MagicMock()
    conn.auth_method = "manual"
    conn.vendor = "generic"
    conn.spend_feed = [
        {
            "timestamp": "2026-02-20T00:00:00Z",
            "system": "VMware Cluster",
            "resource_id": "hyb-node-1",
            "amount_usd": 8.5,
            "region": "eu-west-1",
            "usage_type": "resource_usage",
        }
    ]
    conn.connector_config = {}

    adapter = HybridAdapter(conn)
    adapter.last_error = "stale"
    resources = await adapter.discover_resources("hybrid", region="eu-west-1")

    assert len(resources) == 1
    assert resources[0]["id"] == "hyb-node-1"
    assert resources[0]["type"] == "hybrid_resource"
    assert resources[0]["provider"] == "hybrid"
    assert resources[0]["region"] == "eu-west-1"
    assert adapter.last_error is None
