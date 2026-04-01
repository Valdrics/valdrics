from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.tasks.scheduler_sweep_runtime import run_sweep_with_retries


@pytest.mark.asyncio
async def test_run_sweep_with_retries_uses_perf_counter_when_available() -> None:
    run_once = AsyncMock()
    scheduler_job_runs = MagicMock()
    scheduler_job_duration = MagicMock()
    logger = MagicMock()
    time_module = SimpleNamespace(
        perf_counter=MagicMock(side_effect=[10.0, 10.5]),
        time=MagicMock(return_value=999.0),
    )

    await run_sweep_with_retries(
        job_name="billing_sweep",
        error_event="billing_sweep_failed",
        max_retries=3,
        time_module=time_module,
        asyncio_module=SimpleNamespace(sleep=AsyncMock()),
        scheduler_job_runs=scheduler_job_runs,
        scheduler_job_duration=scheduler_job_duration,
        logger=logger,
        recoverable_errors=(RuntimeError,),
        run_once=run_once,
    )

    run_once.assert_awaited_once()
    scheduler_job_runs.labels.assert_called_once_with(
        job_name="billing_sweep",
        status="success",
    )
    assert (
        scheduler_job_duration.labels.return_value.observe.call_args.args[0]
        == pytest.approx(0.5)
    )
    time_module.time.assert_not_called()


@pytest.mark.asyncio
async def test_run_sweep_with_retries_falls_back_to_time_without_perf_counter() -> None:
    scheduler_job_runs = MagicMock()
    scheduler_job_duration = MagicMock()
    logger = MagicMock()
    time_module = SimpleNamespace(time=MagicMock(side_effect=[2.0, 2.25]))

    await run_sweep_with_retries(
        job_name="acceptance_sweep",
        error_event="acceptance_sweep_failed",
        max_retries=1,
        time_module=time_module,
        asyncio_module=SimpleNamespace(sleep=AsyncMock()),
        scheduler_job_runs=scheduler_job_runs,
        scheduler_job_duration=scheduler_job_duration,
        logger=logger,
        recoverable_errors=(RuntimeError,),
        run_once=AsyncMock(),
    )

    assert (
        scheduler_job_duration.labels.return_value.observe.call_args.args[0]
        == pytest.approx(0.25)
    )
    assert time_module.time.call_count == 2
