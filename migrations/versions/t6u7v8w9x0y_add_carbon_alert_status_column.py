"""add carbon alert status column

Revision ID: t6u7v8w9x0y
Revises: s4t5u6v7w8x
Create Date: 2026-03-14 13:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "t6u7v8w9x0y"
down_revision: Union[str, Sequence[str], None] = "s4t5u6v7w8x"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "carbon_settings",
        sa.Column("last_alert_status", sa.String(length=32), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("carbon_settings", "last_alert_status")
