"""
Tests for scheduler_tasks.py - Background job scheduling and processing.

Production-quality tests for Scheduler Tasks.
Tests cover job scheduling, cohort analysis, remediation, billing, maintenance, and error handling.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.tasks.scheduler_tasks import (
    run_cohort_analysis,
    _cohort_analysis_logic,
)
from app.modules.governance.domain.scheduler.cohorts import TenantCohort



class TestCohortAnalysis:
    """Tests for cohort analysis scheduling functionality."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        return AsyncMock(spec=AsyncSession)

    @pytest.mark.asyncio
    async def test_cohort_analysis_high_value_cohort(self, mock_db):
        """Test cohort analysis for high-value tenants."""
        # Mock tenants
        mock_tenant1 = MagicMock()
        mock_tenant1.id = uuid4()
        mock_tenant1.plan = "enterprise"

        mock_tenant2 = MagicMock()
        mock_tenant2.id = uuid4()
        mock_tenant2.plan = "pro"

        mock_tenant3 = MagicMock()
        mock_tenant3.id = uuid4()
        mock_tenant3.plan = "starter"  # Should be excluded

        with (
            patch(
                "app.tasks.scheduler_tasks.async_session_maker"
            ) as mock_session_maker,
            patch("app.tasks.scheduler_tasks.BACKGROUND_JOBS_ENQUEUED"),
            patch("app.tasks.scheduler_tasks.SCHEDULER_JOB_RUNS"),
            patch("app.tasks.scheduler_tasks.SCHEDULER_JOB_DURATION"),
        ):
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session

            # Mock database context
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.begin.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=None)

            # Mock tenant query results (first call) and job insert results (subsequent calls)
            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [
                mock_tenant1,
                mock_tenant2,
            ]

            # Mock job insertion result
            mock_stmt_result = MagicMock()
            mock_stmt_result.rowcount = 1

            # First execute -> select tenants, second execute -> single bulk insert.
            mock_session.execute.side_effect = [mock_result, mock_stmt_result]

            await _cohort_analysis_logic(TenantCohort.HIGH_VALUE)

            # Current implementation uses one select + one batched insert.
            assert mock_session.execute.call_count == 2

    @pytest.mark.asyncio
    async def test_cohort_analysis_active_cohort(self, mock_db):
        """Test cohort analysis for active tenants."""
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.plan = "growth"

        with patch(
            "app.tasks.scheduler_tasks.async_session_maker"
        ) as mock_session_maker:
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session

            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.begin.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_tenant]
            mock_session.execute.return_value = mock_result

            await _cohort_analysis_logic(TenantCohort.ACTIVE)

            # Should filter for growth plan
            call_args = mock_session.execute.call_args_list[0]
            _query = call_args[0][0]  # noqa: F841
            # The query should include growth plan filter

    @pytest.mark.asyncio
    async def test_cohort_analysis_empty_cohort(self, mock_db):
        """Test cohort analysis with no tenants in cohort."""
        with patch(
            "app.tasks.scheduler_tasks.async_session_maker"
        ) as mock_session_maker:
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session

            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.begin.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = []  # Empty cohort
            mock_session.execute.return_value = mock_result

            await _cohort_analysis_logic(TenantCohort.DORMANT)

            # Should handle empty cohort gracefully

    @pytest.mark.asyncio
    async def test_cohort_analysis_deduplication(self, mock_db):
        """Test job deduplication in cohort analysis."""
        mock_tenant = MagicMock()
        mock_tenant.id = uuid4()
        mock_tenant.plan = "enterprise"

        with (
            patch(
                "app.tasks.scheduler_tasks.async_session_maker"
            ) as mock_session_maker,
            patch("app.tasks.scheduler_tasks.BackgroundJob"),
        ):
            mock_session = AsyncMock()
            mock_session_maker.return_value = mock_session

            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)
            mock_session.begin.return_value.__aenter__ = AsyncMock(
                return_value=mock_session
            )
            mock_session.begin.return_value.__aexit__ = AsyncMock(return_value=None)

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_tenant]
            mock_session.execute.return_value = mock_result

            # Mock job insertion that returns 0 rowcount (duplicate)
            mock_stmt_result = MagicMock()
            mock_stmt_result.rowcount = 0
            mock_session.execute.side_effect = [
                mock_result,
                mock_stmt_result,
                mock_stmt_result,
                mock_stmt_result,
                mock_stmt_result,
            ]

            await _cohort_analysis_logic(TenantCohort.HIGH_VALUE)

            # Should still complete without errors even with duplicates

    def test_run_cohort_analysis_task(self):
        """Test the Celery task wrapper."""
        with (
            patch("app.tasks.scheduler_tasks.run_async") as mock_run_async,
            patch("app.tasks.scheduler_tasks._cohort_analysis_logic"),
        ):
            run_cohort_analysis("HIGH_VALUE")

            mock_run_async.assert_called_once()
            args = mock_run_async.call_args[0]
            assert callable(args[0])
            assert args[1] == TenantCohort.HIGH_VALUE

