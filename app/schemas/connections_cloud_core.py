from __future__ import annotations

from datetime import datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class AzureConnectionCreate(BaseModel):
    """Azure Service Principal connection request."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=100,
        description="Friendly name for connection",
    )
    azure_tenant_id: str = Field(
        ...,
        max_length=50,
        description="Azure Tenant ID (Directory ID)",
    )
    client_id: str = Field(..., max_length=50, description="Application ID")
    subscription_id: str = Field(..., max_length=50, description="Subscription ID")
    client_secret: str | None = Field(
        default=None,
        max_length=255,
        description="Client Secret (Optional for Workload Identity)",
    )
    auth_method: str = Field(
        default="secret",
        max_length=20,
        description="secret or workload_identity",
    )

    @field_validator("auth_method")
    @classmethod
    def _validate_auth_method(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"secret", "workload_identity"}:
            raise ValueError("auth_method must be 'secret' or 'workload_identity'")
        return normalized

    @model_validator(mode="after")
    def _validate_credentials(self) -> Self:
        if self.auth_method == "secret" and not self.client_secret:
            raise ValueError("client_secret is required when auth_method is 'secret'")
        return self


class AzureConnectionResponse(BaseModel):
    id: UUID
    name: str
    azure_tenant_id: str
    client_id: str
    subscription_id: str
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class GCPConnectionCreate(BaseModel):
    """GCP Service Account connection request."""

    name: str = Field(..., min_length=3, max_length=100, description="Friendly name")
    project_id: str = Field(..., max_length=100, description="GCP Project ID")
    service_account_json: str | None = Field(
        default=None,
        max_length=20000,
        description="Full JSON content (Optional for Workload Identity)",
    )
    auth_method: str = Field(
        default="secret",
        max_length=20,
        description="secret or workload_identity",
    )
    billing_project_id: str | None = Field(
        default=None,
        max_length=100,
        description="Project ID holding BigQuery export",
    )
    billing_dataset: str | None = Field(
        default=None,
        max_length=100,
        description="BigQuery dataset ID",
    )
    billing_table: str | None = Field(
        default=None,
        max_length=100,
        description="BigQuery table ID",
    )

    @field_validator("auth_method")
    @classmethod
    def _validate_auth_method(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"secret", "workload_identity"}:
            raise ValueError("auth_method must be 'secret' or 'workload_identity'")
        return normalized

    @model_validator(mode="after")
    def _validate_credentials(self) -> Self:
        import json

        if self.auth_method == "secret" and not self.service_account_json:
            raise ValueError(
                "service_account_json is required when auth_method is 'secret'"
            )
        if self.service_account_json:
            try:
                json.loads(self.service_account_json)
            except json.JSONDecodeError as exc:
                raise ValueError("service_account_json must be valid JSON") from exc
        return self


class GCPConnectionResponse(BaseModel):
    id: UUID
    name: str
    project_id: str
    auth_method: str
    billing_project_id: str | None
    billing_dataset: str | None
    billing_table: str | None
    is_active: bool
    last_synced_at: datetime | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


__all__ = [
    "AzureConnectionCreate",
    "AzureConnectionResponse",
    "GCPConnectionCreate",
    "GCPConnectionResponse",
]
