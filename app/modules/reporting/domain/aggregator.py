from datetime import date
from typing import Any
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.costs import CloudUsageSummary

from .aggregator_breakdown_ops import (
    get_basic_breakdown as _get_basic_breakdown,
    get_cached_breakdown as _get_cached_breakdown,
    refresh_materialized_view as _refresh_materialized_view,
)
from .aggregator_count_freshness_ops import (
    count_records as _count_records,
    get_data_freshness as _get_data_freshness,
)
from .aggregator_governance_ops import get_governance_report as _get_governance_report
from .aggregator_quality_ops import (
    get_canonical_data_quality as _get_canonical_data_quality,
)
from .aggregator_summary_ops import (
    get_dashboard_summary as _get_dashboard_summary,
    get_summary as _get_summary,
)

__all__ = ["CostAggregator", "LARGE_DATASET_THRESHOLD"]

import structlog

logger = structlog.get_logger()

# Enterprise Safety Gates
MAX_AGGREGATION_ROWS = 1000000  # 1M rows max per query
MAX_DETAIL_ROWS = 100000  # 100K rows max for detail records
STATEMENT_TIMEOUT_MS = 5000  # 5 seconds
LARGE_DATASET_THRESHOLD = 5000  # If >5k records, suggest background job
MATERIALIZED_VIEW_READ_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    ValueError,
    TypeError,
)
MATERIALIZED_VIEW_REFRESH_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    AttributeError,
    RuntimeError,
)


class CostAggregator:
    """Centralizes cost aggregation logic for the platform."""

    @staticmethod
    async def count_records(
        db: AsyncSession, tenant_id: UUID, start_date: date, end_date: date
    ) -> int:
        return await _count_records(db, tenant_id, start_date, end_date)

    @staticmethod
    async def get_data_freshness(
        db: AsyncSession, tenant_id: UUID, start_date: date, end_date: date
    ) -> dict[str, Any]:
        return await _get_data_freshness(db, tenant_id, start_date, end_date)

    @staticmethod
    async def get_summary(
        db: AsyncSession,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        provider: str | None = None,
    ) -> CloudUsageSummary:
        return await _get_summary(
            db,
            tenant_id,
            start_date,
            end_date,
            provider,
            max_detail_rows=MAX_DETAIL_ROWS,
            logger=logger,
        )

    @staticmethod
    async def get_dashboard_summary(
        db: AsyncSession,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        provider: str | None = None,
    ) -> dict[str, Any]:
        return await _get_dashboard_summary(
            db,
            tenant_id,
            start_date,
            end_date,
            provider,
            statement_timeout_ms=STATEMENT_TIMEOUT_MS,
            basic_breakdown_fetcher=CostAggregator.get_basic_breakdown,
            data_freshness_fetcher=CostAggregator.get_data_freshness,
            canonical_quality_fetcher=CostAggregator.get_canonical_data_quality,
        )

    @staticmethod
    async def get_canonical_data_quality(
        db: AsyncSession,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        provider: str | None = None,
    ) -> dict[str, Any]:
        return await _get_canonical_data_quality(
            db, tenant_id, start_date, end_date, provider
        )

    @staticmethod
    async def get_basic_breakdown(
        db: AsyncSession,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        provider: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        return await _get_basic_breakdown(
            db,
            tenant_id,
            start_date,
            end_date,
            provider,
            limit=limit,
            offset=offset,
            max_aggregation_rows=MAX_AGGREGATION_ROWS,
            statement_timeout_ms=STATEMENT_TIMEOUT_MS,
        )

    @staticmethod
    async def get_governance_report(
        db: AsyncSession, tenant_id: UUID, start_date: date, end_date: date
    ) -> dict[str, Any]:
        return await _get_governance_report(db, tenant_id, start_date, end_date)

    @staticmethod
    async def get_cached_breakdown(
        db: AsyncSession, tenant_id: UUID, start_date: date, end_date: date
    ) -> dict[str, Any]:
        return await _get_cached_breakdown(
            db,
            tenant_id,
            start_date,
            end_date,
            logger=logger,
            mv_read_recoverable_exceptions=MATERIALIZED_VIEW_READ_RECOVERABLE_EXCEPTIONS,
            basic_breakdown_fetcher=CostAggregator.get_basic_breakdown,
        )

    @staticmethod
    async def refresh_materialized_view(db: AsyncSession) -> bool:
        return await _refresh_materialized_view(
            db,
            logger=logger,
            mv_refresh_recoverable_exceptions=MATERIALIZED_VIEW_REFRESH_RECOVERABLE_EXCEPTIONS,
        )
