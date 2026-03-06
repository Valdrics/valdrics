from __future__ import annotations

import asyncio
import time
from typing import Any, cast

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.engine import CursorResult
from sqlalchemy.exc import SQLAlchemyError

from app.models.enforcement import EnforcementPolicy, EnforcementSource
from app.shared.core.ops_metrics import (
    ENFORCEMENT_GATE_LOCK_EVENTS_TOTAL,
    ENFORCEMENT_GATE_LOCK_WAIT_SECONDS,
)


async def acquire_gate_evaluation_lock(
    service: Any,
    *,
    policy: EnforcementPolicy,
    source: EnforcementSource,
) -> None:
    from app.modules.enforcement.domain import service as enforcement_service_module

    service_asyncio = getattr(enforcement_service_module, "asyncio", asyncio)
    service_time = getattr(enforcement_service_module, "time", time)
    wait_for_fn = getattr(service_asyncio, "wait_for", asyncio.wait_for)
    perf_counter_fn = getattr(service_time, "perf_counter", time.perf_counter)
    lock_events_total = getattr(
        enforcement_service_module,
        "ENFORCEMENT_GATE_LOCK_EVENTS_TOTAL",
        ENFORCEMENT_GATE_LOCK_EVENTS_TOTAL,
    )
    lock_wait_seconds = getattr(
        enforcement_service_module,
        "ENFORCEMENT_GATE_LOCK_WAIT_SECONDS",
        ENFORCEMENT_GATE_LOCK_WAIT_SECONDS,
    )

    lock_timeout_seconds = service._gate_lock_timeout_seconds()
    started_at = perf_counter_fn()
    try:
        result = cast(
            CursorResult[Any],
            await wait_for_fn(
                service.db.execute(
                    update(EnforcementPolicy)
                    .where(EnforcementPolicy.id == policy.id)
                    .where(EnforcementPolicy.tenant_id == policy.tenant_id)
                    .values(policy_version=EnforcementPolicy.policy_version)
                ),
                timeout=lock_timeout_seconds,
            ),
        )
    except TimeoutError as exc:
        wait_seconds = max(0.0, perf_counter_fn() - started_at)
        lock_wait_seconds.labels(
            source=source.value,
            outcome="timeout",
        ).observe(wait_seconds)
        lock_events_total.labels(
            source=source.value,
            event="timeout",
        ).inc()
        lock_events_total.labels(
            source=source.value,
            event="contended",
        ).inc()
        await service.db.rollback()
        raise HTTPException(
            status_code=503,
            detail={
                "code": "gate_lock_timeout",
                "message": "Enforcement gate evaluation lock timeout",
                "lock_timeout_seconds": f"{lock_timeout_seconds:.3f}",
                "lock_wait_seconds": f"{wait_seconds:.3f}",
            },
        ) from exc
    except (SQLAlchemyError, RuntimeError):
        wait_seconds = max(0.0, perf_counter_fn() - started_at)
        lock_wait_seconds.labels(
            source=source.value,
            outcome="error",
        ).observe(wait_seconds)
        lock_events_total.labels(
            source=source.value,
            event="error",
        ).inc()
        raise

    wait_seconds = max(0.0, perf_counter_fn() - started_at)
    lock_wait_seconds.labels(
        source=source.value,
        outcome="acquired",
    ).observe(wait_seconds)
    lock_events_total.labels(
        source=source.value,
        event="acquired",
    ).inc()
    if wait_seconds >= 0.05:
        lock_events_total.labels(
            source=source.value,
            event="contended",
        ).inc()
    if result.rowcount == 0:
        lock_events_total.labels(
            source=source.value,
            event="not_acquired",
        ).inc()
        raise HTTPException(
            status_code=409,
            detail={
                "code": "gate_lock_contended",
                "message": "Unable to acquire enforcement gate evaluation lock",
                "lock_wait_seconds": f"{wait_seconds:.3f}",
            },
        )
