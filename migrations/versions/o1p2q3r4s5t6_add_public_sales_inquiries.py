"""Add persisted public sales inquiries.

Revision ID: o1p2q3r4s5t6
Revises: n0p1q2r3s4t5
Create Date: 2026-03-09
"""

from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


revision = "o1p2q3r4s5t6"
down_revision = "n0p1q2r3s4t5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "public_sales_inquiries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "name",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=False,
        ),
        sa.Column(
            "email",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=False,
        ),
        sa.Column(
            "company",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=False,
        ),
        sa.Column(
            "role",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=True,
        ),
        sa.Column(
            "deployment_scope",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=True,
        ),
        sa.Column(
            "message",
            sqlalchemy_utils.types.encrypted.encrypted_type.StringEncryptedType(),
            nullable=True,
        ),
        sa.Column("email_hash", sa.String(length=64), nullable=False),
        sa.Column("inquiry_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("team_size", sa.String(length=32), nullable=True),
        sa.Column("timeline", sa.String(length=32), nullable=True),
        sa.Column("interest_area", sa.String(length=64), nullable=True),
        sa.Column("referrer", sa.String(length=200), nullable=True),
        sa.Column("source", sa.String(length=120), nullable=True),
        sa.Column("utm_source", sa.String(length=120), nullable=True),
        sa.Column("utm_medium", sa.String(length=120), nullable=True),
        sa.Column("utm_campaign", sa.String(length=120), nullable=True),
        sa.Column(
            "delivery_status",
            sa.String(length=24),
            nullable=False,
            server_default=sa.text("'pending'"),
        ),
        sa.Column(
            "delivery_attempts",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_delivery_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_public_sales_inquiries_email_hash"),
        "public_sales_inquiries",
        ["email_hash"],
        unique=False,
    )
    op.create_index(
        op.f("ix_public_sales_inquiries_inquiry_fingerprint"),
        "public_sales_inquiries",
        ["inquiry_fingerprint"],
        unique=False,
    )
    op.create_index(
        op.f("ix_public_sales_inquiries_delivery_status"),
        "public_sales_inquiries",
        ["delivery_status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_public_sales_inquiries_created_at"),
        "public_sales_inquiries",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_public_sales_inquiries_created_at"),
        table_name="public_sales_inquiries",
    )
    op.drop_index(
        op.f("ix_public_sales_inquiries_delivery_status"),
        table_name="public_sales_inquiries",
    )
    op.drop_index(
        op.f("ix_public_sales_inquiries_inquiry_fingerprint"),
        table_name="public_sales_inquiries",
    )
    op.drop_index(
        op.f("ix_public_sales_inquiries_email_hash"),
        table_name="public_sales_inquiries",
    )
    op.drop_table("public_sales_inquiries")
