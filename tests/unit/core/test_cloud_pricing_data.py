from __future__ import annotations

import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.shared.core import cloud_pricing_data as pricing_data
from app.shared.core.cloud_pricing_data import (
    get_cloud_hourly_rate,
    get_cloud_pricing_quote,
    sync_supported_aws_pricing,
)


@pytest.fixture(autouse=True)
def clear_cloud_pricing_caches() -> None:
    pricing_data._CLOUD_PRICING_CACHE.clear()
    pricing_data._CLOUD_PRICING_DETAILS_CACHE.clear()
    yield
    pricing_data._CLOUD_PRICING_CACHE.clear()
    pricing_data._CLOUD_PRICING_DETAILS_CACHE.clear()


def test_get_cloud_pricing_quote_uses_seeded_cache_rows() -> None:
    refreshed = pricing_data._refresh_cache_from_rows(
        [
            SimpleNamespace(
                provider="aws",
                resource_type="volume",
                resource_size="gp2",
                region="global",
                hourly_rate_usd=0.000137,
                source="default_catalog",
                pricing_metadata={
                    "billing_period_hours": 730,
                    "coverage_scope": "repo_default_catalog",
                },
            )
        ]
    )

    assert refreshed == 1
    quote = get_cloud_pricing_quote("aws", "volume", "gp2", "us-east-1")
    assert quote["source"] == "default_catalog"
    assert quote["pricing_metadata"]["billing_period_hours"] == 730
    assert quote["pricing_metadata"]["coverage_scope"] == "repo_default_catalog"
    assert quote["pricing_metadata"]["match_strategy"] == "global_exact_size_regionalized"
    assert quote["pricing_metadata"]["pricing_confidence"] == "regionalized_catalog_baseline"


def test_get_cloud_hourly_rate_applies_multiplier_from_seeded_cache() -> None:
    pricing_data._refresh_cache_from_rows(
        [
            SimpleNamespace(
                provider="aws",
                resource_type="instance",
                resource_size="t3.micro",
                region="global",
                hourly_rate_usd=0.01,
                source="default_catalog",
                pricing_metadata={"coverage_scope": "repo_default_catalog"},
            )
        ]
    )

    base = get_cloud_hourly_rate("aws", "instance", "t3.micro", "global")
    eu = get_cloud_hourly_rate("aws", "instance", "t3.micro", "eu-west-1")
    assert eu == pytest.approx(base * 1.10)


