"""add spend ledger query indexes

Revision ID: x0y1z2a3b4c
Revises: w9x0y1z2a3b
Create Date: 2026-04-30 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "x0y1z2a3b4c"
down_revision: str | Sequence[str] | None = "w9x0y1z2a3b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_index(
        "ix_llm_usage_tenant_created_id",
        "llm_usage",
        ["tenant_id", "created_at", "id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_llm_usage_tenant_created_id", table_name="llm_usage")
