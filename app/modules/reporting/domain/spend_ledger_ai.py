from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm import LLMUsage

AI_LEDGER_PROVIDER = "ai"
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


def _date_window_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


async def ai_spend_summary(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
) -> dict[str, Decimal | int]:
    window_start, window_end = _date_window_bounds(start_date, end_date)
    stmt = select(
        func.count(LLMUsage.id).label("record_count"),
        func.coalesce(func.sum(LLMUsage.cost_usd), Decimal("0")).label("total_cost"),
    ).where(
        LLMUsage.tenant_id == tenant_id,
        LLMUsage.created_at >= window_start,
        LLMUsage.created_at < window_end,
    )
    row = (await db.execute(stmt)).one()
    total_cost = Decimal(str(row.total_cost or 0))
    return {
        "record_count": int(row.record_count or 0),
        "total_cost": total_cost,
        "total_allocated": Decimal("0"),
        "total_unallocated": total_cost,
    }


async def ai_spend_entries(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    limit: int,
    offset: int,
) -> list[dict[str, Any]]:
    window_start, window_end = _date_window_bounds(start_date, end_date)
    stmt = (
        select(LLMUsage)
        .where(
            LLMUsage.tenant_id == tenant_id,
            LLMUsage.created_at >= window_start,
            LLMUsage.created_at < window_end,
        )
        .order_by(LLMUsage.created_at.asc(), LLMUsage.id.asc())
        .limit(limit)
        .offset(offset)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return [_serialize_llm_usage_row(row) for row in rows]


def _serialize_llm_usage_row(usage: LLMUsage) -> dict[str, Any]:
    provider = (usage.provider or "unknown").strip().lower() or "unknown"
    request_type = usage.request_type or "inference"
    created_at = usage.created_at
    return {
        "id": str(usage.id),
        "recorded_at": created_at.date().isoformat(),
        "timestamp": created_at.isoformat(),
        "provider": AI_LEDGER_PROVIDER,
        "account_id": f"ai:{provider}",
        "account_name": f"AI Spend ({provider})",
        "service": "LLM",
        "region": None,
        "usage_type": request_type,
        "resource_id": usage.operation_id or None,
        "usage_amount": _decimal_string(usage.total_tokens),
        "usage_unit": "tokens",
        "cost_usd": _decimal_string(usage.cost_usd),
        "amount_raw": _decimal_string(usage.cost_usd),
        "currency": "USD",
        "cost_status": "FINAL",
        "canonical_charge_category": "ai",
        "canonical_charge_subcategory": "llm_inference",
        "canonical_mapping_version": "valdrics-ai-spend-v1",
        "allocation_status": "unallocated",
        "allocated_amount_usd": _decimal_string(Decimal("0")),
        "unallocated_amount_usd": _decimal_string(usage.cost_usd),
        "allocation_count": 0,
        "tags": {
            "source": "llm_usage",
            "llm_provider": provider,
            "model": usage.model,
            "is_byok": usage.is_byok,
            "request_type": request_type,
        },
        "allocations": [],
    }
