"""CSV export helpers for reconciliation and close-package outputs."""

from __future__ import annotations

import csv
import io
from datetime import date
from typing import Any


def render_close_package_csv(
    tenant_id: str,
    start_date: date,
    end_date: date,
    close_status: str,
    lifecycle_summary: dict[str, Any],
    reconciliation_summary: dict[str, Any],
    invoice_reconciliation: dict[str, Any] | None,
    restatement_entries: list[dict[str, Any]],
) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["section", "key", "value"])
    writer.writerow(["meta", "tenant_id", tenant_id])
    writer.writerow(["meta", "start_date", start_date.isoformat()])
    writer.writerow(["meta", "end_date", end_date.isoformat()])
    writer.writerow(["meta", "close_status", close_status])

    for key, value in lifecycle_summary.items():
        writer.writerow(["lifecycle", key, value])

    for key, value in reconciliation_summary.items():
        if key in {"impacted_services", "discrepancies"}:
            continue
        writer.writerow(["reconciliation", key, value])

    if isinstance(invoice_reconciliation, dict) and invoice_reconciliation:
        writer.writerow(
            [
                "invoice_reconciliation",
                "status",
                invoice_reconciliation.get("status"),
            ]
        )
        writer.writerow(
            [
                "invoice_reconciliation",
                "threshold_percent",
                invoice_reconciliation.get("threshold_percent"),
            ]
        )
        writer.writerow(
            [
                "invoice_reconciliation",
                "ledger_final_cost_usd",
                invoice_reconciliation.get("ledger_final_cost_usd"),
            ]
        )
        if invoice_reconciliation.get("status") != "missing_invoice":
            writer.writerow(
                [
                    "invoice_reconciliation",
                    "delta_usd",
                    invoice_reconciliation.get("delta_usd"),
                ]
            )
            writer.writerow(
                [
                    "invoice_reconciliation",
                    "absolute_delta_usd",
                    invoice_reconciliation.get("absolute_delta_usd"),
                ]
            )
            writer.writerow(
                [
                    "invoice_reconciliation",
                    "delta_percent",
                    invoice_reconciliation.get("delta_percent"),
                ]
            )
        invoice_obj = invoice_reconciliation.get("invoice")
        if isinstance(invoice_obj, dict):
            writer.writerow(
                [
                    "invoice_reconciliation",
                    "invoice_number",
                    invoice_obj.get("invoice_number"),
                ]
            )
            writer.writerow(
                [
                    "invoice_reconciliation",
                    "invoice_currency",
                    invoice_obj.get("currency"),
                ]
            )
            writer.writerow(
                [
                    "invoice_reconciliation",
                    "invoice_total_amount",
                    invoice_obj.get("total_amount"),
                ]
            )
            writer.writerow(
                [
                    "invoice_reconciliation",
                    "invoice_total_amount_usd",
                    invoice_obj.get("total_amount_usd"),
                ]
            )
            writer.writerow(
                [
                    "invoice_reconciliation",
                    "invoice_status",
                    invoice_obj.get("status"),
                ]
            )

    writer.writerow([])
    writer.writerow(
        [
            "restatements",
            "usage_date",
            "recorded_at",
            "service",
            "region",
            "old_cost",
            "new_cost",
            "delta_usd",
            "reason",
            "cost_record_id",
            "ingestion_batch_id",
        ]
    )
    for entry in restatement_entries:
        writer.writerow(
            [
                "restatements",
                entry["usage_date"],
                entry["recorded_at"],
                entry["service"],
                entry["region"],
                entry["old_cost"],
                entry["new_cost"],
                entry["delta_usd"],
                entry["reason"],
                entry["cost_record_id"],
                entry["ingestion_batch_id"],
            ]
        )
    return out.getvalue()


def render_restatements_csv(entries: list[dict[str, Any]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "usage_date",
            "recorded_at",
            "service",
            "region",
            "old_cost",
            "new_cost",
            "delta_usd",
            "reason",
            "cost_record_id",
            "ingestion_batch_id",
        ]
    )
    for entry in entries:
        writer.writerow(
            [
                entry["usage_date"],
                entry["recorded_at"],
                entry["service"],
                entry["region"],
                entry["old_cost"],
                entry["new_cost"],
                entry["delta_usd"],
                entry["reason"],
                entry["cost_record_id"],
                entry["ingestion_batch_id"],
            ]
        )
    return out.getvalue()


def render_restatement_runs_csv(runs: list[dict[str, Any]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        [
            "ingestion_batch_id",
            "entry_count",
            "net_delta_usd",
            "absolute_delta_usd",
            "first_recorded_at",
            "last_recorded_at",
            "integrity_hash",
        ]
    )
    for run in runs:
        writer.writerow(
            [
                run.get("ingestion_batch_id"),
                run.get("entry_count"),
                run.get("net_delta_usd"),
                run.get("absolute_delta_usd"),
                run.get("first_recorded_at"),
                run.get("last_recorded_at"),
                run.get("integrity_hash"),
            ]
        )
    return out.getvalue()
