from __future__ import annotations

from datetime import datetime
from typing import Any, Self
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator

from app.schemas.connections_common import (
    _HYBRID_NATIVE_VENDORS,
    _LEDGER_NATIVE_VENDORS,
    _LICENSE_NATIVE_VENDORS,
    _PLATFORM_NATIVE_VENDORS,
    _SAAS_NATIVE_VENDORS,
    _normalize_non_empty,
)


class SaaSConnectionCreate(BaseModel):
    """SaaS Cloud+ connection request."""

    name: str = Field(..., min_length=3, max_length=100, description="Friendly name")
    vendor: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="SaaS vendor name",
    )
    auth_method: str = Field(
        default="manual",
        max_length=20,
        description="manual, api_key, oauth, csv",
    )
    api_key: str | None = Field(
        default=None,
        max_length=1024,
        description="Optional API key for vendor access",
    )
    connector_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Vendor-specific non-secret settings (for example Salesforce instance URL, SKU price map).",
    )
    spend_feed: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Normalized SaaS spend records",
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _normalize_non_empty(value, "name")

    @field_validator("vendor")
    @classmethod
    def _validate_vendor(cls, value: str) -> str:
        return _normalize_non_empty(value, "vendor").lower()

    @field_validator("auth_method")
    @classmethod
    def _validate_auth_method(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"manual", "api_key", "oauth", "csv"}:
            raise ValueError("auth_method must be one of: manual, api_key, oauth, csv")
        return normalized

    @model_validator(mode="after")
    def _validate_credentials(self) -> Self:
        if self.auth_method in {"api_key", "oauth"} and not self.api_key:
            raise ValueError(
                "api_key is required when auth_method is 'api_key' or 'oauth'"
            )

        native_mode = self.auth_method in {"api_key", "oauth"}
        if native_mode and self.vendor not in _SAAS_NATIVE_VENDORS:
            raise ValueError(
                "native SaaS auth currently supports vendors: stripe, salesforce. "
                "Use auth_method manual/csv for other vendors."
            )

        if self.vendor == "salesforce" and native_mode:
            instance_url = self.connector_config.get("instance_url")
            if not isinstance(instance_url, str) or not instance_url.strip():
                raise ValueError(
                    "connector_config.instance_url is required for Salesforce native connectors"
                )
            if not instance_url.strip().startswith(("https://", "http://")):
                raise ValueError("connector_config.instance_url must be an http(s) URL")
        return self


class SaaSConnectionResponse(BaseModel):
    id: UUID
    name: str
    vendor: str
    auth_method: str
    connector_config: dict[str, Any]
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LicenseConnectionCreate(BaseModel):
    """License/ITAM Cloud+ connection request."""

    name: str = Field(..., min_length=3, max_length=100, description="Friendly name")
    vendor: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="License vendor name",
    )
    auth_method: str = Field(
        default="manual",
        max_length=20,
        description="manual, api_key, oauth, csv",
    )
    api_key: str | None = Field(
        default=None,
        max_length=1024,
        description="Optional API key for vendor access",
    )
    connector_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Vendor-specific non-secret settings (for example Microsoft 365 SKU pricing overrides).",
    )
    license_feed: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Normalized license spend records",
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _normalize_non_empty(value, "name")

    @field_validator("vendor")
    @classmethod
    def _validate_vendor(cls, value: str) -> str:
        return _normalize_non_empty(value, "vendor").lower()

    @field_validator("auth_method")
    @classmethod
    def _validate_auth_method(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"manual", "api_key", "oauth", "csv"}:
            raise ValueError("auth_method must be one of: manual, api_key, oauth, csv")
        return normalized

    @model_validator(mode="after")
    def _validate_credentials(self) -> Self:
        if self.auth_method in {"api_key", "oauth"} and not self.api_key:
            raise ValueError(
                "api_key is required when auth_method is 'api_key' or 'oauth'"
            )

        native_mode = self.auth_method in {"api_key", "oauth"}
        if native_mode and self.vendor not in _LICENSE_NATIVE_VENDORS:
            raise ValueError(
                "native license auth currently supports: microsoft_365, google_workspace, "
                "github, slack, zoom, salesforce (plus aliases). "
                "Use auth_method manual/csv for other vendors."
            )

        if native_mode and self.vendor in {"salesforce", "sfdc"}:
            instance_url = self.connector_config.get(
                "salesforce_instance_url"
            ) or self.connector_config.get("instance_url")
            if not isinstance(instance_url, str) or not instance_url.strip():
                raise ValueError(
                    "connector_config.salesforce_instance_url (or instance_url) is required "
                    "for Salesforce native license connectors"
                )
            if not instance_url.strip().startswith(("https://", "http://")):
                raise ValueError(
                    "connector_config.salesforce_instance_url must be an http(s) URL"
                )

        default_seat_price = self.connector_config.get("default_seat_price_usd")
        if default_seat_price is not None and not isinstance(
            default_seat_price, (int, float)
        ):
            raise ValueError("connector_config.default_seat_price_usd must be numeric")
        if isinstance(default_seat_price, (int, float)) and default_seat_price < 0:
            raise ValueError(
                "connector_config.default_seat_price_usd cannot be negative"
            )

        sku_prices = self.connector_config.get("sku_prices")
        if sku_prices is not None:
            if not isinstance(sku_prices, dict):
                raise ValueError(
                    "connector_config.sku_prices must be a key/value object"
                )
            for key, value in sku_prices.items():
                if not isinstance(key, str):
                    raise ValueError("connector_config.sku_prices keys must be strings")
                if not isinstance(value, (int, float)):
                    raise ValueError(
                        "connector_config.sku_prices values must be numeric"
                    )
        return self


