"""AWS pricing sync helpers for the persisted cloud pricing catalog."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger()

AWS_MONTHLY_PRICING_UNITS = {"gb-mo", "gb-month", "gb-months"}
AWS_HOURLY_PRICING_UNITS = {"hrs", "hours", "hour"}
AWS_PRICING_BASE_REGION = "us-east-1"
AWS_PRICING_BASE_LOCATION = "US East (N. Virginia)"
AWS_PRICING_REGION_LOCATIONS: dict[str, str] = {
    "us-east-1": "US East (N. Virginia)",
    "us-east-2": "US East (Ohio)",
    "us-west-1": "US West (N. California)",
    "us-west-2": "US West (Oregon)",
    "eu-west-1": "EU (Ireland)",
    "eu-west-2": "EU (London)",
    "eu-west-3": "EU (Paris)",
    "eu-central-1": "EU (Frankfurt)",
    "ap-south-1": "Asia Pacific (Mumbai)",
    "ap-southeast-1": "Asia Pacific (Singapore)",
    "ap-southeast-2": "Asia Pacific (Sydney)",
    "ap-northeast-1": "Asia Pacific (Tokyo)",
    "sa-east-1": "South America (Sao Paulo)",
    "af-south-1": "Africa (Cape Town)",
}
AWS_PRICING_LOCATION_PLACEHOLDER = "__AWS_PRICING_LOCATION__"
AWS_PRICING_PROBE_TEMPLATES: tuple[dict[str, Any], ...] = (
    {
        "service_code": "AmazonEC2",
        "provider": "aws",
        "resource_type": "nat_gateway",
        "resource_size": "default",
        "catalog_probe": "NatGateway-Hours",
        "filters": (
            {"Type": "TERM_MATCH", "Field": "usageType", "Value": "NatGateway-Hours"},
            {
                "Type": "TERM_MATCH",
                "Field": "location",
                "Value": AWS_PRICING_LOCATION_PLACEHOLDER,
            },
        ),
    },
    {
        "service_code": "AmazonEC2",
        "provider": "aws",
        "resource_type": "instance",
        "resource_size": "t3.micro",
        "catalog_probe": "ec2-linux-on-demand-t3.micro",
        "filters": (
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "t3.micro"},
            {
                "Type": "TERM_MATCH",
                "Field": "location",
                "Value": AWS_PRICING_LOCATION_PLACEHOLDER,
            },
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
        ),
    },
    {
        "service_code": "AmazonEC2",
        "provider": "aws",
        "resource_type": "instance",
        "resource_size": "t3.medium",
        "catalog_probe": "ec2-linux-on-demand-t3.medium",
        "filters": (
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "t3.medium"},
            {
                "Type": "TERM_MATCH",
                "Field": "location",
                "Value": AWS_PRICING_LOCATION_PLACEHOLDER,
            },
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
        ),
    },
    {
        "service_code": "AmazonEC2",
        "provider": "aws",
        "resource_type": "instance",
        "resource_size": "m5.large",
        "catalog_probe": "ec2-linux-on-demand-m5.large",
        "filters": (
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "m5.large"},
            {
                "Type": "TERM_MATCH",
                "Field": "location",
                "Value": AWS_PRICING_LOCATION_PLACEHOLDER,
            },
            {"Type": "TERM_MATCH", "Field": "operatingSystem", "Value": "Linux"},
            {"Type": "TERM_MATCH", "Field": "preInstalledSw", "Value": "NA"},
            {"Type": "TERM_MATCH", "Field": "tenancy", "Value": "Shared"},
            {"Type": "TERM_MATCH", "Field": "capacitystatus", "Value": "Used"},
        ),
    },
    {
        "service_code": "AmazonEC2",
        "provider": "aws",
        "resource_type": "volume",
        "resource_size": "gp2",
        "catalog_probe": "ebs-gp2-storage",
        "filters": (
            {"Type": "TERM_MATCH", "Field": "volumeApiName", "Value": "gp2"},
            {
                "Type": "TERM_MATCH",
                "Field": "location",
                "Value": AWS_PRICING_LOCATION_PLACEHOLDER,
            },
            {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
        ),
    },
    {
        "service_code": "AmazonEC2",
        "provider": "aws",
        "resource_type": "volume",
        "resource_size": "gp3",
        "catalog_probe": "ebs-gp3-storage",
        "filters": (
            {"Type": "TERM_MATCH", "Field": "volumeApiName", "Value": "gp3"},
            {
                "Type": "TERM_MATCH",
                "Field": "location",
                "Value": AWS_PRICING_LOCATION_PLACEHOLDER,
            },
            {"Type": "TERM_MATCH", "Field": "productFamily", "Value": "Storage"},
        ),
    },
    {
        "service_code": "AmazonRDS",
        "provider": "aws",
        "resource_type": "rds",
        "resource_size": "db.t3.micro",
        "catalog_probe": "rds-postgresql-db.t3.micro-multi-az",
        "filters": (
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "db.t3.micro"},
            {
                "Type": "TERM_MATCH",
                "Field": "location",
                "Value": AWS_PRICING_LOCATION_PLACEHOLDER,
            },
            {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": "PostgreSQL"},
            {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": "Multi-AZ"},
            {"Type": "TERM_MATCH", "Field": "licenseModel", "Value": "No License required"},
        ),
    },
    {
        "service_code": "AmazonRDS",
        "provider": "aws",
        "resource_type": "rds",
        "resource_size": "db.t3.small",
        "catalog_probe": "rds-postgresql-db.t3.small-multi-az",
        "filters": (
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "db.t3.small"},
            {
                "Type": "TERM_MATCH",
                "Field": "location",
                "Value": AWS_PRICING_LOCATION_PLACEHOLDER,
            },
            {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": "PostgreSQL"},
            {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": "Multi-AZ"},
            {"Type": "TERM_MATCH", "Field": "licenseModel", "Value": "No License required"},
        ),
    },
    {
        "service_code": "AmazonRDS",
        "provider": "aws",
        "resource_type": "rds",
        "resource_size": "db.t3.medium",
        "catalog_probe": "rds-postgresql-db.t3.medium-multi-az",
        "filters": (
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "db.t3.medium"},
            {
                "Type": "TERM_MATCH",
                "Field": "location",
                "Value": AWS_PRICING_LOCATION_PLACEHOLDER,
            },
            {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": "PostgreSQL"},
            {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": "Multi-AZ"},
            {"Type": "TERM_MATCH", "Field": "licenseModel", "Value": "No License required"},
        ),
    },
    {
        "service_code": "AmazonRDS",
        "provider": "aws",
        "resource_type": "rds",
        "resource_size": "db.t3.large",
        "catalog_probe": "rds-postgresql-db.t3.large-multi-az",
        "filters": (
            {"Type": "TERM_MATCH", "Field": "instanceType", "Value": "db.t3.large"},
            {
                "Type": "TERM_MATCH",
                "Field": "location",
                "Value": AWS_PRICING_LOCATION_PLACEHOLDER,
            },
            {"Type": "TERM_MATCH", "Field": "databaseEngine", "Value": "PostgreSQL"},
            {"Type": "TERM_MATCH", "Field": "deploymentOption", "Value": "Multi-AZ"},
            {"Type": "TERM_MATCH", "Field": "licenseModel", "Value": "No License required"},
        ),
    },
)


def _expand_aws_probe_filters(
    filters: tuple[dict[str, str], ...],
    *,
    location: str,
) -> tuple[dict[str, str], ...]:
    return tuple(
        {
            **entry,
            "Value": (
                location
                if entry.get("Field") == "location"
                and entry.get("Value") == AWS_PRICING_LOCATION_PLACEHOLDER
                else entry["Value"]
            ),
        }
        for entry in filters
    )


def _expand_aws_pricing_probes() -> tuple[dict[str, Any], ...]:
    expanded: list[dict[str, Any]] = []
    for region, location in AWS_PRICING_REGION_LOCATIONS.items():
        for template in AWS_PRICING_PROBE_TEMPLATES:
            expanded.append(
                {
                    **template,
                    "region": region,
                    "catalog_location": location,
                    "filters": _expand_aws_probe_filters(
                        template["filters"],
                        location=location,
                    ),
                }
            )
    return tuple(expanded)


AWS_PRICING_PROBES = _expand_aws_pricing_probes()


def _extract_aws_price_dimension(price_list: list[str]) -> tuple[float, str] | None:
    for raw_entry in price_list:
        try:
            payload = json.loads(raw_entry)
        except json.JSONDecodeError:
            continue
        on_demand_terms = payload.get("terms", {}).get("OnDemand", {})
        for term in on_demand_terms.values():
            dimensions = term.get("priceDimensions", {})
            for dimension in dimensions.values():
                usd_value = dimension.get("pricePerUnit", {}).get("USD")
                try:
                    rate = float(usd_value)
                except (TypeError, ValueError):
                    continue
                if rate >= 0:
                    unit = str(dimension.get("unit") or "").strip()
                    return rate, unit
    return None


def _normalize_aws_rate_to_hourly(raw_rate: float, unit: str) -> float | None:
    normalized_unit = str(unit or "").strip().lower()
    if normalized_unit in AWS_HOURLY_PRICING_UNITS:
        return raw_rate
    if normalized_unit in AWS_MONTHLY_PRICING_UNITS:
        return raw_rate / 730
    return None


def _build_aws_pricing_record(*, probe: dict[str, Any], price_list: list[str]) -> dict[str, Any] | None:
    dimension = _extract_aws_price_dimension(price_list)
    if dimension is None:
        return None

    raw_rate, unit = dimension
    normalized_rate = _normalize_aws_rate_to_hourly(raw_rate, unit)
    if normalized_rate is None:
        logger.warning(
            "aws_pricing_sync_unsupported_unit",
            catalog_probe=probe["catalog_probe"],
            unit=unit,
        )
        return None

    return {
        "provider": probe["provider"],
        "resource_type": probe["resource_type"],
        "resource_size": probe["resource_size"],
        "region": probe["region"],
        "hourly_rate_usd": normalized_rate,
        "source": "aws_pricing_api",
        "pricing_metadata": {
            "catalog_probe": probe["catalog_probe"],
            "catalog_location": probe["catalog_location"],
            "catalog_region": probe["region"],
            "catalog_unit": unit,
            "catalog_rate_usd": raw_rate,
            "normalized_hourly_rate_usd": normalized_rate,
            "service_code": probe["service_code"],
            "coverage_scope": "curated_live_catalog",
            "region_coverage_mode": "explicit_multi_region_catalog",
            "covered_regions": tuple(sorted(AWS_PRICING_REGION_LOCATIONS.keys())),
            "coverage_limitations": (
                "Curated live catalog probes cover explicitly supported regions and "
                "resource classes only; uncovered resource classes fall back to defaults."
            ),
            "availability_profile": (
                "multi-az" if probe["resource_type"] == "rds" else "service_default"
            ),
            "synced_at": datetime.now(timezone.utc).isoformat(),
        },
    }


def collect_supported_aws_pricing_records(pricing_client: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for probe in AWS_PRICING_PROBES:
        try:
            response: dict[str, Any] = pricing_client.get_products(
                ServiceCode=probe["service_code"],
                Filters=list(probe["filters"]),
            )
        except (OSError, RuntimeError, ValueError, TypeError) as exc:
            logger.warning(
                "aws_pricing_sync_probe_failed",
                catalog_probe=probe["catalog_probe"],
                error=str(exc),
            )
            continue
        record = _build_aws_pricing_record(
            probe=probe,
            price_list=list(response.get("PriceList", []) or []),
        )
        if record is not None:
            records.append(record)
    return records


__all__ = ["collect_supported_aws_pricing_records"]
