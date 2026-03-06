from __future__ import annotations

import inspect
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Awaitable, Callable


@asynccontextmanager
async def open_transaction_session(
    *,
    open_db_session_fn: Callable[[], Any],
    asyncio_module: Any,
) -> AsyncIterator[Any]:
    async with open_db_session_fn() as db:
        begin_ctx = db.begin()
        if (
            asyncio_module.iscoroutine(begin_ctx)
            or inspect.isawaitable(begin_ctx)
        ) and not hasattr(begin_ctx, "__aenter__"):
            begin_ctx = await begin_ctx
        async with begin_ctx:
            yield db


async def run_sweep_with_retries(
    *,
    job_name: str,
    error_event: str,
    max_retries: int,
    time_module: Any,
    asyncio_module: Any,
    scheduler_job_runs: Any,
    scheduler_job_duration: Any,
    logger: Any,
    recoverable_errors: tuple[type[Exception], ...],
    run_once: Callable[[], Awaitable[None]],
) -> None:
    start_time = time_module.time()
    retry_count = 0

    while retry_count < max_retries:
        try:
            await run_once()
            scheduler_job_runs.labels(job_name=job_name, status="success").inc()
            break
        except recoverable_errors as exc:
            retry_count += 1
            logger.error(error_event, error=str(exc), attempt=retry_count)
            if retry_count == max_retries:
                scheduler_job_runs.labels(job_name=job_name, status="failure").inc()
            else:
                await asyncio_module.sleep(2 ** (retry_count - 1))

    duration = time_module.time() - start_time
    scheduler_job_duration.labels(job_name=job_name).observe(duration)


def increment_background_job_metric(
    *,
    background_jobs_enqueued: Any,
    job_type_value: str,
    cohort: str,
) -> None:
    background_jobs_enqueued.labels(
        job_type=job_type_value,
        cohort=cohort,
    ).inc()
