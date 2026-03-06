from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CostRecord


async def count_records(
    db: AsyncSession, tenant_id: UUID, start_date: date, end_date: date
) -> int:
    """Quickly counts records without fetching data."""
    stmt = select(func.count(CostRecord.id)).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
    )
    result = await db.execute(stmt)
    return result.scalar() or 0


async def get_data_freshness(
    db: AsyncSession, tenant_id: UUID, start_date: date, end_date: date
) -> dict[str, Any]:
    """Returns data freshness indicators for the dashboard."""
    stmt = select(
        func.count(CostRecord.id).label("total_records"),
        func.count(CostRecord.id)
        .filter(CostRecord.cost_status == "PRELIMINARY")
        .label("preliminary_count"),
        func.count(CostRecord.id)
        .filter(CostRecord.cost_status == "FINAL")
        .label("final_count"),
        func.max(CostRecord.recorded_at).label("latest_record_date"),
    ).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
    )

    result = await db.execute(stmt)
    row = result.one_or_none()

    if not row or row.total_records == 0:
        return {
            "status": "no_data",
            "total_records": 0,
            "preliminary_records": 0,
            "final_records": 0,
            "freshness_percentage": 0,
            "latest_record_date": None,
            "message": "No cost data available for the selected range.",
        }

    final_pct = (
        (row.final_count / row.total_records * 100) if row.total_records > 0 else 0
    )

    if row.preliminary_count == 0:
        status = "final"
        message = "All cost data is finalized."
    elif row.preliminary_count > row.total_records * 0.5:
        status = "preliminary"
        message = (
            "More than 50% of data is preliminary and may be restated within 48 hours."
        )
    else:
        status = "mixed"
        message = f"{row.preliminary_count} records are still preliminary."

    return {
        "status": status,
        "total_records": row.total_records,
        "preliminary_records": row.preliminary_count,
        "final_records": row.final_count,
        "freshness_percentage": round(final_pct, 2),
        "latest_record_date": row.latest_record_date.isoformat()
        if row.latest_record_date
        else None,
        "message": message,
    }

