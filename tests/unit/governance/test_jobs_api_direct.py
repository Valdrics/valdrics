from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import BackgroundTasks

from app.modules.governance.api.v1.jobs import internal_process_jobs


@pytest.mark.asyncio
async def test_internal_process_jobs_dispatches_to_celery_when_available() -> None:
    celery_app = MagicMock()

    with patch(
        "app.shared.core.celery_app.celery_app",
        celery_app,
    ):
        result = await internal_process_jobs(
            background_tasks=BackgroundTasks(),
            _db=MagicMock(),
            _auth=None,
        )

    celery_app.send_task.assert_called_once_with("scheduler.process_background_jobs")
    assert result == {
        "status": "accepted",
        "message": "Background job processing dispatched to Celery",
    }


@pytest.mark.asyncio
async def test_internal_process_jobs_runs_inline_when_dispatch_fails() -> None:
    session = AsyncMock()
    processor = AsyncMock()

    @asynccontextmanager
    async def session_context():
        yield session

    processor_cls = MagicMock(return_value=processor)
    celery_app = MagicMock()
    celery_app.send_task.side_effect = RuntimeError("broker unavailable")

    with (
        patch("app.shared.core.celery_app.celery_app", celery_app),
        patch(
            "app.modules.governance.api.v1.jobs.async_session_maker",
            return_value=session_context(),
        ),
        patch(
            "app.modules.governance.api.v1.jobs.mark_session_system_context",
            new=AsyncMock(),
        ) as mark_system,
        patch(
            "app.modules.governance.api.v1.jobs.JobProcessor",
            processor_cls,
        ),
    ):
        result = await internal_process_jobs(
            background_tasks=BackgroundTasks(),
            _db=MagicMock(),
            _auth=None,
        )

    celery_app.send_task.assert_called_once_with("scheduler.process_background_jobs")
    mark_system.assert_awaited_once_with(session)
    processor_cls.assert_called_once_with(session)
    processor.process_pending_jobs.assert_awaited_once()
    assert result == {
        "status": "completed",
        "message": "Background job processing completed inline",
    }