class LicenseConnectionResponse(BaseModel):
    id: UUID
    name: str
    vendor: str
    auth_method: str
    connector_config: dict[str, Any]
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PlatformConnectionCreate(BaseModel):
    """Internal Platform Cloud+ connection request (feed-based + ledger HTTP pull)."""

    name: str = Field(..., min_length=3, max_length=100, description="Friendly name")
    vendor: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Platform category/vendor label",
    )
    auth_method: str = Field(
        default="manual",
        max_length=20,
        description="manual, csv, or api_key",
    )
    api_key: str | None = Field(
        default=None,
        max_length=1024,
        description="API key for native connectors",
    )
    api_secret: str | None = Field(
        default=None,
        max_length=1024,
        description="Optional second secret for native connectors (for example Datadog application key).",
    )
    connector_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-secret settings (for example ledger HTTP base URL and path).",
    )
    spend_feed: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Normalized platform spend records",
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _normalize_non_empty(value, "name")

    @field_validator("vendor")
    @classmethod
    def _validate_vendor(cls, value: str) -> str:
        return _normalize_non_empty(value, "vendor").lower()

    @field_validator("auth_method")
    @classmethod
    def _validate_auth_method(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"manual", "csv", "api_key"}:
            raise ValueError("auth_method must be one of: manual, csv, api_key")
        return normalized

    @model_validator(mode="after")
    def _validate_native_config(self) -> Self:
        if self.auth_method == "api_key" and not self.api_key:
            raise ValueError("api_key is required when auth_method is 'api_key'")

        native_mode = self.auth_method == "api_key"
        if native_mode and self.vendor not in _PLATFORM_NATIVE_VENDORS:
            raise ValueError(
                "native Platform auth currently supports: ledger_http (and aliases), datadog, newrelic. "
                "Use auth_method manual/csv for custom vendors."
            )

        if native_mode:
            if self.vendor in _LEDGER_NATIVE_VENDORS:
                base_url = self.connector_config.get("base_url")
                if not isinstance(base_url, str) or not base_url.strip():
                    raise ValueError(
                        "connector_config.base_url is required for native platform connectors"
                    )
                if not base_url.strip().startswith(("https://", "http://")):
                    raise ValueError("connector_config.base_url must be an http(s) URL")

            if self.vendor == "datadog":
                if not self.api_secret:
                    raise ValueError(
                        "api_secret is required for Datadog (application key)"
                    )
                unit_prices = self.connector_config.get("unit_prices_usd")
                if not isinstance(unit_prices, dict) or not unit_prices:
                    raise ValueError(
                        "connector_config.unit_prices_usd must be a non-empty object for Datadog pricing"
                    )

            if self.vendor in {"newrelic", "new_relic", "new-relic"}:
                account_id = self.connector_config.get("account_id")
                if not isinstance(account_id, int) and not (
                    isinstance(account_id, str) and account_id.isdigit()
                ):
                    raise ValueError(
                        "connector_config.account_id is required for New Relic (numeric)"
                    )
                nrql_template = self.connector_config.get(
                    "nrql_template"
                ) or self.connector_config.get("nrql_query")
                if not isinstance(nrql_template, str) or not nrql_template.strip():
                    raise ValueError(
                        "connector_config.nrql_template is required for New Relic"
                    )
                unit_prices = self.connector_config.get("unit_prices_usd")
                if not isinstance(unit_prices, dict) or not unit_prices:
                    raise ValueError(
                        "connector_config.unit_prices_usd must be a non-empty object for New Relic pricing"
                    )
        return self


