"""Bulk upsert operations for cost persistence."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import case, func, literal, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.cloud import CostRecord
from app.shared.core.async_utils import maybe_await


async def bulk_upsert(db: AsyncSession, values: list[dict[str, Any]]) -> None:
    """Persist cost rows with idempotent upsert semantics across DB backends."""
    if not values:
        return
    bind_url = str(getattr(getattr(db, "bind", None), "url", ""))
    if not bind_url:
        bind = await maybe_await(db.get_bind())
        bind_url = str(getattr(bind, "url", ""))

    if "postgresql" in bind_url:
        stmt = pg_insert(CostRecord).values(values)
        incoming_status = stmt.excluded.cost_status
        is_preliminary_update = case(
            (incoming_status == "FINAL", literal(False)),
            (CostRecord.cost_status == "FINAL", CostRecord.is_preliminary),
            else_=stmt.excluded.is_preliminary,
        )
        cost_status_update = case(
            (incoming_status == "FINAL", literal("FINAL")),
            (CostRecord.cost_status == "FINAL", CostRecord.cost_status),
            else_=incoming_status,
        )
        reconciliation_run_update = func.coalesce(
            stmt.excluded.reconciliation_run_id,
            CostRecord.reconciliation_run_id,
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uix_account_cost_granularity",
            set_={
                "resource_id": stmt.excluded.resource_id,
                "usage_amount": stmt.excluded.usage_amount,
                "usage_unit": stmt.excluded.usage_unit,
                "cost_usd": stmt.excluded.cost_usd,
                "amount_raw": stmt.excluded.amount_raw,
                "currency": stmt.excluded.currency,
                "usage_type": stmt.excluded.usage_type,
                "canonical_charge_category": stmt.excluded.canonical_charge_category,
                "canonical_charge_subcategory": stmt.excluded.canonical_charge_subcategory,
                "canonical_mapping_version": stmt.excluded.canonical_mapping_version,
                "is_preliminary": is_preliminary_update,
                "cost_status": cost_status_update,
                "reconciliation_run_id": reconciliation_run_update,
                "ingestion_metadata": stmt.excluded.ingestion_metadata,
                "tags": stmt.excluded.tags,
            },
        )
        await db.execute(stmt)
        return

    for val in values:
        select_stmt = select(CostRecord).where(
            CostRecord.account_id == val["account_id"],
            CostRecord.recorded_at == val["recorded_at"],
            CostRecord.timestamp == val["timestamp"],
            CostRecord.service == val["service"],
            CostRecord.region == val["region"],
            CostRecord.usage_type == val["usage_type"],
            CostRecord.resource_id == val.get("resource_id", ""),
        )
        res = await db.execute(select_stmt)
        scalars_result = await maybe_await(res.scalars())
        existing = await maybe_await(scalars_result.first())

        if existing:
            if "resource_id" in val and val["resource_id"] is not None:
                existing.resource_id = str(val["resource_id"])
            if val.get("usage_amount") is not None:
                existing.usage_amount = Decimal(str(val["usage_amount"]))
            if val.get("usage_unit") is not None:
                existing.usage_unit = str(val["usage_unit"])
            if val.get("cost_usd") is not None:
                existing.cost_usd = Decimal(str(val["cost_usd"]))
            if val.get("amount_raw") is not None:
                existing.amount_raw = Decimal(str(val["amount_raw"]))
            if val.get("currency") is not None:
                existing.currency = str(val["currency"])
            if val.get("usage_type") is not None:
                existing.usage_type = val["usage_type"]
            if val.get("canonical_charge_category") is not None:
                existing.canonical_charge_category = val["canonical_charge_category"]
            if "canonical_charge_subcategory" in val:
                existing.canonical_charge_subcategory = val[
                    "canonical_charge_subcategory"
                ]
            if val.get("canonical_mapping_version") is not None:
                existing.canonical_mapping_version = val["canonical_mapping_version"]

            incoming_status_val = str(
                val.get("cost_status") or existing.cost_status or "PRELIMINARY"
            )
            if incoming_status_val == "FINAL":
                existing.cost_status = "FINAL"
                existing.is_preliminary = False
            elif str(getattr(existing, "cost_status", "")) == "FINAL":
                existing.cost_status = "FINAL"
                existing.is_preliminary = False
            else:
                existing.cost_status = incoming_status_val
                existing.is_preliminary = bool(
                    val.get("is_preliminary", existing.is_preliminary)
                )

            if val.get("reconciliation_run_id") is not None:
                existing.reconciliation_run_id = val.get("reconciliation_run_id")
            existing.ingestion_metadata = val.get("ingestion_metadata")
            existing.tags = val.get("tags")
        else:
            db.add(CostRecord(**val))

    await db.flush()


__all__ = ["bulk_upsert"]
