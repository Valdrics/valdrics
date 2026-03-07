from __future__ import annotations

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


async def evaluate_background_jobs(
    *,
    db: AsyncSession | None,
    recoverable_errors: tuple[type[Exception], ...],
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

        if stuck_jobs and stuck_jobs > 0:
            return {
                "status": "degraded",
                "message": f"{stuck_jobs} jobs stuck in pending state",
                "stuck_jobs": stuck_jobs,
            }

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

        return {
            "status": "healthy",
            "queue_stats": {
                "total_jobs": stats.total or 0,
                "pending_jobs": stats.pending or 0,
                "running_jobs": stats.running or 0,
                "failed_jobs": stats.failed or 0,
            },
        }
    except recoverable_errors as exc:
        return {"status": "unknown", "error": str(exc)}
