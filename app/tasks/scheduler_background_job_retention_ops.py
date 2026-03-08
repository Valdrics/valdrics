from __future__ import annotations

from typing import Any, Callable

from app.tasks.scheduler_retention_utils import (
    coerce_positive_int,
    extract_deleted_count,
)


async def purge_terminal_background_jobs(
    *,
    db: Any,
    sa: Any,
    logger: Any,
    background_job_model: Any,
    job_status: Any,
    datetime_cls: Any,
    timezone_obj: Any,
    timedelta_cls: Any,
    get_settings_fn: Callable[[], Any],
) -> dict[str, int]:
    settings = get_settings_fn()
    completed_days = coerce_positive_int(
        getattr(settings, "BACKGROUND_JOB_COMPLETED_RETENTION_DAYS", 7),
        default=7,
        minimum=1,
    )
    dead_letter_days = coerce_positive_int(
        getattr(settings, "BACKGROUND_JOB_DEAD_LETTER_RETENTION_DAYS", 30),
        default=30,
        minimum=1,
    )
    batch_size = coerce_positive_int(
        getattr(settings, "BACKGROUND_JOB_RETENTION_PURGE_BATCH_SIZE", 1000),
        default=1000,
        minimum=50,
    )
    max_batches = coerce_positive_int(
        getattr(settings, "BACKGROUND_JOB_RETENTION_PURGE_MAX_BATCHES", 20),
        default=20,
        minimum=1,
    )

    now = datetime_cls.now(timezone_obj.utc)
    retention_plan = (
        (
            job_status.COMPLETED.value,
            now - timedelta_cls(days=completed_days),
            completed_days,
        ),
        (
            job_status.DEAD_LETTER.value,
            now - timedelta_cls(days=dead_letter_days),
            dead_letter_days,
        ),
    )

    deleted_by_status: dict[str, int] = {
        job_status.COMPLETED.value: 0,
        job_status.DEAD_LETTER.value: 0,
    }

    for status_value, cutoff, retention_days in retention_plan:
        status_deleted = 0
        for _ in range(max_batches):
            id_subquery = (
                sa.select(background_job_model.id)
                .where(
                    background_job_model.status == status_value,
                    background_job_model.created_at < cutoff,
                )
                .order_by(background_job_model.created_at)
                .limit(batch_size)
                .subquery()
            )
            delete_stmt = sa.delete(background_job_model).where(
                background_job_model.id.in_(sa.select(id_subquery.c.id))
            )
            delete_result = await db.execute(delete_stmt)
            deleted_count = extract_deleted_count(delete_result)
            if deleted_count == 0:
                break
            status_deleted += deleted_count
        deleted_by_status[status_value] = status_deleted
        if status_deleted:
            logger.info(
                "maintenance_background_jobs_purged",
                status=status_value,
                deleted=status_deleted,
                retention_days=retention_days,
                batch_size=batch_size,
                max_batches=max_batches,
            )

    return {
        "completed_deleted": deleted_by_status[job_status.COMPLETED.value],
        "dead_letter_deleted": deleted_by_status[job_status.DEAD_LETTER.value],
        "total_deleted": (
            deleted_by_status[job_status.COMPLETED.value]
            + deleted_by_status[job_status.DEAD_LETTER.value]
        ),
        "completed_retention_days": completed_days,
        "dead_letter_retention_days": dead_letter_days,
    }
