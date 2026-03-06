from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import and_, func, select

from app.models.cloud import CloudAccount, CostRecord
from app.models.cost_audit import CostAuditLog


async def get_restatement_history_impl(
    service: Any,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    export_csv: bool = False,
    provider: str | None = None,
) -> Dict[str, Any]:
    normalized_provider = service._normalize_provider(provider)
    stmt = (
        select(
            CostAuditLog.recorded_at.label("audit_recorded_at"),
            CostAuditLog.cost_record_id.label("cost_record_id"),
            CostAuditLog.old_cost.label("old_cost"),
            CostAuditLog.new_cost.label("new_cost"),
            CostAuditLog.reason.label("reason"),
            CostAuditLog.ingestion_batch_id.label("ingestion_batch_id"),
            CostRecord.service.label("service"),
            CostRecord.region.label("region"),
            CostRecord.recorded_at.label("usage_date"),
        )
        .join(
            CostRecord,
            and_(
                CostAuditLog.cost_record_id == CostRecord.id,
                CostAuditLog.cost_recorded_at == CostRecord.recorded_at,
            ),
        )
        .where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
        )
    )
    if normalized_provider:
        stmt = stmt.join(CloudAccount, CostRecord.account_id == CloudAccount.id).where(
            CloudAccount.provider == normalized_provider
        )
    result = await service.db.execute(stmt)
    rows = sorted(
        result.all(),
        key=lambda row: (
            str(getattr(row, "usage_date", "")),
            str(getattr(row, "service", "")),
            str(getattr(row, "cost_record_id", "")),
        ),
    )

    entries: list[Dict[str, Any]] = []
    net_delta = Decimal("0")
    abs_delta = Decimal("0")
    for row in rows:
        old_cost = Decimal(str(getattr(row, "old_cost", 0) or 0))
        new_cost = Decimal(str(getattr(row, "new_cost", 0) or 0))
        delta = new_cost - old_cost
        net_delta += delta
        abs_delta += abs(delta)
        usage_date_obj = getattr(row, "usage_date", None)
        audit_recorded_at = getattr(row, "audit_recorded_at", None)

        entries.append(
            {
                "usage_date": usage_date_obj.isoformat()
                if usage_date_obj is not None
                else None,
                "recorded_at": audit_recorded_at.isoformat()
                if audit_recorded_at is not None
                else None,
                "service": str(getattr(row, "service", "") or "Unknown"),
                "region": str(getattr(row, "region", "") or "Global"),
                "old_cost": float(old_cost),
                "new_cost": float(new_cost),
                "delta_usd": float(delta),
                "reason": str(getattr(row, "reason", "") or "RE-INGESTION"),
                "cost_record_id": str(getattr(row, "cost_record_id", "") or ""),
                "ingestion_batch_id": str(getattr(row, "ingestion_batch_id", "") or ""),
            }
        )

    payload: Dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "provider": normalized_provider,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "restatement_count": len(entries),
        "net_delta_usd": float(net_delta),
        "absolute_delta_usd": float(abs_delta),
        "entries": entries,
    }
    if export_csv:
        payload["csv"] = service._render_restatements_csv(entries)
    return payload


async def get_restatement_runs_impl(
    service: Any,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    export_csv: bool = False,
    provider: str | None = None,
) -> Dict[str, Any]:
    normalized_provider = service._normalize_provider(provider)
    delta_expr = CostAuditLog.new_cost - CostAuditLog.old_cost

    stmt = (
        select(
            CostAuditLog.ingestion_batch_id.label("ingestion_batch_id"),
            func.count(CostAuditLog.id).label("entry_count"),
            func.coalesce(func.sum(delta_expr), 0).label("net_delta_usd"),
            func.coalesce(func.sum(func.abs(delta_expr)), 0).label("absolute_delta_usd"),
            func.min(CostAuditLog.recorded_at).label("first_recorded_at"),
            func.max(CostAuditLog.recorded_at).label("last_recorded_at"),
        )
        .join(
            CostRecord,
            and_(
                CostAuditLog.cost_record_id == CostRecord.id,
                CostAuditLog.cost_recorded_at == CostRecord.recorded_at,
            ),
        )
        .where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
        )
        .group_by(CostAuditLog.ingestion_batch_id)
    )
    if normalized_provider:
        stmt = stmt.join(CloudAccount, CostRecord.account_id == CloudAccount.id).where(
            CloudAccount.provider == normalized_provider
        )

    result = await service.db.execute(stmt)
    rows = list(result.all())
    rows.sort(
        key=lambda row: str(getattr(row, "last_recorded_at", "") or ""),
        reverse=True,
    )

    runs: list[Dict[str, Any]] = []
    for row in rows:
        ingestion_batch_id = getattr(row, "ingestion_batch_id", None)
        payload = {
            "ingestion_batch_id": str(ingestion_batch_id) if ingestion_batch_id else None,
            "entry_count": service._to_int(getattr(row, "entry_count", 0)),
            "net_delta_usd": service._to_float(getattr(row, "net_delta_usd", 0)),
            "absolute_delta_usd": service._to_float(
                getattr(row, "absolute_delta_usd", 0)
            ),
            "first_recorded_at": (
                getattr(row, "first_recorded_at").isoformat()
                if getattr(row, "first_recorded_at", None) is not None
                else None
            ),
            "last_recorded_at": (
                getattr(row, "last_recorded_at").isoformat()
                if getattr(row, "last_recorded_at", None) is not None
                else None
            ),
        }
        payload["integrity_hash"] = service._stable_hash(payload)
        runs.append(payload)

    response: Dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "provider": normalized_provider,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "run_count": len(runs),
        "runs": runs,
    }
    if export_csv:
        response["csv"] = service._render_restatement_runs_csv(runs)
    return response
