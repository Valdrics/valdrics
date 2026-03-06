"""Allocation, batch processing, and analytics operations for attribution engine."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, cast
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribution import AttributionRule, CostAllocation
from app.models.cloud import CostRecord
from app.modules.reporting.domain.attribution_engine_simulation_ops import (
    simulate_rule,
)

__all__ = [
    "match_conditions",
    "apply_rules",
    "process_cost_record",
    "apply_rules_to_tenant",
    "get_allocation_summary",
    "get_allocation_coverage",
    "get_unallocated_analysis",
    "simulate_rule",
]


def match_conditions(cost_record: CostRecord, conditions: dict[str, Any]) -> bool:
    """
    Check if a cost record matches the rule conditions.

    Supports matching on: service, region, account_id, tags.
    """
    if "service" in conditions and cost_record.service != conditions["service"]:
        return False
    if "region" in conditions and cost_record.region != conditions["region"]:
        return False
    if "account_id" in conditions and cost_record.account_id != conditions["account_id"]:
        return False

    if "tags" in conditions:
        direct_tags = getattr(cost_record, "tags", None)
        if isinstance(direct_tags, dict):
            cost_tags = direct_tags
        else:
            metadata = (
                cost_record.ingestion_metadata
                if isinstance(cost_record.ingestion_metadata, dict)
                else {}
            )
            raw_tags = metadata.get("tags", {})
            cost_tags = raw_tags if isinstance(raw_tags, dict) else {}
        condition_tags = conditions["tags"] if isinstance(conditions["tags"], dict) else {}
        for tag_key, tag_value in condition_tags.items():
            if cost_tags.get(tag_key) != tag_value:
                return False

    return True


async def apply_rules(
    cost_record: CostRecord,
    rules: list[AttributionRule],
    *,
    match_conditions_fn: Any,
    logger_obj: Any,
) -> list[CostAllocation]:
    """
    Apply attribution rules to a cost record and return CostAllocation records.
    First matching rule wins (rules are pre-sorted by priority).
    """
    allocations: list[CostAllocation] = []

    for rule in rules:
        if not match_conditions_fn(cost_record, rule.conditions):
            continue

        if rule.rule_type == "DIRECT":
            direct_allocation_raw: Any = rule.allocation
            if isinstance(direct_allocation_raw, list) and len(direct_allocation_raw) > 0:
                first_entry = direct_allocation_raw[0]
                bucket = (
                    first_entry.get("bucket", "Unallocated")
                    if isinstance(first_entry, dict)
                    else "Unallocated"
                )
            elif isinstance(direct_allocation_raw, dict):
                bucket = direct_allocation_raw.get("bucket", "Unallocated")
            else:
                bucket = "Unallocated"

            allocations.append(
                CostAllocation(
                    cost_record_id=cost_record.id,
                    recorded_at=cost_record.recorded_at,
                    rule_id=rule.id,
                    allocated_to=bucket,
                    amount=cost_record.cost_usd,
                    percentage=Decimal("100.00"),
                    timestamp=datetime.now(timezone.utc),
                )
            )

        elif rule.rule_type == "PERCENTAGE":
            percentage_allocation_raw: Any = rule.allocation
            if isinstance(percentage_allocation_raw, list):
                percentage_splits = [
                    item for item in percentage_allocation_raw if isinstance(item, dict)
                ]
            elif isinstance(percentage_allocation_raw, dict):
                percentage_splits = [percentage_allocation_raw]
            else:
                percentage_splits = []

            total_percentage = Decimal("0")
            for split in percentage_splits:
                bucket = split.get("bucket", "Unallocated")
                pct = Decimal(str(split.get("percentage", 0)))
                total_percentage += pct
                split_amount = (cost_record.cost_usd * pct) / Decimal("100")
                allocations.append(
                    CostAllocation(
                        cost_record_id=cost_record.id,
                        recorded_at=cost_record.recorded_at,
                        rule_id=rule.id,
                        allocated_to=bucket,
                        amount=split_amount,
                        percentage=pct,
                        timestamp=datetime.now(timezone.utc),
                    )
                )

            if total_percentage != Decimal("100"):
                logger_obj.warning(
                    "attribution_percentage_mismatch",
                    rule_id=str(rule.id),
                    total=float(total_percentage),
                )

        elif rule.rule_type == "FIXED":
            fixed_allocation_raw: Any = rule.allocation
            if isinstance(fixed_allocation_raw, list):
                fixed_splits = [item for item in fixed_allocation_raw if isinstance(item, dict)]
            elif isinstance(fixed_allocation_raw, dict):
                fixed_splits = [fixed_allocation_raw]
            else:
                fixed_splits = []

            allocated_total = Decimal("0")
            for split in fixed_splits:
                bucket = split.get("bucket", "Unallocated")
                fixed_amount = Decimal(str(split.get("amount", 0)))
                allocated_total += fixed_amount
                allocations.append(
                    CostAllocation(
                        cost_record_id=cost_record.id,
                        recorded_at=cost_record.recorded_at,
                        rule_id=rule.id,
                        allocated_to=bucket,
                        amount=fixed_amount,
                        percentage=None,
                        timestamp=datetime.now(timezone.utc),
                    )
                )

            remaining = cost_record.cost_usd - allocated_total
            if remaining > Decimal("0"):
                allocations.append(
                    CostAllocation(
                        cost_record_id=cost_record.id,
                        recorded_at=cost_record.recorded_at,
                        rule_id=rule.id,
                        allocated_to="Unallocated",
                        amount=remaining,
                        percentage=None,
                        timestamp=datetime.now(timezone.utc),
                    )
                )

        break

    if not allocations:
        allocations.append(
            CostAllocation(
                cost_record_id=cost_record.id,
                recorded_at=cost_record.recorded_at,
                rule_id=None,
                allocated_to="Unallocated",
                amount=cost_record.cost_usd,
                percentage=Decimal("100.00"),
                timestamp=datetime.now(timezone.utc),
            )
        )

    return allocations


async def process_cost_record(
    db: AsyncSession,
    cost_record: CostRecord,
    tenant_id: uuid.UUID,
    *,
    get_active_rules_fn: Any,
    apply_rules_fn: Any,
    logger_obj: Any,
) -> list[CostAllocation]:
    """Full pipeline: fetch rules, apply, and persist allocations."""
    rules = await get_active_rules_fn(tenant_id)
    allocations = cast(list[CostAllocation], await apply_rules_fn(cost_record, rules))

    for allocation in allocations:
        db.add(allocation)

    await db.commit()

    logger_obj.info(
        "attribution_applied",
        cost_record_id=str(cost_record.id),
        allocations_count=len(allocations),
    )

    return allocations


async def apply_rules_to_tenant(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    start_date: date,
    end_date: date,
    *,
    get_active_rules_fn: Any,
    apply_rules_fn: Any,
    logger_obj: Any,
    commit: bool = True,
) -> dict[str, int]:
    """Batch apply attribution rules to all cost records in a date range."""
    query = (
        select(CostRecord)
        .where(CostRecord.tenant_id == tenant_id)
        .where(CostRecord.recorded_at >= start_date)
        .where(CostRecord.recorded_at <= end_date)
    )
    result = await db.execute(query)
    records = result.scalars().all()

    if not records:
        logger_obj.info("no_cost_records_found_for_attribution", tenant_id=str(tenant_id))
        return {"records_processed": 0, "allocations_created": 0}

    rules = await get_active_rules_fn(tenant_id)

    record_ids = [r.id for r in records]
    for i in range(0, len(record_ids), 1000):
        chunk = record_ids[i : i + 1000]
        await db.execute(delete(CostAllocation).where(CostAllocation.cost_record_id.in_(chunk)))

    all_allocations: list[CostAllocation] = []
    for record in records:
        allocations = await apply_rules_fn(record, rules)
        all_allocations.extend(allocations)

    if all_allocations:
        db.add_all(all_allocations)

    if commit:
        await db.commit()
    else:
        await db.flush()

    logger_obj.info(
        "batch_attribution_complete",
        tenant_id=str(tenant_id),
        records_processed=len(records),
        allocations_count=len(all_allocations),
    )
    return {
        "records_processed": len(records),
        "allocations_created": len(all_allocations),
    }


async def get_allocation_summary(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    bucket: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    """Get aggregated allocation summary by bucket for a tenant."""
    from sqlalchemy import func

    query = (
        select(
            CostAllocation.allocated_to,
            func.sum(CostAllocation.amount).label("total_amount"),
            func.count(CostAllocation.id).label("record_count"),
        )
        .join(
            CostRecord,
            (CostAllocation.cost_record_id == CostRecord.id)
            & (CostAllocation.recorded_at == CostRecord.recorded_at),
        )
        .where(CostRecord.tenant_id == tenant_id)
        .group_by(CostAllocation.allocated_to)
        .order_by(func.sum(CostAllocation.amount).desc())
        .limit(limit)
        .offset(offset)
    )

    if start_date:
        query = query.where(CostAllocation.timestamp >= start_date)
    if end_date:
        query = query.where(CostAllocation.timestamp <= end_date)
    if bucket:
        query = query.where(CostAllocation.allocated_to == bucket)

    result = await db.execute(query)
    rows = result.all()

    return {
        "buckets": [
            {
                "name": row.allocated_to,
                "total_amount": float(row.total_amount),
                "record_count": row.record_count,
            }
            for row in rows
        ],
        "total": sum(float(row.total_amount) for row in rows),
    }


async def get_allocation_coverage(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    start_date: date | None = None,
    end_date: date | None = None,
    target_percentage: float = 90.0,
) -> dict[str, Any]:
    """Compute allocation coverage KPI for a tenant and date window."""
    from sqlalchemy import func

    total_query = select(
        func.coalesce(func.sum(CostRecord.cost_usd), 0).label("total_cost"),
        func.count(CostRecord.id).label("total_records"),
    ).where(CostRecord.tenant_id == tenant_id)
    if start_date:
        total_query = total_query.where(CostRecord.recorded_at >= start_date)
    if end_date:
        total_query = total_query.where(CostRecord.recorded_at <= end_date)

    total_result = await db.execute(total_query)
    total_row = total_result.one()
    total_cost = float(total_row.total_cost or 0)
    total_records = int(total_row.total_records or 0)

    allocated_query = (
        select(
            func.coalesce(func.sum(CostAllocation.amount), 0).label("allocated_cost"),
            func.count(CostAllocation.id).label("allocation_rows"),
            func.count(func.distinct(CostAllocation.cost_record_id)).label(
                "allocated_records"
            ),
        )
        .join(
            CostRecord,
            (CostAllocation.cost_record_id == CostRecord.id)
            & (CostAllocation.recorded_at == CostRecord.recorded_at),
        )
        .where(CostRecord.tenant_id == tenant_id)
    )
    if start_date:
        allocated_query = allocated_query.where(CostRecord.recorded_at >= start_date)
    if end_date:
        allocated_query = allocated_query.where(CostRecord.recorded_at <= end_date)

    allocated_result = await db.execute(allocated_query)
    allocated_row = allocated_result.one()
    raw_allocated_cost = float(allocated_row.allocated_cost or 0)
    allocated_cost = min(raw_allocated_cost, total_cost) if total_cost > 0 else 0.0
    over_allocated_cost = max(raw_allocated_cost - total_cost, 0.0)
    coverage_percentage = (allocated_cost / total_cost * 100.0) if total_cost > 0 else 0.0

    return {
        "target_percentage": target_percentage,
        "coverage_percentage": round(coverage_percentage, 2),
        "meets_target": coverage_percentage >= target_percentage if total_cost > 0 else False,
        "status": "no_data"
        if total_cost <= 0
        else ("ok" if coverage_percentage >= target_percentage else "warning"),
        "total_cost": round(total_cost, 6),
        "allocated_cost": round(allocated_cost, 6),
        "unallocated_cost": round(max(total_cost - allocated_cost, 0.0), 6),
        "over_allocated_cost": round(over_allocated_cost, 6),
        "total_records": total_records,
        "allocated_records": int(allocated_row.allocated_records or 0),
        "allocation_rows": int(allocated_row.allocation_rows or 0),
        "start_date": start_date.isoformat() if start_date else None,
        "end_date": end_date.isoformat() if end_date else None,
    }


async def get_unallocated_analysis(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    """Identify top services contributing to unallocated spend."""
    from sqlalchemy import func

    query = (
        select(
            CostRecord.service,
            func.sum(CostRecord.cost_usd).label("total_unallocated"),
            func.count(CostRecord.id).label("record_count"),
        )
        .where(CostRecord.tenant_id == tenant_id)
        .where(CostRecord.recorded_at >= start_date)
        .where(CostRecord.recorded_at <= end_date)
        .where(
            (CostRecord.allocated_to.is_(None))
            | (CostRecord.allocated_to == "Unallocated")
        )
        .group_by(CostRecord.service)
        .order_by(func.sum(CostRecord.cost_usd).desc())
        .limit(5)
    )

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "service": row.service,
            "amount": float(row.total_unallocated),
            "count": row.record_count,
            "recommendation": (
                f"Create a DIRECT rule for service '{row.service}' to a specific team bucket."
            ),
        }
        for row in rows
    ]
