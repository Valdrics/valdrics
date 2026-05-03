from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CostRecord
from app.modules.reporting.domain.allocation_ledger import (
    cost_allocation_rollup_subquery,
    unallocated_amount_expr,
)


async def get_governance_report(
    db: AsyncSession, tenant_id: UUID, start_date: date, end_date: date
) -> dict[str, float | int | str | None | dict[str, object]]:
    """
    Detects untagged and unallocated costs.
    Flags customers if untagged cost > 10%.
    """
    allocation_rollup = cost_allocation_rollup_subquery(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )
    unallocated_amount = unallocated_amount_expr(
        origin_amount=CostRecord.cost_usd,
        allocated_amount=allocation_rollup.c.allocated_amount,
        allocation_count=allocation_rollup.c.allocation_count,
    )
    stmt = (
        select(
            func.sum(unallocated_amount).label("total_untagged_cost"),
            func.sum(case((unallocated_amount > Decimal("0"), 1), else_=0)).label(
                "untagged_count"
            ),
        )
        .outerjoin(
            allocation_rollup,
            (allocation_rollup.c.cost_record_id == CostRecord.id)
            & (allocation_rollup.c.recorded_at == CostRecord.recorded_at),
        )
        .where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
        )
    )

    total_stmt = select(func.sum(CostRecord.cost_usd)).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
    )

    total_res = await db.execute(total_stmt)
    total_cost = total_res.scalar() or Decimal("0")

    result = await db.execute(stmt)
    row = result.one()

    untagged_cost = row.total_untagged_cost or Decimal(0)
    untagged_percent = (
        (untagged_cost / total_cost) * 100 if total_cost > 0 else Decimal("0")
    )

    from app.modules.reporting.domain.attribution_engine import AttributionEngine

    engine = AttributionEngine(db)
    insights = await engine.get_unallocated_analysis(tenant_id, start_date, end_date)

    return {
        "total_cost": float(total_cost),
        "unallocated_cost": float(untagged_cost),
        "unallocated_percentage": round(float(untagged_percent), 2),
        "resource_count": row.untagged_count,
        "insights": insights,
        "status": "warning" if untagged_percent > 10 else "healthy",
        "message": (
            "High unallocated spend detected (>10%)."
            if untagged_percent > 10
            else "Cost attribution is within healthy bounds."
        ),
        "recommendation": (
            "High unallocated spend detected. Implement attribution rules to improve visibility."
            if untagged_percent > 10
            else None
        ),
    }
