"""add tenant growth funnel snapshots

Revision ID: r3s4t5u6v7w8
Revises: q2r3s4t5u6v7
Create Date: 2026-03-10 08:45:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "r3s4t5u6v7w8"
down_revision: Union[str, Sequence[str], None] = "q2r3s4t5u6v7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "tenant_growth_funnel_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("utm_source", sa.String(length=96), nullable=True),
        sa.Column("utm_medium", sa.String(length=96), nullable=True),
        sa.Column("utm_campaign", sa.String(length=96), nullable=True),
        sa.Column("utm_term", sa.String(length=96), nullable=True),
        sa.Column("utm_content", sa.String(length=96), nullable=True),
        sa.Column("persona", sa.String(length=64), nullable=True),
        sa.Column("acquisition_intent", sa.String(length=64), nullable=True),
        sa.Column("first_path", sa.String(length=256), nullable=True),
        sa.Column("first_touch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_touch_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_tier", sa.String(length=20), nullable=False),
        sa.Column("tenant_onboarded_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "first_connection_verified_at", sa.DateTime(timezone=True), nullable=True
        ),
        sa.Column("first_connection_provider", sa.String(length=32), nullable=True),
        sa.Column("pricing_viewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("checkout_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_value_activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("first_value_source", sa.String(length=64), nullable=True),
        sa.Column("pql_qualified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["tenant_id"], ["tenants.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", name="uq_tenant_growth_funnel_snapshot_tenant"
        ),
    )
    op.create_index(
        op.f("ix_tenant_growth_funnel_snapshots_tenant_id"),
        "tenant_growth_funnel_snapshots",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_growth_funnel_snapshots_utm_campaign"),
        "tenant_growth_funnel_snapshots",
        ["utm_campaign"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_growth_funnel_snapshots_utm_medium"),
        "tenant_growth_funnel_snapshots",
        ["utm_medium"],
        unique=False,
    )
    op.create_index(
        op.f("ix_tenant_growth_funnel_snapshots_utm_source"),
        "tenant_growth_funnel_snapshots",
        ["utm_source"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_tenant_growth_funnel_snapshots_utm_source"),
        table_name="tenant_growth_funnel_snapshots",
    )
    op.drop_index(
        op.f("ix_tenant_growth_funnel_snapshots_utm_medium"),
        table_name="tenant_growth_funnel_snapshots",
    )
    op.drop_index(
        op.f("ix_tenant_growth_funnel_snapshots_utm_campaign"),
        table_name="tenant_growth_funnel_snapshots",
    )
    op.drop_index(
        op.f("ix_tenant_growth_funnel_snapshots_tenant_id"),
        table_name="tenant_growth_funnel_snapshots",
    )
    op.drop_table("tenant_growth_funnel_snapshots")
