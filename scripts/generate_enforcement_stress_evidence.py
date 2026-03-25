#!/usr/bin/env python3
"""Generate enforcement stress evidence from a real in-process execution run."""

from __future__ import annotations

import argparse
import asyncio
import json
import math
from contextlib import suppress
from datetime import datetime, timedelta, timezone
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scripts.env_generation_common import (
    checked_in_evidence_paths as _checked_in_evidence_paths_shared,
    ensure_parent_dir as _ensure_parent_dir_shared,
    promote_staged_file as _promote_staged_file,
    protected_output_paths_from_root as _protected_output_paths_from_root,
    repo_root_for as _repo_root_for,
    resolve_output_path_from_root as _resolve_output_path_from_root,
    stage_json_file as _stage_json_file,
)
from scripts.in_process_runtime_env import configure_isolated_test_environment
from scripts.verify_enforcement_stress_evidence import verify_evidence


ENFORCEMENT_ENDPOINTS: tuple[str, ...] = (
    "/health/live",
    "/api/v1/enforcement/policies",
    "/api/v1/enforcement/budgets",
    "/api/v1/enforcement/credits",
    "/api/v1/enforcement/approvals/queue?limit=50",
    "/api/v1/enforcement/ledger?limit=50",
    "/api/v1/enforcement/exports/parity?limit=50",
)


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _checked_in_evidence_paths(repo_root: Path) -> set[Path]:
    return _checked_in_evidence_paths_shared(repo_root)


def _protected_output_paths() -> set[Path]:
    return _protected_output_paths_from_root(
        _repo_root(),
        __file__,
        "scripts/load_test_api.py",
        "scripts/verify_enforcement_stress_evidence.py",
        "docs/ops/evidence/enforcement_stress_artifact_TEMPLATE.json",
        "docs/ops/evidence/enforcement_stress_artifact_2026-02-27.json",
        "docs/ops/evidence/finance_guardrails_TEMPLATE.json",
        "docs/ops/evidence/pricing_benchmark_register_2026-02-27.json",
        "docs/ops/evidence/README.md",
    )


def _resolve_output_path(value: str) -> Path:
    return _resolve_output_path_from_root(
        _repo_root(),
        value,
        field_name="output",
        protected_paths=_protected_output_paths(),
        protected_error=(
            "output must not overwrite enforcement stress source, runner, verifier, or template files"
        ),
    )


def _ensure_output_parent_dir(output_path: Path) -> None:
    _ensure_parent_dir_shared(output_path, field_name="output")


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


