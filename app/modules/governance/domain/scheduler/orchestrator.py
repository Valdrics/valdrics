from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timezone
import asyncio
import time
import structlog
import sqlalchemy as sa
from httpx import HTTPError
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Protocol
from contextlib import AbstractAsyncContextManager

from app.modules.governance.domain.scheduler.cohorts import TenantCohort
from app.modules.governance.domain.scheduler.processors import AnalysisProcessor
from app.shared.core.config import get_settings
from app.shared.core.rate_limit import get_redis_client
from app.shared.db.session import mark_session_system_context
from app.shared.core.ops_metrics import (
    STUCK_JOB_COUNT,
    record_scheduler_inline_fallback,
    set_background_jobs_overdue_pending,
)

logger = structlog.get_logger()
settings = get_settings()

# Arbitrary constant for scheduler advisory locks - DEPRECATED in favor of SELECT FOR UPDATE
# Keeping for reference of lock inheritance
SCHEDULER_LOCK_BASE_ID = 48293021
SCHEDULER_LOCK_RECOVERABLE_ERRORS = (
    RuntimeError,
    OSError,
    TimeoutError,
    ValueError,
    TypeError,
)
SCHEDULER_DISPATCH_RECOVERABLE_ERRORS = (
    ImportError,
    AttributeError,
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


class AsyncSessionFactory(Protocol):
    """Call signature for objects that open AsyncSession context managers."""

    def __call__(self) -> AbstractAsyncContextManager[AsyncSession]:
        ...


class SchedulerOrchestrator:
    """Manages APScheduler and job distribution."""

    REGION_TO_ELECTRICITYMAP_ZONE = {
        "us-east-1": "US-MIDA-PJM",
        "us-west-2": "US-NW-BPAT",
        "eu-west-1": "IE",
        "eu-central-1": "DE",
        "ap-southeast-1": "SG",
        "ap-northeast-1": "JP-TK",
    }

    def __init__(self, session_maker: "AsyncSessionFactory"):
        self.scheduler = AsyncIOScheduler()
        self.session_maker = session_maker
        self.processor = AnalysisProcessor()
        self.semaphore = asyncio.Semaphore(10)
        self._last_run_success: bool | None = None
        self._last_run_time: str | None = None
        self._carbon_cache: dict[str, tuple[float, float]] = {}

    async def _dispatch_task(
        self,
        *,
        task_name: str,
        job_name: str,
        args: list[Any] | None = None,
        inline_fallback: Any = None,
    ) -> bool:
        try:
            from app.shared.core.celery_app import celery_app

            if args is None:
                celery_app.send_task(task_name)
            else:
                celery_app.send_task(task_name, args=args)
            return True
        except SCHEDULER_DISPATCH_RECOVERABLE_ERRORS as exc:
            logger.warning(
                "scheduler_celery_unavailable",
                error=str(exc),
                job=job_name,
            )
            if inline_fallback is None:
                return False
            logger.info(
                "scheduler_dispatch_falling_back_inline",
                task_name=task_name,
                job=job_name,
            )
            try:
                await inline_fallback()
                record_scheduler_inline_fallback(job_name, outcome="succeeded")
                return True
            except SCHEDULER_DISPATCH_RECOVERABLE_ERRORS as fallback_exc:
                record_scheduler_inline_fallback(job_name, outcome="failed")
                logger.error(
                    "scheduler_inline_fallback_failed",
                    task_name=task_name,
                    job=job_name,
                    error=str(fallback_exc),
                    error_type=type(fallback_exc).__name__,
                )
                return False

    async def _run_cohort_analysis_inline(self, target_cohort: TenantCohort) -> None:
        from app.tasks.scheduler_tasks import _cohort_analysis_logic

        await _cohort_analysis_logic(target_cohort)

    async def _run_remediation_sweep_inline(self) -> None:
        from app.tasks.scheduler_tasks import _remediation_sweep_logic

        await _remediation_sweep_logic()

    async def _run_billing_sweep_inline(self) -> None:
        from app.tasks.scheduler_tasks import _billing_sweep_logic

        await _billing_sweep_logic()

    async def _run_acceptance_sweep_inline(self) -> None:
        from app.tasks.scheduler_tasks import _acceptance_sweep_logic

        await _acceptance_sweep_logic()

    async def _run_license_governance_sweep_inline(self) -> None:
        from app.tasks.license_tasks import _license_governance_sweep_logic

        await _license_governance_sweep_logic()

    async def _run_enforcement_reconciliation_sweep_inline(self) -> None:
        from app.tasks.scheduler_tasks import _enforcement_reconciliation_sweep_logic

        await _enforcement_reconciliation_sweep_logic()

    async def _run_maintenance_sweep_inline(self) -> None:
        from app.tasks.scheduler_tasks import _maintenance_sweep_logic

        await _maintenance_sweep_logic()

    async def _run_landing_funnel_health_refresh_inline(self) -> None:
        from app.tasks.scheduler_tasks import _refresh_landing_funnel_health_logic

        await _refresh_landing_funnel_health_logic()

    async def _acquire_dispatch_lock(
        self, job_name: str, ttl_seconds: int = 180
    ) -> bool:
        """
        Acquire a distributed dispatch lock to prevent duplicate schedule dispatches
        when multiple API instances are running APScheduler.
        """
        # Test runs should be deterministic and fast; do not depend on Redis lock timing.
        if settings.TESTING or settings.PYTEST_CURRENT_TEST:
            return True

        redis = get_redis_client()
        if redis is None:
            if settings.SCHEDULER_LOCK_FAIL_OPEN:
                logger.warning(
                    "scheduler_dispatch_lock_unavailable_fail_open",
                    job=job_name,
                )
                return True
            logger.error(
                "scheduler_dispatch_lock_unavailable_fail_closed",
                job=job_name,
            )
            return False

        lock_key = f"scheduler:dispatch-lock:{job_name}"
        try:
            acquired = await redis.set(lock_key, "1", ex=ttl_seconds, nx=True)
            if not acquired:
                logger.info("scheduler_dispatch_skipped_lock_held", job=job_name)
                return False
            return True
        except SCHEDULER_LOCK_RECOVERABLE_ERRORS as exc:
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

    async def cohort_analysis_job(self, target_cohort: TenantCohort) -> None:
        """
        PRODUCTION: Enqueues a distributed task for cohort analysis.
        """
        logger.info("scheduler_dispatching_cohort_job", cohort=target_cohort.value)
        if not await self._acquire_dispatch_lock(f"cohort:{target_cohort.value}"):
            return

        dispatched = await self._dispatch_task(
            task_name="scheduler.cohort_analysis",
            job_name=f"cohort:{target_cohort.value}",
            args=[target_cohort.value],
            inline_fallback=lambda: self._run_cohort_analysis_inline(target_cohort),
        )
        if dispatched:
            self._last_run_success = True
            self._last_run_time = datetime.now(timezone.utc).isoformat()

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
        if live_intensity is not None:
            is_green = live_intensity <= settings.CARBON_LOW_INTENSITY_THRESHOLD
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
        api_key = settings.ELECTRICITY_MAPS_API_KEY
        if not api_key:
            return None

        zone = self.REGION_TO_ELECTRICITYMAP_ZONE.get(region_hint)
        if not zone:
            return None

        now = time.time()
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
        if not await self._acquire_dispatch_lock("remediation_sweep"):
            return
        await self._dispatch_task(
            task_name="scheduler.remediation_sweep",
            job_name="remediation",
            inline_fallback=self._run_remediation_sweep_inline,
        )

    async def billing_sweep_job(self) -> None:
        """Dispatches billing sweep."""
        logger.info("scheduler_dispatching_billing_sweep")
        if not await self._acquire_dispatch_lock("billing_sweep"):
            return
        await self._dispatch_task(
            task_name="scheduler.billing_sweep",
            job_name="billing",
            inline_fallback=self._run_billing_sweep_inline,
        )

    async def acceptance_sweep_job(self) -> None:
        """Dispatches daily acceptance-suite evidence capture sweep."""
        logger.info("scheduler_dispatching_acceptance_sweep")
        if not await self._acquire_dispatch_lock("acceptance_sweep"):
            return
        await self._dispatch_task(
            task_name="scheduler.acceptance_sweep",
            job_name="acceptance",
            inline_fallback=self._run_acceptance_sweep_inline,
        )

    async def license_governance_sweep_job(self) -> None:
        """Dispatches tenant-wide license governance sweep."""
        logger.info("scheduler_dispatching_license_governance_sweep")
        if not await self._acquire_dispatch_lock("license_governance_sweep"):
            return
        await self._dispatch_task(
            task_name="license.governance_sweep",
            job_name="license_governance",
            inline_fallback=self._run_license_governance_sweep_inline,
        )

    async def enforcement_reconciliation_sweep_job(self) -> None:
        """Dispatches periodic enforcement reservation reconciliation sweep."""
        if not bool(
            getattr(settings, "ENFORCEMENT_RECONCILIATION_SWEEP_ENABLED", True)
        ):
            logger.info("scheduler_enforcement_reconciliation_sweep_disabled")
            return
        logger.info("scheduler_dispatching_enforcement_reconciliation_sweep")
        if not await self._acquire_dispatch_lock("enforcement_reconciliation_sweep"):
            return
        await self._dispatch_task(
            task_name="scheduler.enforcement_reconciliation_sweep",
            job_name="enforcement_reconciliation",
            inline_fallback=self._run_enforcement_reconciliation_sweep_inline,
        )

    async def _process_background_jobs_inline(self) -> None:
        from app.modules.governance.domain.jobs.processor import JobProcessor

        batch_size = max(
            1, int(getattr(settings, "BACKGROUND_JOB_PROCESS_BATCH_SIZE", 25))
        )
        max_batches = max(
            1,
            int(getattr(settings, "BACKGROUND_JOB_PROCESS_MAX_BATCHES_PER_TICK", 8)),
        )
        totals = {"processed": 0, "succeeded": 0, "failed": 0, "batches": 0}

        for _ in range(max_batches):
            async with self.session_maker() as db:
                await mark_session_system_context(db)
                processor = JobProcessor(db)
                batch = await processor.process_pending_jobs(limit=batch_size)
            totals["batches"] += 1
            totals["processed"] += int(batch.get("processed", 0))
            totals["succeeded"] += int(batch.get("succeeded", 0))
            totals["failed"] += int(batch.get("failed", 0))
            if int(batch.get("processed", 0)) < batch_size:
                break

        logger.info("scheduler_background_job_processing_inline_complete", **totals)

    async def background_job_processing_job(self) -> None:
        """Dispatches the durable background job drainer."""
        logger.info("scheduler_dispatching_background_job_processing")
        if not await self._acquire_dispatch_lock("background_job_processing", ttl_seconds=55):
            return
        await self._dispatch_task(
            task_name="scheduler.process_background_jobs",
            job_name="background_job_processing",
            inline_fallback=self._process_background_jobs_inline,
        )

    async def detect_stuck_jobs(self) -> None:
        """
        Detect overdue pending jobs without mutating future-scheduled retries.
        """
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
        if not await self._acquire_dispatch_lock("maintenance_sweep"):
            return
        await self._dispatch_task(
            task_name="scheduler.maintenance_sweep",
            job_name="maintenance",
            inline_fallback=self._run_maintenance_sweep_inline,
        )

        # NOTE: Internal metric migration to task is deliberate (resolved Phase 13 uncertainty).

    async def landing_funnel_health_refresh_job(self) -> None:
        """Dispatches proactive landing funnel health refresh for internal alerting."""
        logger.info("scheduler_dispatching_landing_funnel_health_refresh")
        if not await self._acquire_dispatch_lock("landing_funnel_health_refresh"):
            return
        await self._dispatch_task(
            task_name="scheduler.refresh_landing_funnel_health",
            job_name="landing_funnel_health_refresh",
            inline_fallback=self._run_landing_funnel_health_refresh_inline,
        )

    def start(self) -> None:
        """Defines cron schedules and starts APScheduler."""
        # HIGH_VALUE: Every 6 hours
        self.scheduler.add_job(
            self.cohort_analysis_job,
            trigger=CronTrigger(hour="0,6,12,18", minute=0, timezone="UTC"),
            id="cohort_high_value_scan",
            args=[TenantCohort.HIGH_VALUE],
            replace_existing=True,
        )
        # ACTIVE: Daily 2AM
        self.scheduler.add_job(
            self.cohort_analysis_job,
            trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
            id="cohort_active_scan",
            args=[TenantCohort.ACTIVE],
            replace_existing=True,
        )
        # DORMANT: Weekly Sun 3AM
        self.scheduler.add_job(
            self.cohort_analysis_job,
            trigger=CronTrigger(day_of_week="sun", hour=3, minute=0, timezone="UTC"),
            id="cohort_dormant_scan",
            args=[TenantCohort.DORMANT],
            replace_existing=True,
        )
        # Remediation: Fri 8PM
        self.scheduler.add_job(
            self.auto_remediation_job,
            trigger=CronTrigger(day_of_week="fri", hour=20, minute=0, timezone="UTC"),
            id="weekly_remediation_sweep",
            replace_existing=True,
        )
        # Billing: Daily 4AM
        self.scheduler.add_job(
            self.billing_sweep_job,
            trigger=CronTrigger(hour=4, minute=0, timezone="UTC"),
            id="daily_billing_sweep",
            replace_existing=True,
        )
        # Acceptance evidence capture: Daily 5AM UTC
        self.scheduler.add_job(
            self.acceptance_sweep_job,
            trigger=CronTrigger(hour=5, minute=0, timezone="UTC"),
            id="daily_acceptance_sweep",
            replace_existing=True,
        )
        # License governance: Daily 6AM UTC
        self.scheduler.add_job(
            self.license_governance_sweep_job,
            trigger=CronTrigger(hour=6, minute=0, timezone="UTC"),
            id="daily_license_governance_sweep",
            replace_existing=True,
        )
        # Enforcement reconciliation sweep: Hourly at minute 20 UTC
        self.scheduler.add_job(
            self.enforcement_reconciliation_sweep_job,
            trigger=CronTrigger(minute=20, timezone="UTC"),
            id="hourly_enforcement_reconciliation_sweep",
            replace_existing=True,
        )
        # Background job processing: Every minute
        self.scheduler.add_job(
            self.background_job_processing_job,
            trigger=CronTrigger(minute="*", second=0, timezone="UTC"),
            id="background_job_processor",
            replace_existing=True,
        )
        # Stuck Job Detector: Every hour
        self.scheduler.add_job(
            self.detect_stuck_jobs,
            trigger=CronTrigger(minute=0, timezone="UTC"),
            id="stuck_job_detector",
            replace_existing=True,
        )
        # Landing funnel health refresh: Hourly at minute 10 UTC
        self.scheduler.add_job(
            self.landing_funnel_health_refresh_job,
            trigger=CronTrigger(minute=10, timezone="UTC"),
            id="hourly_landing_funnel_health_refresh",
            replace_existing=True,
        )
        # Maintenance: Daily 3AM UTC
        self.scheduler.add_job(
            self.maintenance_sweep_job,
            trigger=CronTrigger(hour=3, minute=0, timezone="UTC"),
            id="daily_maintenance_sweep",
            replace_existing=True,
        )
        self.scheduler.start()

    def stop(self) -> None:
        if not self.scheduler.running:
            logger.debug("scheduler_stop_skipped_not_running")
            return
        self.scheduler.shutdown(wait=True)

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self.scheduler.running,
            "last_run_success": self._last_run_success,
            "last_run_time": self._last_run_time,
            "jobs": [str(job.id) for job in self.scheduler.get_jobs()],
        }


class SchedulerService(SchedulerOrchestrator):
    """
    Scheduler API used by app lifecycle and admin routes.
    """

    def __init__(self, session_maker: "AsyncSessionFactory") -> None:
        super().__init__(session_maker)
        logger.info("scheduler_service_initialized", implementation="modular")

    async def daily_analysis_job(self) -> None:
        """Run the daily full cohort scan sequence."""
        from .cohorts import TenantCohort

        # High value → Active → Dormant
        await self.cohort_analysis_job(TenantCohort.HIGH_VALUE)
        await self.cohort_analysis_job(TenantCohort.ACTIVE)
        await self.cohort_analysis_job(TenantCohort.DORMANT)
        self._last_run_success = True
        self._last_run_time = datetime.now(timezone.utc).isoformat()
