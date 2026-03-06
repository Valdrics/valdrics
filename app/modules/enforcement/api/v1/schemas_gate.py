from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enforcement import EnforcementSource


class GateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: str = Field(default="default", min_length=1, max_length=128)
    environment: str = Field(default="nonprod", min_length=1, max_length=32)
    action: str = Field(..., min_length=1, max_length=64)
    resource_reference: str = Field(..., min_length=1, max_length=512)
    estimated_monthly_delta_usd: Decimal = Field(..., ge=0)
    estimated_hourly_delta_usd: Decimal = Field(default=Decimal("0"), ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=4, max_length=128)
    dry_run: bool = Field(default=False)


class GateDecisionResponse(BaseModel):
    decision: str
    reason_codes: list[str]
    decision_id: UUID
    policy_version: int
    approval_required: bool
    approval_request_id: UUID | None = None
    approval_token: str | None = None
    approval_token_contract: Literal["approval_flow_only"] = "approval_flow_only"
    ttl_seconds: int
    request_fingerprint: str
    reservation_active: bool
    computed_context: dict[str, Any] | None = None


class TerraformPreflightRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str = Field(..., min_length=1, max_length=128)
    stage: str = Field(default="pre_plan", min_length=1, max_length=64)
    workspace_id: str | None = Field(default=None, min_length=1, max_length=128)
    workspace_name: str | None = Field(default=None, min_length=1, max_length=256)
    callback_url: str | None = Field(default=None, min_length=1, max_length=2048)
    run_url: str | None = Field(default=None, min_length=1, max_length=2048)
    project_id: str = Field(default="default", min_length=1, max_length=128)
    environment: str = Field(default="nonprod", min_length=1, max_length=32)
    action: str = Field(default="terraform.apply", min_length=1, max_length=64)
    resource_reference: str = Field(..., min_length=1, max_length=512)
    estimated_monthly_delta_usd: Decimal = Field(..., ge=0)
    estimated_hourly_delta_usd: Decimal = Field(default=Decimal("0"), ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=4, max_length=128)
    expected_request_fingerprint: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )
    dry_run: bool = Field(default=False)


class TerraformPreflightBinding(BaseModel):
    expected_source: EnforcementSource
    expected_project_id: str
    expected_environment: str
    expected_request_fingerprint: str
    expected_resource_reference: str


class TerraformPreflightContinuation(BaseModel):
    approval_consume_endpoint: str
    binding: TerraformPreflightBinding


class TerraformPreflightResponse(BaseModel):
    run_id: str
    stage: str
    decision: str
    reason_codes: list[str]
    decision_id: UUID
    policy_version: int
    approval_required: bool
    approval_request_id: UUID | None = None
    approval_token_contract: Literal["approval_flow_only"] = "approval_flow_only"
    ttl_seconds: int
    request_fingerprint: str
    reservation_active: bool
    computed_context: dict[str, Any] | None = None
    continuation: TerraformPreflightContinuation


class K8sAdmissionReviewKind(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group: str = Field(default="")
    version: str = Field(default="v1")
    kind: str = Field(..., min_length=1, max_length=128)


class K8sAdmissionReviewResource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    group: str = Field(default="")
    version: str = Field(default="v1")
    resource: str = Field(..., min_length=1, max_length=128)


class K8sAdmissionReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    uid: str = Field(..., min_length=1, max_length=256)
    kind: K8sAdmissionReviewKind
    resource: K8sAdmissionReviewResource
    sub_resource: str | None = Field(default=None, alias="subResource", max_length=128)
    request_kind: K8sAdmissionReviewKind | None = Field(
        default=None,
        alias="requestKind",
    )
    request_resource: K8sAdmissionReviewResource | None = Field(
        default=None,
        alias="requestResource",
    )
    request_sub_resource: str | None = Field(
        default=None,
        alias="requestSubResource",
        max_length=128,
    )
    name: str | None = Field(default=None, max_length=256)
    namespace: str | None = Field(default=None, max_length=256)
    operation: Literal["CREATE", "UPDATE", "DELETE", "CONNECT"]
    user_info: dict[str, Any] = Field(default_factory=dict, alias="userInfo")
    obj: dict[str, Any] | None = Field(default=None, alias="object")
    old_object: dict[str, Any] | None = Field(default=None, alias="oldObject")
    dry_run: bool | None = Field(default=None, alias="dryRun")
    options: dict[str, Any] | None = None


class K8sAdmissionReviewPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    api_version: str = Field(default="admission.k8s.io/v1", alias="apiVersion")
    kind: str = Field(default="AdmissionReview", min_length=1, max_length=64)
    request: K8sAdmissionReviewRequest


class K8sAdmissionReviewStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: int | None = None
    reason: str | None = None
    message: str | None = None


class K8sAdmissionReviewResult(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    uid: str
    allowed: bool
    status: K8sAdmissionReviewStatus | None = None
    warnings: list[str] = Field(default_factory=list)
    audit_annotations: dict[str, str] = Field(default_factory=dict, alias="auditAnnotations")


class K8sAdmissionReviewResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    api_version: str = Field(default="admission.k8s.io/v1", alias="apiVersion")
    kind: str = Field(default="AdmissionReview", min_length=1, max_length=64)
    response: K8sAdmissionReviewResult


class CloudEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="allow")

    specversion: Literal["1.0"] = "1.0"
    id: str = Field(..., min_length=1, max_length=256)
    source: str = Field(..., min_length=1, max_length=1024)
    type: str = Field(..., min_length=1, max_length=512)
    subject: str | None = Field(default=None, max_length=1024)
    time: datetime | None = None
    datacontenttype: str | None = Field(default=None, max_length=256)
    dataschema: str | None = Field(default=None, max_length=2048)
    data: Any = None


class CloudEventGateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cloud_event: CloudEventEnvelope
    project_id: str = Field(default="default", min_length=1, max_length=128)
    environment: str = Field(default="nonprod", min_length=1, max_length=32)
    action: str = Field(default="cloud_event.observe", min_length=1, max_length=64)
    resource_reference: str | None = Field(default=None, min_length=1, max_length=512)
    estimated_monthly_delta_usd: Decimal = Field(default=Decimal("0"), ge=0)
    estimated_hourly_delta_usd: Decimal = Field(default=Decimal("0"), ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=4, max_length=128)
    expected_request_fingerprint: str | None = Field(
        default=None,
        min_length=64,
        max_length=64,
    )
    dry_run: bool = Field(default=False)


__all__ = [
    "GateRequest",
    "GateDecisionResponse",
    "TerraformPreflightRequest",
    "TerraformPreflightBinding",
    "TerraformPreflightContinuation",
    "TerraformPreflightResponse",
    "K8sAdmissionReviewKind",
    "K8sAdmissionReviewResource",
    "K8sAdmissionReviewRequest",
    "K8sAdmissionReviewPayload",
    "K8sAdmissionReviewStatus",
    "K8sAdmissionReviewResult",
    "K8sAdmissionReviewResponse",
    "CloudEventEnvelope",
    "CloudEventGateRequest",
]
