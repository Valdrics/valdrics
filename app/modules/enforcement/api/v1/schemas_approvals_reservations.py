from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enforcement import EnforcementSource


class ApprovalCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: UUID
    notes: str | None = Field(default=None, max_length=1000)


class ApprovalReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    notes: str | None = Field(default=None, max_length=1000)


class ApprovalTokenConsumeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approval_token: str = Field(..., min_length=32, max_length=8192)
    expected_source: EnforcementSource | None = None
    expected_project_id: str | None = Field(default=None, min_length=1, max_length=128)
    expected_environment: str | None = Field(default=None, min_length=1, max_length=32)
    expected_request_fingerprint: str | None = Field(
        default=None,
        min_length=32,
        max_length=64,
    )
    expected_resource_reference: str | None = Field(
        default=None,
        min_length=1,
        max_length=512,
    )


class ReservationReconcileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actual_monthly_delta_usd: Decimal = Field(..., ge=0)
    notes: str | None = Field(default=None, max_length=1000)
    idempotency_key: str | None = Field(default=None, min_length=4, max_length=128)


class ReservationReconcileOverdueRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    older_than_seconds: int | None = Field(default=None, ge=60, le=604800)
    limit: int = Field(default=200, ge=1, le=1000)


class ApprovalQueueItem(BaseModel):
    approval_id: UUID
    decision_id: UUID
    status: str
    source: str
    environment: str
    project_id: str
    action: str
    resource_reference: str
    estimated_monthly_delta_usd: Decimal
    reason_codes: list[str]
    routing_rule_id: str | None = None
    expires_at: datetime
    created_at: datetime


class ApprovalReviewResponse(BaseModel):
    status: str
    approval_id: UUID
    decision_id: UUID
    routing_rule_id: str | None = None
    approval_token: str | None = None
    token_expires_at: datetime | None = None


class ApprovalTokenConsumeResponse(BaseModel):
    status: str
    approval_id: UUID
    decision_id: UUID
    source: str
    environment: str
    project_id: str
    action: str
    resource_reference: str
    request_fingerprint: str
    max_monthly_delta_usd: Decimal
    max_hourly_delta_usd: Decimal
    token_expires_at: datetime
    consumed_at: datetime


class ActiveReservationItem(BaseModel):
    decision_id: UUID
    source: str
    environment: str
    project_id: str
    action: str
    resource_reference: str
    reason_codes: list[str]
    reserved_allocation_usd: Decimal
    reserved_credit_usd: Decimal
    reserved_total_usd: Decimal
    created_at: datetime
    age_seconds: int


class ReservationReconcileResponse(BaseModel):
    decision_id: UUID
    status: str
    released_reserved_usd: Decimal
    actual_monthly_delta_usd: Decimal
    drift_usd: Decimal
    reservation_active: bool
    reconciled_at: datetime


class ReservationReconcileOverdueResponse(BaseModel):
    released_count: int
    total_released_usd: Decimal
    decision_ids: list[UUID]
    older_than_seconds: int


class ReservationReconciliationExceptionItem(BaseModel):
    decision_id: UUID
    source: str
    environment: str
    project_id: str
    action: str
    resource_reference: str
    expected_reserved_usd: Decimal
    actual_monthly_delta_usd: Decimal
    drift_usd: Decimal
    status: str
    reconciled_at: datetime | None
    notes: str | None
    credit_settlement: list[dict[str, str]] = Field(default_factory=list)


__all__ = [
    "ApprovalCreateRequest",
    "ApprovalReviewRequest",
    "ApprovalTokenConsumeRequest",
    "ReservationReconcileRequest",
    "ReservationReconcileOverdueRequest",
    "ApprovalQueueItem",
    "ApprovalReviewResponse",
    "ApprovalTokenConsumeResponse",
    "ActiveReservationItem",
    "ReservationReconcileResponse",
    "ReservationReconcileOverdueResponse",
    "ReservationReconciliationExceptionItem",
]
