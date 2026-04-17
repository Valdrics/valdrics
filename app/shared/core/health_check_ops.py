from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_job import BackgroundJob, JobStatus
from app.shared.core.async_utils import maybe_await
from app.shared.core.config import get_settings
from app.shared.orchestration.contracts import (
    platform_runtime_profile,
    PlatformRuntimeProfile,
)


def evaluate_system_resources(
    *,
    virtual_memory_sampler: Callable[[], Any],
    cpu_percent_sampler: Callable[[], float],
    disk_usage_sampler: Callable[[str], Any],
    recoverable_errors: tuple[type[Exception], ...],
) -> dict[str, Any]:
    try:
        memory = virtual_memory_sampler()
        memory_percent = memory.percent

        cpu_percent = cpu_percent_sampler()

        disk = disk_usage_sampler("/")
        disk_percent = disk.percent

        status = "healthy"
        warnings: list[str] = []

        if memory_percent > 85:
            status = "degraded"
            warnings.append("memory_high")
        if cpu_percent > 90:
            status = "degraded"
            warnings.append("cpu_high")
        if disk_percent > 90:
            status = "degraded"
            warnings.append("disk_high")

        return {
            "status": status,
            "memory": {
                "percent": memory_percent,
                "used_gb": round(memory.used / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
            },
            "cpu": {"percent": cpu_percent},
            "disk": {
                "percent": disk_percent,
                "free_gb": round(disk_usage_sampler("/").free / (1024**3), 2),
            },
            "warnings": warnings,
        }
    except recoverable_errors as exc:
        return {"status": "unknown", "error": str(exc)}


def _default_worker_probe() -> dict[str, Any]:
    settings = get_settings()
    if settings.TESTING:
        return {
            "status": "skipped",
            "message": "Worker health probe skipped during tests",
            "worker_count": 0,
            "workers": [],
        }

    if platform_runtime_profile(settings) is not PlatformRuntimeProfile.GCP:
        raise ValueError("Only the managed GCP runtime profile is supported.")

    queue_name = str(getattr(settings, "GCP_CLOUD_TASKS_QUEUE", "") or "").strip()
    batch_job_name = str(
        getattr(settings, "GCP_CLOUD_RUN_BATCH_JOB_NAME", "") or ""
    ).strip()
    service_name = str(
        getattr(settings, "GCP_CLOUD_RUN_SERVICE_NAME", "") or ""
    ).strip()
    return {
        "status": "healthy",
        "message": (
            "Managed background execution is handled by Cloud Tasks, "
            "Cloud Scheduler, and Cloud Run Jobs."
        ),
        "runtime": "gcp_managed",
        "scheduler_owner": "cloud_scheduler",
        "task_queue": queue_name,
        "batch_job": batch_job_name,
        "service_name": service_name,
        "worker_count": 0,
        "workers": [],
    }


def _default_worker_probe_requires_thread() -> bool:
    return False


async def _probe_worker_health(
    *,
    worker_probe: Callable[[], Any] | None,
) -> dict[str, Any]:
    if worker_probe is None:
        if _default_worker_probe_requires_thread():
            result = await asyncio.to_thread(_default_worker_probe)
        else:
            result = _default_worker_probe()
    else:
        result = await maybe_await(worker_probe())

    if isinstance(result, dict):
        return dict(result)

    raise ValueError("Worker probe must return a dictionary payload")


async def evaluate_background_jobs(
    *,
    db: AsyncSession | None,
    recoverable_errors: tuple[type[Exception], ...],
    worker_probe: Callable[[], Any] | None = None,
) -> dict[str, Any]:
    try:
        if db is None:
            return {
                "status": "unknown",
                "message": "Database session not available",
            }

        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=1)

        result = await db.execute(
            select(func.count()).where(
                BackgroundJob.status == JobStatus.PENDING,
                BackgroundJob.scheduled_for <= cutoff_time,
                sa.not_(BackgroundJob.is_deleted),
            )
        )

        stuck_jobs = await maybe_await(result.scalar())

        result = await db.execute(
            select(
                func.count().label("total"),
                func.sum(
                    sa.cast(BackgroundJob.status == JobStatus.PENDING, sa.Integer)
                ).label("pending"),
                func.sum(
                    sa.cast(BackgroundJob.status == JobStatus.RUNNING, sa.Integer)
                ).label("running"),
                func.sum(
                    sa.cast(BackgroundJob.status == JobStatus.FAILED, sa.Integer)
                ).label("failed"),
            )
        )

        stats = await maybe_await(result.first())
        queue_stats = {
            "total_jobs": stats.total or 0,
            "pending_jobs": stats.pending or 0,
            "running_jobs": stats.running or 0,
            "failed_jobs": stats.failed or 0,
        }
        worker_health = await _probe_worker_health(worker_probe=worker_probe)

        if stuck_jobs and stuck_jobs > 0:
            return {
                "status": "degraded",
                "message": f"{stuck_jobs} jobs stuck in pending state",
                "stuck_jobs": stuck_jobs,
                "queue_stats": queue_stats,
                "worker_health": worker_health,
            }

        worker_status = str(worker_health.get("status") or "").strip().lower()
        if worker_status == "degraded":
            return {
                "status": "degraded",
                "message": str(
                    worker_health.get("message")
                    or "Background workers are not responding to heartbeat probes"
                ),
                "queue_stats": queue_stats,
                "worker_health": worker_health,
            }
        if worker_status not in {"healthy", "skipped"}:
            return {
                "status": "unknown",
                "message": str(
                    worker_health.get("message")
                    or "Background worker health is unavailable"
                ),
                "queue_stats": queue_stats,
                "worker_health": worker_health,
            }

        return {
            "status": "healthy",
            "queue_stats": queue_stats,
            "worker_health": worker_health,
        }
    except recoverable_errors as exc:
        if _should_skip_background_jobs_check(exc):
            return {
                "status": "disabled",
                "message": "Background job health check skipped because the background_jobs table is not initialized in testing.",
                "reason": "testing_background_jobs_table_missing",
            }
        return {"status": "unknown", "error": str(exc)}


def _should_skip_background_jobs_check(exc: Exception) -> bool:
    settings = get_settings()
    if not bool(getattr(settings, "TESTING", False)):
        return False
    return _is_missing_background_jobs_table_error(exc)


def _is_missing_background_jobs_table_error(exc: Exception) -> bool:
    if not isinstance(exc, OperationalError):
        return False

    orig = getattr(exc, "orig", None)
    if orig is not None and not isinstance(orig, sqlite3.OperationalError):
        message = f"{exc} {orig}".lower()
    else:
        message = str(exc).lower()

    return "background_jobs" in message and any(
        marker in message
        for marker in ("no such table", "does not exist", "undefined table")
    )
