"""Canonical technology spend ledger query service."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribution import CostAllocation
from app.models.cloud import CloudAccount, CostRecord
from app.modules.reporting.domain.allocation_ledger import (
    cost_allocation_rollup_subquery,
    unallocated_amount_expr,
)
from app.modules.reporting.domain.spend_ledger_ai import (
    AI_LEDGER_PROVIDER,
    ai_spend_entries,
    ai_spend_summary,
)

SPEND_LEDGER_DECIMAL_PARSE_EXCEPTIONS: tuple[type[Exception], ...] = (
    InvalidOperation,
    TypeError,
    ValueError,
)

def _decimal_string(value: Any, *, places: int = 8) -> str:
    if value is None:
        return format(Decimal("0").quantize(Decimal(1).scaleb(-places)), "f")
    try:
        amount = value if isinstance(value, Decimal) else Decimal(str(value))
    except SPEND_LEDGER_DECIMAL_PARSE_EXCEPTIONS as exc:
        raise ValueError("Spend ledger amount must be numeric") from exc
    if not amount.is_finite():
        raise ValueError("Spend ledger amount must be finite")
    return format(amount.quantize(Decimal(1).scaleb(-places)), "f")


def _optional_decimal_string(value: Any, *, places: int = 8) -> str | None:
    if value is None:
        return None
    return _decimal_string(value, places=places)


def _metadata_tags(record: CostRecord) -> dict[str, Any]:
    tags = getattr(record, "tags", None)
    if isinstance(tags, dict):
        return tags
    metadata = getattr(record, "ingestion_metadata", None)
    if isinstance(metadata, dict):
        metadata_tags = metadata.get("tags")
        if isinstance(metadata_tags, dict):
            return metadata_tags
    return {}


def _allocation_key(allocation: CostAllocation) -> tuple[date, datetime, str, str]:
    return (
        allocation.recorded_at,
        allocation.timestamp,
        allocation.allocated_to,
        str(allocation.id),
    )


async def list_spend_ledger_entries(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    provider: str | None,
    include_preliminary: bool,
    limit: int,
    offset: int,
) -> dict[str, Any]:
    include_origin_spend = provider != AI_LEDGER_PROVIDER
    include_ai_spend = provider in (None, AI_LEDGER_PROVIDER)

    origin_summary = (
        await _origin_spend_summary(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            include_preliminary=include_preliminary,
        )
        if include_origin_spend
        else _empty_summary()
    )
    ai_summary = (
        await ai_spend_summary(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        if include_ai_spend
        else _empty_summary()
    )

    if include_origin_spend and not include_ai_spend:
        entries = await _origin_spend_entries(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            include_preliminary=include_preliminary,
            limit=limit,
            offset=offset,
        )
    elif include_ai_spend and not include_origin_spend:
        entries = await ai_spend_entries(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
            offset=offset,
        )
    else:
        fetch_limit = limit + offset
        candidate_entries = [
            *await _origin_spend_entries(
                db=db,
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
                provider=None,
                include_preliminary=include_preliminary,
                limit=fetch_limit,
                offset=0,
            ),
            *await ai_spend_entries(
                db=db,
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
                limit=fetch_limit,
                offset=0,
            ),
        ]
        entries = sorted(candidate_entries, key=_ledger_entry_sort_key)[
            offset : offset + limit
        ]

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "provider": provider,
        "include_preliminary": include_preliminary,
        "limit": limit,
        "offset": offset,
        "record_count": int(origin_summary["record_count"] + ai_summary["record_count"]),
        "total_cost_usd": _decimal_string(
            origin_summary["total_cost"] + ai_summary["total_cost"]
        ),
        "total_allocated_usd": _decimal_string(
            origin_summary["total_allocated"] + ai_summary["total_allocated"]
        ),
        "total_unallocated_usd": _decimal_string(
            origin_summary["total_unallocated"] + ai_summary["total_unallocated"]
        ),
        "entries": entries,
    }


def _empty_summary() -> dict[str, Decimal | int]:
    return {
        "record_count": 0,
        "total_cost": Decimal("0"),
        "total_allocated": Decimal("0"),
        "total_unallocated": Decimal("0"),
    }


async def _origin_spend_summary(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    provider: str | None,
    include_preliminary: bool,
) -> dict[str, Decimal | int]:
    allocation_rollup = cost_allocation_rollup_subquery(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        include_preliminary=include_preliminary,
    )
    allocated_amount = func.coalesce(allocation_rollup.c.allocated_amount, Decimal("0"))
    unallocated_amount = unallocated_amount_expr(
        origin_amount=CostRecord.cost_usd,
        allocated_amount=allocation_rollup.c.allocated_amount,
        allocation_count=allocation_rollup.c.allocation_count,
    )
    filters: list[Any] = [
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
    ]
    if not include_preliminary:
        filters.append(CostRecord.cost_status == "FINAL")
    if provider:
        filters.append(CloudAccount.provider == provider)

    base_from = (
        select(CostRecord)
        .join(CloudAccount, CostRecord.account_id == CloudAccount.id)
        .outerjoin(
            allocation_rollup,
            (allocation_rollup.c.cost_record_id == CostRecord.id)
            & (allocation_rollup.c.recorded_at == CostRecord.recorded_at),
        )
        .where(*filters)
    )

    summary_stmt = base_from.with_only_columns(
        func.count(CostRecord.id).label("record_count"),
        func.coalesce(func.sum(CostRecord.cost_usd), Decimal("0")).label("total_cost"),
        func.coalesce(func.sum(allocated_amount), Decimal("0")).label(
            "total_allocated"
        ),
        func.coalesce(func.sum(unallocated_amount), Decimal("0")).label(
            "total_unallocated"
        ),
    )
    summary = (await db.execute(summary_stmt)).one()
    return {
        "record_count": int(summary.record_count or 0),
        "total_cost": Decimal(str(summary.total_cost or 0)),
        "total_allocated": Decimal(str(summary.total_allocated or 0)),
        "total_unallocated": Decimal(str(summary.total_unallocated or 0)),
    }


async def _origin_spend_entries(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    provider: str | None,
    include_preliminary: bool,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    allocation_rollup = cost_allocation_rollup_subquery(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        include_preliminary=include_preliminary,
    )
    allocated_amount = func.coalesce(allocation_rollup.c.allocated_amount, Decimal("0"))
    unallocated_amount = unallocated_amount_expr(
        origin_amount=CostRecord.cost_usd,
        allocated_amount=allocation_rollup.c.allocated_amount,
        allocation_count=allocation_rollup.c.allocation_count,
    )
    filters: list[Any] = [
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
    ]
    if not include_preliminary:
        filters.append(CostRecord.cost_status == "FINAL")
    if provider:
        filters.append(CloudAccount.provider == provider)
    detail_stmt = (
        select(
            CostRecord,
            CloudAccount,
            allocated_amount.label("allocated_amount"),
            unallocated_amount.label("unallocated_amount"),
            func.coalesce(allocation_rollup.c.allocation_count, 0).label(
                "allocation_count"
            ),
        )
        .join(CloudAccount, CostRecord.account_id == CloudAccount.id)
        .outerjoin(
            allocation_rollup,
            (allocation_rollup.c.cost_record_id == CostRecord.id)
            & (allocation_rollup.c.recorded_at == CostRecord.recorded_at),
        )
        .where(*filters)
        .order_by(
            CostRecord.recorded_at.asc(),
            CostRecord.timestamp.asc(),
            CostRecord.id.asc(),
        )
        .limit(limit)
        .offset(offset)
    )
    detail_rows = (await db.execute(detail_stmt)).all()
    record_keys = [
        (row.CostRecord.id, row.CostRecord.recorded_at) for row in detail_rows
    ]
    allocations_by_record = await _load_page_allocations(db, record_keys)

    return [
        _serialize_ledger_row(
            record=row.CostRecord,
            account=row.CloudAccount,
            allocated_amount=row.allocated_amount,
            unallocated_amount=row.unallocated_amount,
            allocation_count=int(row.allocation_count or 0),
            allocations=allocations_by_record.get(
                (row.CostRecord.id, row.CostRecord.recorded_at),
                [],
            ),
        )
        for row in detail_rows
    ]


def _ledger_entry_sort_key(entry: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(entry.get("recorded_at") or ""),
        str(entry.get("timestamp") or ""),
        str(entry.get("provider") or ""),
        str(entry.get("id") or ""),
    )


async def _load_page_allocations(
    db: AsyncSession,
    record_keys: Sequence[tuple[UUID, date]],
) -> dict[tuple[UUID, date], list[CostAllocation]]:
    if not record_keys:
        return {}
    stmt = (
        select(CostAllocation)
        .where(
            tuple_(CostAllocation.cost_record_id, CostAllocation.recorded_at).in_(
                list(record_keys)
            )
        )
        .order_by(
            CostAllocation.recorded_at.asc(),
            CostAllocation.timestamp.asc(),
            CostAllocation.allocated_to.asc(),
            CostAllocation.id.asc(),
        )
    )
    allocations = (await db.execute(stmt)).scalars().all()
    grouped: dict[tuple[UUID, date], list[CostAllocation]] = {}
    for allocation in sorted(allocations, key=_allocation_key):
        grouped.setdefault(
            (allocation.cost_record_id, allocation.recorded_at),
            [],
        ).append(allocation)
    return grouped


def _serialize_ledger_row(
    *,
    record: CostRecord,
    account: CloudAccount,
    allocated_amount: Any,
    unallocated_amount: Any,
    allocation_count: int,
    allocations: list[CostAllocation],
) -> dict[str, Any]:
    allocated_decimal = Decimal(_decimal_string(allocated_amount))
    unallocated_decimal = Decimal(_decimal_string(unallocated_amount))
    if allocation_count <= 0:
        allocation_status = "unallocated"
    elif unallocated_decimal > Decimal("0") and allocated_decimal > Decimal("0"):
        allocation_status = "partially_allocated"
    elif unallocated_decimal > Decimal("0"):
        allocation_status = "unallocated"
    else:
        allocation_status = "allocated"

    return {
        "id": str(record.id),
        "recorded_at": record.recorded_at.isoformat(),
        "timestamp": record.timestamp.isoformat() if record.timestamp else None,
        "provider": account.provider,
        "account_id": str(account.id),
        "account_name": account.name,
        "service": record.service,
        "region": record.region,
        "usage_type": record.usage_type,
        "resource_id": record.resource_id or None,
        "usage_amount": _optional_decimal_string(record.usage_amount),
        "usage_unit": record.usage_unit,
        "cost_usd": _decimal_string(record.cost_usd),
        "amount_raw": _optional_decimal_string(record.amount_raw),
        "currency": record.currency,
        "cost_status": record.cost_status,
        "canonical_charge_category": record.canonical_charge_category,
        "canonical_charge_subcategory": record.canonical_charge_subcategory,
        "canonical_mapping_version": record.canonical_mapping_version,
        "allocation_status": allocation_status,
        "allocated_amount_usd": _decimal_string(allocated_amount),
        "unallocated_amount_usd": _decimal_string(unallocated_amount),
        "allocation_count": allocation_count,
        "tags": _metadata_tags(record),
        "allocations": [_serialize_allocation(allocation) for allocation in allocations],
    }


def _serialize_allocation(allocation: CostAllocation) -> dict[str, Any]:
    return {
        "id": str(allocation.id),
        "rule_id": str(allocation.rule_id) if allocation.rule_id else None,
        "allocated_to": allocation.allocated_to,
        "amount_usd": _decimal_string(allocation.amount),
        "percentage": _optional_decimal_string(allocation.percentage, places=2),
        "recorded_at": allocation.recorded_at.isoformat(),
        "timestamp": allocation.timestamp.isoformat(),
    }


__all__ = ["list_spend_ledger_entries"]
