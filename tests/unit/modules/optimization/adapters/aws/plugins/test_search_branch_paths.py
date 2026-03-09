from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.optimization.adapters.aws.plugins.search import IdleOpenSearchPlugin


class _AsyncClientCtx:
    def __init__(self, client: object) -> None:
        self._client = client

    async def __aenter__(self) -> object:
        return self._client

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        del exc_type, exc_val, exc_tb
        return None


def _wire_clients(plugin: IdleOpenSearchPlugin, opensearch: object, cloudwatch: object) -> None:
    def _get_client(session: object, service_name: str, region: str, credentials: object, config=None):
        del session, region, credentials, config
        return _AsyncClientCtx(opensearch if service_name == "opensearch" else cloudwatch)

    plugin._get_client = _get_client  # type: ignore[method-assign]


@pytest.mark.asyncio
async def test_opensearch_helper_methods_cover_edge_branches() -> None:
    plugin = IdleOpenSearchPlugin()
    assert plugin.category_key == "idle_opensearch_domains"

    assert plugin._as_positive_int("5", default=1) == 5
    assert plugin._as_positive_int(0, default=3) == 3
    assert plugin._as_positive_int("bad", default=7) == 7

    assert plugin._client_id_from_domain({"DomainId": ""}) is None
    assert plugin._client_id_from_domain({"DomainId": "12345/domain-name"}) == "12345"


@pytest.mark.asyncio
async def test_metric_has_non_zero_handles_invalid_and_non_positive_datapoints() -> None:
    cloudwatch = SimpleNamespace(get_metric_statistics=AsyncMock())

    cloudwatch.get_metric_statistics.return_value = {"Datapoints": "not-a-list"}
    assert (
        await IdleOpenSearchPlugin._metric_has_non_zero(
            cloudwatch=cloudwatch,
            dimensions=[],
            metric_name="SearchRate",
            start_time=MagicMock(),
            end_time=MagicMock(),
            statistic="Average",
        )
        is False
    )

    cloudwatch.get_metric_statistics.return_value = {
        "Datapoints": [None, {"Average": 0}, {"Average": -1}]
    }
    assert (
        await IdleOpenSearchPlugin._metric_has_non_zero(
            cloudwatch=cloudwatch,
            dimensions=[],
            metric_name="SearchRate",
            start_time=MagicMock(),
            end_time=MagicMock(),
            statistic="Average",
        )
        is False
    )

    cloudwatch.get_metric_statistics.return_value = {
        "Datapoints": [None, {"Average": 0}, {"Average": 1}]
    }
    assert (
        await IdleOpenSearchPlugin._metric_has_non_zero(
            cloudwatch=cloudwatch,
            dimensions=[],
            metric_name="SearchRate",
            start_time=MagicMock(),
            end_time=MagicMock(),
            statistic="Average",
        )
        is True
    )


def test_estimate_monthly_cost_handles_non_dict_cluster_and_dedicated_masters() -> None:
    with patch(
        "app.modules.optimization.adapters.aws.plugins.search.PricingService.estimate_monthly_waste_quote",
        side_effect=[
            SimpleNamespace(
                monthly_cost_usd=10.0,
                source="default_catalog",
                requested_region="us-east-1",
                effective_region="global",
                hourly_rate_usd=0.0,
                pricing_metadata={
                    "coverage_scope": "repo_default_catalog",
                    "pricing_confidence": "regionalized_default_baseline",
                    "match_strategy": "global_default_regionalized",
                },
            ),
            SimpleNamespace(
                monthly_cost_usd=20.0,
                source="default_catalog",
                requested_region="us-east-1",
                effective_region="global",
                hourly_rate_usd=0.0,
                pricing_metadata={
                    "coverage_scope": "repo_default_catalog",
                    "pricing_confidence": "regionalized_default_baseline",
                    "match_strategy": "global_default_regionalized",
                },
            ),
            SimpleNamespace(
                monthly_cost_usd=30.0,
                source="default_catalog",
                requested_region="us-east-1",
                effective_region="global",
                hourly_rate_usd=0.0,
                pricing_metadata={
                    "coverage_scope": "repo_default_catalog",
                    "pricing_confidence": "regionalized_default_baseline",
                    "match_strategy": "global_default_regionalized",
                },
            ),
        ],
    ) as estimate:
        no_cluster = IdleOpenSearchPlugin._estimate_monthly_cost(
            {"ClusterConfig": "invalid"},
            "us-east-1",
        )
        with_masters = IdleOpenSearchPlugin._estimate_monthly_cost(
            {
                "ClusterConfig": {
                    "InstanceType": "r6g.large.search",
                    "InstanceCount": 0,
                    "DedicatedMasterEnabled": True,
                    "DedicatedMasterType": "m6g.large.search",
                    "DedicatedMasterCount": "bad",
                }
            },
            "us-east-1",
        )

    assert no_cluster == 10.0
    assert with_masters == 50.0
    assert estimate.call_args_list[1].kwargs["resource_type"] == "opensearch"
    assert estimate.call_args_list[1].kwargs["quantity"] == 1.0
    assert estimate.call_args_list[2].kwargs["resource_type"] == "opensearch_master"
    assert estimate.call_args_list[2].kwargs["quantity"] == 3.0


