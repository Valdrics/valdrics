from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
import sqlalchemy as sa

from app.models.background_job import BackgroundJob, JobStatus
from app.tasks.scheduler_background_job_retention_ops import (
    purge_terminal_background_jobs,
)


def _delete_result(rowcount: int | object) -> MagicMock:
    result = MagicMock()
    result.rowcount = rowcount
    return result


@pytest.mark.asyncio
async def test_purge_terminal_background_jobs_batches_until_empty() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _delete_result(2),
            _delete_result(1),
            _delete_result(0),
            _delete_result(4),
            _delete_result(0),
            _delete_result(3),
            _delete_result(0),
        ]
    )
    logger = MagicMock()

    summary = await purge_terminal_background_jobs(
        db=db,
        sa=sa,
        logger=logger,
        background_job_model=BackgroundJob,
        job_status=JobStatus,
        datetime_cls=datetime,
        timezone_obj=timezone,
        timedelta_cls=timedelta,
        get_settings_fn=lambda: SimpleNamespace(
            BACKGROUND_JOB_COMPLETED_RETENTION_DAYS=7,
            BACKGROUND_JOB_FAILED_RETENTION_DAYS=30,
            BACKGROUND_JOB_DEAD_LETTER_RETENTION_DAYS=30,
            BACKGROUND_JOB_RETENTION_PURGE_BATCH_SIZE=1000,
            BACKGROUND_JOB_RETENTION_PURGE_MAX_BATCHES=20,
        ),
    )

    assert summary["completed_deleted"] == 3
    assert summary["failed_deleted"] == 4
    assert summary["dead_letter_deleted"] == 3
    assert summary["total_deleted"] == 10
    assert db.execute.await_count == 7
    purged_statuses = {
        call.kwargs.get("status")
        for call in logger.info.call_args_list
        if call.args and call.args[0] == "maintenance_background_jobs_purged"
    }
    assert purged_statuses == {
        JobStatus.COMPLETED.value,
        JobStatus.FAILED.value,
        JobStatus.DEAD_LETTER.value,
    }


@pytest.mark.asyncio
async def test_purge_terminal_background_jobs_defaults_on_invalid_settings() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[_delete_result(0), _delete_result(0), _delete_result(0)]
    )

    summary = await purge_terminal_background_jobs(
        db=db,
        sa=sa,
        logger=MagicMock(),
        background_job_model=BackgroundJob,
        job_status=JobStatus,
        datetime_cls=datetime,
        timezone_obj=timezone,
        timedelta_cls=timedelta,
        get_settings_fn=lambda: SimpleNamespace(
            BACKGROUND_JOB_COMPLETED_RETENTION_DAYS=-1,
            BACKGROUND_JOB_FAILED_RETENTION_DAYS=0,
            BACKGROUND_JOB_DEAD_LETTER_RETENTION_DAYS=0,
            BACKGROUND_JOB_RETENTION_PURGE_BATCH_SIZE=10,
            BACKGROUND_JOB_RETENTION_PURGE_MAX_BATCHES=0,
        ),
    )

    assert summary["completed_retention_days"] == 7
    assert summary["failed_retention_days"] == 30
    assert summary["dead_letter_retention_days"] == 30
    assert summary["total_deleted"] == 0
    assert db.execute.await_count == 3


@pytest.mark.asyncio
async def test_purge_terminal_background_jobs_ignores_non_integer_rowcount() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_delete_result("not-an-int"))

    summary = await purge_terminal_background_jobs(
        db=db,
        sa=sa,
        logger=MagicMock(),
        background_job_model=BackgroundJob,
        job_status=JobStatus,
        datetime_cls=datetime,
        timezone_obj=timezone,
        timedelta_cls=timedelta,
        get_settings_fn=lambda: SimpleNamespace(),
    )

    assert summary["total_deleted"] == 0
    assert db.execute.await_count == 3
