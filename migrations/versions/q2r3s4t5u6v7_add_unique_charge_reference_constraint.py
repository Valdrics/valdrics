"""add unique constraint for tenant subscription charge references

Revision ID: q2r3s4t5u6v7
Revises: o1p2q3r4s5t6
Create Date: 2026-03-09 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "q2r3s4t5u6v7"
down_revision: Union[str, Sequence[str], None] = "o1p2q3r4s5t6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "uq_tenant_subscriptions_last_charge_reference",
        "tenant_subscriptions",
        ["last_charge_reference"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_tenant_subscriptions_last_charge_reference",
        "tenant_subscriptions",
        type_="unique",
    )
