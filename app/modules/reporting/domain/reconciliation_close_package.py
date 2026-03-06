from __future__ import annotations

from datetime import date
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import func, select

from app.models.cloud import CloudAccount, CostRecord


async def generate_close_package_impl(
    service: Any,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    enforce_finalized: bool = True,
    provider: str | None = None,
    max_restatement_entries: int | None = None,
) -> Dict[str, Any]:
    normalized_provider = service._normalize_provider(provider)
    lifecycle_stmt = select(
        func.count(CostRecord.id).label("total_records"),
        func.count(CostRecord.id)
        .filter(CostRecord.cost_status == "PRELIMINARY")
        .label("preliminary_records"),
        func.count(CostRecord.id)
        .filter(CostRecord.cost_status == "FINAL")
        .label("final_records"),
        func.coalesce(func.sum(CostRecord.cost_usd), 0).label("total_cost_usd"),
        func.coalesce(
            func.sum(CostRecord.cost_usd).filter(CostRecord.cost_status == "PRELIMINARY"),
            0,
        ).label("preliminary_cost_usd"),
        func.coalesce(
            func.sum(CostRecord.cost_usd).filter(CostRecord.cost_status == "FINAL"),
            0,
        ).label("final_cost_usd"),
    ).where(
        CostRecord.tenant_id == tenant_id,
        CostRecord.recorded_at >= start_date,
        CostRecord.recorded_at <= end_date,
    )
    if normalized_provider:
        lifecycle_stmt = lifecycle_stmt.join(
            CloudAccount, CostRecord.account_id == CloudAccount.id
        ).where(CloudAccount.provider == normalized_provider)
    lifecycle_result = await service.db.execute(lifecycle_stmt)
    lifecycle_row = lifecycle_result.one()

    lifecycle_summary = {
        "total_records": service._to_int(getattr(lifecycle_row, "total_records", 0)),
        "preliminary_records": service._to_int(
            getattr(lifecycle_row, "preliminary_records", 0)
        ),
        "final_records": service._to_int(getattr(lifecycle_row, "final_records", 0)),
        "total_cost_usd": service._to_float(getattr(lifecycle_row, "total_cost_usd", 0)),
        "preliminary_cost_usd": service._to_float(
            getattr(lifecycle_row, "preliminary_cost_usd", 0)
        ),
        "final_cost_usd": service._to_float(getattr(lifecycle_row, "final_cost_usd", 0)),
    }
    preliminary_records = lifecycle_summary["preliminary_records"]
    close_status = "ready" if preliminary_records == 0 else "blocked_preliminary_data"
    if enforce_finalized and preliminary_records > 0:
        raise ValueError(
            "Cannot generate final close package while preliminary records exist in the selected period."
        )

    reconciliation_summary = await service.compare_explorer_vs_cur(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        provider=normalized_provider,
    )

    invoice_summary = None
    if normalized_provider:
        invoice_summary = await service.get_invoice_reconciliation_summary(
            tenant_id=tenant_id,
            provider=normalized_provider,
            start_date=start_date,
            end_date=end_date,
            ledger_final_cost_usd=float(lifecycle_summary.get("final_cost_usd") or 0.0),
        )
    restatement_payload = await service.get_restatement_history(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        export_csv=False,
        provider=normalized_provider,
    )
    restatement_entries = list(restatement_payload.get("entries") or [])
    restatement_total = len(restatement_entries)
    restatement_truncated = False
    if isinstance(max_restatement_entries, int) and max_restatement_entries >= 0:
        if restatement_total > max_restatement_entries:
            restatement_truncated = True
            restatement_entries = restatement_entries[:max_restatement_entries]

    package_core: Dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "provider": normalized_provider,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "close_status": close_status,
        "lifecycle": lifecycle_summary,
        "reconciliation": reconciliation_summary,
        "invoice_reconciliation": invoice_summary,
        "restatements": {
            "count": restatement_payload["restatement_count"],
            "included_count": len(restatement_entries),
            "truncated": restatement_truncated,
            "net_delta_usd": restatement_payload["net_delta_usd"],
            "absolute_delta_usd": restatement_payload["absolute_delta_usd"],
            "entries": restatement_entries,
        },
        "package_version": "reconciliation-v3",
    }
    package_hash = service._stable_hash(package_core)
    close_csv = service._render_close_package_csv(
        tenant_id=str(tenant_id),
        start_date=start_date,
        end_date=end_date,
        close_status=close_status,
        lifecycle_summary=lifecycle_summary,
        reconciliation_summary=reconciliation_summary,
        invoice_reconciliation=invoice_summary,
        restatement_entries=restatement_entries,
    )
    package_core["integrity_hash"] = package_hash
    package_core["csv"] = close_csv
    return package_core
