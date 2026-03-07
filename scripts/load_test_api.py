#!/usr/bin/env python3
"""
Lightweight API load test runner for local/staging validation.

This wraps `app.shared.core.performance_testing.LoadTester` so we can
standardize how we measure p95/p99 for key endpoints during hardening.

Example:
  export VALDRICS_TOKEN="$(uv run python scripts/dev_bearer_token.py --email owner@valdrics.io)"
  uv run python scripts/load_test_api.py --url http://127.0.0.1:8000 --endpoint /health/live --endpoint /api/v1/costs/acceptance/kpis

Perf smoke (dashboard profile):
  uv run python scripts/load_test_api.py --profile dashboard --duration 30 --users 15 \\
    --p95-target 2.0 --max-error-rate 1.0 --out reports/performance/dashboard_smoke.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from typing import Any
from datetime import date, timedelta
from datetime import datetime, timezone

import httpx

from app.shared.core.evidence_capture import sanitize_bearer_token
from app.shared.core.performance_testing import (
    LoadTestConfig,
    LoadTester,
    format_exception_message,
)
from scripts.load_test_api_cli import parse_load_test_args
from scripts.load_test_api_reporting import (
    aggregate_load_results,
    attach_threshold_evaluation,
    build_preflight_failure_payload,
    resolve_threshold_inputs,
    result_to_payload,
)

LIVENESS_ENDPOINT = "/health/live"
DEEP_HEALTH_ENDPOINT = "/health"
LOAD_TEST_PROBE_RECOVERABLE_EXCEPTIONS = (
    httpx.HTTPError,
    json.JSONDecodeError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


def _parse_args() -> argparse.Namespace:
    return parse_load_test_args()


def _resolve_date_window(args: argparse.Namespace) -> tuple[str, str]:
    if args.start_date and args.end_date:
        return str(args.start_date).strip(), str(args.end_date).strip()
    end = date.today()
    start = end - timedelta(days=30)
    return start.isoformat(), end.isoformat()


def _build_profile_endpoints(args: argparse.Namespace) -> list[str]:
    provider = str(args.provider or "").strip().lower()
    provider_query = f"&provider={provider}" if provider else ""
    carbon_provider_query = (
        provider_query if provider in {"aws", "azure", "gcp"} else ""
    )
    zombies_provider_query = (
        provider_query if provider in {"aws", "azure", "gcp", "saas", "license"} else ""
    )

    if args.profile == "health":
        endpoints = [LIVENESS_ENDPOINT]
    elif args.profile == "health_deep":
        endpoints = [DEEP_HEALTH_ENDPOINT]
    elif args.profile == "enforcement":
        endpoints = _build_enforcement_profile_endpoints(args)
    elif args.profile == "dashboard":
        start_date, end_date = _resolve_date_window(args)
        endpoints = [
            LIVENESS_ENDPOINT,
            f"/api/v1/costs?start_date={start_date}&end_date={end_date}{provider_query}",
            f"/api/v1/carbon?start_date={start_date}&end_date={end_date}{carbon_provider_query}",
            f"/api/v1/zombies?analyze=false{zombies_provider_query}",
        ]
    elif args.profile in {"scale", "soak"}:
        endpoints = _build_scale_profile_endpoints(args)
    else:
        # ops profile
        start_date, end_date = _resolve_date_window(args)
        endpoints = [
            LIVENESS_ENDPOINT,
            "/api/v1/costs/ingestion/sla?window_hours=24&target_success_rate_percent=95",
            (
                "/api/v1/costs/acceptance/kpis?"
                f"start_date={start_date}&end_date={end_date}"
                "&ingestion_window_hours=168"
                "&ingestion_target_success_rate_percent=95"
                "&recency_target_hours=48"
                "&chargeback_target_percent=90"
                "&max_unit_anomalies=0"
                "&response_format=json"
            ),
        ]

    if args.include_deep_health and DEEP_HEALTH_ENDPOINT not in endpoints:
        endpoints.insert(0, DEEP_HEALTH_ENDPOINT)

    return endpoints


def _build_scale_profile_endpoints(args: argparse.Namespace) -> list[str]:
    start_date, end_date = _resolve_date_window(args)
    provider = str(args.provider or "").strip().lower()
    provider_query = f"&provider={provider}" if provider else ""
    return [
        LIVENESS_ENDPOINT,
        f"/api/v1/costs?start_date={start_date}&end_date={end_date}{provider_query}",
        (
            "/api/v1/costs/acceptance/kpis?"
            f"start_date={start_date}&end_date={end_date}"
            "&ingestion_window_hours=168"
            "&ingestion_target_success_rate_percent=95"
            "&recency_target_hours=48"
            "&chargeback_target_percent=90"
            "&max_unit_anomalies=0"
            "&response_format=json"
        ),
        f"/api/v1/leadership/kpis?start_date={start_date}&end_date={end_date}&response_format=json{provider_query}",
        f"/api/v1/savings/proof?start_date={start_date}&end_date={end_date}&response_format=json{provider_query}",
        "/api/v1/leaderboards?period=30d",
    ]


def _build_enforcement_profile_endpoints(args: argparse.Namespace) -> list[str]:
    del args  # profile does not currently depend on date/provider filters.
    return [
        LIVENESS_ENDPOINT,
        "/api/v1/enforcement/policies",
        "/api/v1/enforcement/budgets",
        "/api/v1/enforcement/credits",
        "/api/v1/enforcement/approvals/queue?limit=50",
        "/api/v1/enforcement/ledger?limit=50",
        "/api/v1/enforcement/exports/parity?limit=50",
    ]


def _normalize_database_engine_name(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    candidate = raw.split("://", 1)[0].split("+", 1)[0]
    if candidate.startswith("postgres"):
        return "postgresql"
    if candidate.startswith("sqlite"):
        return "sqlite"
    return candidate


def _extract_health_database_engine(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    database = payload.get("database")
    if not isinstance(database, dict):
        return ""
    return _normalize_database_engine_name(
        database.get("engine") or database.get("dialect")
    )


async def _collect_runtime_snapshot(
    *,
    target_url: str,
    headers: dict[str, str],
    timeout_seconds: float,
) -> dict[str, Any]:
    request_timeout = max(0.1, float(timeout_seconds))
    snapshot: dict[str, Any] = {
        "health_endpoint": DEEP_HEALTH_ENDPOINT,
        "database_engine": "unknown",
    }
    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(request_timeout, connect=min(request_timeout, 5.0)),
            headers=headers,
        ) as client:
            response = await client.get(f"{target_url}{DEEP_HEALTH_ENDPOINT}")
        snapshot["health_status_code"] = int(response.status_code)
        if response.headers.get("content-type", "").lower().startswith(
            "application/json"
        ):
            payload = response.json()
        else:
            payload = {}
        if isinstance(payload, dict):
            status = payload.get("status")
            if status is not None:
                snapshot["status"] = str(status)
            database_engine = _extract_health_database_engine(payload)
            if database_engine:
                snapshot["database_engine"] = database_engine
    except LOAD_TEST_PROBE_RECOVERABLE_EXCEPTIONS as exc:
        snapshot["probe_error"] = format_exception_message(exc)
    return snapshot


async def _run_preflight_checks(
    *,
    target_url: str,
    endpoints: list[str],
    headers: dict[str, str],
    timeout_seconds: float,
    attempts: int,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    request_timeout = max(0.1, float(timeout_seconds))
    attempts = max(1, int(attempts))

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(request_timeout, connect=min(request_timeout, 5.0)),
        headers=headers,
    ) as client:
        for endpoint in endpoints:
            passed = False
            for attempt in range(1, attempts + 1):
                started = datetime.now(timezone.utc)
                try:
                    response = await client.get(f"{target_url}{endpoint}")
                    latency_ms = max(
                        0.0,
                        (datetime.now(timezone.utc) - started).total_seconds() * 1000.0,
                    )
                    status_code = int(response.status_code)
                    preview = str(response.text or "").replace("\n", " ")[:140]
                    ok = status_code < 400
                    checks.append(
                        {
                            "endpoint": endpoint,
                            "attempt": attempt,
                            "status_code": status_code,
                            "ok": ok,
                            "latency_ms": round(latency_ms, 2),
                            "error": "" if ok else f"HTTP {status_code}: {preview}",
                        }
                    )
                    if ok:
                        passed = True
                        break
                except LOAD_TEST_PROBE_RECOVERABLE_EXCEPTIONS as exc:
                    latency_ms = max(
                        0.0,
                        (datetime.now(timezone.utc) - started).total_seconds() * 1000.0,
                    )
                    checks.append(
                        {
                            "endpoint": endpoint,
                            "attempt": attempt,
                            "status_code": None,
                            "ok": False,
                            "latency_ms": round(latency_ms, 2),
                            "error": format_exception_message(exc),
                        }
                    )
                if attempt < attempts:
                    await asyncio.sleep(min(0.25, attempt * 0.1))
            if not passed:
                last = checks[-1]
                failures.append(
                    {
                        "endpoint": endpoint,
                        "error": str(last.get("error") or "preflight failed"),
                    }
                )

    return {
        "enabled": True,
        "passed": len(failures) == 0,
        "attempts_per_endpoint": attempts,
        "request_timeout_seconds": request_timeout,
        "checks": checks,
        "failures": failures,
    }


async def main() -> None:
    args = _parse_args()
    endpoints = args.endpoints or _build_profile_endpoints(args)

    headers: dict[str, str] = {}
    token = ""
    raw_token = os.getenv("VALDRICS_TOKEN", "").strip()
    if raw_token:
        try:
            token = sanitize_bearer_token(raw_token)
        except ValueError as exc:
            raise SystemExit(
                "Invalid VALDRICS_TOKEN. Ensure it's a single JWT string. "
                f"Details: {exc}"
            ) from None
        headers["Authorization"] = f"Bearer {token}"

    config = LoadTestConfig(
        duration_seconds=int(args.duration),
        concurrent_users=int(args.users),
        ramp_up_seconds=int(args.ramp),
        target_url=str(args.url).rstrip("/"),
        endpoints=endpoints,
        request_timeout=float(args.timeout),
        headers=headers,
    )

    rounds = max(1, int(args.rounds or 1))
    pause_seconds = max(0.0, float(args.pause or 0.0))
    preflight_attempts = max(1, int(args.preflight_attempts or 1))
    preflight_timeout = max(0.1, float(args.preflight_timeout or 0.1))
    skip_preflight = bool(args.skip_preflight)
    allow_preflight_failures = bool(args.allow_preflight_failures)

    preflight: dict[str, Any]
    if skip_preflight:
        preflight = {
            "enabled": False,
            "passed": None,
            "attempts_per_endpoint": 0,
            "request_timeout_seconds": preflight_timeout,
            "checks": [],
            "failures": [],
        }
    else:
        preflight = await _run_preflight_checks(
            target_url=config.target_url,
            endpoints=endpoints,
            headers=headers,
            timeout_seconds=preflight_timeout,
            attempts=preflight_attempts,
        )
        runtime_snapshot = await _collect_runtime_snapshot(
            target_url=config.target_url,
            headers=headers,
            timeout_seconds=preflight_timeout,
        )
        if not preflight.get("passed") and not allow_preflight_failures:
            failure_payload = build_preflight_failure_payload(
                profile=str(args.profile),
                target_url=str(config.target_url),
                endpoints=list(endpoints),
                preflight=preflight,
                runtime_snapshot=runtime_snapshot,
            )
            print(json.dumps(failure_payload, indent=2, sort_keys=True))
            if args.out:
                with open(args.out, "w", encoding="utf-8") as f:
                    json.dump(failure_payload, f, indent=2, sort_keys=True)
            raise SystemExit(
                "Preflight checks failed. Fix endpoint/auth/runtime health or re-run with --allow-preflight-failures."
            )
    if skip_preflight:
        runtime_snapshot = await _collect_runtime_snapshot(
            target_url=config.target_url,
            headers=headers,
            timeout_seconds=preflight_timeout,
        )

    run_payloads: list[dict[str, object]] = []
    raw_results = []

    for idx in range(rounds):
        tester = LoadTester(config)
        raw = await tester.run_load_test()
        raw_results.append(raw)
        run_payloads.append(
            {
                "run_index": idx + 1,
                "captured_at": datetime.now(timezone.utc).isoformat(),
                "results": result_to_payload(raw),
            }
        )
        if pause_seconds and idx < rounds - 1:
            await asyncio.sleep(pause_seconds)
    aggregate = aggregate_load_results(raw_results)

    evidence_payload: dict[str, object] = {
        "profile": str(args.profile),
        "target_url": str(config.target_url),
        "endpoints": list(endpoints),
        "duration_seconds": int(config.duration_seconds),
        "concurrent_users": int(config.concurrent_users),
        "ramp_up_seconds": int(config.ramp_up_seconds),
        "request_timeout": float(config.request_timeout),
        "results": aggregate.results_payload,
        "rounds": rounds,
        "runs": run_payloads,
        "min_throughput_rps": round(aggregate.min_throughput, 4),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "runner": "scripts/load_test_api.py",
        "preflight": preflight,
        "runtime": runtime_snapshot,
    }

    thresholds, enforce = resolve_threshold_inputs(
        profile=str(args.profile),
        p95_target=args.p95_target,
        max_error_rate=args.max_error_rate,
        min_throughput=args.min_throughput,
        enforce_thresholds=bool(args.enforce_thresholds),
    )
    if thresholds is not None:
        attach_threshold_evaluation(
            evidence_payload=evidence_payload,
            raw_results=raw_results,
            thresholds=thresholds,
            worst_p95=aggregate.worst_p95,
            min_throughput=aggregate.min_throughput,
        )

    print(json.dumps(evidence_payload, indent=2, sort_keys=True))
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(evidence_payload, f, indent=2, sort_keys=True)

    if args.publish:
        if not token:
            raise SystemExit("VALDRICS_TOKEN is required for --publish.")

        publish_url = f"{config.target_url}/api/v1/audit/performance/load-test/evidence"
        async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
            resp = await client.post(publish_url, json=evidence_payload)
        if resp.status_code >= 400:
            raise SystemExit(f"Publish failed ({resp.status_code}): {resp.text}")

    if thresholds is not None and enforce:
        meets = bool(evidence_payload.get("meets_targets"))
        if not meets:
            raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
