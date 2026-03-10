from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, Uuid as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base


class TenantGrowthFunnelSnapshot(Base):
    """
    Authenticated tenant funnel milestones from signup through paid activation.

    One row is maintained per tenant. Stage timestamps are write-once milestones
    so conversion reporting stays deterministic under retries and duplicate events.
    """

    __tablename__ = "tenant_growth_funnel_snapshots"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_growth_funnel_snapshot_tenant"),
        {"extend_existing": True},
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(), primary_key=True, default=uuid4)
    tenant_id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    utm_source: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    utm_medium: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(96), nullable=True, index=True)
    utm_term: Mapped[str | None] = mapped_column(String(96), nullable=True)
    utm_content: Mapped[str | None] = mapped_column(String(96), nullable=True)
    persona: Mapped[str | None] = mapped_column(String(64), nullable=True)
    acquisition_intent: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_path: Mapped[str | None] = mapped_column(String(256), nullable=True)
    first_touch_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_touch_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    current_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="free")
    tenant_onboarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_connection_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_connection_provider: Mapped[str | None] = mapped_column(String(32), nullable=True)
    pricing_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    checkout_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_value_activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    first_value_source: Mapped[str | None] = mapped_column(String(64), nullable=True)
    pql_qualified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paid_activated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
