"""Evidence payload and threshold evaluation helpers for load-test runner."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from app.shared.core.performance_evidence import (
    LoadTestThresholds,
    evaluate_load_test_result,
)


@dataclass(frozen=True)
class AggregatedLoadResults:
    results_payload: dict[str, object]
    worst_p95: float
    min_throughput: float


def result_to_payload(result: object) -> dict[str, object]:
    return {
        "total_requests": int(getattr(result, "total_requests", 0) or 0),
        "successful_requests": int(getattr(result, "successful_requests", 0) or 0),
        "failed_requests": int(getattr(result, "failed_requests", 0) or 0),
        "throughput_rps": float(getattr(result, "throughput_rps", 0.0) or 0.0),
        "avg_response_time": float(getattr(result, "avg_response_time", 0.0) or 0.0),
        "median_response_time": float(
            getattr(result, "median_response_time", 0.0) or 0.0
        ),
        "p95_response_time": float(getattr(result, "p95_response_time", 0.0) or 0.0),
        "p99_response_time": float(getattr(result, "p99_response_time", 0.0) or 0.0),
        "min_response_time": float(getattr(result, "min_response_time", 0.0) or 0.0),
        "max_response_time": float(getattr(result, "max_response_time", 0.0) or 0.0),
        "errors_sample": list(getattr(result, "errors", [])[:10]),
    }


def build_preflight_failure_payload(
    *,
    profile: str,
    target_url: str,
    endpoints: list[str],
    preflight: dict[str, Any],
    runtime_snapshot: dict[str, Any],
) -> dict[str, object]:
    return {
        "profile": profile,
        "target_url": target_url,
        "endpoints": endpoints,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "runner": "scripts/load_test_api.py",
        "status": "preflight_failed",
        "preflight": preflight,
        "runtime": runtime_snapshot,
        "meets_targets": False,
        "results": {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "throughput_rps": 0.0,
            "avg_response_time": 0.0,
            "median_response_time": 0.0,
            "p95_response_time": 0.0,
            "p99_response_time": 0.0,
            "min_response_time": 0.0,
            "max_response_time": 0.0,
            "errors_sample": [
                f"Preflight failed for {item['endpoint']}: {item['error']}"
                for item in list(preflight.get("failures", []))[:10]
            ],
        },
    }


def aggregate_load_results(raw_results: list[object]) -> AggregatedLoadResults:
    rounds = max(1, len(raw_results))
    total_requests = sum(int(getattr(r, "total_requests", 0) or 0) for r in raw_results)
    successful_requests = sum(
        int(getattr(r, "successful_requests", 0) or 0) for r in raw_results
    )
    failed_requests = sum(int(getattr(r, "failed_requests", 0) or 0) for r in raw_results)
    worst_p95 = max(float(getattr(r, "p95_response_time", 0.0) or 0.0) for r in raw_results)
    worst_p99 = max(float(getattr(r, "p99_response_time", 0.0) or 0.0) for r in raw_results)
    min_throughput = min(
        float(getattr(r, "throughput_rps", 0.0) or 0.0) for r in raw_results
    )
    avg_throughput = sum(
        float(getattr(r, "throughput_rps", 0.0) or 0.0) for r in raw_results
    ) / rounds
    min_response = min(
        float(getattr(r, "min_response_time", 0.0) or 0.0) for r in raw_results
    )
    max_response = max(
        float(getattr(r, "max_response_time", 0.0) or 0.0) for r in raw_results
    )
    avg_response_time = sum(
        float(getattr(r, "avg_response_time", 0.0) or 0.0) for r in raw_results
    ) / rounds
    median_response_time = sum(
        float(getattr(r, "median_response_time", 0.0) or 0.0) for r in raw_results
    ) / rounds

    errors_sample: list[str] = []
    for raw in raw_results:
        for err in list(getattr(raw, "errors", [])[:10]):
            if err not in errors_sample:
                errors_sample.append(err)
        if len(errors_sample) >= 10:
            break

    results_payload = {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
        "throughput_rps": round(avg_throughput, 4),
        "avg_response_time": round(avg_response_time, 4),
        "median_response_time": round(median_response_time, 4),
        "p95_response_time": round(worst_p95, 4),
        "p99_response_time": round(worst_p99, 4),
        "min_response_time": round(min_response, 4),
        "max_response_time": round(max_response, 4),
        "errors_sample": errors_sample[:10],
    }
    return AggregatedLoadResults(
        results_payload=results_payload,
        worst_p95=float(worst_p95),
        min_throughput=float(min_throughput),
    )


def profile_default_thresholds() -> dict[str, LoadTestThresholds]:
    return {
        "health": LoadTestThresholds(
            max_p95_seconds=1.0, max_error_rate_percent=1.0, min_throughput_rps=1.0
        ),
        "health_deep": LoadTestThresholds(
            max_p95_seconds=4.0, max_error_rate_percent=2.0, min_throughput_rps=0.2
        ),
        "dashboard": LoadTestThresholds(
            max_p95_seconds=2.5, max_error_rate_percent=1.0, min_throughput_rps=0.5
        ),
        "ops": LoadTestThresholds(
            max_p95_seconds=2.5, max_error_rate_percent=1.0, min_throughput_rps=0.5
        ),
        "scale": LoadTestThresholds(
            max_p95_seconds=4.0, max_error_rate_percent=2.0, min_throughput_rps=0.2
        ),
        "soak": LoadTestThresholds(
            max_p95_seconds=4.0, max_error_rate_percent=2.0, min_throughput_rps=0.2
        ),
        "enforcement": LoadTestThresholds(
            max_p95_seconds=2.0, max_error_rate_percent=1.0, min_throughput_rps=0.5
        ),
    }


def resolve_threshold_inputs(
    *,
    profile: str,
    p95_target: float | None,
    max_error_rate: float | None,
    min_throughput: float | None,
    enforce_thresholds: bool,
) -> tuple[LoadTestThresholds | None, bool]:
    enforce = bool(enforce_thresholds)
    explicit_thresholds = (
        p95_target is not None
        or max_error_rate is not None
        or min_throughput is not None
    )
    if explicit_thresholds:
        thresholds = LoadTestThresholds(
            max_p95_seconds=float(p95_target or 999999),
            max_error_rate_percent=float(max_error_rate or 100),
            min_throughput_rps=(
                float(min_throughput) if min_throughput is not None else None
            ),
        )
        return thresholds, True
    return profile_default_thresholds().get(profile), enforce


def attach_threshold_evaluation(
    *,
    evidence_payload: dict[str, object],
    raw_results: list[object],
    thresholds: LoadTestThresholds,
    worst_p95: float,
    min_throughput: float,
) -> bool | None:
    per_round = [evaluate_load_test_result(raw, thresholds) for raw in raw_results]
    evidence_payload["thresholds"] = {
        "max_p95_seconds": thresholds.max_p95_seconds,
        "max_error_rate_percent": thresholds.max_error_rate_percent,
        "min_throughput_rps": thresholds.min_throughput_rps,
    }
    evidence_payload["evaluation"] = {
        "rounds": [item.model_dump() for item in per_round],
        "overall_meets_targets": (
            all(item.meets_targets for item in per_round) if per_round else None
        ),
        "worst_p95_seconds": float(worst_p95),
        "min_throughput_rps": float(min_throughput),
    }
    meets_targets = all(item.meets_targets for item in per_round) if per_round else None
    evidence_payload["meets_targets"] = meets_targets
    return meets_targets
