from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CostRecord


async def get_governance_report(
    db: AsyncSession, tenant_id: UUID, start_date: date, end_date: date
) -> dict[str, float | int | str | None | dict[str, object]]:
    """
    Detects untagged and unallocated costs.
    Flags customers if untagged cost > 10%.
    """
    stmt = select(
        func.sum(CostRecord.cost_usd).label("total_untagged_cost"),
        func.count(CostRecord.id).label("untagged_count"),
    ).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
        (CostRecord.allocated_to.is_(None)) | (CostRecord.allocated_to == "Unallocated"),
    )

    total_stmt = select(func.sum(CostRecord.cost_usd)).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
    )

    total_res = await db.execute(total_stmt)
    total_cost = total_res.scalar() or Decimal("0.01")

    result = await db.execute(stmt)
    row = result.one()

    untagged_cost = row.total_untagged_cost or Decimal(0)
    untagged_percent = (untagged_cost / total_cost) * 100

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

