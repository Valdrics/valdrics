from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CloudAccount, CostRecord
from app.models.llm import LLMUsage
from app.modules.reporting.api.v1.costs_models import AcceptanceKpiMetric


def _date_window_bounds(start_date: date, end_date: date) -> tuple[datetime, datetime]:
    return (
        datetime.combine(start_date, time.min, tzinfo=timezone.utc),
        datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc),
    )


async def _load_ai_ledger_quality_counts(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
) -> dict[str, int]:
    window_start, window_end = _date_window_bounds(start_date, end_date)
    invalid_provider_filter = (
        (LLMUsage.provider.is_(None))
        | (LLMUsage.provider == "")
        | (func.length(func.trim(LLMUsage.provider)) == 0)
    )
    invalid_model_filter = (
        (LLMUsage.model.is_(None))
        | (LLMUsage.model == "")
        | (func.length(func.trim(LLMUsage.model)) == 0)
    )
    normalized_filter = ~(invalid_provider_filter | invalid_model_filter)
    stmt = select(
        func.count(LLMUsage.id).label("total_records"),
        func.count(LLMUsage.id).filter(normalized_filter).label("normalized_records"),
        func.count(LLMUsage.id).label("mapped_records"),
        func.count(LLMUsage.id)
        .filter(invalid_provider_filter)
        .label("invalid_provider_records"),
        func.count(LLMUsage.id)
        .filter(invalid_model_filter)
        .label("invalid_model_records"),
    ).where(
        LLMUsage.tenant_id == tenant_id,
        LLMUsage.created_at >= window_start,
        LLMUsage.created_at < window_end,
    )
    row = (await db.execute(stmt)).one()
    return {
        "total_records": int(getattr(row, "total_records", 0) or 0),
        "normalized_records": int(getattr(row, "normalized_records", 0) or 0),
        "mapped_records": int(getattr(row, "mapped_records", 0) or 0),
        "invalid_provider_records": int(
            getattr(row, "invalid_provider_records", 0) or 0
        ),
        "invalid_model_records": int(getattr(row, "invalid_model_records", 0) or 0),
    }