def _parse_positive_int(value: Any, *, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be integer-like") from exc
    if parsed <= 0:
        raise ValueError(f"{field} must be > 0")
    return parsed


def _parse_non_negative_int(value: Any, *, field: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be integer-like") from exc
    if parsed < 0:
        raise ValueError(f"{field} must be >= 0")
    return parsed


def _parse_positive_float(value: Any, *, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    if parsed <= 0:
        raise ValueError(f"{field} must be > 0")
    return parsed


def _parse_non_negative_float(value: Any, *, field: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    if parsed < 0:
        raise ValueError(f"{field} must be >= 0")
    return parsed


def _normalize_load_profile_args(args: argparse.Namespace) -> dict[str, float | int]:
    return {
        "duration_seconds": _parse_positive_int(
            getattr(args, "duration_seconds", None),
            field="duration_seconds",
        ),
        "concurrent_users": _parse_positive_int(
            getattr(args, "concurrent_users", None),
            field="concurrent_users",
        ),
        "ramp_seconds": _parse_non_negative_int(
            getattr(args, "ramp_seconds", None),
            field="ramp_seconds",
        ),
        "rounds": _parse_positive_int(
            getattr(args, "rounds", None),
            field="rounds",
        ),
        "pause_seconds": _parse_non_negative_float(
            getattr(args, "pause_seconds", None),
            field="pause_seconds",
        ),
        "max_p95_seconds": _parse_positive_float(
            getattr(args, "max_p95_seconds", None),
            field="max_p95_seconds",
        ),
        "max_error_rate_percent": _parse_non_negative_float(
            getattr(args, "max_error_rate_percent", None),
            field="max_error_rate_percent",
        ),
        "min_throughput_rps": _parse_positive_float(
            getattr(args, "min_throughput_rps", None),
            field="min_throughput_rps",
        ),
    }


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


@contextmanager
def _configure_isolated_bootstrap_env(*, database_url: str) -> Iterator[str]:
    resolved_database_url = str(database_url or "").strip()
    with configure_isolated_test_environment(database_url=resolved_database_url):
        yield resolved_database_url


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
    with _configure_isolated_bootstrap_env(database_url=database_url):
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

        token = create_access_token(
            {"sub": str(user_id), "email": email}, timedelta(hours=2)
        )
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
    counts = _result_counts(result)
    metrics = _result_metrics(result)
    return {
        **counts,
        **metrics,
        "errors_sample": list(getattr(result, "errors", [])[:10]),
    }


def _normalize_result_metric(value: Any, *, field: str) -> float:
    try:
        parsed = float(value or 0.0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    if parsed < 0:
        raise ValueError(f"{field} must be >= 0")
    return parsed


def _normalize_result_count(value: Any, *, field: str) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be integer-like") from exc
    if parsed < 0:
        raise ValueError(f"{field} must be >= 0")
    return parsed


def _result_counts(result: Any) -> dict[str, int]:
    total_requests = _normalize_result_count(
        getattr(result, "total_requests", 0),
        field="result.total_requests",
    )
    successful_requests = _normalize_result_count(
        getattr(result, "successful_requests", 0),
        field="result.successful_requests",
    )
    failed_requests = _normalize_result_count(
        getattr(result, "failed_requests", 0),
        field="result.failed_requests",
    )
    if successful_requests + failed_requests > total_requests:
        raise ValueError(
            "result.successful_requests + result.failed_requests must be <= result.total_requests"
        )
    return {
        "total_requests": total_requests,
        "successful_requests": successful_requests,
        "failed_requests": failed_requests,
    }


def _result_metrics(result: Any) -> dict[str, float]:
    return {
        "throughput_rps": _normalize_result_metric(
            getattr(result, "throughput_rps", 0.0),
            field="result.throughput_rps",
        ),
        "avg_response_time": _normalize_result_metric(
            getattr(result, "avg_response_time", 0.0),
            field="result.avg_response_time",
        ),
        "median_response_time": _normalize_result_metric(
            getattr(result, "median_response_time", 0.0),
            field="result.median_response_time",
        ),
        "p95_response_time": _normalize_result_metric(
            getattr(result, "p95_response_time", 0.0),
            field="result.p95_response_time",
        ),
        "p99_response_time": _normalize_result_metric(
            getattr(result, "p99_response_time", 0.0),
            field="result.p99_response_time",
        ),
        "min_response_time": _normalize_result_metric(
            getattr(result, "min_response_time", 0.0),
            field="result.min_response_time",
        ),
        "max_response_time": _normalize_result_metric(
            getattr(result, "max_response_time", 0.0),
            field="result.max_response_time",
        ),
    }


async def generate_evidence(args: argparse.Namespace) -> dict[str, Any]:
    load_profile = _normalize_load_profile_args(args)
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
        normalized_results: list[dict[str, float]] = []
        try:
            rounds = int(load_profile["rounds"])
            for idx in range(rounds):
                tester = LoadTester(
                    LoadTestConfig(
                        duration_seconds=int(load_profile["duration_seconds"]),
                        concurrent_users=int(load_profile["concurrent_users"]),
                        ramp_up_seconds=int(load_profile["ramp_seconds"]),
                        target_url=target_url,
                        endpoints=endpoints,
                        request_timeout=15.0,
                        headers=headers,
                    )
                )
                raw = await tester.run_load_test()
                raw_results.append(raw)
                counts = _result_counts(raw)
                normalized = _result_metrics(raw)
                normalized_results.append(normalized)
                run_payloads.append(
                    {
                        "run_index": idx + 1,
                        "captured_at": datetime.now(timezone.utc).isoformat(),
                        "results": {
                            **counts,
                            **normalized,
                            "errors_sample": list(getattr(raw, "errors", [])[:10]),
                        },
                    }
                )
                if float(load_profile["pause_seconds"]) > 0 and idx < rounds - 1:
                    await asyncio.sleep(float(load_profile["pause_seconds"]))
        finally:
            http_core._client = previous_client
            if previous_client is None:
                with suppress(Exception):
                    await http_core.close_http_client()

    normalized_counts = [_result_counts(result) for result in raw_results]
    total_requests = sum(item["total_requests"] for item in normalized_counts)
    successful_requests = sum(item["successful_requests"] for item in normalized_counts)
    failed_requests = sum(item["failed_requests"] for item in normalized_counts)
    worst_p95 = max(item["p95_response_time"] for item in normalized_results)
    worst_p99 = max(item["p99_response_time"] for item in normalized_results)
    min_throughput = min(item["throughput_rps"] for item in normalized_results)
    avg_throughput = sum(item["throughput_rps"] for item in normalized_results) / max(
        1, len(normalized_results)
    )
    min_response = min(item["min_response_time"] for item in normalized_results)
    max_response = max(item["max_response_time"] for item in normalized_results)
    avg_response_time = sum(item["avg_response_time"] for item in normalized_results) / max(
        1, len(normalized_results)
    )
    median_response_time = sum(
        item["median_response_time"] for item in normalized_results
    ) / max(1, len(normalized_results))

    errors_sample: list[str] = []
    for raw in raw_results:
        for item in list(getattr(raw, "errors", [])[:10]):
            if item not in errors_sample:
                errors_sample.append(str(item))
        if len(errors_sample) >= 10:
            break

    thresholds = LoadTestThresholds(
        max_p95_seconds=float(load_profile["max_p95_seconds"]),
        max_error_rate_percent=float(load_profile["max_error_rate_percent"]),
        min_throughput_rps=float(load_profile["min_throughput_rps"]),
    )
    per_round = [evaluate_load_test_result(raw, thresholds) for raw in raw_results]

    payload: dict[str, Any] = {
        "profile": "enforcement",
        "target_url": target_url,
        "endpoints": endpoints,
        "duration_seconds": int(load_profile["duration_seconds"]),
        "concurrent_users": int(load_profile["concurrent_users"]),
        "ramp_up_seconds": int(load_profile["ramp_seconds"]),
        "request_timeout": 15.0,
        "rounds": int(load_profile["rounds"]),
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
    output_path = _resolve_output_path(str(args.output))
    _ensure_output_parent_dir(output_path)
    load_profile = _normalize_load_profile_args(args)
    payload = asyncio.run(generate_evidence(args))
    temp_path = _stage_json_file(output_path, payload)
    try:
        verify_evidence(
            evidence_path=temp_path,
            expected_profile="enforcement",
            min_rounds=int(load_profile["rounds"]),
            min_duration_seconds=int(load_profile["duration_seconds"]),
            min_concurrent_users=int(load_profile["concurrent_users"]),
            required_database_engine=str(getattr(args, "required_database_engine", "postgresql")),
            max_p95_seconds=float(load_profile["max_p95_seconds"]),
            max_error_rate_percent=float(load_profile["max_error_rate_percent"]),
            min_throughput_rps=float(load_profile["min_throughput_rps"]),
            max_artifact_age_hours=4.0,
        )
        _promote_staged_file(temp_path, output_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    print(json.dumps(payload, indent=2, sort_keys=True))
    if not bool(payload.get("meets_targets")):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
