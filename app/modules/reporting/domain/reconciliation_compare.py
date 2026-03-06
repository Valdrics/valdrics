from __future__ import annotations

from datetime import date
from typing import Any, Dict
from uuid import UUID

from sqlalchemy import func, select

from app.models.cloud import CloudAccount, CostRecord


async def compare_explorer_vs_cur_impl(
    service: Any,
    *,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
    alert_threshold_pct: float,
    provider: str | None,
    recoverable_alert_errors: tuple[type[Exception], ...],
    log: Any,
) -> Dict[str, Any]:
    normalized_provider = service._normalize_provider(provider)
    source_expr = func.coalesce(
        func.lower(CostRecord.ingestion_metadata["source_adapter"].as_string()),
        "unknown",
    )
    stmt = (
        select(
            CostRecord.service.label("service"),
            source_expr.label("source_adapter"),
            func.sum(CostRecord.cost_usd).label("total_cost"),
            func.count(CostRecord.id).label("record_count"),
        )
        .where(
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
        )
        .group_by(CostRecord.service, source_expr)
    )
    if normalized_provider:
        stmt = stmt.join(CloudAccount, CostRecord.account_id == CloudAccount.id).where(
            CloudAccount.provider == normalized_provider
        )

    result = await service.db.execute(stmt)
    rows = result.all()

    total_records = 0
    total_cost = 0.0
    by_service: dict[str, dict[str, float]] = {}
    by_service_records: dict[str, dict[str, int]] = {}

    comparison_basis = "explorer_vs_cur"
    expected_primary_source = "cur"
    expected_secondary_source = "explorer"
    if normalized_provider in {"saas", "license", "platform", "hybrid"}:
        comparison_basis = "native_vs_feed"
        expected_primary_source = "native"
        expected_secondary_source = "feed"

    for row in rows:
        service_name = str(getattr(row, "service", "") or "Unknown")
        if normalized_provider in {"saas", "license", "platform", "hybrid"}:
            source_name = service._normalize_cloud_plus_source(
                getattr(row, "source_adapter", None), normalized_provider
            )
        else:
            source_name = service._normalize_source(getattr(row, "source_adapter", None))
        row_cost = float(getattr(row, "total_cost", 0) or 0)
        row_records = int(getattr(row, "record_count", 0) or 0)

        total_records += row_records
        total_cost += row_cost

        by_service.setdefault(service_name, {})
        by_service_records.setdefault(service_name, {})
        by_service[service_name][source_name] = (
            by_service[service_name].get(source_name, 0.0) + row_cost
        )
        by_service_records[service_name][source_name] = (
            by_service_records[service_name].get(source_name, 0) + row_records
        )

    impacted_services: list[dict[str, Any]] = []
    total_cur = 0.0
    total_explorer = 0.0
    comparable_record_count = 0

    for service_name, sources in by_service.items():
        if (
            expected_primary_source not in sources
            or expected_secondary_source not in sources
        ):
            continue

        primary_cost = float(sources[expected_primary_source])
        secondary_cost = float(sources[expected_secondary_source])
        delta_usd = secondary_cost - primary_cost
        denominator = abs(primary_cost) if abs(primary_cost) > 0 else max(abs(secondary_cost), 1.0)
        discrepancy_pct = abs(delta_usd) / denominator * 100

        total_cur += primary_cost
        total_explorer += secondary_cost
        comparable_record_count += by_service_records[service_name].get(
            expected_primary_source, 0
        ) + by_service_records[service_name].get(expected_secondary_source, 0)

        payload: dict[str, Any] = {
            "service": service_name,
            "delta_usd": round(delta_usd, 6),
            "discrepancy_percentage": round(discrepancy_pct, 4),
        }
        if comparison_basis == "native_vs_feed":
            payload["native_cost"] = round(primary_cost, 6)
            payload["feed_cost"] = round(secondary_cost, 6)
        else:
            payload["cur_cost"] = round(primary_cost, 6)
            payload["explorer_cost"] = round(secondary_cost, 6)
        impacted_services.append(payload)

    comparable_services = len(impacted_services)
    if comparable_services > 0:
        overall_denominator = abs(total_cur) if abs(total_cur) > 0 else max(abs(total_explorer), 1.0)
        overall_discrepancy_pct = abs(total_explorer - total_cur) / overall_denominator * 100
        status = "warning" if overall_discrepancy_pct > alert_threshold_pct else "healthy"
    else:
        overall_discrepancy_pct = 0.0
        status = "no_comparable_data"

    confidence = service._compute_confidence(
        total_service_count=len(by_service),
        comparable_service_count=comparable_services,
        comparable_record_count=comparable_record_count,
    )

    threshold_discrepancies = [
        impacted
        for impacted in impacted_services
        if impacted["discrepancy_percentage"] > alert_threshold_pct
    ]
    alert_triggered = False
    alert_error: str | None = None
    if overall_discrepancy_pct > alert_threshold_pct and comparable_services > 0:
        from app.shared.core.notifications import NotificationDispatcher

        try:
            await NotificationDispatcher.send_alert(
                title=f"Cost reconciliation variance {overall_discrepancy_pct:.2f}% (tenant {tenant_id})",
                message=(
                    f"Reconciliation variance exceeded {alert_threshold_pct:.2f}% "
                    f"for {start_date} to {end_date}. "
                    f"Impacted services: {', '.join(s['service'] for s in threshold_discrepancies[:5]) or 'n/a'}."
                ),
                severity="warning",
                tenant_id=str(tenant_id),
                db=service.db,
            )
            alert_triggered = True
        except recoverable_alert_errors as exc:  # pragma: no cover
            alert_error = str(exc)
            log.warning(
                "cost_reconciliation_alert_failed",
                tenant_id=str(tenant_id),
                error=alert_error,
            )

    summary: Dict[str, Any] = {
        "tenant_id": str(tenant_id),
        "provider_scope": normalized_provider or "all",
        "period": f"{start_date} to {end_date}",
        "comparison_basis": comparison_basis,
        "status": status,
        "total_records": total_records,
        "total_cost": round(total_cost, 6),
        "threshold_percentage": alert_threshold_pct,
        "discrepancy_percentage": round(overall_discrepancy_pct, 4),
        "confidence": confidence,
        "impacted_services": impacted_services,
        "discrepancies": threshold_discrepancies,
        "source_totals": {
            expected_secondary_source: round(total_explorer, 6),
            expected_primary_source: round(total_cur, 6),
        },
        "alert_triggered": alert_triggered,
    }
    if alert_error:
        summary["alert_error"] = alert_error

    log.info(
        "cost_reconciliation_summary_generated",
        tenant_id=str(tenant_id),
        cost=summary["total_cost"],
        discrepancy_percentage=summary["discrepancy_percentage"],
        status=status,
        confidence=confidence,
    )
    return summary