async def build_ledger_quality_metrics(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    ledger_normalization_target_percent: float,
    canonical_mapping_target_percent: float,
    logger: Any,
) -> list[AcceptanceKpiMetric]:
    try:
        origin_total_records = int(
            await db.scalar(
                select(func.count(CostRecord.id)).where(
                    CostRecord.tenant_id == tenant_id,
                    CostRecord.recorded_at >= start_date,
                    CostRecord.recorded_at <= end_date,
                )
            )
            or 0
        )
        ai_quality_counts = await _load_ai_ledger_quality_counts(
            db=db,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
        )
        total_records = origin_total_records + ai_quality_counts["total_records"]
    except (SQLAlchemyError, RuntimeError) as exc:
        logger.warning(
            "acceptance_kpis_ledger_quality_query_failed",
            tenant_id=str(tenant_id),
            error=str(exc),
            error_type=type(exc).__name__,
        )
        origin_total_records = 0
        ai_quality_counts = {
            "total_records": 0,
            "normalized_records": 0,
            "mapped_records": 0,
            "invalid_provider_records": 0,
            "invalid_model_records": 0,
        }
        total_records = 0

    if total_records <= 0:
        return [
            AcceptanceKpiMetric(
                key="ledger_normalization_coverage",
                label="Ledger Normalization Coverage",
                available=False,
                target=f">={ledger_normalization_target_percent:.2f}%",
                actual="No ledger records in window",
                meets_target=False,
                details={"total_records": 0},
            ),
            AcceptanceKpiMetric(
                key="canonical_mapping_coverage",
                label="Canonical Mapping Coverage",
                available=False,
                target=f">={canonical_mapping_target_percent:.2f}%",
                actual="No ledger records in window",
                meets_target=False,
                details={"total_records": 0},
            ),
        ]

    unknown_service_filter = (
        (CostRecord.service.is_(None))
        | (CostRecord.service == "")
        | (func.lower(CostRecord.service) == "unknown")
    )
    invalid_currency_filter = (
        (CostRecord.currency.is_(None))
        | (CostRecord.currency == "")
        | (func.length(CostRecord.currency) != 3)
    )
    usage_unit_missing_filter = (CostRecord.usage_amount.is_not(None)) & (
        (CostRecord.usage_unit.is_(None)) | (CostRecord.usage_unit == "")
    )
    normalized_filter = ~(
        unknown_service_filter | invalid_currency_filter | usage_unit_missing_filter
    )

    mapped_filter = (CostRecord.canonical_charge_category.is_not(None)) & (
        func.lower(CostRecord.canonical_charge_category) != "unmapped"
    )

    summary_stmt = select(
        func.count(CostRecord.id).label("total_records"),
        func.count(CostRecord.id).filter(normalized_filter).label("normalized_records"),
        func.count(CostRecord.id).filter(mapped_filter).label("mapped_records"),
        func.count(CostRecord.id)
        .filter(unknown_service_filter)
        .label("unknown_service_records"),
        func.count(CostRecord.id)
        .filter(invalid_currency_filter)
        .label("invalid_currency_records"),
        func.count(CostRecord.id)
        .filter(usage_unit_missing_filter)
        .label("usage_unit_missing_records"),
    ).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
    )
    row = (await db.execute(summary_stmt)).one()

    total = int(getattr(row, "total_records", 0) or 0) + ai_quality_counts[
        "total_records"
    ]
    normalized_count = int(
        getattr(row, "normalized_records", 0) or 0
    ) + ai_quality_counts["normalized_records"]
    mapped_count = int(getattr(row, "mapped_records", 0) or 0) + ai_quality_counts[
        "mapped_records"
    ]

    unknown_service_count = int(getattr(row, "unknown_service_records", 0) or 0)
    invalid_currency_count = int(getattr(row, "invalid_currency_records", 0) or 0)
    usage_unit_missing_count = int(getattr(row, "usage_unit_missing_records", 0) or 0)

    normalized_pct = (normalized_count / total * 100.0) if total > 0 else 0.0
    mapped_pct = (mapped_count / total * 100.0) if total > 0 else 0.0

    provider_stmt = (
        select(
            CloudAccount.provider.label("provider"),
            func.count(CostRecord.id).label("total_records"),
            func.count(CostRecord.id)
            .filter(normalized_filter)
            .label("normalized_records"),
            func.count(CostRecord.id).filter(mapped_filter).label("mapped_records"),
        )
        .join(CloudAccount, CostRecord.account_id == CloudAccount.id)
        .where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
        )
        .group_by(CloudAccount.provider)
        .order_by(CloudAccount.provider.asc())
    )
    provider_rows = (await db.execute(provider_stmt)).all()
    provider_breakdown: list[dict[str, Any]] = []
    for provider_row in provider_rows:
        provider_total = int(getattr(provider_row, "total_records", 0) or 0)
        provider_normalized = int(getattr(provider_row, "normalized_records", 0) or 0)
        provider_mapped = int(getattr(provider_row, "mapped_records", 0) or 0)
        provider_breakdown.append(
            {
                "provider": str(getattr(provider_row, "provider", "") or "unknown"),
                "total_records": provider_total,
                "normalized_percentage": round(
                    (provider_normalized / provider_total * 100.0)
                    if provider_total > 0
                    else 0.0,
                    2,
                ),
                "mapped_percentage": round(
                    (provider_mapped / provider_total * 100.0)
                    if provider_total > 0
                    else 0.0,
                    2,
                ),
            }
        )
    ai_total = ai_quality_counts["total_records"]
    if ai_total > 0:
        provider_breakdown.append(
            {
                "provider": "ai",
                "total_records": ai_total,
                "normalized_percentage": round(
                    ai_quality_counts["normalized_records"] / ai_total * 100.0,
                    2,
                ),
                "mapped_percentage": round(
                    ai_quality_counts["mapped_records"] / ai_total * 100.0,
                    2,
                ),
            }
        )
        provider_breakdown.sort(key=lambda item: str(item["provider"]))

    top_unmapped_stmt = (
        select(
            CloudAccount.provider.label("provider"),
            CostRecord.service.label("service"),
            CostRecord.usage_type.label("usage_type"),
            func.count(CostRecord.id).label("record_count"),
            func.min(CostRecord.recorded_at).label("first_seen"),
            func.max(CostRecord.recorded_at).label("last_seen"),
        )
        .join(CloudAccount, CostRecord.account_id == CloudAccount.id)
        .where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
            ~mapped_filter,
        )
        .group_by(CloudAccount.provider, CostRecord.service, CostRecord.usage_type)
        .order_by(func.count(CostRecord.id).desc())
        .limit(10)
    )
    top_unmapped_rows = (await db.execute(top_unmapped_stmt)).all()
    top_unmapped_signatures: list[dict[str, Any]] = []
    for unmapped_row in top_unmapped_rows:
        first_seen = getattr(unmapped_row, "first_seen", None)
        last_seen = getattr(unmapped_row, "last_seen", None)
        top_unmapped_signatures.append(
            {
                "provider": str(getattr(unmapped_row, "provider", "") or "unknown"),
                "service": str(getattr(unmapped_row, "service", "") or "Unknown"),
                "usage_type": str(getattr(unmapped_row, "usage_type", "") or "Unknown"),
                "record_count": int(getattr(unmapped_row, "record_count", 0) or 0),
                "first_seen": first_seen.isoformat() if first_seen else None,
                "last_seen": last_seen.isoformat() if last_seen else None,
            }
        )

    return [
        AcceptanceKpiMetric(
            key="ledger_normalization_coverage",
            label="Ledger Normalization Coverage",
            available=True,
            target=f">={ledger_normalization_target_percent:.2f}%",
            actual=f"{normalized_pct:.2f}%",
            meets_target=normalized_pct >= ledger_normalization_target_percent,
            details={
                "total_records": total,
                "normalized_records": normalized_count,
                "normalized_percentage": round(normalized_pct, 2),
                "unknown_service_records": unknown_service_count,
                "invalid_currency_records": invalid_currency_count,
                "usage_unit_missing_records": usage_unit_missing_count,
                "ai_records": ai_quality_counts["total_records"],
                "ai_invalid_provider_records": ai_quality_counts[
                    "invalid_provider_records"
                ],
                "ai_invalid_model_records": ai_quality_counts["invalid_model_records"],
                "provider_breakdown": provider_breakdown,
            },
        ),
        AcceptanceKpiMetric(
            key="canonical_mapping_coverage",
            label="Canonical Mapping Coverage",
            available=True,
            target=f">={canonical_mapping_target_percent:.2f}%",
            actual=f"{mapped_pct:.2f}%",
            meets_target=mapped_pct >= canonical_mapping_target_percent,
            details={
                "total_records": total,
                "mapped_records": mapped_count,
                "unmapped_records": max(total - mapped_count, 0),
                "mapped_percentage": round(mapped_pct, 2),
                "target_percentage": float(canonical_mapping_target_percent),
                "provider_breakdown": provider_breakdown,
                "top_unmapped_signatures": top_unmapped_signatures,
            },
        ),
    ]
