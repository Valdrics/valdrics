from __future__ import annotations

from types import SimpleNamespace

from scripts.load_test_api_reporting import (
    aggregate_load_results,
    build_preflight_failure_payload,
    resolve_threshold_inputs,
)


def _result(
    *,
    total: int,
    success: int,
    failed: int,
    throughput: float,
    avg: float,
    median: float,
    p95: float,
    p99: float,
    min_rt: float,
    max_rt: float,
    errors: list[str],
) -> SimpleNamespace:
    return SimpleNamespace(
        total_requests=total,
        successful_requests=success,
        failed_requests=failed,
        throughput_rps=throughput,
        avg_response_time=avg,
        median_response_time=median,
        p95_response_time=p95,
        p99_response_time=p99,
        min_response_time=min_rt,
        max_response_time=max_rt,
        errors=errors,
    )


def test_aggregate_load_results_preserves_worst_case_and_deduped_errors() -> None:
    raw_results = [
        _result(
            total=20,
            success=19,
            failed=1,
            throughput=2.5,
            avg=0.4,
            median=0.35,
            p95=0.9,
            p99=1.2,
            min_rt=0.1,
            max_rt=1.3,
            errors=["e1", "e2"],
        ),
        _result(
            total=30,
            success=30,
            failed=0,
            throughput=3.0,
            avg=0.5,
            median=0.45,
            p95=1.1,
            p99=1.4,
            min_rt=0.2,
            max_rt=1.5,
            errors=["e2", "e3"],
        ),
    ]

    aggregate = aggregate_load_results(raw_results)
    payload = aggregate.results_payload
    assert payload["total_requests"] == 50
    assert payload["failed_requests"] == 1
    assert payload["p95_response_time"] == 1.1
    assert payload["p99_response_time"] == 1.4
    assert payload["errors_sample"] == ["e1", "e2", "e3"]
    assert aggregate.worst_p95 == 1.1
    assert aggregate.min_throughput == 2.5


def test_resolve_threshold_inputs_promotes_explicit_targets_to_enforced() -> None:
    thresholds, enforce = resolve_threshold_inputs(
        profile="dashboard",
        p95_target=2.0,
        max_error_rate=1.0,
        min_throughput=0.8,
        enforce_thresholds=False,
    )
    assert thresholds is not None
    assert thresholds.max_p95_seconds == 2.0
    assert thresholds.max_error_rate_percent == 1.0
    assert thresholds.min_throughput_rps == 0.8
    assert enforce is True


def test_build_preflight_failure_payload_contains_failed_endpoints() -> None:
    payload = build_preflight_failure_payload(
        profile="health",
        target_url="http://127.0.0.1:8000",
        endpoints=["/health/live"],
        preflight={
            "failures": [{"endpoint": "/health/live", "error": "HTTP 500"}],
        },
        runtime_snapshot={"database_engine": "postgresql"},
    )
    assert payload["status"] == "preflight_failed"
    errors = payload["results"]["errors_sample"]  # type: ignore[index]
    assert errors == ["Preflight failed for /health/live: HTTP 500"]
