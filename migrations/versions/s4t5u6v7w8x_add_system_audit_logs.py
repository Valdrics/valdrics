"""add system audit logs table

Revision ID: s4t5u6v7w8x
Revises: r3s4t5u6v7w8
Create Date: 2026-03-10 13:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "s4t5u6v7w8x"
down_revision: Union[str, Sequence[str], None] = "r3s4t5u6v7w8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "system_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("event_timestamp", sa.DateTime(timezone=False), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_email", sa.String(length=255), nullable=True),
        sa.Column("actor_ip", sa.String(length=45), nullable=True),
        sa.Column("correlation_id", sa.String(length=36), nullable=True),
        sa.Column("request_method", sa.String(length=10), nullable=True),
        sa.Column("request_path", sa.String(length=500), nullable=True),
        sa.Column("resource_type", sa.String(length=50), nullable=True),
        sa.Column("resource_id", sa.String(length=255), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_system_audit_logs_actor_id"),
        "system_audit_logs",
        ["actor_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_audit_logs_correlation_id"),
        "system_audit_logs",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_audit_logs_event_timestamp"),
        "system_audit_logs",
        ["event_timestamp"],
        unique=False,
    )
    op.create_index(
        op.f("ix_system_audit_logs_event_type"),
        "system_audit_logs",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_system_audit_type_time",
        "system_audit_logs",
        ["event_type", "event_timestamp"],
        unique=False,
    )
    op.execute("ALTER TABLE system_audit_logs ENABLE ROW LEVEL SECURITY")
    op.execute(
        "DROP POLICY IF EXISTS system_audit_logs_system_context_policy ON system_audit_logs"
    )
    op.execute(
        """
        CREATE POLICY system_audit_logs_system_context_policy ON system_audit_logs
        USING (current_setting('app.is_system_context', TRUE) = 'true')
        WITH CHECK (current_setting('app.is_system_context', TRUE) = 'true')
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "DROP POLICY IF EXISTS system_audit_logs_system_context_policy ON system_audit_logs"
    )
    op.drop_index("ix_system_audit_type_time", table_name="system_audit_logs")
    op.drop_index(
        op.f("ix_system_audit_logs_event_type"), table_name="system_audit_logs"
    )
    op.drop_index(
        op.f("ix_system_audit_logs_event_timestamp"),
        table_name="system_audit_logs",
    )
    op.drop_index(
        op.f("ix_system_audit_logs_correlation_id"),
        table_name="system_audit_logs",
    )
    op.drop_index(
        op.f("ix_system_audit_logs_actor_id"), table_name="system_audit_logs"
    )
    op.drop_table("system_audit_logs")
