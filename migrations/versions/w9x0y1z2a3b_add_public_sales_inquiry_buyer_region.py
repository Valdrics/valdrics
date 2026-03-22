"""add buyer region to public sales inquiries

Revision ID: w9x0y1z2a3b
Revises: v8w9x0y1z2a
Create Date: 2026-03-21 10:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "w9x0y1z2a3b"
down_revision: str | Sequence[str] | None = "v8w9x0y1z2a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "public_sales_inquiries",
        sa.Column("buyer_region", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("public_sales_inquiries", "buyer_region")
