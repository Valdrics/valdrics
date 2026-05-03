"""Canonical allocation ledger SQL helpers.

`CostAllocation` is the source of truth for split allocation. `CostRecord`
remains the origin-charge ledger row.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select

from app.models.attribution import CostAllocation
from app.models.cloud import CloudAccount, CostRecord


def cost_allocation_rollup_subquery(
    *,
    tenant_id: UUID | None = None,
    start_date: Any = None,
    end_date: Any = None,
    provider: str | None = None,
    include_preliminary: bool = True,
) -> Any:
    allocated_amount = func.sum(
        case(
            (
                func.lower(CostAllocation.allocated_to) != "unallocated",
                CostAllocation.amount,
            ),
            else_=Decimal("0"),
        )
    )
    stmt = (
        select(
            CostAllocation.cost_record_id.label("cost_record_id"),
            CostAllocation.recorded_at.label("recorded_at"),
            allocated_amount.label("allocated_amount"),
            func.count(CostAllocation.id).label("allocation_count"),
        )
        .join(
            CostRecord,
            (CostAllocation.cost_record_id == CostRecord.id)
            & (CostAllocation.recorded_at == CostRecord.recorded_at),
        )
        .group_by(CostAllocation.cost_record_id, CostAllocation.recorded_at)
    )
    if tenant_id is not None:
        stmt = stmt.where(CostRecord.tenant_id == tenant_id)
    if start_date is not None:
        stmt = stmt.where(CostRecord.recorded_at >= start_date)
    if end_date is not None:
        stmt = stmt.where(CostRecord.recorded_at <= end_date)
    if not include_preliminary:
        stmt = stmt.where(CostRecord.cost_status == "FINAL")
    if provider:
        stmt = stmt.join(CloudAccount, CostRecord.account_id == CloudAccount.id).where(
            CloudAccount.provider == provider
        )
    return stmt.subquery()


def unallocated_amount_expr(
    *,
    origin_amount: Any,
    allocated_amount: Any,
    allocation_count: Any,
) -> Any:
    zero = Decimal("0")
    remaining = origin_amount - func.coalesce(allocated_amount, zero)
    return case(
        (func.coalesce(allocation_count, 0) == 0, origin_amount),
        (remaining < zero, zero),
        else_=remaining,
    )


__all__ = ["cost_allocation_rollup_subquery", "unallocated_amount_expr"]
