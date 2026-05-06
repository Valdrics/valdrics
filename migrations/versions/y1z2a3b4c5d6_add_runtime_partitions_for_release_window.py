"""add_runtime_partitions_for_release_window

Revision ID: y1z2a3b4c5d6
Revises: x0y1z2a3b4c
Create Date: 2026-05-06 03:10:00.000000

"""

from __future__ import annotations

from datetime import date
from typing import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "y1z2a3b4c5d6"
down_revision: str | Sequence[str] | None = "x0y1z2a3b4c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _add_months(value: date, months: int) -> date:
    month_index = (value.month - 1) + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    return date(year, month, 1)


def _table_is_partitioned(table_name: str) -> bool:
    bind = op.get_bind()
    return bool(
        bind.scalar(
            sa.text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_partitioned_table AS pt
                    JOIN pg_class AS cls ON cls.oid = pt.partrelid
                    JOIN pg_namespace AS ns ON ns.oid = cls.relnamespace
                    WHERE cls.relname = :table_name
                      AND ns.nspname = current_schema()
                )
                """
            ),
            {"table_name": table_name},
        )
    )


def _create_monthly_partitions(
    *,
    table_name: str,
    name_prefix: str,
    start_month: date,
    months: int,
) -> None:
    if not _table_is_partitioned(table_name):
        return

    for offset in range(months):
        start = _add_months(start_month, offset)
        end = _add_months(start, 1)
        partition_name = f"{name_prefix}{start.year}_{start.month:02d}"
        op.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {partition_name}
            PARTITION OF {table_name}
            FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}')
            """
        )
        op.execute(f"ALTER TABLE {partition_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {partition_name} FORCE ROW LEVEL SECURITY")


def upgrade() -> None:
    """Create runtime partitions that cover the managed launch window."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    start_month = date(2026, 5, 1)
    months_to_create = 24
    _create_monthly_partitions(
        table_name="audit_logs",
        name_prefix="audit_logs_p",
        start_month=start_month,
        months=months_to_create,
    )
    _create_monthly_partitions(
        table_name="cost_records",
        name_prefix="cost_records_",
        start_month=start_month,
        months=months_to_create,
    )


def downgrade() -> None:
    """Drop the launch-window partitions created by this migration."""
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    start_month = date(2026, 5, 1)
    months_to_drop = 24
    for offset in reversed(range(months_to_drop)):
        month = _add_months(start_month, offset)
        op.execute(f"DROP TABLE IF EXISTS audit_logs_p{month.year}_{month.month:02d}")
        op.execute(f"DROP TABLE IF EXISTS cost_records_{month.year}_{month.month:02d}")
