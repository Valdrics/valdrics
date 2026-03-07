from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.shared.adapters.platform import PlatformAdapter
from app.shared.core.exceptions import ExternalAPIError
from tests.unit.services.adapters.platform_additional_test_helpers import _conn, _Secret


def test_platform_extract_billable_usage_metrics_additional_shapes() -> None:
    adapter = PlatformAdapter(_conn())

    usage_dict = adapter._extract_billable_usage_metrics({"usage": {"hosts": 2, "bad": "x"}})
    assert usage_dict == [("hosts", 2.0, None)]

    list_with_non_dict = adapter._extract_billable_usage_metrics(
        {"usage": ["skip-me", {"metric": "hosts", "value": 4}]}
    )
    assert list_with_non_dict == [("hosts", 4.0, None)]

    top_level = adapter._extract_billable_usage_metrics({"containers": 3, "label": "ignored"})
    assert top_level == [("containers", 3.0, None)]

    with pytest.raises(ExternalAPIError, match="missing billable usage metrics"):
        adapter._extract_billable_usage_metrics({"usage": [{"metric": "", "value": "x"}]})
    with pytest.raises(ExternalAPIError, match="missing billable usage metrics"):
        adapter._extract_billable_usage_metrics("not-a-dict")  # type: ignore[arg-type]


def test_platform_helper_resolution_branches() -> None:
    unknown_native = PlatformAdapter(_conn(vendor="custom", auth_method="api_key"))
    assert unknown_native._native_vendor is None

    not_api_key = PlatformAdapter(_conn(vendor="ledger", auth_method="manual"))
    assert not_api_key._native_vendor is None

    with pytest.raises(ExternalAPIError, match="Missing API token"):
        PlatformAdapter(_conn(auth_method="api_key", api_key=None))._resolve_api_key()
    with pytest.raises(ExternalAPIError, match="Missing API token"):
        PlatformAdapter(
            _conn(auth_method="api_key", api_key=_Secret("   "))
        )._resolve_api_key()

    with pytest.raises(ExternalAPIError, match="Missing API secret"):
        PlatformAdapter(_conn(auth_method="api_key", api_secret=None))._resolve_api_secret()
    with pytest.raises(ExternalAPIError, match="Missing API secret"):
        PlatformAdapter(
            _conn(auth_method="api_key", api_secret=_Secret(" "))
        )._resolve_api_secret()

    assert (
        PlatformAdapter(_conn(vendor="new_relic", auth_method="api_key"))._native_vendor
        == "newrelic"
    )


def test_platform_url_pricing_and_ssl_resolution_branches() -> None:
    with pytest.raises(ExternalAPIError, match="api_base_url must be an http"):
        PlatformAdapter(
            _conn(vendor="datadog", connector_config={"api_base_url": "datadog.local"})
        )._resolve_datadog_base_url()

    with pytest.raises(ExternalAPIError, match="site must be a hostname"):
        PlatformAdapter(
            _conn(vendor="datadog", connector_config={"site": "bad/path"})
        )._resolve_datadog_base_url()

    assert (
        PlatformAdapter(_conn(vendor="datadog", connector_config={"site": "datadoghq.eu"}))
        ._resolve_datadog_base_url()
        .startswith("https://api.")
    )
    assert (
        PlatformAdapter(
            _conn(vendor="datadog", connector_config={"site": "https://api.datadoghq.com/"})
        )._resolve_datadog_base_url()
        == "https://api.datadoghq.com"
    )

    with pytest.raises(ExternalAPIError, match="api_base_url must be an http"):
        PlatformAdapter(
            _conn(vendor="newrelic", connector_config={"api_base_url": "newrelic.local"})
        )._resolve_newrelic_endpoint()
    assert (
        PlatformAdapter(_conn(vendor="newrelic", connector_config={}))
        ._resolve_newrelic_endpoint()
        == "https://api.newrelic.com/graphql"
    )

    with pytest.raises(ExternalAPIError, match="Missing connector_config.unit_prices_usd"):
        PlatformAdapter(_conn(connector_config={}))._resolve_unit_prices()
    with pytest.raises(ExternalAPIError, match="must contain at least one positive"):
        PlatformAdapter(
            _conn(connector_config={"unit_prices_usd": {"": 1, "x": -1}})
        )._resolve_unit_prices()

    prices = PlatformAdapter(
        _conn(connector_config={"unit_prices_usd": {"hosts": 2, "bad": "x"}})
    )._resolve_unit_prices()
    assert prices == {"hosts": 2.0}

    assert PlatformAdapter(_conn(connector_config={"verify_ssl": False}))._resolve_verify_ssl() is False
    assert PlatformAdapter(_conn(connector_config={"ssl_verify": False}))._resolve_verify_ssl() is False
    assert PlatformAdapter(_conn(connector_config={}))._resolve_verify_ssl() is True


def test_platform_manual_feed_validation_error_branches() -> None:
    adapter = PlatformAdapter(_conn())
    assert adapter._validate_manual_feed("bad-shape") is False  # type: ignore[arg-type]
    assert "at least one record" in (adapter.last_error or "")

    assert adapter._validate_manual_feed(["bad-entry"]) is False
    assert "must be a JSON object" in (adapter.last_error or "")

    assert adapter._validate_manual_feed([{"cost_usd": 1.0}]) is False
    assert "missing timestamp/date" in (adapter.last_error or "")

    assert adapter._validate_manual_feed([{"timestamp": "2026-01-01T00:00:00Z", "cost_usd": "x"}]) is False
    assert "must include numeric cost_usd" in (adapter.last_error or "")


def test_platform_date_and_base_url_resolution_branches() -> None:
    adapter = PlatformAdapter(_conn())
    months = adapter._iter_month_starts(
        datetime(2025, 12, 15, tzinfo=timezone.utc),
        datetime(2026, 1, 15, tzinfo=timezone.utc),
    )
    assert months == [datetime(2025, 12, 1).date(), datetime(2026, 1, 1).date()]

    dd_api_base = PlatformAdapter(
        _conn(vendor="datadog", connector_config={"api_base_url": "https://api.dd.example.com/"})
    )
    assert dd_api_base._resolve_datadog_base_url() == "https://api.dd.example.com"

    dd_default = PlatformAdapter(_conn(vendor="datadog", connector_config={}))
    assert dd_default._resolve_datadog_base_url() == "https://api.datadoghq.com"

    nr_api_base = PlatformAdapter(
        _conn(vendor="newrelic", connector_config={"api_base_url": "https://nr.example.com/"})
    )
    assert nr_api_base._resolve_newrelic_endpoint() == "https://nr.example.com"


def test_platform_newrelic_and_usage_metric_branch_edges() -> None:
    with pytest.raises(ExternalAPIError, match="requires connector_config.account_id"):
        PlatformAdapter(_conn(vendor="newrelic", connector_config={}))._resolve_newrelic_account_id()

    with pytest.raises(ExternalAPIError, match="requires connector_config.nrql_template"):
        PlatformAdapter(
            _conn(vendor="newrelic", connector_config={"account_id": 1})
        )._resolve_newrelic_nrql_template()

    adapter = PlatformAdapter(_conn())
    metrics = adapter._extract_billable_usage_metrics(
        {"usage": {"bad": "x"}, "hosts": 3}
    )
    assert metrics == [("hosts", 3.0, None)]

