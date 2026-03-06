from datetime import date
from decimal import Decimal
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CloudAccount, CostRecord


async def get_basic_breakdown(
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    provider: str | None,
    *,
    limit: int,
    offset: int,
    max_aggregation_rows: int,
    statement_timeout_ms: int,
) -> dict[str, Any]:
    """Provides a simplified breakdown for the API."""
    stmt = (
        select(
            CostRecord.service,
            func.sum(CostRecord.cost_usd).label("total_cost"),
            func.sum(CostRecord.carbon_kg).label("total_carbon"),
        )
        .where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
        )
        .group_by(CostRecord.service)
    )

    if provider:
        stmt = stmt.join(CloudAccount, CostRecord.account_id == CloudAccount.id).where(
            CloudAccount.provider == provider.lower()
        )

    stmt = stmt.limit(min(limit, max_aggregation_rows)).offset(offset)

    if db.bind.dialect.name != "sqlite":
        await db.execute(text(f"SET LOCAL statement_timeout TO {statement_timeout_ms}"))

    result = await db.execute(stmt)
    rows = result.all()

    total_cost = Decimal("0.00")
    total_carbon = Decimal("0.00")
    breakdown = []

    for row in rows:
        cost_value = row.total_cost or Decimal(0)
        carbon_value = row.total_carbon or Decimal(0)
        total_cost += cost_value
        total_carbon += carbon_value

        service_name = row.service
        if not service_name or service_name.lower() == "unknown":
            service_name = "Uncategorized"

        breakdown.append(
            {
                "service": service_name,
                "cost": float(cost_value),
                "carbon_kg": float(carbon_value),
            }
        )

    return {
        "total_cost": float(total_cost),
        "total_carbon_kg": float(total_carbon),
        "breakdown": breakdown,
    }


async def get_cached_breakdown(
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    *,
    logger: Any,
    mv_read_recoverable_exceptions: tuple[type[Exception], ...],
    basic_breakdown_fetcher: Callable[..., Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    """Query cached view breakdown; fallback to direct aggregation if unavailable."""
    try:
        async with db.begin_nested():
            stmt = text("""
                SELECT
                    service,
                    SUM(total_cost) as total_cost,
                    SUM(total_carbon) as total_carbon
                FROM mv_daily_cost_aggregates
                WHERE tenant_id = :tenant_id
                  AND cost_date >= :start_date
                  AND cost_date <= :end_date
                GROUP BY service
                ORDER BY total_cost DESC
            """)

            result = await db.execute(
                stmt,
                {
                    "tenant_id": tenant_id,
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            rows = result.all()

        if not rows:
            logger.info("cache_miss_falling_back", tenant_id=str(tenant_id))
            return await basic_breakdown_fetcher(db, tenant_id, start_date, end_date)

        total_cost = Decimal("0.00")
        total_carbon = Decimal("0.00")
        breakdown = []

        for row in rows:
            cost_value = row.total_cost or Decimal(0)
            carbon_value = row.total_carbon or Decimal(0)
            total_cost += cost_value
            total_carbon += carbon_value
            breakdown.append(
                {
                    "service": row.service,
                    "cost": float(cost_value),
                    "carbon_kg": float(carbon_value),
                }
            )

        logger.info("cache_hit", tenant_id=str(tenant_id), services=len(breakdown))

        return {
            "total_cost": float(total_cost),
            "total_carbon_kg": float(total_carbon),
            "breakdown": breakdown,
            "cached": True,
        }

    except mv_read_recoverable_exceptions as exc:
        logger.warning("mv_query_failed_fallback", error=str(exc))
        return await basic_breakdown_fetcher(db, tenant_id, start_date, end_date)


async def refresh_materialized_view(
    db: AsyncSession,
    *,
    logger: Any,
    mv_refresh_recoverable_exceptions: tuple[type[Exception], ...],
) -> bool:
    """Manually refresh the materialized view."""
    try:
        if db.bind.dialect.name == "sqlite":
            logger.info("materialized_view_refresh_skipped_sqlite")
            return True

        await db.execute(
            text("REFRESH MATERIALIZED VIEW CONCURRENTLY mv_daily_cost_aggregates")
        )
        await db.commit()
        logger.info("materialized_view_refreshed")
        return True
    except mv_refresh_recoverable_exceptions as exc:
        logger.error("materialized_view_refresh_failed", error=str(exc))
        return False

