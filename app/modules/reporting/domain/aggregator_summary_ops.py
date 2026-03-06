from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Awaitable, Callable
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.cloud import CloudAccount, CostRecord
from app.schemas.costs import CloudUsageSummary, CostRecord as SchemaCostRecord


async def get_summary(
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    provider: str | None,
    *,
    max_detail_rows: int,
    logger: Any,
) -> CloudUsageSummary:
    total_stmt = select(
        func.sum(CostRecord.cost_usd).label("total_cost"),
        func.count(CostRecord.id).label("total_count"),
    ).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
    )
    if provider:
        total_stmt = total_stmt.join(CloudAccount).where(
            CloudAccount.provider == provider.lower()
        )

    total_result = await db.execute(total_stmt)
    total_row = total_result.one()
    full_total_cost = total_row.total_cost or Decimal("0.00")
    full_total_count = total_row.total_count or 0

    stmt = (
        select(CostRecord)
        .options(selectinload(CostRecord.account))
        .where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
        )
    )
    if provider:
        stmt = stmt.join(CloudAccount).where(CloudAccount.provider == provider.lower())

    stmt = stmt.limit(max_detail_rows)

    result = await db.execute(stmt)
    records = result.scalars().all()

    is_truncated = full_total_count > max_detail_rows
    if is_truncated:
        logger.warning(
            "query_truncated",
            tenant_id=str(tenant_id),
            actual=full_total_count,
            limit=max_detail_rows,
        )

    schema_records = []
    for record in records:
        schema_records.append(
            SchemaCostRecord(
                date=datetime.combine(
                    record.recorded_at, datetime.min.time(), tzinfo=timezone.utc
                ),
                amount=record.cost_usd,
                service=record.service,
                region=record.region,
            )
        )

    by_service: dict[str, Decimal] = {}
    for record in records:
        by_service[record.service] = (
            by_service.get(record.service, Decimal(0)) + record.cost_usd
        )

    return CloudUsageSummary(
        tenant_id=str(tenant_id),
        provider=provider or "multi",
        start_date=start_date,
        end_date=end_date,
        total_cost=full_total_cost,
        records=schema_records,
        by_service=by_service,
        metadata={
            "is_truncated": is_truncated,
            "total_records_in_range": full_total_count,
            "records_returned": len(records),
            "summary": "Breakdown/records are partial" if is_truncated else "Full data",
        },
    )


async def get_dashboard_summary(
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    provider: str | None,
    *,
    statement_timeout_ms: int,
    basic_breakdown_fetcher: Callable[..., Awaitable[dict[str, Any]]],
    data_freshness_fetcher: Callable[..., Awaitable[dict[str, Any]]],
    canonical_quality_fetcher: Callable[..., Awaitable[dict[str, Any]]],
) -> dict[str, Any]:
    if db.bind.dialect.name != "sqlite":
        await db.execute(text(f"SET LOCAL statement_timeout TO {statement_timeout_ms}"))

    stmt = select(
        func.sum(CostRecord.cost_usd).label("total_cost"),
        func.sum(CostRecord.carbon_kg).label("total_carbon"),
    ).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
    )
    if provider:
        stmt = stmt.join(CloudAccount, CostRecord.account_id == CloudAccount.id).where(
            CloudAccount.provider == provider.lower()
        )

    result = await db.execute(stmt)
    row = result.one_or_none()

    total_cost = row.total_cost if row and row.total_cost else Decimal("0.00")
    total_carbon = row.total_carbon if row and row.total_carbon else Decimal("0.00")

    breakdown_data = await basic_breakdown_fetcher(
        db, tenant_id, start_date, end_date, provider
    )
    freshness = await data_freshness_fetcher(db, tenant_id, start_date, end_date)
    canonical_quality = await canonical_quality_fetcher(
        db, tenant_id, start_date, end_date, provider
    )

    return {
        "total_cost": float(total_cost),
        "total_carbon_kg": float(total_carbon),
        "provider": provider or "multi",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "breakdown": breakdown_data["breakdown"],
        "data_quality": {
            "freshness": freshness,
            "canonical_mapping": canonical_quality,
        },
    }

