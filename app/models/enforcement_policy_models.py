from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum as SQLEnum,
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
    EnforcementCreditPoolType,
    EnforcementMode,
)
from app.shared.db.base import Base


class EnforcementPolicy(Base):
    __tablename__ = "enforcement_policies"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_enforcement_policy_tenant"),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    terraform_mode: Mapped[EnforcementMode] = mapped_column(
        SQLEnum(EnforcementMode, name="enforcement_mode", native_enum=False),
        nullable=False,
        default=EnforcementMode.SOFT,
    )
    terraform_mode_prod: Mapped[EnforcementMode] = mapped_column(
        SQLEnum(EnforcementMode, name="enforcement_mode", native_enum=False),
        nullable=False,
        default=EnforcementMode.SOFT,
    )
    terraform_mode_nonprod: Mapped[EnforcementMode] = mapped_column(
        SQLEnum(EnforcementMode, name="enforcement_mode", native_enum=False),
        nullable=False,
        default=EnforcementMode.SOFT,
    )
    k8s_admission_mode: Mapped[EnforcementMode] = mapped_column(
        SQLEnum(EnforcementMode, name="enforcement_mode", native_enum=False),
        nullable=False,
        default=EnforcementMode.SOFT,
    )
    k8s_admission_mode_prod: Mapped[EnforcementMode] = mapped_column(
        SQLEnum(EnforcementMode, name="enforcement_mode", native_enum=False),
        nullable=False,
        default=EnforcementMode.SOFT,
    )
    k8s_admission_mode_nonprod: Mapped[EnforcementMode] = mapped_column(
        SQLEnum(EnforcementMode, name="enforcement_mode", native_enum=False),
        nullable=False,
        default=EnforcementMode.SOFT,
    )
    require_approval_for_prod: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True
    )
    require_approval_for_nonprod: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    enforce_prod_requester_reviewer_separation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )
    enforce_nonprod_requester_reviewer_separation: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
    )
    approval_routing_rules: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
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
    policy_document: Mapped[dict[str, Any]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    plan_monthly_ceiling_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4),
        nullable=True,
    )
    enterprise_monthly_ceiling_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(14, 4),
        nullable=True,
    )
    auto_approve_below_monthly_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("25.0")
    )
    hard_deny_above_monthly_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("5000.0")
    )
    default_ttl_seconds: Mapped[int] = mapped_column(
        Integer, nullable=False, default=900
    )
    policy_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class EnforcementBudgetAllocation(Base):
    __tablename__ = "enforcement_budget_allocations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "scope_key",
            name="uq_enforcement_budget_scope",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scope_key: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    monthly_limit_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class EnforcementCreditGrant(Base):
    __tablename__ = "enforcement_credit_grants"
    __table_args__ = (
        Index(
            "ix_enforcement_credit_scope_active_expiry",
            "tenant_id",
            "scope_key",
            "active",
            "expires_at",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pool_type: Mapped[EnforcementCreditPoolType] = mapped_column(
        SQLEnum(
            EnforcementCreditPoolType,
            name="enforcement_credit_pool_type",
            native_enum=False,
        ),
        nullable=False,
        default=EnforcementCreditPoolType.RESERVED,
        index=True,
    )
    scope_key: Mapped[str] = mapped_column(String(128), nullable=False, default="default")
    total_amount_usd: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    remaining_amount_usd: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_user_id: Mapped[UUID | None] = mapped_column(PG_UUID(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )


class EnforcementCreditReservationAllocation(Base):
    __tablename__ = "enforcement_credit_reservation_allocations"
    __table_args__ = (
        UniqueConstraint(
            "decision_id",
            "credit_grant_id",
            name="uq_enforcement_credit_reservation_decision_grant",
        ),
        Index(
            "ix_enforcement_credit_reservation_tenant_active",
            "tenant_id",
            "active",
        ),
        CheckConstraint(
            "reserved_amount_usd > 0",
            name="ck_enforcement_credit_reservation_reserved_positive",
        ),
        CheckConstraint(
            "consumed_amount_usd >= 0",
            name="ck_enforcement_credit_reservation_consumed_non_negative",
        ),
        CheckConstraint(
            "released_amount_usd >= 0",
            name="ck_enforcement_credit_reservation_released_non_negative",
        ),
        CheckConstraint(
            "consumed_amount_usd + released_amount_usd <= reserved_amount_usd",
            name="ck_enf_credit_resv_settlement_lte_reserved",
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
    credit_grant_id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        ForeignKey("enforcement_credit_grants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    credit_pool_type: Mapped[EnforcementCreditPoolType] = mapped_column(
        SQLEnum(
            EnforcementCreditPoolType,
            name="enforcement_credit_pool_type",
            native_enum=False,
        ),
        nullable=False,
        default=EnforcementCreditPoolType.RESERVED,
        index=True,
    )
    reserved_amount_usd: Mapped[Decimal] = mapped_column(Numeric(14, 4), nullable=False)
    consumed_amount_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    released_amount_usd: Mapped[Decimal] = mapped_column(
        Numeric(14, 4), nullable=False, default=Decimal("0")
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
    )
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


__all__ = [
    "EnforcementPolicy",
    "EnforcementBudgetAllocation",
    "EnforcementCreditGrant",
    "EnforcementCreditReservationAllocation",
]
