from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_job import BackgroundJob, JobStatus
from app.shared.core.async_utils import maybe_await


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


def _resolve_worker_broker_url() -> str | None:
    from app.shared.core.config import get_settings

    settings = get_settings()
    configured_url = str(getattr(settings, "REDIS_URL", "") or "").strip()
    if configured_url:
        return configured_url

    host = str(getattr(settings, "REDIS_HOST", "") or "").strip()
    port = str(getattr(settings, "REDIS_PORT", "") or "").strip()
    if host and port:
        return f"redis://{host}:{port}/0"

    return None


def _default_worker_probe() -> dict[str, Any]:
    from app.shared.core.config import get_settings

    settings = get_settings()
    broker_url = _resolve_worker_broker_url()
    if settings.TESTING or not broker_url or broker_url.startswith("memory://"):
        return {
            "status": "skipped",
            "message": "Worker heartbeat probe skipped because no runtime broker is configured",
            "worker_count": 0,
            "workers": [],
        }

    from app.shared.core.celery_app import celery_app

    inspector = celery_app.control.inspect(timeout=1.0)
    ping_response = inspector.ping()
    if not isinstance(ping_response, dict) or not ping_response:
        return {
            "status": "degraded",
            "message": "No Celery workers responded to the heartbeat probe",
            "worker_count": 0,
            "workers": [],
        }

    workers = sorted(str(name) for name, payload in ping_response.items() if payload)
    if not workers:
        return {
            "status": "degraded",
            "message": "Celery worker heartbeat responses were empty",
            "worker_count": 0,
            "workers": [],
        }

    return {
        "status": "healthy",
        "message": "Celery workers responded to the heartbeat probe",
        "worker_count": len(workers),
        "workers": workers,
    }


async def _probe_worker_health(
    *,
    worker_probe: Callable[[], Any] | None,
) -> dict[str, Any]:
    if worker_probe is None:
        result = await asyncio.to_thread(_default_worker_probe)
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
                BackgroundJob.created_at < cutoff_time,
            )
        )

        stuck_jobs = await maybe_await(result.scalar())

        result = await db.execute(
            select(
                func.count().label("total"),
                func.sum(sa.cast(BackgroundJob.status == JobStatus.PENDING, sa.Integer)).label(
                    "pending"
                ),
                func.sum(sa.cast(BackgroundJob.status == JobStatus.RUNNING, sa.Integer)).label(
                    "running"
                ),
                func.sum(sa.cast(BackgroundJob.status == JobStatus.FAILED, sa.Integer)).label(
                    "failed"
                ),
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
        return {"status": "unknown", "error": str(exc)}
