import asyncio
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timezone
import hashlib
from httpx import HTTPError
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
import structlog
import time
from typing import Any, Protocol

from app.modules.governance.domain.scheduler.cohorts import TenantCohort
from app.shared.core.config import get_settings
from app.shared.core.ops_metrics import (
    STUCK_JOB_COUNT,
    record_scheduler_dispatch_fail_closed,
    set_background_jobs_overdue_pending,
)
from app.shared.orchestration.contracts import (
    DispatchUnavailableError,
    ManagedWorkItem,
    ManagedWorkRequest,
    platform_runtime_profile,
)
from app.shared.orchestration.runtime import get_scheduled_trigger_dispatcher
logger = structlog.get_logger()


def _monotonic_time() -> float:
    return time.monotonic()


SCHEDULER_LOCK_NAMESPACE = 48293021
SCHEDULER_LOCK_RECOVERABLE_ERRORS = (
    sa.exc.SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    ValueError,
    TypeError,
)
CARBON_INTENSITY_RECOVERABLE_ERRORS = (
    HTTPError,
    ImportError,
    RuntimeError,
    OSError,
    TimeoutError,
    ValueError,
    TypeError,
)


# Metrics are now imported from app.modules.governance.domain.scheduler.metrics


def _scheduler_dispatch_lock_key(job_name: str) -> int:
    raw = int(hashlib.sha256(job_name.encode("utf-8")).hexdigest()[:8], 16)
    return raw if raw < 2**31 else raw - 2**32


class AsyncSessionFactory(Protocol):
    """Call signature for objects that open AsyncSession context managers."""

    def __call__(self) -> AbstractAsyncContextManager[AsyncSession]: ...


