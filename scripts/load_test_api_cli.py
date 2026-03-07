"""CLI parsing for the load-test runner."""

from __future__ import annotations

import argparse


LOAD_TEST_PROFILES: tuple[str, ...] = (
    "health",
    "health_deep",
    "dashboard",
    "ops",
    "scale",
    "soak",
    "enforcement",
)


def parse_load_test_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a small API load test.")
    parser.add_argument(
        "--url", dest="url", default="http://127.0.0.1:8000", help="Base URL"
    )
    parser.add_argument(
        "--profile",
        dest="profile",
        choices=list(LOAD_TEST_PROFILES),
        default="health",
        help="Use a pre-defined endpoint profile when --endpoint is not supplied.",
    )
    parser.add_argument(
        "--endpoint",
        dest="endpoints",
        action="append",
        default=[],
        help="Endpoint path (repeatable). Default: /health/live",
    )
    parser.add_argument(
        "--include-deep-health",
        dest="include_deep_health",
        action="store_true",
        help="Include /health in generated profile endpoints.",
    )
    parser.add_argument(
        "--start-date", dest="start_date", default="", help="ISO date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date", dest="end_date", default="", help="ISO date (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--provider",
        dest="provider",
        default="",
        help="Provider filter (aws/azure/gcp/...)",
    )
    parser.add_argument(
        "--duration", dest="duration", type=int, default=30, help="Duration in seconds"
    )
    parser.add_argument(
        "--users", dest="users", type=int, default=10, help="Concurrent users"
    )
    parser.add_argument(
        "--ramp", dest="ramp", type=int, default=5, help="Ramp-up seconds"
    )
    parser.add_argument(
        "--timeout",
        dest="timeout",
        type=float,
        default=15.0,
        help="Request timeout seconds",
    )
    parser.add_argument(
        "--skip-preflight",
        dest="skip_preflight",
        action="store_true",
        help="Skip preflight endpoint validation before the load run.",
    )
    parser.add_argument(
        "--allow-preflight-failures",
        dest="allow_preflight_failures",
        action="store_true",
        help="Continue load run even if preflight checks fail.",
    )
    parser.add_argument(
        "--preflight-attempts",
        dest="preflight_attempts",
        type=int,
        default=2,
        help="Number of preflight attempts per endpoint.",
    )
    parser.add_argument(
        "--preflight-timeout",
        dest="preflight_timeout",
        type=float,
        default=5.0,
        help="Timeout (seconds) per preflight request.",
    )
    parser.add_argument(
        "--rounds",
        dest="rounds",
        type=int,
        default=1,
        help="Repeat the run N times (soak). Aggregates worst-case p95/error-rate for evidence.",
    )
    parser.add_argument(
        "--pause",
        dest="pause",
        type=float,
        default=0.0,
        help="Pause in seconds between rounds (soak).",
    )
    parser.add_argument(
        "--out",
        dest="out",
        default="",
        help="Write JSON results to this path (optional)",
    )
    parser.add_argument(
        "--p95-target",
        dest="p95_target",
        type=float,
        default=None,
        help="Fail if p95 response time exceeds this value (seconds).",
    )
    parser.add_argument(
        "--max-error-rate",
        dest="max_error_rate",
        type=float,
        default=None,
        help="Fail if failed request rate exceeds this value (percent).",
    )
    parser.add_argument(
        "--min-throughput",
        dest="min_throughput",
        type=float,
        default=None,
        help="Fail if throughput is below this value (requests per second).",
    )
    parser.add_argument(
        "--enforce-thresholds",
        dest="enforce_thresholds",
        action="store_true",
        help="Exit non-zero if the evaluated thresholds are not met.",
    )
    parser.add_argument(
        "--publish",
        dest="publish",
        action="store_true",
        help="Publish the load test evidence to the tenant audit log (Pro+ admin only).",
    )
    return parser.parse_args()
