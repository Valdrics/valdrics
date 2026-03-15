"""add subscription billing cycle

Revision ID: u7v8w9x0y1z
Revises: t6u7v8w9x0y
Create Date: 2026-03-15 20:45:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "u7v8w9x0y1z"
down_revision: str | Sequence[str] | None = "t6u7v8w9x0y"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenant_subscriptions",
        sa.Column(
            "billing_cycle",
            sa.String(length=20),
            nullable=False,
            server_default="monthly",
        ),
    )
    op.alter_column("tenant_subscriptions", "billing_cycle", server_default=None)


def downgrade() -> None:
    op.drop_column("tenant_subscriptions", "billing_cycle")
