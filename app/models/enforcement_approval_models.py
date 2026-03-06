from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    Uuid as PG_UUID,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.enforcement_common import (
    _utcnow,
    EnforcementActionStatus,
    EnforcementApprovalStatus,
)
from app.shared.db.base import Base


class EnforcementApprovalRequest(Base):
    __tablename__ = "enforcement_approval_requests"
    __table_args__ = (
        UniqueConstraint("decision_id", name="uq_enforcement_approval_decision"),
        Index("ix_enforcement_approval_status_expires", "status", "expires_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision_id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        ForeignKey("enforcement_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[EnforcementApprovalStatus] = mapped_column(
        SQLEnum(
            EnforcementApprovalStatus,
            name="enforcement_approval_status",
            native_enum=False,
        ),
        nullable=False,
        default=EnforcementApprovalStatus.PENDING,
        index=True,
    )
    requested_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(), nullable=True)
    reviewed_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(), nullable=True)
    review_notes: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    routing_rule_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    routing_trace: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    approval_token_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approval_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    approval_token_consumed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    denied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class EnforcementActionExecution(Base):
    __tablename__ = "enforcement_action_executions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "decision_id",
            "action_type",
            "idempotency_key",
            name="uq_enforcement_action_idempotency",
        ),
        Index(
            "ix_enforcement_action_retry_queue",
            "tenant_id",
            "status",
            "next_retry_at",
        ),
        Index(
            "ix_enforcement_action_decision_created",
            "decision_id",
            "created_at",
        ),
        CheckConstraint(
            "max_attempts >= 1",
            name="ck_enforcement_action_max_attempts_ge_1",
        ),
        CheckConstraint(
            "attempt_count >= 0",
            name="ck_enforcement_action_attempt_count_ge_0",
        ),
        CheckConstraint(
            "attempt_count <= max_attempts",
            name="ck_enforcement_action_attempt_count_lte_max",
        ),
        CheckConstraint(
            "retry_backoff_seconds >= 1 AND retry_backoff_seconds <= 86400",
            name="ck_enforcement_action_retry_backoff_bounds",
        ),
        CheckConstraint(
            "lease_ttl_seconds >= 30 AND lease_ttl_seconds <= 3600",
            name="ck_enforcement_action_lease_ttl_bounds",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    decision_id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        ForeignKey("enforcement_decisions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    approval_request_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(),
        ForeignKey("enforcement_approval_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    request_payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[EnforcementActionStatus] = mapped_column(
        SQLEnum(
            EnforcementActionStatus,
            name="enforcement_action_status",
            native_enum=False,
        ),
        nullable=False,
        default=EnforcementActionStatus.QUEUED,
        index=True,
    )
    attempt_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    retry_backoff_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=60)
    lease_ttl_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=300)
    next_retry_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )
    locked_by_worker_id: Mapped[UUID | None] = mapped_column(PG_UUID(), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    last_error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    result_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=True,
    )
    result_payload_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


__all__ = [
    "EnforcementApprovalRequest",
    "EnforcementActionExecution",
]
