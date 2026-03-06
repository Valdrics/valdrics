from __future__ import annotations

from datetime import date, datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.db.base import Base


class LandingTelemetryDailyRollup(Base):
    """
    Daily rollup for anonymous landing telemetry, keyed by campaign and event dimensions.

    Design:
    - Stores only aggregate counters (no raw PII payload replay).
    - Uses a unique dimensional key for deterministic upsert increments.
    """

    __tablename__ = "landing_telemetry_daily_rollups"
    __table_args__ = (
        UniqueConstraint(
            "event_date",
            "event_name",
            "section",
            "funnel_stage",
            "utm_source",
            "utm_medium",
            "utm_campaign",
            name="uq_landing_telemetry_daily_rollup_dims",
        ),
    )

    id: Mapped[UUID] = mapped_column(PG_UUID(), primary_key=True, default=uuid4)
    event_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    event_name: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    section: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    funnel_stage: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    utm_source: Mapped[str] = mapped_column(String(96), nullable=False, default="", index=True)
    utm_medium: Mapped[str] = mapped_column(String(96), nullable=False, default="", index=True)
    utm_campaign: Mapped[str] = mapped_column(
        String(96), nullable=False, default="", index=True
    )
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
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