@pytest.mark.asyncio
async def test_sync_supported_aws_pricing_persists_supported_probes() -> None:
    class FakeClient:
        def get_products(self, **kwargs):
            service_code = kwargs["ServiceCode"]
            filters = {item["Field"]: item["Value"] for item in kwargs["Filters"]}
            if service_code == "AmazonEC2" and filters.get("usageType") == "NatGateway-Hours":
                return {
                    "PriceList": [
                        '{"terms":{"OnDemand":{"x":{"priceDimensions":{"y":{"pricePerUnit":{"USD":"0.123"},"unit":"Hrs"}}}}}}'
                    ]
                }
            if service_code == "AmazonEC2" and filters.get("instanceType") == "t3.micro":
                return {
                    "PriceList": [
                        '{"terms":{"OnDemand":{"x":{"priceDimensions":{"y":{"pricePerUnit":{"USD":"0.0104"},"unit":"Hrs"}}}}}}'
                    ]
                }
            if service_code == "AmazonEC2" and filters.get("volumeApiName") == "gp3":
                return {
                    "PriceList": [
                        '{"terms":{"OnDemand":{"x":{"priceDimensions":{"y":{"pricePerUnit":{"USD":"0.08"},"unit":"GB-Mo"}}}}}}'
                    ]
                }
            if (
                service_code == "AmazonRDS"
                and filters.get("instanceType") == "db.t3.micro"
                and filters.get("deploymentOption") == "Multi-AZ"
            ):
                return {
                    "PriceList": [
                        '{"terms":{"OnDemand":{"x":{"priceDimensions":{"y":{"pricePerUnit":{"USD":"0.031"},"unit":"Hrs"}}}}}}'
                    ]
                }
            return {"PriceList": []}

    captured: dict[str, object] = {}

    async def fake_upsert_catalog_records(*, db_session, records):
        captured["db_session"] = db_session
        captured["records"] = list(records)
        return len(captured["records"])

    async def fake_refresh_cloud_resource_pricing(db_session):
        captured["refreshed_with"] = db_session
        return len(captured.get("records", []))

    session = AsyncMock()
    with (
        patch(
            "app.shared.core.cloud_pricing_data._upsert_catalog_records",
            side_effect=fake_upsert_catalog_records,
        ),
        patch(
            "app.shared.core.cloud_pricing_data.refresh_cloud_resource_pricing",
            side_effect=fake_refresh_cloud_resource_pricing,
        ),
    ):
        updated = await sync_supported_aws_pricing(session, client=FakeClient())

    session.flush.assert_awaited_once()
    assert captured["db_session"] is session
    assert captured["refreshed_with"] is session
    assert updated >= 4

    records = {record["resource_type"]: record for record in captured["records"]}
    record_regions = {
        (record["resource_type"], record["resource_size"], record["region"])
        for record in captured["records"]
    }
    assert ("instance", "t3.micro", "us-east-1") in record_regions
    assert ("instance", "t3.micro", "eu-west-1") in record_regions

    nat_gateway = records["nat_gateway"]
    assert nat_gateway["hourly_rate_usd"] == pytest.approx(0.123)
    assert nat_gateway["pricing_metadata"]["catalog_probe"] == "NatGateway-Hours"
    assert nat_gateway["pricing_metadata"]["coverage_scope"] == "curated_live_catalog"
    assert (
        nat_gateway["pricing_metadata"]["region_coverage_mode"]
        == "explicit_multi_region_catalog"
    )

    volume = records["volume"]
    assert volume["pricing_metadata"]["catalog_unit"] == "GB-Mo"
    assert volume["pricing_metadata"]["normalized_hourly_rate_usd"] == pytest.approx(
        0.08 / 730
    )

    rds = records["rds"]
    assert rds["hourly_rate_usd"] == pytest.approx(0.031)
    assert rds["pricing_metadata"]["availability_profile"] == "multi-az"
    assert "coverage_limitations" in rds["pricing_metadata"]
    assert "eu-west-1" in rds["pricing_metadata"]["covered_regions"]


@pytest.mark.asyncio
async def test_sync_supported_aws_pricing_returns_zero_without_boto3() -> None:
    with patch.dict(sys.modules, {"boto3": None}):
        updated = await sync_supported_aws_pricing(client=None)
    assert updated == 0


@pytest.mark.asyncio
async def test_sync_supported_aws_pricing_returns_zero_on_catalog_probe_error() -> None:
    class FakeClient:
        def get_products(self, **kwargs):
            del kwargs
            raise OSError("pricing endpoint unavailable")

    session = AsyncMock()
    updated = await sync_supported_aws_pricing(session, client=FakeClient())
    assert updated == 0
    session.flush.assert_not_awaited()


def test_get_cloud_pricing_quote_reports_exact_match_strategy() -> None:
    pricing_data._refresh_cache_from_rows(
        [
            SimpleNamespace(
                provider="aws",
                resource_type="instance",
                resource_size="t3.micro",
                region="us-east-1",
                hourly_rate_usd=0.011,
                source="aws_pricing_api",
                pricing_metadata={"coverage_scope": "curated_live_catalog"},
            )
        ]
    )

    quote = get_cloud_pricing_quote("aws", "instance", "t3.micro", "us-east-1")
    assert quote["pricing_metadata"]["match_strategy"] == "exact_region_size"
    assert quote["pricing_metadata"]["pricing_confidence"] == "catalog_exact"
    assert quote["pricing_metadata"]["region_multiplier_applied"] == pytest.approx(1.0)
