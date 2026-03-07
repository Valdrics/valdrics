"""Database query helpers for finance telemetry snapshot collection."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import bindparam, text
from sqlalchemy.ext.asyncio import AsyncSession


async def fetch_subscription_snapshot(
    db: AsyncSession,
    *,
    window_start: datetime,
    window_end_exclusive: datetime,
    tracked_tiers: tuple[str, ...],
    active_subscription_statuses: tuple[str, ...],
) -> dict[str, dict[str, int]]:
    query = text(
        """
        WITH effective_tiers AS (
            SELECT
                t.id AS tenant_id,
                LOWER(COALESCE(NULLIF(ts.tier, ''), NULLIF(t.plan, ''), 'free')) AS tier,
                LOWER(COALESCE(ts.status, 'active')) AS subscription_status,
                ts.last_dunning_at AS last_dunning_at
            FROM tenants t
            LEFT JOIN tenant_subscriptions ts ON ts.tenant_id = t.id
            WHERE COALESCE(t.is_deleted, FALSE) = FALSE
        )
        SELECT
            tier,
            COUNT(*) AS total_tenants,
            SUM(
                CASE
                    WHEN subscription_status IN :active_statuses THEN 1
                    ELSE 0
                END
            ) AS active_subscriptions,
            SUM(
                CASE
                    WHEN last_dunning_at IS NOT NULL
                         AND last_dunning_at >= :window_start
                         AND last_dunning_at < :window_end_exclusive
                    THEN 1
                    ELSE 0
                END
            ) AS dunning_events
        FROM effective_tiers
        GROUP BY tier
        """
    ).bindparams(
        bindparam(
            "active_statuses",
            value=active_subscription_statuses,
            expanding=True,
        )
    )
    result = await db.execute(
        query,
        {
            "window_start": window_start,
            "window_end_exclusive": window_end_exclusive,
        },
    )
    rows = result.fetchall()

    snapshot: dict[str, dict[str, int]] = {
        tier: {"total_tenants": 0, "active_subscriptions": 0, "dunning_events": 0}
        for tier in tracked_tiers
    }
    for row in rows:
        tier = str(row.tier or "").strip().lower()
        if tier not in snapshot:
            continue
        snapshot[tier] = {
            "total_tenants": int(row.total_tenants or 0),
            "active_subscriptions": int(row.active_subscriptions or 0),
            "dunning_events": int(row.dunning_events or 0),
        }
    return snapshot


async def fetch_llm_usage_snapshot(
    db: AsyncSession,
    *,
    window_start: datetime,
    window_end_exclusive: datetime,
    tracked_tiers: tuple[str, ...],
    to_float_fn: Any,
    percentile_fn: Any,
) -> dict[str, dict[str, float]]:
    query = text(
        """
        WITH effective_tiers AS (
            SELECT
                t.id AS tenant_id,
                LOWER(COALESCE(NULLIF(ts.tier, ''), NULLIF(t.plan, ''), 'free')) AS tier
            FROM tenants t
            LEFT JOIN tenant_subscriptions ts ON ts.tenant_id = t.id
            WHERE COALESCE(t.is_deleted, FALSE) = FALSE
        )
        SELECT
            e.tier AS tier,
            e.tenant_id AS tenant_id,
            COALESCE(SUM(lu.cost_usd), 0) AS tenant_monthly_cost_usd
        FROM effective_tiers e
        LEFT JOIN llm_usage lu
            ON lu.tenant_id = e.tenant_id
           AND lu.created_at >= :window_start
           AND lu.created_at < :window_end_exclusive
        GROUP BY e.tier, e.tenant_id
        """
    )
    result = await db.execute(
        query,
        {
            "window_start": window_start,
            "window_end_exclusive": window_end_exclusive,
        },
    )
    rows = result.fetchall()

    tier_costs: dict[str, list[float]] = {tier: [] for tier in tracked_tiers}
    for row in rows:
        tier = str(row.tier or "").strip().lower()
        if tier not in tier_costs:
            continue
        tier_costs[tier].append(float(to_float_fn(row.tenant_monthly_cost_usd)))

    snapshot: dict[str, dict[str, float]] = {}
    for tier in tracked_tiers:
        values = tier_costs[tier]
        total_cost = sum(values)
        snapshot[tier] = {
            "total_cost_usd": round(total_cost, 6),
            "p50": round(float(percentile_fn(values, 50.0)), 6),
            "p95": round(float(percentile_fn(values, 95.0)), 6),
            "p99": round(float(percentile_fn(values, 99.0)), 6),
        }
    return snapshot
