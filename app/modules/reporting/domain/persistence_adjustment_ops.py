"""Significant-adjustment detection and audit logging for cost restatements."""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CostRecord


async def check_for_significant_adjustments(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    account_id: UUID,
    new_records: list[dict[str, Any]],
    logger_obj: Any,
) -> None:
    """Persist audit trails for restatements and log >2% deltas as critical."""
    if not new_records:
        return

    from app.models.cost_audit import CostAuditLog

    dates: set[date] = set()
    services: set[str] = set()
    for record in new_records:
        ts = record.get("timestamp")
        if isinstance(ts, datetime):
            dates.add(ts.date())
        elif isinstance(record.get("recorded_at"), date):
            dates.add(record["recorded_at"])
        services.add(str(record.get("service", "Unknown") or "Unknown"))

    stmt = select(
        CostRecord.id,
        CostRecord.timestamp,
        CostRecord.service,
        CostRecord.region,
        CostRecord.usage_type,
        CostRecord.resource_id,
        CostRecord.cost_usd,
    ).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.account_id == account_id,
        CostRecord.recorded_at.in_(dates),
        CostRecord.service.in_(services),
        CostRecord.cost_status == "FINAL",
    )

    result = await db.execute(stmt)
    existing: dict[tuple[datetime, str, str, str, str], tuple[Any, float]] = {}
    for row in result.all():
        ts = getattr(row, "timestamp", None)
        if not isinstance(ts, datetime):
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        service = str(getattr(row, "service", "") or "Unknown")
        region = str(getattr(row, "region", "") or "Global")
        usage_type = str(getattr(row, "usage_type", "") or "")
        resource_id = str(getattr(row, "resource_id", "") or "")
        key = (ts, service, region, usage_type, resource_id)
        existing[key] = (
            getattr(row, "id"),
            float(getattr(row, "cost_usd", 0) or 0),
        )

    audit_logs = []
    for nr in new_records:
        ts = nr.get("timestamp")
        if not isinstance(ts, datetime):
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        key = (
            ts,
            str(nr.get("service", "Unknown") or "Unknown"),
            str(nr.get("region", "Global") or "Global"),
            str(nr.get("usage_type", "") or ""),
            str(nr.get("resource_id", "") or ""),
        )
        existing_data = existing.get(key)
        if not existing_data:
            continue

        record_id, old_cost = existing_data
        new_cost = float(nr.get("cost_usd") or 0)
        if new_cost == old_cost:
            continue

        audit_logs.append(
            CostAuditLog(
                cost_record_id=record_id,
                cost_recorded_at=ts.date(),
                old_cost=Decimal(str(old_cost)),
                new_cost=Decimal(str(new_cost)),
                reason="RESTATEMENT",
                ingestion_batch_id=nr.get("reconciliation_run_id"),
            )
        )

        delta_ratio: float | None = None
        if old_cost and old_cost != 0:
            delta_ratio = abs(new_cost - old_cost) / abs(old_cost)
        elif new_cost != 0:
            delta_ratio = 1.0

        if delta_ratio is not None and delta_ratio > 0.02:
            logger_obj.critical(
                "significant_cost_adjustment_detected",
                tenant_id=tenant_id,
                account_id=account_id,
                service=key[1],
                timestamp=ts.isoformat(),
                old_cost=old_cost,
                new_cost=new_cost,
                delta_percent=round(delta_ratio * 100, 2),
                record_id=str(record_id),
            )

    if audit_logs:
        db.add_all(audit_logs)
        await db.flush()


__all__ = ["check_for_significant_adjustments"]