class SchedulerOrchestrator:
    """Coordinates managed scheduler dispatch."""

    REGION_TO_ELECTRICITYMAP_ZONE = {
        "us-east-1": "US-MIDA-PJM",
        "us-west-2": "US-NW-BPAT",
        "eu-west-1": "IE",
        "eu-central-1": "DE",
        "ap-southeast-1": "SG",
        "ap-northeast-1": "JP-TK",
    }

    def __init__(self, session_maker: "AsyncSessionFactory"):
        self.session_maker = session_maker
        self.scheduled_trigger_dispatcher = get_scheduled_trigger_dispatcher()
        self.semaphore = asyncio.Semaphore(10)
        self._last_run_success: bool | None = None
        self._last_run_time: str | None = None
        self._carbon_cache: dict[str, tuple[float, float]] = {}
        self._held_dispatch_locks: dict[
            str, tuple[AbstractAsyncContextManager[AsyncSession], AsyncSession]
        ] = {}

    @staticmethod
    def _settings() -> Any:
        return get_settings()

    async def _dispatch_work(
        self,
        *,
        work_item: ManagedWorkItem,
        job_name: str,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        try:
            await self.scheduled_trigger_dispatcher.dispatch(
                ManagedWorkRequest(
                    work_item=work_item,
                    payload=dict(payload or {}),
                )
            )
            return True
        except (
            DispatchUnavailableError,
            ImportError,
            AttributeError,
            RuntimeError,
            OSError,
            TimeoutError,
            ValueError,
            TypeError,
        ) as exc:
            logger.warning(
                "scheduler_dispatch_unavailable",
                error=str(exc),
                job=job_name,
                work_item=work_item.value,
            )
            runtime_profile = platform_runtime_profile(self._settings())
            record_scheduler_dispatch_fail_closed(
                job_name,
                work_item=work_item.value,
                runtime_profile=runtime_profile.value,
            )
            logger.error(
                "scheduler_dispatch_unavailable_fail_closed",
                job=job_name,
                work_item=work_item.value,
                runtime_profile=runtime_profile.value,
            )
            return False

    async def _acquire_dispatch_lock(self, job_name: str) -> bool:
        """
        Acquire a Postgres-backed advisory lock to prevent duplicate schedule
        dispatches when Cloud Scheduler retries or multiple runtime instances
        race on the same managed trigger.
        """
        settings = self._settings()
        # Test runs should be deterministic and fast; do not depend on external lock timing.
        if settings.TESTING or settings.PYTEST_CURRENT_TEST:
            return True

        session_cm = self.session_maker()
        session: AsyncSession | None = None

        try:
            session = await session_cm.__aenter__()
            bind = session.get_bind()
            dialect_name = str(
                getattr(getattr(bind, "dialect", None), "name", "") or ""
            ).lower()
            if dialect_name != "postgresql":
                await session_cm.__aexit__(None, None, None)
                logger.info(
                    "scheduler_dispatch_lock_skipped_non_postgres",
                    job=job_name,
                    dialect=dialect_name or "unknown",
                )
                return True

            acquired = bool(
                await session.scalar(
                    sa.text(
                        "SELECT pg_try_advisory_lock(:namespace, :lock_key)"
                    ),
                    {
                        "namespace": SCHEDULER_LOCK_NAMESPACE,
                        "lock_key": _scheduler_dispatch_lock_key(job_name),
                    },
                )
            )
            if not acquired:
                logger.info("scheduler_dispatch_skipped_lock_held", job=job_name)
                await session_cm.__aexit__(None, None, None)
                return False
            self._held_dispatch_locks[job_name] = (session_cm, session)
            return True
        except SCHEDULER_LOCK_RECOVERABLE_ERRORS as exc:
            if session is not None:
                await session_cm.__aexit__(None, None, None)
            if settings.SCHEDULER_LOCK_FAIL_OPEN:
                logger.warning(
                    "scheduler_dispatch_lock_error_fail_open",
                    job=job_name,
                    error=str(exc),
                )
                return True
            logger.error(
                "scheduler_dispatch_lock_error_fail_closed",
                job=job_name,
                error=str(exc),
            )
            return False

    async def _release_dispatch_lock(self, job_name: str) -> None:
        held_lock = self._held_dispatch_locks.pop(job_name, None)
        if held_lock is None:
            return

        session_cm, session = held_lock
        try:
            await session.scalar(
                sa.text("SELECT pg_advisory_unlock(:namespace, :lock_key)"),
                {
                    "namespace": SCHEDULER_LOCK_NAMESPACE,
                    "lock_key": _scheduler_dispatch_lock_key(job_name),
                },
            )
        except SCHEDULER_LOCK_RECOVERABLE_ERRORS as exc:
            logger.warning(
                "scheduler_dispatch_lock_release_failed",
                job=job_name,
                error=str(exc),
            )
        finally:
            await session_cm.__aexit__(None, None, None)

    async def _dispatch_work_with_lock(
        self,
        *,
        work_item: ManagedWorkItem,
        job_name: str,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        if not await self._acquire_dispatch_lock(job_name):
            return False
        try:
            return await self._dispatch_work(
                work_item=work_item,
                job_name=job_name,
                payload=payload,
            )
        finally:
            await self._release_dispatch_lock(job_name)

    async def cohort_analysis_job(self, target_cohort: TenantCohort) -> bool:
        """
        PRODUCTION: Enqueues a distributed task for cohort analysis.
        """
        logger.info("scheduler_dispatching_cohort_job", cohort=target_cohort.value)
        dispatched = await self._dispatch_work_with_lock(
            work_item=ManagedWorkItem.SCHEDULER_COHORT_ANALYSIS,
            job_name=f"cohort:{target_cohort.value}",
            payload={"cohort": target_cohort.value},
        )
        if dispatched:
            self._last_run_success = True
            self._last_run_time = datetime.now(timezone.utc).isoformat()
        return dispatched

    async def is_low_carbon_window(self, region: str = "global") -> bool:
        """
        Series-A (Phase 4): Carbon-Aware Scheduling.
        Returns True if the current time is a 'Green Window' for the region.

        Logic:
        - 10 AM to 4 PM (10:00 - 16:00) usually has high solar output.
        - 12 AM to 5 AM (00:00 - 05:00) usually has low grid demand.
        """
        region_hint = str(region or "").strip().lower() or "global"
        live_intensity = await self._fetch_live_carbon_intensity(region_hint)
        settings = self._settings()
        if live_intensity is not None:
            is_green = bool(live_intensity <= settings.CARBON_LOW_INTENSITY_THRESHOLD)
            logger.info(
                "scheduler_green_window_check_live",
                region=region_hint,
                live_intensity=live_intensity,
                threshold=settings.CARBON_LOW_INTENSITY_THRESHOLD,
                is_green=is_green,
            )
            return is_green

        now = datetime.now(timezone.utc)
        hour = now.hour
        # Fallback heuristic when live carbon data is unavailable.
        is_green = (10 <= hour <= 16) or (0 <= hour <= 5)
        logger.info(
            "scheduler_green_window_check_fallback",
            hour=hour,
            is_green=is_green,
            region=region_hint,
        )
        return is_green

    async def _fetch_live_carbon_intensity(self, region: str) -> float | None:
        region_hint = str(region or "").strip().lower() or "global"
        settings = self._settings()
        api_key = settings.ELECTRICITY_MAPS_API_KEY
        if not api_key:
            return None

        zone = self.REGION_TO_ELECTRICITYMAP_ZONE.get(region_hint)
        if not zone:
            return None

        now = _monotonic_time()
        cached = self._carbon_cache.get(region_hint)
        if cached and (now - cached[1]) < 600:
            return cached[0]

        try:
            from app.shared.core.http import get_http_client

            client = get_http_client()
            response = await client.get(
                "https://api.electricitymap.org/v3/carbon-intensity/latest",
                params={"zone": zone},
                headers={"auth-token": api_key},
            )
            response.raise_for_status()
            payload = response.json()
            intensity = payload.get("carbonIntensity")
            if intensity is None:
                return None
            value = float(intensity)
            self._carbon_cache[region_hint] = (value, now)
            return value
        except CARBON_INTENSITY_RECOVERABLE_ERRORS as exc:
            logger.warning(
                "live_carbon_intensity_fetch_failed",
                region=region_hint,
                error=str(exc),
            )
            return None

    async def auto_remediation_job(self) -> None:
        """Dispatches weekly remediation sweep."""
        logger.info("scheduler_dispatching_remediation_sweep")
        await self._dispatch_work_with_lock(
            work_item=ManagedWorkItem.SCHEDULER_REMEDIATION_SWEEP,
            job_name="remediation",
        )

    async def billing_sweep_job(self) -> None:
        """Dispatches billing sweep."""
        logger.info("scheduler_dispatching_billing_sweep")
        await self._dispatch_work_with_lock(
            work_item=ManagedWorkItem.SCHEDULER_BILLING_SWEEP,
            job_name="billing",
        )

    async def acceptance_sweep_job(self) -> None:
        """Dispatches daily acceptance-suite evidence capture sweep."""
        logger.info("scheduler_dispatching_acceptance_sweep")
        await self._dispatch_work_with_lock(
            work_item=ManagedWorkItem.SCHEDULER_ACCEPTANCE_SWEEP,
            job_name="acceptance",
        )

    async def license_governance_sweep_job(self) -> None:
        """Dispatches tenant-wide license governance sweep."""
        logger.info("scheduler_dispatching_license_governance_sweep")
        await self._dispatch_work_with_lock(
            work_item=ManagedWorkItem.LICENSE_GOVERNANCE_SWEEP,
            job_name="license_governance",
        )

    async def enforcement_reconciliation_sweep_job(self) -> None:
        """Dispatches periodic enforcement reservation reconciliation sweep."""
        settings = self._settings()
        if not bool(
            getattr(settings, "ENFORCEMENT_RECONCILIATION_SWEEP_ENABLED", True)
        ):
            logger.info("scheduler_enforcement_reconciliation_sweep_disabled")
            return
        logger.info("scheduler_dispatching_enforcement_reconciliation_sweep")
        await self._dispatch_work_with_lock(
            work_item=ManagedWorkItem.SCHEDULER_ENFORCEMENT_RECONCILIATION_SWEEP,
            job_name="enforcement_reconciliation",
        )

    async def background_job_processing_job(self) -> None:
        """Dispatches the durable background job drainer."""
        logger.info("scheduler_dispatching_background_job_processing")
        await self._dispatch_work_with_lock(
            work_item=ManagedWorkItem.BACKGROUND_JOB_PROCESSING,
            job_name="background_job_processing",
        )

    async def background_job_stuck_detection_job(self) -> None:
        """Dispatches the overdue pending-job detector."""
        logger.info("scheduler_dispatching_stuck_job_detection")
        await self._dispatch_work_with_lock(
            work_item=ManagedWorkItem.BACKGROUND_JOB_STUCK_DETECTION,
            job_name="background_job_stuck_detection",
        )

    async def detect_stuck_jobs(self) -> None:
        """
        Detect overdue pending jobs without mutating future-scheduled retries.
        """
        settings = self._settings()
        async with self.session_maker() as db:
            from app.models.background_job import BackgroundJob, JobStatus
            from datetime import datetime, timezone, timedelta

            alert_minutes = max(
                1,
                int(
                    getattr(
                        settings,
                        "BACKGROUND_JOB_PENDING_OVERDUE_ALERT_MINUTES",
                        60,
                    )
                ),
            )
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=alert_minutes)

            # Detect only jobs that were due to run and are still pending.
            stmt = sa.select(BackgroundJob).where(
                BackgroundJob.status == JobStatus.PENDING,
                BackgroundJob.scheduled_for <= cutoff,
                sa.not_(BackgroundJob.is_deleted),
            )
            result = await db.execute(stmt)
            overdue_jobs = result.scalars().all()
            STUCK_JOB_COUNT.set(len(overdue_jobs))
            set_background_jobs_overdue_pending(len(overdue_jobs))

            if overdue_jobs:
                logger.critical(
                    "overdue_pending_jobs_detected",
                    count=len(overdue_jobs),
                    alert_minutes=alert_minutes,
                    job_ids=[str(j.id) for j in overdue_jobs[:10]],
                )

    async def maintenance_sweep_job(self) -> None:
        """Dispatches maintenance sweep."""
        logger.info("scheduler_dispatching_maintenance_sweep")
        await self._dispatch_work_with_lock(
            work_item=ManagedWorkItem.SCHEDULER_MAINTENANCE_SWEEP,
            job_name="maintenance",
        )

        # NOTE: Internal metric migration to task is deliberate (resolved Phase 13 uncertainty).

    async def landing_funnel_health_refresh_job(self) -> None:
        """Dispatches proactive landing funnel health refresh for internal alerting."""
        logger.info("scheduler_dispatching_landing_funnel_health_refresh")
        await self._dispatch_work_with_lock(
            work_item=ManagedWorkItem.SCHEDULER_LANDING_FUNNEL_HEALTH_REFRESH,
            job_name="landing_funnel_health_refresh",
        )

    async def daily_analysis_job(self) -> dict[str, Any]:
        """Run the daily full cohort scan sequence and report what actually dispatched."""
        results = []
        for cohort in (
            TenantCohort.HIGH_VALUE,
            TenantCohort.ACTIVE,
            TenantCohort.DORMANT,
        ):
            dispatched = await self.cohort_analysis_job(cohort)
            results.append(
                {
                    "cohort": cohort.value,
                    "dispatched": dispatched,
                }
            )

        dispatched_count = sum(1 for item in results if item["dispatched"])
        all_dispatched = dispatched_count == len(results)
        self._last_run_success = all_dispatched
        self._last_run_time = datetime.now(timezone.utc).isoformat()
        if not all_dispatched:
            logger.warning(
                "scheduler_daily_analysis_incomplete",
                dispatched=dispatched_count,
                attempted=len(results),
                failed_cohorts=[
                    item["cohort"] for item in results if not item["dispatched"]
                ],
            )

        return {
            "attempted": len(results),
            "dispatched": dispatched_count,
            "all_dispatched": all_dispatched,
            "results": results,
        }
