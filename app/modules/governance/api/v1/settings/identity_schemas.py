from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class IdentitySettingsResponse(BaseModel):
    sso_enabled: bool
    allowed_email_domains: list[str]
    sso_federation_enabled: bool
    sso_federation_mode: str
    sso_federation_provider_id: str | None
    scim_enabled: bool
    has_scim_token: bool
    scim_last_rotated_at: str | None
    scim_group_mappings: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class RotateScimTokenResponse(BaseModel):
    scim_token: str
    rotated_at: str


class SsoDiagnostics(BaseModel):
    enabled: bool
    allowed_email_domains: list[str]
    enforcement_active: bool
    federation_enabled: bool
    federation_mode: str
    federation_ready: bool
    current_admin_domain: str | None
    current_admin_domain_allowed: bool | None
    issues: list[str] = Field(default_factory=list)


class ScimDiagnostics(BaseModel):
    available: bool
    enabled: bool
    has_token: bool
    token_blind_index_present: bool
    last_rotated_at: str | None
    token_age_days: int | None
    rotation_recommended_days: int
    rotation_overdue: bool
    issues: list[str] = Field(default_factory=list)


class IdentityDiagnosticsResponse(BaseModel):
    tier: str
    sso: SsoDiagnostics
    scim: ScimDiagnostics
    recommendations: list[str] = Field(default_factory=list)


class SsoFederationValidationCheck(BaseModel):
    name: str
    passed: bool
    severity: str = Field(default="error", description="info|warning|error")
    detail: str | None = None


class SsoFederationValidationResponse(BaseModel):
    tier: str
    enforcement_active: bool
    federation_enabled: bool
    federation_mode: str
    provider_id_configured: bool
    frontend_url: str
    expected_redirect_url: str
    discovery_endpoint: str
    passed: bool
    checks: list[SsoFederationValidationCheck] = Field(default_factory=list)


class ScimTokenTestRequest(BaseModel):
    scim_token: str = Field(
        ...,
        min_length=10,
        description="The SCIM bearer token you configured in your IdP.",
    )


class ScimTokenTestResponse(BaseModel):
    status: str
    token_matches: bool
