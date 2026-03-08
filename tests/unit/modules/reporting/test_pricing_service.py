import pytest
from unittest.mock import AsyncMock, patch

from app.modules.reporting.domain.pricing.service import PricingService


def test_get_hourly_rate_with_multiplier():
    with patch(
        "app.modules.reporting.domain.pricing.service.get_cloud_hourly_rate",
        return_value=0.011,
    ):
        rate = PricingService.get_hourly_rate(
            "aws", "instance", "t3.micro", region="us-west-2"
        )
        assert rate == pytest.approx(0.011)


def test_get_hourly_rate_missing_logs():
    with (
        patch(
            "app.modules.reporting.domain.pricing.service.get_cloud_hourly_rate",
            return_value=0.0,
        ),
        patch("app.modules.reporting.domain.pricing.service.logger") as mock_logger,
    ):
        rate = PricingService.get_hourly_rate("aws", "unknown", "x", region="us-east-1")
        assert rate == 0.0
        mock_logger.debug.assert_called()


def test_estimate_monthly_waste_uses_hourly():
    with patch(
        "app.modules.reporting.domain.pricing.service.PricingService.get_hourly_rate_quote",
        return_value=type(
            "Quote",
            (),
            {
                "monthly_cost_usd": 2.0 * 730 * 3,
                "source": "aws_pricing_api",
                "pricing_metadata": {
                    "pricing_confidence": "catalog_exact",
                    "match_strategy": "exact_region_size",
                },
            },
        )(),
    ) as mock_quote:
        waste = PricingService.estimate_monthly_waste("aws", "nat_gateway", quantity=3)
        assert waste == pytest.approx(2.0 * 730 * 3)
        assert mock_quote.call_args.kwargs["region"] == "global"
        assert mock_quote.call_args.kwargs["quantity"] == 3


def test_get_hourly_rate_default_region_is_provider_neutral():
    with patch(
        "app.modules.reporting.domain.pricing.service.get_cloud_hourly_rate",
        return_value=1.0,
    ):
        rate = PricingService.get_hourly_rate("aws", "instance")
        assert rate == pytest.approx(1.0)


def test_get_hourly_rate_quote_includes_source_provenance():
    with patch(
        "app.modules.reporting.domain.pricing.service.get_cloud_pricing_quote",
        return_value={
            "provider": "aws",
            "resource_type": "instance",
            "resource_size": "t3.micro",
            "requested_region": "us-east-1",
            "effective_region": "us-east-1",
            "hourly_rate_usd": 0.011,
            "source": "aws_pricing_api",
            "pricing_metadata": {
                "catalog_probe": "NatGateway-Hours",
                "billing_period_hours": 730,
                "coverage_scope": "curated_live_catalog",
                "match_strategy": "exact_region_size",
                "pricing_confidence": "catalog_exact",
            },
        },
    ):
        quote = PricingService.get_hourly_rate_quote(
            "aws", "instance", "t3.micro", region="us-east-1", quantity=2
        )

    assert quote.hourly_rate_usd == pytest.approx(0.011)
    assert quote.monthly_cost_usd == pytest.approx(0.011 * 730 * 2)
    assert quote.source == "aws_pricing_api"
    assert quote.pricing_metadata["catalog_probe"] == "NatGateway-Hours"
    assert quote.pricing_metadata["coverage_scope"] == "curated_live_catalog"
    assert quote.pricing_metadata["pricing_confidence"] == "catalog_exact"


@pytest.mark.asyncio
async def test_sync_with_aws_delegates_to_supported_catalog_sync():
    with patch(
        "app.modules.reporting.domain.pricing.service.sync_supported_aws_pricing",
        new=AsyncMock(return_value=3),
    ) as sync_mock:
        updated = await PricingService.sync_with_aws()
    assert updated == 3
    sync_mock.assert_awaited_once()


def test_estimate_monthly_waste_logs_when_quote_is_non_exact():
    quote = type(
        "Quote",
        (),
        {
            "monthly_cost_usd": 10.0,
            "source": "default_catalog",
            "pricing_metadata": {
                "pricing_confidence": "regionalized_default_baseline",
                "match_strategy": "global_default_regionalized",
            },
        },
    )()

    with (
        patch(
            "app.modules.reporting.domain.pricing.service.PricingService.get_hourly_rate_quote",
            return_value=quote,
        ) as quote_mock,
        patch("app.modules.reporting.domain.pricing.service.logger") as mock_logger,
    ):
        assert PricingService.estimate_monthly_waste("aws", "instance") == pytest.approx(
            10.0
        )

    quote_mock.assert_called_once()
    mock_logger.info.assert_called_once()
