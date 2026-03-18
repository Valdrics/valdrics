"""add optimization findings and request binding

Revision ID: v8w9x0y1z2a
Revises: u7v8w9x0y1z
Create Date: 2026-03-17 14:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "v8w9x0y1z2a"
down_revision: str | Sequence[str] | None = "u7v8w9x0y1z"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


finding_source_enum = sa.Enum("ZOMBIE_SCAN", name="findingsource")
finding_status_enum = sa.Enum("OPEN", "RESOLVED", name="findingstatus")


def upgrade() -> None:
    finding_source_enum.create(op.get_bind(), checkfirst=True)
    finding_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "optimization_findings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("source", finding_source_enum, nullable=False, server_default="ZOMBIE_SCAN"),
        sa.Column("status", finding_status_enum, nullable=False, server_default="OPEN"),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=20), nullable=False),
        sa.Column("category", sa.String(length=100), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("connection_name", sa.String(length=255), nullable=True),
        sa.Column("resource_id", sa.String(length=255), nullable=False),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("region", sa.String(length=64), nullable=False, server_default="global"),
        sa.Column("estimated_monthly_savings", sa.Numeric(12, 2), nullable=True),
        sa.Column("confidence_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("explainability_notes", sa.String(length=2000), nullable=True),
        sa.Column("requires_manual_review", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("automated_action_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("decision_gate", sa.String(length=64), nullable=True),
        sa.Column(
            "payload",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_detected_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "fingerprint", name="uix_optimization_findings_tenant_fingerprint"),
    )
    op.create_index(
        "ix_optimization_findings_tenant_status_last_detected",
        "optimization_findings",
        ["tenant_id", "status", "last_detected_at"],
        unique=False,
    )
    op.create_index(
        "ix_optimization_findings_tenant_connection_region",
        "optimization_findings",
        ["tenant_id", "connection_id", "region"],
        unique=False,
    )
    op.create_index(op.f("ix_optimization_findings_tenant_id"), "optimization_findings", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_optimization_findings_source"), "optimization_findings", ["source"], unique=False)
    op.create_index(op.f("ix_optimization_findings_status"), "optimization_findings", ["status"], unique=False)
    op.create_index(op.f("ix_optimization_findings_provider"), "optimization_findings", ["provider"], unique=False)
    op.create_index(op.f("ix_optimization_findings_category"), "optimization_findings", ["category"], unique=False)
    op.create_index(op.f("ix_optimization_findings_connection_id"), "optimization_findings", ["connection_id"], unique=False)
    op.create_index(op.f("ix_optimization_findings_resource_id"), "optimization_findings", ["resource_id"], unique=False)
    op.create_index(op.f("ix_optimization_findings_last_detected_at"), "optimization_findings", ["last_detected_at"], unique=False)

    op.add_column(
        "remediation_requests",
        sa.Column("finding_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "remediation_requests",
        sa.Column(
            "finding_snapshot",
            sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
            nullable=True,
        ),
    )
    op.create_index(op.f("ix_remediation_requests_finding_id"), "remediation_requests", ["finding_id"], unique=False)
    op.create_index(
        "uix_remediation_requests_open_finding_action",
        "remediation_requests",
        ["tenant_id", "finding_id", "action"],
        unique=True,
        sqlite_where=sa.text(
            "finding_id IS NOT NULL AND status IN "
            "('PENDING', 'PENDING_APPROVAL', 'APPROVED', 'SCHEDULED', 'EXECUTING')"
        ),
        postgresql_where=sa.text(
            "finding_id IS NOT NULL AND status IN "
            "('PENDING', 'PENDING_APPROVAL', 'APPROVED', 'SCHEDULED', 'EXECUTING')"
        ),
    )
    op.create_foreign_key(
        "fk_remediation_requests_finding_id_optimization_findings",
        "remediation_requests",
        "optimization_findings",
        ["finding_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.add_column(
        "realized_savings_events",
        sa.Column("finding_id", sa.Uuid(), nullable=True),
    )
    op.add_column(
        "realized_savings_events",
        sa.Column("finding_category", sa.String(length=100), nullable=True),
    )
    op.create_index(op.f("ix_realized_savings_events_finding_id"), "realized_savings_events", ["finding_id"], unique=False)
    op.create_index(op.f("ix_realized_savings_events_finding_category"), "realized_savings_events", ["finding_category"], unique=False)
    op.create_foreign_key(
        "fk_realized_savings_events_finding_id_optimization_findings",
        "realized_savings_events",
        "optimization_findings",
        ["finding_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.alter_column("optimization_findings", "source", server_default=None)
    op.alter_column("optimization_findings", "status", server_default=None)
    op.alter_column("optimization_findings", "region", server_default=None)
    op.alter_column("optimization_findings", "requires_manual_review", server_default=None)
    op.alter_column("optimization_findings", "automated_action_allowed", server_default=None)
    op.alter_column("optimization_findings", "payload", server_default=None)


def downgrade() -> None:
    op.drop_constraint(
        "fk_realized_savings_events_finding_id_optimization_findings",
        "realized_savings_events",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_realized_savings_events_finding_category"), table_name="realized_savings_events")
    op.drop_index(op.f("ix_realized_savings_events_finding_id"), table_name="realized_savings_events")
    op.drop_column("realized_savings_events", "finding_category")
    op.drop_column("realized_savings_events", "finding_id")

    op.drop_constraint(
        "fk_remediation_requests_finding_id_optimization_findings",
        "remediation_requests",
        type_="foreignkey",
    )
    op.drop_index(
        "uix_remediation_requests_open_finding_action",
        table_name="remediation_requests",
    )
    op.drop_index(op.f("ix_remediation_requests_finding_id"), table_name="remediation_requests")
    op.drop_column("remediation_requests", "finding_snapshot")
    op.drop_column("remediation_requests", "finding_id")

    op.drop_index(op.f("ix_optimization_findings_last_detected_at"), table_name="optimization_findings")
    op.drop_index(op.f("ix_optimization_findings_resource_id"), table_name="optimization_findings")
    op.drop_index(op.f("ix_optimization_findings_connection_id"), table_name="optimization_findings")
    op.drop_index(op.f("ix_optimization_findings_category"), table_name="optimization_findings")
    op.drop_index(op.f("ix_optimization_findings_provider"), table_name="optimization_findings")
    op.drop_index(op.f("ix_optimization_findings_status"), table_name="optimization_findings")
    op.drop_index(op.f("ix_optimization_findings_source"), table_name="optimization_findings")
    op.drop_index(op.f("ix_optimization_findings_tenant_id"), table_name="optimization_findings")
    op.drop_index("ix_optimization_findings_tenant_connection_region", table_name="optimization_findings")
    op.drop_index("ix_optimization_findings_tenant_status_last_detected", table_name="optimization_findings")
    op.drop_table("optimization_findings")

    finding_status_enum.drop(op.get_bind(), checkfirst=True)
    finding_source_enum.drop(op.get_bind(), checkfirst=True)
