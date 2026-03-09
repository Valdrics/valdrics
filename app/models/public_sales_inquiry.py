"""Persisted public talk-to-sales inquiries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text, func, text, Uuid as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import AesEngine

from app.models._encryption import get_encryption_key
from app.shared.db.base import Base


class PublicSalesInquiry(Base):
    """Durable record for public sales-intake submissions."""

    __tablename__ = "public_sales_inquiries"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    name: Mapped[str] = mapped_column(
        StringEncryptedType(String(120), get_encryption_key, AesEngine, "pkcs5"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(
        StringEncryptedType(String(254), get_encryption_key, AesEngine, "pkcs5"),
        nullable=False,
    )
    company: Mapped[str] = mapped_column(
        StringEncryptedType(String(120), get_encryption_key, AesEngine, "pkcs5"),
        nullable=False,
    )
    role: Mapped[str | None] = mapped_column(
        StringEncryptedType(String(120), get_encryption_key, AesEngine, "pkcs5"),
        nullable=True,
    )
    deployment_scope: Mapped[str | None] = mapped_column(
        StringEncryptedType(String(200), get_encryption_key, AesEngine, "pkcs5"),
        nullable=True,
    )
    message: Mapped[str | None] = mapped_column(
        StringEncryptedType(Text, get_encryption_key, AesEngine, "pkcs5"),
        nullable=True,
    )
    email_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    inquiry_fingerprint: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    team_size: Mapped[str | None] = mapped_column(String(32), nullable=True)
    timeline: Mapped[str | None] = mapped_column(String(32), nullable=True)
    interest_area: Mapped[str | None] = mapped_column(String(64), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(200), nullable=True)
    source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(120), nullable=True)
    delivery_status: Mapped[str] = mapped_column(
        String(24), nullable=False, default="pending", index=True
    )
    delivery_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_delivery_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return (
            f"<PublicSalesInquiry id={self.id} "
            f"email_hash={self.email_hash[:12]} status={self.delivery_status}>"
        )
