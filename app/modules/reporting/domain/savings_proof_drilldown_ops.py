from __future__ import annotations

from datetime import datetime
from typing import Any, Callable
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.optimization import OptimizationStrategy, StrategyRecommendation
from app.models.realized_savings import RealizedSavingsEvent
from app.models.remediation import RemediationRequest, RemediationStatus


async def build_strategy_type_buckets(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    normalized_provider: str | None,
    window_start: datetime,
    window_end: datetime,
    ensure_bucket: Callable[[str], dict[str, Any]],
    as_float: Callable[[Any], float],
) -> list[str]:
    # Opportunity: open recommendations (as-of now), grouped by strategy.type.
    open_stmt = (
        select(
            OptimizationStrategy.type,
            func.coalesce(func.sum(StrategyRecommendation.estimated_monthly_savings), 0),
            func.count(StrategyRecommendation.id),
        )
        .join(
            OptimizationStrategy,
            StrategyRecommendation.strategy_id == OptimizationStrategy.id,
        )
        .where(
            StrategyRecommendation.tenant_id == tenant_id,
            StrategyRecommendation.status == "open",
        )
        .group_by(OptimizationStrategy.type)
    )
    if normalized_provider:
        open_stmt = open_stmt.where(OptimizationStrategy.provider == normalized_provider)
    open_rows = list((await db.execute(open_stmt)).all())
    for strategy_type, savings_sum, count in open_rows:
        key = str(getattr(strategy_type, "value", strategy_type)).lower()
        bucket = ensure_bucket(key)
        bucket["open_recommendations"] += int(count or 0)
        bucket["opportunity_monthly_usd"] += as_float(savings_sum)

    # Realized: applied recommendations within window, grouped by strategy.type.
    applied_stmt = (
        select(
            OptimizationStrategy.type,
            func.coalesce(func.sum(StrategyRecommendation.estimated_monthly_savings), 0),
            func.count(StrategyRecommendation.id),
        )
        .join(
            OptimizationStrategy,
            StrategyRecommendation.strategy_id == OptimizationStrategy.id,
        )
        .where(
            StrategyRecommendation.tenant_id == tenant_id,
            StrategyRecommendation.status == "applied",
            StrategyRecommendation.applied_at.is_not(None),
            StrategyRecommendation.applied_at >= window_start,
            StrategyRecommendation.applied_at <= window_end,
        )
        .group_by(OptimizationStrategy.type)
    )
    if normalized_provider:
        applied_stmt = applied_stmt.where(
            OptimizationStrategy.provider == normalized_provider
        )
    applied_rows = list((await db.execute(applied_stmt)).all())
    for strategy_type, savings_sum, count in applied_rows:
        key = str(getattr(strategy_type, "value", strategy_type)).lower()
        bucket = ensure_bucket(key)
        bucket["applied_recommendations"] += int(count or 0)
        bucket["realized_monthly_usd"] += as_float(savings_sum)

    return [
        "Opportunity is a snapshot of currently open recommendations, grouped by strategy type.",
        "Realized is applied recommendations within the window (estimated monthly savings).",
    ]


