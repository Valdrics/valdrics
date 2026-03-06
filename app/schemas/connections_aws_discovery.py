from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class AWSConnectionCreate(BaseModel):
    """Request body for creating a new AWS connection."""

    aws_account_id: str = Field(
        ..., pattern=r"^\d{12}$", description="12-digit AWS account ID"
    )
    role_arn: str = Field(
        ...,
        pattern=r"^arn:aws:iam::\d{12}:role/[\w+=,.@-]+$",
        description="Full ARN of the IAM role to assume",
    )
    external_id: str = Field(
        ..., pattern=r"^vx-[a-f0-9]{32}$", description="External ID from setup step"
    )
    region: str = Field(
        default="global",
        max_length=20,
        description="Region hint for resource discovery (use global for multi-region detection)",
    )
    is_management_account: bool = Field(
        default=False,
        description="Whether this is a Management Account for Organizations",
    )
    organization_id: str | None = Field(
        default=None,
        max_length=12,
        description="AWS Organization ID",
    )


class AWSConnectionResponse(BaseModel):
    """Response body for AWS connection."""

    id: UUID
    aws_account_id: str
    role_arn: str
    region: str
    status: str
    last_verified_at: datetime | None
    error_message: str | None
    is_management_account: bool
    organization_id: str | None
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class AWSConnectionSetup(BaseModel):
    """Response for initial setup - includes external_id for CloudFormation."""

    external_id: str
    instructions: str


class DiscoveredAccountResponse(BaseModel):
    id: UUID
    account_id: str
    name: str | None
    email: str | None
    status: str
    last_discovered_at: datetime | None

    model_config = ConfigDict(from_attributes=True)


class TemplateResponse(BaseModel):
    """Response containing template content for IAM role setup."""

    external_id: str
    cloudformation_yaml: str
    terraform_hcl: str
    magic_link: str
    instructions: str
    permissions_summary: list[str]


__all__ = [
    "AWSConnectionCreate",
    "AWSConnectionResponse",
    "AWSConnectionSetup",
    "DiscoveredAccountResponse",
    "TemplateResponse",
]
