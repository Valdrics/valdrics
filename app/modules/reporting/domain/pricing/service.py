"""DB-backed cloud pricing service."""

from dataclasses import dataclass
import structlog
from typing import Any

from app.shared.core.cloud_pricing_data import (
    get_cloud_hourly_rate,
    get_cloud_pricing_quote,
    sync_supported_aws_pricing,
)
from app.shared.core.pricing_defaults import AVERAGE_BILLING_MONTH_HOURS

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class PricingQuote:
    provider: str
    resource_type: str
    resource_size: str
    requested_region: str
    effective_region: str
    hourly_rate_usd: float
    monthly_cost_usd: float
    source: str
    pricing_metadata: dict[str, Any]


class PricingService:
    """
    Standardized pricing engine.
    """

    @staticmethod
    def get_hourly_rate(
        provider: str,
        resource_type: str,
        resource_size: str | None = None,
        region: str = "global",
    ) -> float:
        """
        Returns the hourly rate for a resource.
        """
        final_rate = get_cloud_hourly_rate(
            provider=provider,
            resource_type=resource_type,
            resource_size=resource_size,
            region=region,
        )
        if final_rate == 0.0:
            logger.debug(
                "pricing_missing",
                provider=provider,
                type=resource_type,
                size=resource_size,
                region=region,
            )

        return final_rate

    @staticmethod
    def get_hourly_rate_quote(
        provider: str,
        resource_type: str,
        resource_size: str | None = None,
        region: str = "global",
        *,
        quantity: float = 1.0,
    ) -> PricingQuote:
        quote = get_cloud_pricing_quote(
            provider=provider,
            resource_type=resource_type,
            resource_size=resource_size,
            region=region,
        )
        hourly_rate = float(quote.get("hourly_rate_usd", 0.0) or 0.0)
        normalized_quantity = float(quantity or 0.0)
        billing_period_hours = float(
            (quote.get("pricing_metadata") or {}).get(
                "billing_period_hours",
                AVERAGE_BILLING_MONTH_HOURS,
            )
            or AVERAGE_BILLING_MONTH_HOURS
        )
        monthly_cost = hourly_rate * billing_period_hours * normalized_quantity
        return PricingQuote(
            provider=str(quote.get("provider") or provider),
            resource_type=str(quote.get("resource_type") or resource_type),
            resource_size=str(quote.get("resource_size") or resource_size or "default"),
            requested_region=str(quote.get("requested_region") or region or "global"),
            effective_region=str(quote.get("effective_region") or "global"),
            hourly_rate_usd=hourly_rate,
            monthly_cost_usd=monthly_cost,
            source=str(quote.get("source") or "missing"),
            pricing_metadata=dict(quote.get("pricing_metadata") or {}),
        )

    @staticmethod
    async def sync_with_aws(db_session: Any = None, *, client: Any = None) -> int:
        """Persist supported AWS Pricing API observations into the cloud pricing catalog."""
        return await sync_supported_aws_pricing(db_session=db_session, client=client)

    @staticmethod
    def estimate_monthly_waste(
        provider: str,
        resource_type: str,
        resource_size: str | None = None,
        region: str = "global",
        quantity: float = 1.0,
    ) -> float:
        """Estimates monthly waste based on hourly rates."""
        quote = PricingService.get_hourly_rate_quote(
            provider=provider,
            resource_type=resource_type,
            resource_size=resource_size,
            region=region,
            quantity=quantity,
        )
        if quote.source == "missing":
            logger.warning(
                "pricing_quote_missing_for_estimate",
                provider=provider,
                resource_type=resource_type,
                resource_size=resource_size,
                region=region,
            )
        elif quote.pricing_metadata.get("pricing_confidence") != "catalog_exact":
            logger.info(
                "pricing_quote_non_exact_estimate",
                provider=provider,
                resource_type=resource_type,
                resource_size=resource_size,
                region=region,
                source=quote.source,
                pricing_confidence=quote.pricing_metadata.get("pricing_confidence"),
                match_strategy=quote.pricing_metadata.get("match_strategy"),
            )
        return quote.monthly_cost_usd

    @staticmethod
    def estimate_monthly_waste_quote(
        provider: str,
        resource_type: str,
        resource_size: str | None = None,
        region: str = "global",
        quantity: float = 1.0,
    ) -> PricingQuote:
        """Return monthly waste with source provenance for downstream evidence paths."""
        return PricingService.get_hourly_rate_quote(
            provider=provider,
            resource_type=resource_type,
            resource_size=resource_size,
            region=region,
            quantity=quantity,
        )
