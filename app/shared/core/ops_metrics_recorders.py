"""Recorder helpers for Prometheus operational metrics."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

F = TypeVar("F", bound=Callable[..., Any])


def time_operation(*, operation_name: str, db_query_duration: Any, sys_module: Any) -> Callable[[F], F]:
    """Build a decorator that records duration for DB-tagged operations."""

    def decorator(func: F) -> F:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = sys_module.modules["time"].time()
            completed = False
            try:
                result = func(*args, **kwargs)
                completed = True
                return result
            finally:
                duration = sys_module.modules["time"].time() - start_time
                if "db" in operation_name.lower():
                    if completed:
                        db_query_duration.labels(operation_type=operation_name).observe(duration)
                    elif sys_module.exc_info()[0] is not None:
                        db_query_duration.labels(
                            operation_type=f"{operation_name}_error"
                        ).observe(duration)

        return cast(F, wrapper)

    return decorator


def record_circuit_breaker_metrics(
    *,
    circuit_name: str,
    state: str,
    failures: int,
    successes: int,
    circuit_breaker_state: Any,
    circuit_breaker_failures: Any,
    circuit_breaker_recoveries: Any,
) -> None:
    """Record circuit breaker state changes and aggregate counters."""
    state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state, 0)
    circuit_breaker_state.labels(circuit_name=circuit_name).set(state_value)

    if failures > 0:
        circuit_breaker_failures.labels(circuit_name=circuit_name).inc(failures)

    if successes > 0:
        circuit_breaker_recoveries.labels(circuit_name=circuit_name).inc(successes)


def record_retry_metrics(*, operation_type: str, attempt: int, operation_retries_total: Any) -> None:
    """Record retry metrics."""
    operation_retries_total.labels(operation_type=operation_type, attempt=str(attempt)).inc()


def record_timeout_metrics(*, operation_type: str, operation_timeouts_total: Any) -> None:
    """Record timeout metrics."""
    operation_timeouts_total.labels(operation_type=operation_type).inc()
