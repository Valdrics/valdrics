"""
Savings Proof (Domain)

Provides a procurement-friendly view of:
- Current savings opportunity (open recommendations + pending remediations)
- Estimated realized savings (applied recommendations + completed remediations) over a window

Notes:
- "Realized" here is estimated monthly savings based on recommendation/remediation metadata.
  Finance-grade realized savings requires post-action billing deltas and attribution, which
  should be layered in as the ledger matures.
"""

from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

import structlog
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.optimization import OptimizationStrategy, StrategyRecommendation
from app.models.realized_savings import RealizedSavingsEvent
from app.models.remediation import RemediationRequest, RemediationStatus
from app.modules.reporting.domain.savings_proof_drilldown_ops import (
    build_remediation_action_buckets,
    build_strategy_type_buckets,
    sort_and_limit_buckets,
)
from app.modules.reporting.domain.savings_proof_render_ops import (
    render_drilldown_csv,
    render_summary_csv,
)

logger = structlog.get_logger()


def _as_float(value: Decimal | float | int | None) -> float:
    if value is None:
        return 0.0
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _as_utc_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


class SavingsProofBreakdownItem(BaseModel):
    provider: str
    opportunity_monthly_usd: float
    realized_monthly_usd: float
    open_recommendations: int
    applied_recommendations: int
    pending_remediations: int
    completed_remediations: int


class SavingsProofResponse(BaseModel):
    start_date: str
    end_date: str
    as_of: str
    tier: str
    opportunity_monthly_usd: float
    realized_monthly_usd: float
    open_recommendations: int
    applied_recommendations: int
    pending_remediations: int
    completed_remediations: int
    breakdown: list[SavingsProofBreakdownItem]
    notes: list[str]


class SavingsProofDrilldownBucket(BaseModel):
    key: str
    opportunity_monthly_usd: float
    realized_monthly_usd: float
    open_recommendations: int
    applied_recommendations: int
    pending_remediations: int
    completed_remediations: int


class SavingsProofDrilldownResponse(BaseModel):
    start_date: str
    end_date: str
    as_of: str
    tier: str
    provider: str | None
    dimension: str
    opportunity_monthly_usd: float
    realized_monthly_usd: float
    buckets: list[SavingsProofDrilldownBucket]
    truncated: bool
    limit: int
    notes: list[str]