def test_estimate_monthly_cost_details_include_pricing_provenance() -> None:
    with patch(
        "app.modules.optimization.adapters.aws.plugins.search.PricingService.estimate_monthly_waste_quote",
        side_effect=[
            SimpleNamespace(
                monthly_cost_usd=25.0,
                source="aws_pricing_api",
                requested_region="us-east-1",
                effective_region="us-east-1",
                hourly_rate_usd=0.034247,
                pricing_metadata={
                    "coverage_scope": "curated_live_catalog",
                    "pricing_confidence": "catalog_exact",
                    "match_strategy": "exact_region_size",
                    "catalog_probe": "opensearch-data-node",
                },
            ),
            SimpleNamespace(
                monthly_cost_usd=15.0,
                source="default_catalog",
                requested_region="us-east-1",
                effective_region="global",
                hourly_rate_usd=0.020548,
                pricing_metadata={
                    "coverage_scope": "repo_default_catalog",
                    "pricing_confidence": "regionalized_default_baseline",
                    "match_strategy": "global_default_regionalized",
                },
            ),
        ],
    ):
        details = IdleOpenSearchPlugin._estimate_monthly_cost_details(
            {
                "ClusterConfig": {
                    "InstanceType": "m6g.large.search",
                    "InstanceCount": 1,
                    "DedicatedMasterEnabled": True,
                    "DedicatedMasterType": "t3.small.search",
                    "DedicatedMasterCount": 3,
                }
            },
            "us-east-1",
        )

    assert details["monthly_cost"] == 40.0
    assert details["pricing_evidence"]["cluster"]["source"] == "aws_pricing_api"
    assert (
        details["pricing_evidence"]["dedicated_masters"]["pricing_confidence"]
        == "regionalized_default_baseline"
    )


@pytest.mark.asyncio
async def test_scan_returns_empty_when_domain_names_is_not_a_list() -> None:
    plugin = IdleOpenSearchPlugin()
    opensearch = SimpleNamespace(
        list_domain_names=AsyncMock(return_value={"DomainNames": "bad"})
    )
    cloudwatch = SimpleNamespace()
    _wire_clients(plugin, opensearch, cloudwatch)

    zombies = await plugin.scan(
        session=MagicMock(),
        region="us-east-1",
        credentials={"a": "b"},
    )

    assert zombies == []


@pytest.mark.asyncio
async def test_scan_skips_invalid_entries_and_non_idle_domains_without_client_id() -> None:
    plugin = IdleOpenSearchPlugin()
    opensearch = SimpleNamespace(
        list_domain_names=AsyncMock(
            return_value={
                "DomainNames": [
                    None,
                    {},
                    {"DomainName": "status-missing"},
                    {"DomainName": "deleted"},
                    {"DomainName": "missing-arn"},
                    {"DomainName": "active-domain"},
                ]
            }
        ),
        describe_domain=AsyncMock(
            side_effect=[
                {"DomainStatus": None},
                {"DomainStatus": {"Deleted": True, "ARN": "arn:deleted"}},
                {"DomainStatus": {"Deleted": False, "ARN": ""}},
                {
                    "DomainStatus": {
                        "Deleted": False,
                        "ARN": "arn:aws:es:us-east-1:12345:domain/active-domain",
                        "DomainId": "",
                    }
                },
            ]
        ),
    )
    cloudwatch = SimpleNamespace()
    _wire_clients(plugin, opensearch, cloudwatch)

    metric = AsyncMock(side_effect=[True, True])
    plugin._metric_has_non_zero = metric  # type: ignore[method-assign]

    zombies = await plugin.scan(
        session=MagicMock(),
        region="us-east-1",
        credentials={"a": "b"},
    )

    assert zombies == []
    assert metric.await_count == 2
    first_dimensions = metric.await_args_list[0].kwargs["dimensions"]
    assert first_dimensions == [{"Name": "DomainName", "Value": "active-domain"}]


@pytest.mark.asyncio
async def test_scan_logs_outer_exception() -> None:
    plugin = IdleOpenSearchPlugin()
    opensearch = SimpleNamespace(
        list_domain_names=AsyncMock(side_effect=RuntimeError("boom"))
    )
    cloudwatch = SimpleNamespace()
    _wire_clients(plugin, opensearch, cloudwatch)

    with patch(
        "app.modules.optimization.adapters.aws.plugins.search.logger.error"
    ) as logger_error:
        zombies = await plugin.scan(
            session=MagicMock(),
            region="us-east-1",
            credentials={"a": "b"},
        )

    assert zombies == []
    logger_error.assert_called_once()
