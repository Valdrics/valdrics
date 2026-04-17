#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import time

from app.shared.orchestration.managed_work_runners import (
    SCHEDULER_RECOVERABLE_ERRORS,
    run_background_job_processing,
    run_background_job_stuck_detection,
)


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the repository-managed local background worker loop used by CI and"
            " drill workflows."
        )
    )
    parser.add_argument(
        "--interval-seconds",
        type=float,
        default=1.0,
        help="Delay between background job drain iterations.",
    )
    parser.add_argument(
        "--stuck-check-interval-seconds",
        type=float,
        default=300.0,
        help="Delay between overdue-pending detection runs.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one processing iteration and one stuck-job check, then exit.",
    )
    return parser.parse_args(argv)


class _ManagedWorkerLoop:
    def __init__(
        self,
        *,
        interval_seconds: float,
        stuck_check_interval_seconds: float,
        once: bool,
    ) -> None:
        self._interval_seconds = max(0.1, float(interval_seconds))
        self._stuck_check_interval_seconds = max(
            self._interval_seconds,
            float(stuck_check_interval_seconds),
        )
        self._once = once
        self._stop_requested = asyncio.Event()

    def request_stop(self) -> None:
        self._stop_requested.set()

    async def _run_iteration(self, *, force_stuck_check: bool) -> None:
        await run_background_job_processing({})
        if force_stuck_check:
            await run_background_job_stuck_detection({})

    async def run(self) -> int:
        next_stuck_check_at = time.monotonic()
        while True:
            now = time.monotonic()
            force_stuck_check = self._once or now >= next_stuck_check_at
            await self._run_iteration(force_stuck_check=force_stuck_check)
            if force_stuck_check:
                next_stuck_check_at = (
                    time.monotonic() + self._stuck_check_interval_seconds
                )

            if self._once or self._stop_requested.is_set():
                return 0

            try:
                await asyncio.wait_for(
                    self._stop_requested.wait(),
                    timeout=self._interval_seconds,
                )
            except TimeoutError:
                continue


async def _run_async(argv: list[str]) -> int:
    args = _parse_args(argv)
    worker = _ManagedWorkerLoop(
        interval_seconds=args.interval_seconds,
        stuck_check_interval_seconds=args.stuck_check_interval_seconds,
        once=bool(args.once),
    )

    loop = asyncio.get_running_loop()
    for signame in ("SIGINT", "SIGTERM"):
        sig = getattr(signal, signame, None)
        if sig is None:
            continue
        try:
            loop.add_signal_handler(sig, worker.request_stop)
        except (RuntimeError, ValueError):
            signal.signal(sig, lambda *_args: worker.request_stop())

    try:
        return await worker.run()
    except SCHEDULER_RECOVERABLE_ERRORS as exc:
        print(f"managed worker loop failed: {exc}", file=sys.stderr, flush=True)
        return 1


def main(argv: list[str] | None = None) -> int:
    return asyncio.run(_run_async(list(sys.argv[1:] if argv is None else argv)))


if __name__ == "__main__":
    raise SystemExit(main())
