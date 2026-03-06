from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CloudAccount, CostRecord


async def get_canonical_data_quality(
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    provider: str | None,
) -> dict[str, Any]:
    """Returns canonical mapping coverage metrics."""
    mapped_filter = (CostRecord.canonical_charge_category.is_not(None)) & (
        func.lower(CostRecord.canonical_charge_category) != "unmapped"
    )
    stmt = select(
        func.count(CostRecord.id).label("total_records"),
        func.count(CostRecord.id).filter(mapped_filter).label("mapped_records"),
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

    total_records = int(row.total_records or 0) if row else 0
    mapped_records = int(row.mapped_records or 0) if row else 0
    unmapped_records = max(total_records - mapped_records, 0)
    mapped_pct = (mapped_records / total_records * 100) if total_records > 0 else 0.0
    target_pct = 99.0

    unmapped_filter = (CostRecord.canonical_charge_category.is_(None)) | (
        func.lower(CostRecord.canonical_charge_category) == "unmapped"
    )

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
            unmapped_filter,
        )
        .group_by(CloudAccount.provider, CostRecord.service, CostRecord.usage_type)
        .order_by(func.count(CostRecord.id).desc())
        .limit(10)
    )
    if provider:
        top_unmapped_stmt = top_unmapped_stmt.where(
            CloudAccount.provider == provider.lower()
        )

    top_unmapped_res = await db.execute(top_unmapped_stmt)
    top_unmapped_rows = top_unmapped_res.all()
    top_unmapped_signatures: list[dict[str, Any]] = []
    for row_item in top_unmapped_rows:
        first_seen = getattr(row_item, "first_seen", None)
        last_seen = getattr(row_item, "last_seen", None)
        top_unmapped_signatures.append(
            {
                "provider": str(getattr(row_item, "provider", "") or "unknown"),
                "service": str(getattr(row_item, "service", "") or "Unknown"),
                "usage_type": str(getattr(row_item, "usage_type", "") or "Unknown"),
                "record_count": int(getattr(row_item, "record_count", 0) or 0),
                "first_seen": first_seen.isoformat() if first_seen else None,
                "last_seen": last_seen.isoformat() if last_seen else None,
            }
        )

    reasons_stmt = (
        select(CostRecord.ingestion_metadata)
        .where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
            unmapped_filter,
        )
        .limit(5000)
    )
    if provider:
        reasons_stmt = reasons_stmt.join(
            CloudAccount, CostRecord.account_id == CloudAccount.id
        ).where(CloudAccount.provider == provider.lower())
    reasons_res = await db.execute(reasons_stmt)
    reason_counts: dict[str, int] = {}
    sampled_unmapped_records = 0
    for metadata in reasons_res.scalars().all():
        sampled_unmapped_records += 1
        if not isinstance(metadata, dict):
            continue
        canonical_meta = metadata.get("canonical_mapping")
        if not isinstance(canonical_meta, dict):
            continue
        reason = canonical_meta.get("unmapped_reason")
        reason_key = str(reason).strip() if reason is not None else ""
        if not reason_key:
            reason_key = "unknown"
        reason_counts[reason_key] = reason_counts.get(reason_key, 0) + 1

    return {
        "status": (
            "no_data"
            if total_records == 0
            else ("warning" if mapped_pct < target_pct else "ok")
        ),
        "target_percentage": target_pct,
        "total_records": total_records,
        "mapped_records": mapped_records,
        "unmapped_records": unmapped_records,
        "mapped_percentage": round(mapped_pct, 2),
        "target_gap_percentage": round(max(target_pct - mapped_pct, 0.0), 2),
        "meets_target": mapped_pct >= target_pct if total_records > 0 else False,
        "top_unmapped_signatures": top_unmapped_signatures,
        "unmapped_reason_breakdown": reason_counts,
        "sampled_unmapped_records": sampled_unmapped_records,
    }

