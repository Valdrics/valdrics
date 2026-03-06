"""Rule simulation helpers for attribution engine."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribution import AttributionRule
from app.models.cloud import CostRecord


async def simulate_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    rule_type: str,
    conditions: dict[str, Any],
    allocation: Any,
    start_date: date,
    end_date: date,
    normalize_rule_type_fn: Any,
    match_conditions_fn: Any,
    apply_rules_fn: Any,
    sample_limit: int = 500,
) -> dict[str, Any]:
    """Run a dry-run simulation of one rule against tenant records in a range."""
    query = (
        select(CostRecord)
        .where(CostRecord.tenant_id == tenant_id)
        .where(CostRecord.recorded_at >= start_date)
        .where(CostRecord.recorded_at <= end_date)
        .order_by(CostRecord.recorded_at.desc())
        .limit(sample_limit)
    )
    result = await db.execute(query)
    records = list(result.scalars().all())

    simulated_rule = AttributionRule(
        tenant_id=tenant_id,
        name="simulation",
        priority=1,
        rule_type=normalize_rule_type_fn(rule_type),
        conditions=conditions,
        allocation=allocation,
        is_active=True,
    )

    matched_records = 0
    matched_cost = Decimal("0")
    projected_by_bucket: dict[str, Decimal] = {}
    for record in records:
        if not match_conditions_fn(record, conditions):
            continue
        matched_records += 1
        matched_cost += record.cost_usd
        allocations = await apply_rules_fn(record, [simulated_rule])
        for alloc in allocations:
            projected_by_bucket[alloc.allocated_to] = (
                projected_by_bucket.get(alloc.allocated_to, Decimal("0")) + alloc.amount
            )

    allocation_rows = [
        {"bucket": bucket, "amount": float(amount)}
        for bucket, amount in sorted(
            projected_by_bucket.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    sampled_records = len(records)
    match_rate = round((matched_records / sampled_records), 4) if sampled_records else 0.0
    projected_total = float(sum(projected_by_bucket.values(), Decimal("0")))

    return {
        "sampled_records": sampled_records,
        "matched_records": matched_records,
        "match_rate": match_rate,
        "matched_cost": float(matched_cost),
        "projected_allocation_total": projected_total,
        "projected_allocations": allocation_rows,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }
