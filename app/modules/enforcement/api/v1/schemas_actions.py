from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enforcement import EnforcementActionStatus


class ActionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: UUID
    action_type: str = Field(..., min_length=1, max_length=64)
    target_reference: str = Field(..., min_length=1, max_length=512)
    request_payload: dict[str, Any] = Field(default_factory=dict)
    idempotency_key: str | None = Field(default=None, min_length=4, max_length=128)
    max_attempts: int | None = Field(default=None, ge=1, le=10)
    retry_backoff_seconds: int | None = Field(default=None, ge=1, le=86400)
    lease_ttl_seconds: int | None = Field(default=None, ge=30, le=3600)


class ActionListQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: EnforcementActionStatus | None = None
    decision_id: UUID | None = None
    limit: int = Field(default=100, ge=1, le=500)


class ActionLeaseRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action_type: str | None = Field(default=None, min_length=1, max_length=64)


class ActionCompleteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    result_payload: dict[str, Any] = Field(default_factory=dict)


class ActionFailRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error_code: str = Field(..., min_length=1, max_length=64)
    error_message: str = Field(..., min_length=1, max_length=1000)
    retryable: bool = Field(default=True)
    result_payload: dict[str, Any] = Field(default_factory=dict)


class ActionCancelRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(default=None, max_length=1000)


class ActionExecutionResponse(BaseModel):
    action_id: UUID
    decision_id: UUID
    approval_request_id: UUID | None = None
    action_type: str
    target_reference: str
    idempotency_key: str
    request_payload: dict[str, Any]
    request_payload_sha256: str
    status: EnforcementActionStatus
    attempt_count: int
    max_attempts: int
    retry_backoff_seconds: int
    lease_ttl_seconds: int
    next_retry_at: datetime
    locked_by_worker_id: UUID | None = None
    lease_expires_at: datetime | None = None
    last_error_code: str | None = None
    last_error_message: str | None = None
    result_payload: dict[str, Any] | None = None
    result_payload_sha256: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


__all__ = [
    "ActionCreateRequest",
    "ActionListQuery",
    "ActionLeaseRequest",
    "ActionCompleteRequest",
    "ActionFailRequest",
    "ActionCancelRequest",
    "ActionExecutionResponse",
]