class SavingsProofService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(
        self,
        *,
        tenant_id: UUID,
        tier: str,
        start_date: date,
        end_date: date,
        provider: Optional[str] = None,
    ) -> SavingsProofResponse:
        if start_date > end_date:
            raise ValueError("start_date must be <= end_date")

        now = datetime.now(timezone.utc)
        window_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        window_end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)

        normalized_provider = provider.strip().lower() if provider else None

        # --- Opportunity snapshot (as-of now) ---
        open_recs_stmt = (
            select(StrategyRecommendation, OptimizationStrategy.provider)
            .join(
                OptimizationStrategy,
                StrategyRecommendation.strategy_id == OptimizationStrategy.id,
            )
            .where(
                StrategyRecommendation.tenant_id == tenant_id,
                StrategyRecommendation.status == "open",
            )
        )
        open_recs_rows = list((await self.db.execute(open_recs_stmt)).all())

        pending_statuses = {
            RemediationStatus.PENDING.value,
            RemediationStatus.PENDING_APPROVAL.value,
            RemediationStatus.APPROVED.value,
            RemediationStatus.SCHEDULED.value,
            RemediationStatus.EXECUTING.value,
        }
        pending_stmt = select(RemediationRequest).where(
            RemediationRequest.tenant_id == tenant_id,
            RemediationRequest.status.in_(pending_statuses),
        )
        pending_rems = list((await self.db.execute(pending_stmt)).scalars().all())

        # --- Realized in window ---
        applied_stmt = (
            select(StrategyRecommendation, OptimizationStrategy.provider)
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
        )
        applied_rows = list((await self.db.execute(applied_stmt)).all())

        completed_stmt = select(RemediationRequest).where(
            RemediationRequest.tenant_id == tenant_id,
            RemediationRequest.status == RemediationStatus.COMPLETED.value,
        )
        completed_rems_all = list(
            (await self.db.execute(completed_stmt)).scalars().all()
        )
        completed_rems: list[RemediationRequest] = []
        for item in completed_rems_all:
            completed_at = _as_utc_datetime(
                item.executed_at or item.updated_at or item.created_at
            )
            if completed_at is None:
                continue
            if window_start <= completed_at <= window_end:
                completed_rems.append(item)

        # Provider filter (optional)
        if normalized_provider:
            open_recs_rows = [
                row
                for row in open_recs_rows
                if str(row[1]).lower() == normalized_provider
            ]
            applied_rows = [
                row
                for row in applied_rows
                if str(row[1]).lower() == normalized_provider
            ]
            pending_rems = [
                row
                for row in pending_rems
                if str(row.provider).lower() == normalized_provider
            ]
            completed_rems = [
                row
                for row in completed_rems
                if str(row.provider).lower() == normalized_provider
            ]

        providers = {"aws", "azure", "gcp", "saas", "license", "platform", "hybrid"}
        if normalized_provider:
            providers = {normalized_provider}

        realized_events: dict[UUID, RealizedSavingsEvent] = {}
        if completed_rems:
            event_stmt = select(RealizedSavingsEvent).where(
                RealizedSavingsEvent.tenant_id == tenant_id,
                RealizedSavingsEvent.remediation_request_id.in_(
                    [rem.id for rem in completed_rems]
                ),
            )
            realized_events = {
                item.remediation_request_id: item
                for item in list((await self.db.execute(event_stmt)).scalars().all())
            }

        breakdown: dict[str, dict[str, Any]] = {
            p: {
                "opportunity_monthly_usd": 0.0,
                "realized_monthly_usd": 0.0,
                "open_recommendations": 0,
                "applied_recommendations": 0,
                "pending_remediations": 0,
                "completed_remediations": 0,
            }
            for p in sorted(providers)
        }

        for rec, rec_provider in open_recs_rows:
            p = str(rec_provider).lower()
            if p not in breakdown:
                continue
            breakdown[p]["open_recommendations"] += 1
            breakdown[p]["opportunity_monthly_usd"] += _as_float(
                rec.estimated_monthly_savings
            )

        for rec, rec_provider in applied_rows:
            p = str(rec_provider).lower()
            if p not in breakdown:
                continue
            breakdown[p]["applied_recommendations"] += 1
            breakdown[p]["realized_monthly_usd"] += _as_float(
                rec.estimated_monthly_savings
            )

        for rem in pending_rems:
            p = str(rem.provider).lower()
            if p not in breakdown:
                continue
            breakdown[p]["pending_remediations"] += 1
            breakdown[p]["opportunity_monthly_usd"] += _as_float(
                rem.estimated_monthly_savings
            )

        for rem in completed_rems:
            p = str(rem.provider).lower()
            if p not in breakdown:
                continue
            breakdown[p]["completed_remediations"] += 1
            realized_event = realized_events.get(rem.id)
            if realized_event is not None:
                breakdown[p]["realized_monthly_usd"] += _as_float(
                    realized_event.realized_monthly_savings_usd
                )
            else:
                breakdown[p]["realized_monthly_usd"] += _as_float(
                    rem.estimated_monthly_savings
                )

        breakdown_items = [
            SavingsProofBreakdownItem(provider=p, **values)
            for p, values in breakdown.items()
        ]
        opportunity_total = sum(
            item.opportunity_monthly_usd for item in breakdown_items
        )
        realized_total = sum(item.realized_monthly_usd for item in breakdown_items)
        open_recs_count = sum(item.open_recommendations for item in breakdown_items)
        applied_recs_count = sum(
            item.applied_recommendations for item in breakdown_items
        )
        pending_rems_count = sum(item.pending_remediations for item in breakdown_items)
        completed_rems_count = sum(
            item.completed_remediations for item in breakdown_items
        )

        payload = SavingsProofResponse(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            as_of=now.isoformat(),
            tier=str(tier),
            opportunity_monthly_usd=round(opportunity_total, 2),
            realized_monthly_usd=round(realized_total, 2),
            open_recommendations=open_recs_count,
            applied_recommendations=applied_recs_count,
            pending_remediations=pending_rems_count,
            completed_remediations=completed_rems_count,
            breakdown=breakdown_items,
            notes=[
                "Opportunity is a snapshot of currently open recommendations/pending remediations.",
                "Realized savings uses finance-grade ledger deltas where evidence exists; otherwise it falls back to estimated monthly savings.",
            ],
        )

        logger.info(
            "savings_proof_generated",
            tenant_id=str(tenant_id),
            provider=normalized_provider,
            start_date=payload.start_date,
            end_date=payload.end_date,
            opportunity_monthly_usd=payload.opportunity_monthly_usd,
            realized_monthly_usd=payload.realized_monthly_usd,
        )

        return payload

    async def drilldown(
        self,
        *,
        tenant_id: UUID,
        tier: str,
        start_date: date,
        end_date: date,
        dimension: str,
        provider: Optional[str] = None,
        limit: int = 50,
    ) -> SavingsProofDrilldownResponse:
        if start_date > end_date:
            raise ValueError("start_date must be <= end_date")

        dim = str(dimension or "").strip().lower()
        normalized_provider = provider.strip().lower() if provider else None

        supported_dims = {"provider", "strategy_type", "remediation_action"}
        if dim not in supported_dims:
            supported = ", ".join(sorted(supported_dims))
            raise ValueError(
                f"Unsupported drilldown dimension '{dimension}'. Use one of: {supported}"
            )

        top_limit = max(1, min(int(limit), 200))

        now = datetime.now(timezone.utc)
        window_start = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
        window_end = datetime.combine(end_date, time.max, tzinfo=timezone.utc)

        # "provider" drilldown is just a reshaped SavingsProofResponse breakdown.
        if dim == "provider":
            summary = await self.generate(
                tenant_id=tenant_id,
                tier=tier,
                start_date=start_date,
                end_date=end_date,
                provider=normalized_provider,
            )
            buckets = [
                SavingsProofDrilldownBucket(
                    key=item.provider,
                    opportunity_monthly_usd=float(item.opportunity_monthly_usd),
                    realized_monthly_usd=float(item.realized_monthly_usd),
                    open_recommendations=int(item.open_recommendations),
                    applied_recommendations=int(item.applied_recommendations),
                    pending_remediations=int(item.pending_remediations),
                    completed_remediations=int(item.completed_remediations),
                )
                for item in summary.breakdown
            ]
            return SavingsProofDrilldownResponse(
                start_date=summary.start_date,
                end_date=summary.end_date,
                as_of=summary.as_of,
                tier=summary.tier,
                provider=normalized_provider,
                dimension="provider",
                opportunity_monthly_usd=float(summary.opportunity_monthly_usd),
                realized_monthly_usd=float(summary.realized_monthly_usd),
                buckets=buckets,
                truncated=False,
                limit=top_limit,
                notes=summary.notes,
            )

        buckets_by_key: dict[str, dict[str, Any]] = {}

        def _ensure_bucket(key: str) -> dict[str, Any]:
            if key not in buckets_by_key:
                buckets_by_key[key] = {
                    "opportunity_monthly_usd": 0.0,
                    "realized_monthly_usd": 0.0,
                    "open_recommendations": 0,
                    "applied_recommendations": 0,
                    "pending_remediations": 0,
                    "completed_remediations": 0,
                }
            return buckets_by_key[key]

        if dim == "strategy_type":
            notes = await build_strategy_type_buckets(
                db=self.db,
                tenant_id=tenant_id,
                normalized_provider=normalized_provider,
                window_start=window_start,
                window_end=window_end,
                ensure_bucket=_ensure_bucket,
                as_float=_as_float,
            )
        else:
            notes = await build_remediation_action_buckets(
                db=self.db,
                tenant_id=tenant_id,
                normalized_provider=normalized_provider,
                window_start=window_start,
                window_end=window_end,
                ensure_bucket=_ensure_bucket,
                as_float=_as_float,
            )

        bucket_items, truncated = sort_and_limit_buckets(
            buckets_by_key, top_limit=top_limit
        )

        buckets = [
            SavingsProofDrilldownBucket(key=key, **values)
            for key, values in bucket_items
        ]
        opportunity_total = sum(item.opportunity_monthly_usd for item in buckets)
        realized_total = sum(item.realized_monthly_usd for item in buckets)

        if truncated:
            notes.append(f"Buckets truncated to top {top_limit} by opportunity.")

        payload = SavingsProofDrilldownResponse(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            as_of=now.isoformat(),
            tier=str(tier),
            provider=normalized_provider,
            dimension=dim,
            opportunity_monthly_usd=round(float(opportunity_total), 2),
            realized_monthly_usd=round(float(realized_total), 2),
            buckets=buckets,
            truncated=truncated,
            limit=top_limit,
            notes=notes,
        )

        logger.info(
            "savings_proof_drilldown_generated",
            tenant_id=str(tenant_id),
            provider=normalized_provider,
            dimension=dim,
            start_date=payload.start_date,
            end_date=payload.end_date,
            opportunity_monthly_usd=payload.opportunity_monthly_usd,
            realized_monthly_usd=payload.realized_monthly_usd,
            buckets=len(payload.buckets),
            truncated=payload.truncated,
        )

        return payload

    @staticmethod
    def render_csv(payload: SavingsProofResponse) -> str:
        return render_summary_csv(payload)

    @staticmethod
    def render_drilldown_csv(payload: SavingsProofDrilldownResponse) -> str:
        return render_drilldown_csv(payload)
