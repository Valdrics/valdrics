#!/usr/bin/env python3
"""Generate enforcement stress evidence from a real in-process execution run."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scripts.in_process_runtime_env import configure_isolated_test_environment


ENFORCEMENT_ENDPOINTS: tuple[str, ...] = (
    "/health/live",
    "/api/v1/enforcement/policies",
    "/api/v1/enforcement/budgets",
    "/api/v1/enforcement/credits",
    "/api/v1/enforcement/approvals/queue?limit=50",
    "/api/v1/enforcement/ledger?limit=50",
    "/api/v1/enforcement/exports/parity?limit=50",
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate enforcement stress evidence artifact in CI/local runs.",
    )
    parser.add_argument("--output", required=True, help="Output JSON artifact path.")
    parser.add_argument(
        "--database-url",
        required=True,
        help=(
            "Explicit database URL for the in-process runtime. Release evidence never "
            "inherits a shell-exported DATABASE_URL."
        ),
    )
    parser.add_argument(
        "--required-database-engine",
        default="postgresql",
        help="Required runtime database engine for emitted evidence (default: postgresql).",
    )
    parser.add_argument(
        "--duration-seconds",
        type=int,
        default=30,
        help="Duration per round in seconds.",
    )
    parser.add_argument(
        "--concurrent-users",
        type=int,
        default=10,
        help="Concurrent users for each round.",
    )
    parser.add_argument(
        "--ramp-seconds",
        type=int,
        default=5,
        help="Ramp-up time in seconds.",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=3,
        help="Number of repeated rounds.",
    )
    parser.add_argument(
        "--pause-seconds",
        type=float,
        default=0.0,
        help="Pause between rounds.",
    )
    parser.add_argument(
        "--max-p95-seconds",
        type=float,
        default=2.0,
        help="Max p95 response time threshold.",
    )
    parser.add_argument(
        "--max-error-rate-percent",
        type=float,
        default=1.0,
        help="Max error-rate threshold.",
    )
    parser.add_argument(
        "--min-throughput-rps",
        type=float,
        default=0.5,
        help="Min throughput threshold.",
    )
    return parser.parse_args(argv)


def _normalize_database_engine_name(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    base = raw.split("://", 1)[0].split("+", 1)[0]
    if base.startswith("postgres"):
        return "postgresql"
    if base.startswith("sqlite"):
        return "sqlite"
    return base


def _extract_health_database_engine(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    database = payload.get("database")
    if not isinstance(database, dict):
        return ""
    return _normalize_database_engine_name(
        database.get("engine") or database.get("dialect")
    )


def _resolve_requested_database_url(
    *,
    database_url: str,
    required_database_engine: str,
) -> str:
    resolved_database_url = str(database_url or "").strip()
    if not resolved_database_url:
        raise ValueError("--database-url must be provided for enforcement stress evidence")

    actual_engine = _normalize_database_engine_name(resolved_database_url)
    required_engine = _normalize_database_engine_name(required_database_engine)
    if not actual_engine:
        raise ValueError(
            f"Unable to determine database engine from --database-url: {resolved_database_url!r}"
        )
    if required_engine and actual_engine != required_engine:
        raise ValueError(
            "enforcement stress evidence requires a "
            f"{required_engine} runtime, got {actual_engine}"
        )
    return resolved_database_url


def _configure_isolated_bootstrap_env(*, database_url: str) -> str:
    resolved_database_url = str(database_url or "").strip()
    configure_isolated_test_environment(database_url=resolved_database_url)
    return resolved_database_url


def _validate_runtime_database_engine(
    *,
    runtime_snapshot: dict[str, Any],
    required_database_engine: str,
) -> str:
    actual_engine = _normalize_database_engine_name(runtime_snapshot.get("database_engine"))
    required_engine = _normalize_database_engine_name(required_database_engine)
    if not actual_engine:
        raise ValueError(
            "runtime health snapshot did not report a database engine for enforcement evidence"
        )
    if required_engine and actual_engine != required_engine:
        raise ValueError(
            "runtime database engine does not satisfy the enforcement evidence contract: "
            f"expected {required_engine}, got {actual_engine}"
        )
    return actual_engine


async def _bootstrap_app_and_token(*, database_url: str) -> tuple[Any, str]:
    _configure_isolated_bootstrap_env(database_url=database_url)

    from app.shared.db.base import Base
    from app.shared.db.session import get_engine, reset_db_runtime

    # Register relationship targets before metadata creation.
    import app.models.aws_connection  # noqa: F401
    import app.models.background_job  # noqa: F401
    import app.models.cloud  # noqa: F401
    import app.models.license_connection  # noqa: F401
    import app.models.llm  # noqa: F401
    import app.models.notification_settings  # noqa: F401
    import app.models.remediation_settings  # noqa: F401
    import app.models.saas_connection  # noqa: F401
    import app.models.tenant  # noqa: F401
    import app.models.tenant_identity_settings  # noqa: F401

    reset_db_runtime()
    async_engine = get_engine()
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    from app.models.tenant import Tenant, User, UserRole
    from app.shared.core.auth import create_access_token

    tenant_id = UUID("00000000-0000-0000-0000-000000000101")
    user_id = UUID("00000000-0000-0000-0000-000000000102")
    email = "enforcement.ci@valdrics.local"

    session_maker = async_sessionmaker(
        async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_maker() as db:
        tenant = await db.get(Tenant, tenant_id)
        if tenant is None:
            db.add(
                Tenant(
                    id=tenant_id,
                    name="Enforcement Stress Tenant",
                    plan="enterprise",
                )
            )
        user = await db.get(User, user_id)
        if user is None:
            db.add(
                User(
                    id=user_id,
                    email=email,
                    tenant_id=tenant_id,
                    role=UserRole.ADMIN.value,
                )
            )
        await db.commit()

    token = create_access_token({"sub": str(user_id), "email": email}, timedelta(hours=2))
    from app.main import app as valdrics_app

    return valdrics_app, token


async def _run_preflight(
    *,
    client: httpx.AsyncClient,
    endpoints: list[str],
    attempts: int,
) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    for endpoint in endpoints:
        passed = False
        last_error = ""
        for attempt in range(1, max(1, attempts) + 1):
            try:
                response = await client.get(endpoint)
                status_code = int(response.status_code)
                ok = status_code < 400
                checks.append(
                    {
                        "endpoint": endpoint,
                        "attempt": attempt,
                        "status_code": status_code,
                        "ok": ok,
                    }
                )
                if ok:
                    passed = True
                    break
                preview = response.text[:200]
                last_error = f"HTTP {status_code}: {preview}"
            except httpx.HTTPError as exc:
                last_error = str(exc)
        if not passed:
            failures.append({"endpoint": endpoint, "error": last_error or "preflight failed"})

    return {
        "enabled": True,
        "passed": len(failures) == 0,
        "attempts_per_endpoint": max(1, attempts),
        "checks": checks,
        "failures": failures,
    }


async def _collect_runtime_snapshot(client: httpx.AsyncClient) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "health_endpoint": "/health",
        "database_engine": "unknown",
    }
    try:
        response = await client.get("/health")
        snapshot["health_status_code"] = int(response.status_code)
        payload = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
        if isinstance(payload, dict):
            status = payload.get("status")
            if status is not None:
                snapshot["status"] = str(status)
            engine = _extract_health_database_engine(payload)
            if engine:
                snapshot["database_engine"] = engine
    except (httpx.HTTPError, json.JSONDecodeError):
        pass
    return snapshot


def _result_to_payload(result: Any) -> dict[str, Any]:
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


async def generate_evidence(args: argparse.Namespace) -> dict[str, Any]:
    required_database_engine = _normalize_database_engine_name(
        getattr(args, "required_database_engine", "postgresql")
    )
    database_url = _resolve_requested_database_url(
        database_url=str(getattr(args, "database_url", "")),
        required_database_engine=required_database_engine,
    )
    app, token = await _bootstrap_app_and_token(database_url=database_url)
    target_url = "http://testserver"
    endpoints = list(ENFORCEMENT_ENDPOINTS)
    headers = {"Authorization": f"Bearer {token}"}
    transport = httpx.ASGITransport(app=app)

    timeout = httpx.Timeout(15.0, connect=5.0)
    async with httpx.AsyncClient(
        transport=transport,
        base_url=target_url,
        timeout=timeout,
        headers=headers,
    ) as client:
        preflight = await _run_preflight(client=client, endpoints=endpoints, attempts=2)
        runtime_snapshot = await _collect_runtime_snapshot(client)
        if not preflight.get("passed"):
            raise ValueError("enforcement stress preflight failed")
        runtime_snapshot["database_engine"] = _validate_runtime_database_engine(
            runtime_snapshot=runtime_snapshot,
            required_database_engine=required_database_engine,
        )

        from app.shared.core import http as http_core
        from app.shared.core.performance_evidence import (
            LoadTestThresholds,
            evaluate_load_test_result,
        )
        from app.shared.core.performance_testing import LoadTestConfig, LoadTester

        previous_client = http_core._client
        http_core._client = client
        run_payloads: list[dict[str, Any]] = []
        raw_results: list[Any] = []
        try:
            rounds = max(1, int(args.rounds))
            for idx in range(rounds):
                tester = LoadTester(
                    LoadTestConfig(
                        duration_seconds=max(1, int(args.duration_seconds)),
                        concurrent_users=max(1, int(args.concurrent_users)),
                        ramp_up_seconds=max(0, int(args.ramp_seconds)),
                        target_url=target_url,
                        endpoints=endpoints,
                        request_timeout=15.0,
                        headers=headers,
                    )
                )
                raw = await tester.run_load_test()
                raw_results.append(raw)
                run_payloads.append(
                    {
                        "run_index": idx + 1,
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                        "results": _result_to_payload(raw),
                    }
                )
                if float(args.pause_seconds) > 0 and idx < rounds - 1:
                    await asyncio.sleep(float(args.pause_seconds))
        finally:
            http_core._client = previous_client
            if previous_client is None:
                with suppress(Exception):
                    await http_core.close_http_client()

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
    ) / max(1, len(raw_results))
    min_response = min(
        float(getattr(r, "min_response_time", 0.0) or 0.0) for r in raw_results
    )
    max_response = max(
        float(getattr(r, "max_response_time", 0.0) or 0.0) for r in raw_results
    )
    avg_response_time = sum(
        float(getattr(r, "avg_response_time", 0.0) or 0.0) for r in raw_results
    ) / max(1, len(raw_results))
    median_response_time = sum(
        float(getattr(r, "median_response_time", 0.0) or 0.0) for r in raw_results
    ) / max(1, len(raw_results))

    errors_sample: list[str] = []
    for raw in raw_results:
        for item in list(getattr(raw, "errors", [])[:10]):
            if item not in errors_sample:
                errors_sample.append(str(item))
        if len(errors_sample) >= 10:
            break

    thresholds = LoadTestThresholds(
        max_p95_seconds=float(args.max_p95_seconds),
        max_error_rate_percent=float(args.max_error_rate_percent),
        min_throughput_rps=float(args.min_throughput_rps),
    )
    per_round = [evaluate_load_test_result(raw, thresholds) for raw in raw_results]

    payload: dict[str, Any] = {
        "profile": "enforcement",
        "target_url": target_url,
        "endpoints": endpoints,
        "duration_seconds": max(1, int(args.duration_seconds)),
        "concurrent_users": max(1, int(args.concurrent_users)),
        "ramp_up_seconds": max(0, int(args.ramp_seconds)),
        "request_timeout": 15.0,
        "rounds": max(1, int(args.rounds)),
        "runs": run_payloads,
        "results": {
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
        },
        "min_throughput_rps": round(min_throughput, 4),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "runner": "scripts/load_test_api.py",
        "preflight": preflight,
        "runtime": runtime_snapshot,
        "required_database_engine": required_database_engine,
        "thresholds": {
            "max_p95_seconds": thresholds.max_p95_seconds,
            "max_error_rate_percent": thresholds.max_error_rate_percent,
            "min_throughput_rps": thresholds.min_throughput_rps,
        },
        "evaluation": {
            "rounds": [item.model_dump() for item in per_round],
            "overall_meets_targets": all(item.meets_targets for item in per_round),
            "worst_p95_seconds": float(worst_p95),
            "min_throughput_rps": float(min_throughput),
        },
        "meets_targets": all(item.meets_targets for item in per_round),
    }
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = asyncio.run(generate_evidence(args))
    output_path = Path(str(args.output))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not bool(payload.get("meets_targets")):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
