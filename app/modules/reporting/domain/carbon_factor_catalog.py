from __future__ import annotations

import hashlib
import json
from typing import Any

# Carbon intensity by cloud region (gCO2eq per kWh)
# Source: Electricity Maps, EPA eGRID, and provider sustainability reports.
REGION_CARBON_INTENSITY = {
    # Low carbon (renewables/nuclear)
    "us-west-2": 21,  # Oregon - hydro
    "eu-north-1": 28,  # Stockholm - hydro/nuclear
    "ca-central-1": 35,  # Montreal - hydro
    "eu-west-1": 316,  # Ireland - wind/gas mix
    # Medium carbon
    "us-west-1": 218,  # N. California
    "eu-west-2": 225,  # London
    "eu-central-1": 338,  # Frankfurt
    # High carbon (coal/gas heavy)
    "us-east-1": 379,  # N. Virginia
    "us-east-2": 440,  # Ohio
    "ap-southeast-1": 408,  # Singapore
    "ap-south-1": 708,  # Mumbai
    "ap-northeast-1": 506,  # Tokyo
    # Synthetic global average for provider-agnostic defaults.
    "global": 400,
    # Default for unknown regions
    "default": 400,
}

# Energy consumption per dollar spent (kWh/$), provider-aware.
AWS_SERVICE_ENERGY_FACTORS = {
    "Amazon Elastic Compute Cloud - Compute": 0.05,
    "EC2 - Other": 0.04,
    "Amazon Simple Storage Service": 0.01,
    "Amazon Relational Database Service": 0.04,
    "Amazon CloudFront": 0.02,
    "AWS Lambda": 0.03,
    "Amazon DynamoDB": 0.02,
    "Amazon Virtual Private Cloud": 0.02,
    "default": 0.03,
}

AZURE_SERVICE_ENERGY_FACTORS = {
    "Virtual Machines": 0.05,
    "Azure Kubernetes Service": 0.04,
    "Storage": 0.012,
    "SQL Database": 0.04,
    "Functions": 0.03,
    "default": 0.03,
}

GCP_SERVICE_ENERGY_FACTORS = {
    "Compute Engine": 0.05,
    "Google Kubernetes Engine": 0.04,
    "Cloud Storage": 0.01,
    "Cloud SQL": 0.04,
    "Cloud Functions": 0.03,
    "default": 0.03,
}

SAAS_SERVICE_ENERGY_FACTORS = {
    "default": 0.015,
}

LICENSE_SERVICE_ENERGY_FACTORS = {
    "default": 0.01,
}

PLATFORM_SERVICE_ENERGY_FACTORS = {
    "default": 0.03,
}

HYBRID_SERVICE_ENERGY_FACTORS = {
    "default": 0.03,
}

GENERIC_SERVICE_ENERGY_FACTORS = {
    "default": 0.03,
}

SERVICE_ENERGY_FACTORS_BY_PROVIDER = {
    "aws": AWS_SERVICE_ENERGY_FACTORS,
    "azure": AZURE_SERVICE_ENERGY_FACTORS,
    "gcp": GCP_SERVICE_ENERGY_FACTORS,
    "saas": SAAS_SERVICE_ENERGY_FACTORS,
    "license": LICENSE_SERVICE_ENERGY_FACTORS,
    "platform": PLATFORM_SERVICE_ENERGY_FACTORS,
    "hybrid": HYBRID_SERVICE_ENERGY_FACTORS,
    "generic": GENERIC_SERVICE_ENERGY_FACTORS,
}

# Power Usage Effectiveness (PUE) - cloud datacenter overhead.
CLOUD_PUE = 1.2

# Embodied emissions factor (kgCO2e per kWh of compute)
EMBODIED_EMISSIONS_FACTOR = 0.025
CARBON_FACTOR_SOURCE = "Electricity Maps + EPA eGRID + provider sustainability reports"
CARBON_FACTOR_VERSION = "2025-12-01"
CARBON_FACTOR_TIMESTAMP = "2025-12-01"
CARBON_METHODOLOGY_VERSION = "valdrics-carbon-v2.0"


def build_carbon_factor_payload() -> dict[str, Any]:
    """
    Build the canonical carbon factor payload used for:
    - DB-backed factor set staging/activation
    - audit evidence (carbon assurance snapshots)
    - methodology metadata checksums

    Important: this payload must NOT include request-specific context like provider/tenant.
    """
    return {
        "region_carbon_intensity": REGION_CARBON_INTENSITY,
        "service_energy_factors_by_provider": SERVICE_ENERGY_FACTORS_BY_PROVIDER,
        "cloud_pue": float(CLOUD_PUE),
        "embodied_emissions_factor": float(EMBODIED_EMISSIONS_FACTOR),
        "factor_source": CARBON_FACTOR_SOURCE,
        "factor_version": CARBON_FACTOR_VERSION,
        "factor_timestamp": CARBON_FACTOR_TIMESTAMP,
        "methodology_version": CARBON_METHODOLOGY_VERSION,
    }


def compute_carbon_factor_checksum(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def carbon_assurance_snapshot(
    factor_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Return an auditable snapshot of the carbon methodology and factor versions.

    This is used for procurement/compliance evidence capture (reproducibility).
    """
    payload = (
        factor_payload
        if isinstance(factor_payload, dict) and factor_payload
        else build_carbon_factor_payload()
    )
    checksum = compute_carbon_factor_checksum(payload)

    return {
        "methodology_version": str(
            payload.get("methodology_version") or CARBON_METHODOLOGY_VERSION
        ),
        "factor_source": str(payload.get("factor_source") or CARBON_FACTOR_SOURCE),
        "factor_version": str(payload.get("factor_version") or CARBON_FACTOR_VERSION),
        "factor_timestamp": str(
            payload.get("factor_timestamp") or CARBON_FACTOR_TIMESTAMP
        ),
        "constants": {
            "cloud_pue": float(payload.get("cloud_pue") or CLOUD_PUE),
            "embodied_emissions_factor_kg_per_kwh": float(
                payload.get("embodied_emissions_factor") or EMBODIED_EMISSIONS_FACTOR
            ),
        },
        "region_intensity": {
            "count": len(payload.get("region_carbon_intensity") or {}),
            "default_gco2_kwh": int(
                (payload.get("region_carbon_intensity") or {}).get("default", 400)
            ),
        },
        "providers": sorted(
            (payload.get("service_energy_factors_by_provider") or {}).keys()
        ),
        "factors_checksum_sha256": checksum,
    }
