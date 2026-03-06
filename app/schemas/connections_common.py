from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

_SAAS_NATIVE_VENDORS = {"stripe", "salesforce"}
_LICENSE_NATIVE_VENDORS = {
    "microsoft_365",
    "microsoft365",
    "m365",
    "microsoft",
    "google_workspace",
    "googleworkspace",
    "gsuite",
    "google",
    "github",
    "github_enterprise",
    "slack",
    "slack_enterprise",
    "zoom",
    "salesforce",
    "sfdc",
}
_LEDGER_NATIVE_VENDORS = {"ledger_http", "cmdb_ledger", "cmdb-ledger", "ledger"}
_PLATFORM_NATIVE_VENDORS = {
    *_LEDGER_NATIVE_VENDORS,
    "datadog",
    "newrelic",
    "new_relic",
    "new-relic",
}
_HYBRID_NATIVE_VENDORS = {
    *_LEDGER_NATIVE_VENDORS,
    "openstack",
    "cloudkitty",
    "vmware",
    "vcenter",
    "vsphere",
}


def _normalize_non_empty(value: str, field_name: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty")
    return normalized


class DiscoveryStageARequest(BaseModel):
    """Stage A discovery request based on an email domain."""

    email: EmailStr = Field(
        ...,
        description="User email used for domain-based discovery signals.",
    )


class DiscoveryDeepScanRequest(BaseModel):
    """Stage B deep scan request after IdP admin connection."""

    domain: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Verified organization domain to attach discovery candidates to.",
    )
    idp_provider: str = Field(
        ...,
        description="Primary IdP provider (microsoft_365 or google_workspace).",
    )
    max_users: int = Field(
        default=20,
        ge=1,
        le=50,
        description="Google Workspace user sampling cap for token-based app discovery.",
    )

    @field_validator("domain")
    @classmethod
    def _normalize_domain(cls, value: str) -> str:
        normalized = value.strip().lower().strip(".")
        if "." not in normalized:
            raise ValueError("domain must be a fully qualified domain, e.g. example.com")
        return normalized

    @field_validator("idp_provider")
    @classmethod
    def _normalize_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"microsoft_365", "google_workspace"}:
            raise ValueError("idp_provider must be microsoft_365 or google_workspace")
        return normalized


class DiscoveryCandidateResponse(BaseModel):
    id: UUID
    domain: str
    category: str
    provider: str
    source: str
    status: str
    confidence_score: float
    requires_admin_auth: bool
    connection_target: str | None
    connection_vendor_hint: str | None
    evidence: list[str]
    details: dict[str, Any]
    last_seen_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DiscoveryStageResponse(BaseModel):
    domain: str
    candidates: list[DiscoveryCandidateResponse]
    warnings: list[str] = Field(default_factory=list)
    total_candidates: int


__all__ = [
    "_HYBRID_NATIVE_VENDORS",
    "_LEDGER_NATIVE_VENDORS",
    "_LICENSE_NATIVE_VENDORS",
    "_PLATFORM_NATIVE_VENDORS",
    "_SAAS_NATIVE_VENDORS",
    "_normalize_non_empty",
    "DiscoveryCandidateResponse",
    "DiscoveryDeepScanRequest",
    "DiscoveryStageARequest",
    "DiscoveryStageResponse",
]