async def build_remediation_action_buckets(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    normalized_provider: str | None,
    window_start: datetime,
    window_end: datetime,
    ensure_bucket: Callable[[str], dict[str, Any]],
    as_float: Callable[[Any], float],
) -> list[str]:
    pending_statuses = {
        RemediationStatus.PENDING.value,
        RemediationStatus.PENDING_APPROVAL.value,
        RemediationStatus.APPROVED.value,
        RemediationStatus.SCHEDULED.value,
        RemediationStatus.EXECUTING.value,
    }

    pending_stmt = (
        select(
            RemediationRequest.action,
            func.coalesce(func.sum(RemediationRequest.estimated_monthly_savings), 0),
            func.count(RemediationRequest.id),
        )
        .where(
            RemediationRequest.tenant_id == tenant_id,
            RemediationRequest.status.in_(pending_statuses),
        )
        .group_by(RemediationRequest.action)
    )
    if normalized_provider:
        pending_stmt = pending_stmt.where(
            RemediationRequest.provider == normalized_provider
        )
    pending_rows = list((await db.execute(pending_stmt)).all())
    for action, savings_sum, count in pending_rows:
        key = str(getattr(action, "value", action)).lower()
        bucket = ensure_bucket(key)
        bucket["pending_remediations"] += int(count or 0)
        bucket["opportunity_monthly_usd"] += as_float(savings_sum)

    completed_at = func.coalesce(
        RemediationRequest.executed_at,
        RemediationRequest.updated_at,
        RemediationRequest.created_at,
    )

    completed_count_stmt = (
        select(
            RemediationRequest.action,
            func.count(RemediationRequest.id),
        )
        .where(
            RemediationRequest.tenant_id == tenant_id,
            RemediationRequest.status == RemediationStatus.COMPLETED.value,
            completed_at >= window_start,
            completed_at <= window_end,
        )
        .group_by(RemediationRequest.action)
    )
    if normalized_provider:
        completed_count_stmt = completed_count_stmt.where(
            RemediationRequest.provider == normalized_provider
        )
    completed_count_rows = list((await db.execute(completed_count_stmt)).all())
    for action, count in completed_count_rows:
        key = str(getattr(action, "value", action)).lower()
        bucket = ensure_bucket(key)
        bucket["completed_remediations"] += int(count or 0)

    evidence_stmt = (
        select(
            RemediationRequest.action,
            func.coalesce(func.sum(RealizedSavingsEvent.realized_monthly_savings_usd), 0),
        )
        .join(
            RealizedSavingsEvent,
            (RealizedSavingsEvent.remediation_request_id == RemediationRequest.id)
            & (RealizedSavingsEvent.tenant_id == RemediationRequest.tenant_id),
        )
        .where(
            RemediationRequest.tenant_id == tenant_id,
            RemediationRequest.status == RemediationStatus.COMPLETED.value,
            completed_at >= window_start,
            completed_at <= window_end,
        )
        .group_by(RemediationRequest.action)
    )
    if normalized_provider:
        evidence_stmt = evidence_stmt.where(
            RemediationRequest.provider == normalized_provider
        )
    evidence_rows = list((await db.execute(evidence_stmt)).all())
    for action, savings_sum in evidence_rows:
        key = str(getattr(action, "value", action)).lower()
        bucket = ensure_bucket(key)
        bucket["realized_monthly_usd"] += as_float(savings_sum)

    fallback_stmt = (
        select(
            RemediationRequest.action,
            func.coalesce(func.sum(RemediationRequest.estimated_monthly_savings), 0),
        )
        .outerjoin(
            RealizedSavingsEvent,
            (RealizedSavingsEvent.remediation_request_id == RemediationRequest.id)
            & (RealizedSavingsEvent.tenant_id == RemediationRequest.tenant_id),
        )
        .where(
            RemediationRequest.tenant_id == tenant_id,
            RemediationRequest.status == RemediationStatus.COMPLETED.value,
            completed_at >= window_start,
            completed_at <= window_end,
            RealizedSavingsEvent.id.is_(None),
        )
        .group_by(RemediationRequest.action)
    )
    if normalized_provider:
        fallback_stmt = fallback_stmt.where(
            RemediationRequest.provider == normalized_provider
        )
    fallback_rows = list((await db.execute(fallback_stmt)).all())
    for action, savings_sum in fallback_rows:
        key = str(getattr(action, "value", action)).lower()
        bucket = ensure_bucket(key)
        bucket["realized_monthly_usd"] += as_float(savings_sum)

    return [
        "Opportunity is a snapshot of pending/approved/scheduled remediations, grouped by action.",
        "Realized uses finance-grade ledger deltas where evidence exists; otherwise it falls back to estimated monthly savings.",
    ]


def sort_and_limit_buckets(
    buckets_by_key: dict[str, dict[str, Any]], *, top_limit: int
) -> tuple[list[tuple[str, dict[str, Any]]], bool]:
    bucket_items = sorted(
        buckets_by_key.items(),
        key=lambda item: (
            item[1]["opportunity_monthly_usd"],
            item[1]["realized_monthly_usd"],
            item[0],
        ),
        reverse=True,
    )
    truncated = len(bucket_items) > top_limit
    return bucket_items[:top_limit], truncated
