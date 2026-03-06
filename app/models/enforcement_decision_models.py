from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum as SQLEnum,
    event,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid as PG_UUID,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.enforcement_common import (
    _EMPTY_POLICY_DOCUMENT_SHA256,
    _POLICY_DOCUMENT_SCHEMA_VERSION,
    _utcnow,
    EnforcementApprovalStatus,
    EnforcementDecisionType,
    EnforcementSource,
)
from app.shared.db.base import Base


class EnforcementDecision(Base):
    __tablename__ = "enforcement_decisions"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source",
            "idempotency_key",
            name="uq_enforcement_decision_idempotency",
        ),
        Index("ix_enforcement_decision_tenant_created", "tenant_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source: Mapped[EnforcementSource] = mapped_column(
        SQLEnum(EnforcementSource, name="enforcement_source", native_enum=False),
        nullable=False,
        index=True,
    )
    environment: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    decision: Mapped[EnforcementDecisionType] = mapped_column(
        SQLEnum(
            EnforcementDecisionType,
            name="enforcement_decision_type",
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )
    reason_codes: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=list
    )
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_document_schema_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=_POLICY_DOCUMENT_SCHEMA_VERSION,
    )
    policy_document_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=_EMPTY_POLICY_DOCUMENT_SHA256,
    )
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    request_payload: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
    response_payload: Mapped[dict[str, Any] | None] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    estimated_monthly_delta_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False
    )
    estimated_hourly_delta_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 6), nullable=False, default=Decimal("0")
    )
    burn_rate_daily_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    forecast_eom_usd: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    risk_class: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anomaly_signal: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    allocation_available_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    credits_available_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4), nullable=True
    )
    reserved_allocation_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    reserved_credit_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    reservation_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_token_issued: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow, index=True
    )


class EnforcementDecisionLedger(Base):
    __tablename__ = "enforcement_decision_ledger"
    __table_args__ = (
        Index(
            "ix_enforcement_decision_ledger_tenant_recorded",
            "tenant_id",
            "recorded_at",
        ),
        Index(
            "ix_enforcement_decision_ledger_decision",
            "decision_id",
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
    source: Mapped[EnforcementSource] = mapped_column(
        SQLEnum(
            EnforcementSource,
            name="enforcement_source",
            native_enum=False,
        ),
        nullable=False,
        index=True,
    )
    environment: Mapped[str] = mapped_column(String(32), nullable=False)
    project_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    resource_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    decision: Mapped[EnforcementDecisionType] = mapped_column(
        SQLEnum(
            EnforcementDecisionType,
            name="enforcement_decision_type",
            native_enum=False,
        ),
        nullable=False,
    )
    reason_codes: Mapped[list[str]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False)
    policy_document_schema_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=_POLICY_DOCUMENT_SCHEMA_VERSION,
    )
    policy_document_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=_EMPTY_POLICY_DOCUMENT_SHA256,
    )
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    estimated_monthly_delta_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
    )
    estimated_hourly_delta_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 6),
        nullable=False,
    )
    burn_rate_daily_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4),
        nullable=True,
    )
    forecast_eom_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4),
        nullable=True,
    )
    risk_class: Mapped[str | None] = mapped_column(
        String(32),
        nullable=True,
    )
    risk_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    anomaly_signal: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
    )
    reserved_total_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4),
        nullable=False,
        default=Decimal("0"),
    )
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approval_request_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(),
        ForeignKey("enforcement_approval_requests.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approval_status: Mapped[EnforcementApprovalStatus | None] = mapped_column(
        SQLEnum(
            EnforcementApprovalStatus,
            name="enforcement_approval_status",
            native_enum=False,
        ),
        nullable=True,
    )
    request_payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    response_payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(), nullable=True)
    decision_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        index=True,
    )


@event.listens_for(EnforcementDecisionLedger, "before_update")
def _enforcement_decision_ledger_prevent_update(*_: object) -> None:
    raise ValueError("EnforcementDecisionLedger is append-only and immutable.")


@event.listens_for(EnforcementDecisionLedger, "before_delete")
def _enforcement_decision_ledger_prevent_delete(*_: object) -> None:
    raise ValueError("EnforcementDecisionLedger is append-only and immutable.")


__all__ = [
    "EnforcementDecision",
    "EnforcementDecisionLedger",
]