class PlatformConnectionResponse(BaseModel):
    id: UUID
    name: str
    vendor: str
    auth_method: str
    connector_config: dict[str, Any]
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class HybridConnectionCreate(BaseModel):
    """Private/Hybrid infrastructure Cloud+ connection request (feed-based + ledger HTTP pull)."""

    name: str = Field(..., min_length=3, max_length=100, description="Friendly name")
    vendor: str = Field(
        ...,
        min_length=2,
        max_length=100,
        description="Hybrid system/vendor label",
    )
    auth_method: str = Field(
        default="manual",
        max_length=20,
        description="manual, csv, or api_key",
    )
    api_key: str | None = Field(
        default=None,
        max_length=1024,
        description="API key for native connectors",
    )
    api_secret: str | None = Field(
        default=None,
        max_length=1024,
        description="Optional second secret for native connectors (for example OpenStack app credential secret).",
    )
    connector_config: dict[str, Any] = Field(
        default_factory=dict,
        description="Non-secret settings (for example ledger HTTP base URL and path).",
    )
    spend_feed: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Normalized hybrid spend records",
    )

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        return _normalize_non_empty(value, "name")

    @field_validator("vendor")
    @classmethod
    def _validate_vendor(cls, value: str) -> str:
        return _normalize_non_empty(value, "vendor").lower()

    @field_validator("auth_method")
    @classmethod
    def _validate_auth_method(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"manual", "csv", "api_key"}:
            raise ValueError("auth_method must be one of: manual, csv, api_key")
        return normalized

    @model_validator(mode="after")
    def _validate_native_config(self) -> Self:
        if self.auth_method == "api_key" and not self.api_key:
            raise ValueError("api_key is required when auth_method is 'api_key'")

        native_mode = self.auth_method == "api_key"
        if native_mode and self.vendor not in _HYBRID_NATIVE_VENDORS:
            raise ValueError(
                "native Hybrid auth currently supports: ledger_http (and aliases), openstack/cloudkitty, vmware/vcenter. "
                "Use auth_method manual/csv for custom vendors."
            )

        if native_mode:
            if self.vendor in _LEDGER_NATIVE_VENDORS:
                base_url = self.connector_config.get("base_url")
                if not isinstance(base_url, str) or not base_url.strip():
                    raise ValueError(
                        "connector_config.base_url is required for native hybrid connectors"
                    )
                if not base_url.strip().startswith(("https://", "http://")):
                    raise ValueError("connector_config.base_url must be an http(s) URL")

            if self.vendor in {"openstack", "cloudkitty"}:
                if not self.api_secret:
                    raise ValueError(
                        "api_secret is required for OpenStack/CloudKitty (application credential secret)"
                    )
                auth_url = self.connector_config.get("auth_url")
                if not isinstance(auth_url, str) or not auth_url.strip():
                    raise ValueError(
                        "connector_config.auth_url is required for OpenStack Keystone"
                    )
                if not auth_url.strip().startswith(("https://", "http://")):
                    raise ValueError("connector_config.auth_url must be an http(s) URL")
                cloudkitty_url = self.connector_config.get(
                    "cloudkitty_base_url"
                ) or self.connector_config.get("base_url")
                if not isinstance(cloudkitty_url, str) or not cloudkitty_url.strip():
                    raise ValueError(
                        "connector_config.cloudkitty_base_url is required for CloudKitty API"
                    )
                if not cloudkitty_url.strip().startswith(("https://", "http://")):
                    raise ValueError(
                        "connector_config.cloudkitty_base_url must be an http(s) URL"
                    )

            if self.vendor in {"vmware", "vcenter", "vsphere"}:
                if not self.api_secret:
                    raise ValueError(
                        "api_secret is required for VMware/vCenter (password)"
                    )
                base_url = self.connector_config.get("base_url")
                if not isinstance(base_url, str) or not base_url.strip():
                    raise ValueError(
                        "connector_config.base_url is required for VMware/vCenter"
                    )
                if not base_url.strip().startswith(("https://", "http://")):
                    raise ValueError("connector_config.base_url must be an http(s) URL")
                cpu_price = self.connector_config.get("cpu_hour_usd")
                ram_price = self.connector_config.get("ram_gb_hour_usd")
                if not isinstance(cpu_price, (int, float)) or cpu_price <= 0:
                    raise ValueError(
                        "connector_config.cpu_hour_usd must be a positive number for VMware pricing"
                    )
                if not isinstance(ram_price, (int, float)) or ram_price <= 0:
                    raise ValueError(
                        "connector_config.ram_gb_hour_usd must be a positive number for VMware pricing"
                    )
        return self


class HybridConnectionResponse(BaseModel):
    id: UUID
    name: str
    vendor: str
    auth_method: str
    connector_config: dict[str, Any]
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "HybridConnectionCreate",
    "HybridConnectionResponse",
    "LicenseConnectionCreate",
    "LicenseConnectionResponse",
    "PlatformConnectionCreate",
    "PlatformConnectionResponse",
    "SaaSConnectionCreate",
    "SaaSConnectionResponse",
]
