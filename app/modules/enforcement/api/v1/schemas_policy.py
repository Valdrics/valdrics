from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enforcement import EnforcementCreditPoolType, EnforcementMode
from app.modules.enforcement.domain.policy_document import (
    ApprovalRoutingRule,
    PolicyDocument,
)


class PolicyResponse(BaseModel):
    terraform_mode: EnforcementMode
    terraform_mode_prod: EnforcementMode
    terraform_mode_nonprod: EnforcementMode
    k8s_admission_mode: EnforcementMode
    k8s_admission_mode_prod: EnforcementMode
    k8s_admission_mode_nonprod: EnforcementMode
    require_approval_for_prod: bool
    require_approval_for_nonprod: bool
    enforce_prod_requester_reviewer_separation: bool
    enforce_nonprod_requester_reviewer_separation: bool
    plan_monthly_ceiling_usd: Decimal | None
    enterprise_monthly_ceiling_usd: Decimal | None
    auto_approve_below_monthly_usd: Decimal
    hard_deny_above_monthly_usd: Decimal
    default_ttl_seconds: int
    approval_routing_rules: list[ApprovalRoutingRule]
    policy_document_schema_version: str
    policy_document_sha256: str
    policy_document: PolicyDocument
    policy_version: int
    updated_at: datetime


class PolicyUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    terraform_mode: EnforcementMode = Field(default=EnforcementMode.SOFT)
    terraform_mode_prod: EnforcementMode | None = None
    terraform_mode_nonprod: EnforcementMode | None = None
    k8s_admission_mode: EnforcementMode = Field(default=EnforcementMode.SOFT)
    k8s_admission_mode_prod: EnforcementMode | None = None
    k8s_admission_mode_nonprod: EnforcementMode | None = None
    require_approval_for_prod: bool = Field(default=True)
    require_approval_for_nonprod: bool = Field(default=False)
    enforce_prod_requester_reviewer_separation: bool = Field(default=True)
    enforce_nonprod_requester_reviewer_separation: bool = Field(default=False)
    plan_monthly_ceiling_usd: Decimal | None = Field(default=None, ge=0)
    enterprise_monthly_ceiling_usd: Decimal | None = Field(default=None, ge=0)
    auto_approve_below_monthly_usd: Decimal = Field(default=Decimal("25"), ge=0)
    hard_deny_above_monthly_usd: Decimal = Field(default=Decimal("5000"), gt=0)
    default_ttl_seconds: int = Field(default=900, ge=60, le=86400)
    approval_routing_rules: list[ApprovalRoutingRule] = Field(default_factory=list)
    policy_document: PolicyDocument | None = None


class BudgetUpsertRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scope_key: str = Field(default="default", min_length=1, max_length=128)
    monthly_limit_usd: Decimal = Field(..., ge=0)
    active: bool = Field(default=True)


class BudgetResponse(BaseModel):
    id: UUID
    scope_key: str
    monthly_limit_usd: Decimal
    active: bool
    created_at: datetime
    updated_at: datetime


class CreditCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pool_type: EnforcementCreditPoolType = Field(
        default=EnforcementCreditPoolType.RESERVED
    )
    scope_key: str = Field(default="default", min_length=1, max_length=128)
    total_amount_usd: Decimal = Field(..., gt=0)
    expires_at: datetime | None = None
    reason: str | None = Field(default=None, max_length=500)


class CreditResponse(BaseModel):
    id: UUID
    pool_type: EnforcementCreditPoolType
    scope_key: str
    total_amount_usd: Decimal
    remaining_amount_usd: Decimal
    expires_at: datetime | None
    reason: str | None
    active: bool
    created_at: datetime


__all__ = [
    "PolicyResponse",
    "PolicyUpdateRequest",
    "BudgetUpsertRequest",
    "BudgetResponse",
    "CreditCreateRequest",
    "CreditResponse",
]
