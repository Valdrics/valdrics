#!/usr/bin/env python3
"""Generate staged enforcement failure-injection evidence from real test execution."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess  # nosec B404 - controlled local pytest invocation only
import sys
import tempfile
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from scripts.verify_enforcement_failure_injection_evidence import verify_evidence


@dataclass(frozen=True)
class FailureScenario:
    scenario_id: str
    checks: tuple[str, ...]
    selectors: tuple[str, ...]


SCENARIOS: tuple[FailureScenario, ...] = (
    FailureScenario(
        scenario_id="FI-001",
        checks=("gate timeout failure routes to configured fail-safe behavior",),
        selectors=(
            "tests/unit/enforcement/test_enforcement_api.py::test_gate_failsafe_timeout_and_error_modes",
            "tests/unit/enforcement/test_enforcement_service.py::test_resolve_fail_safe_gate_timeout_mode_behavior",
        ),
    ),
    FailureScenario(
        scenario_id="FI-002",
        checks=("gate lock contention and timeout map to explicit fail-safe reason codes",),
        selectors=(
            "tests/unit/enforcement/test_enforcement_api.py::test_gate_lock_failures_route_to_failsafe_with_lock_reason_codes",
            "tests/unit/enforcement/test_enforcement_service_helpers.py::test_acquire_gate_evaluation_lock_rowcount_zero_raises_contended_reason",
        ),
    ),
    FailureScenario(
        scenario_id="FI-003",
        checks=("approval token replay/tamper attempts are rejected under fault paths",),
        selectors=(
            "tests/unit/enforcement/test_enforcement_api.py::test_consume_approval_token_endpoint_rejects_replay_and_tamper",
            "tests/unit/enforcement/test_enforcement_service.py::test_consume_approval_token_rejects_replay",
        ),
    ),
    FailureScenario(
        scenario_id="FI-004",
        checks=("reservation reconciliation races remain idempotent and bounded",),
        selectors=(
            "tests/unit/enforcement/test_enforcement_property_and_concurrency.py::test_concurrency_reconcile_same_idempotency_key_settles_credit_once",
            "tests/unit/enforcement/test_enforcement_property_and_concurrency.py::test_concurrency_reconcile_overdue_claims_each_reservation_once",
        ),
    ),
    FailureScenario(
        scenario_id="FI-005",
        checks=("cross-tenant limiter saturation preserves global throttle behavior",),
        selectors=(
            "tests/unit/core/test_rate_limit.py::test_global_rate_limit_throttles_cross_tenant_requests",
            "tests/unit/enforcement/test_enforcement_api.py::test_enforcement_global_gate_limit_uses_configured_cap",
        ),
    ),
)
EXPECTED_PROFILE = "enforcement_failure_injection"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Execute failure-injection scenarios and emit staged evidence JSON."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for generated evidence JSON artifact.",
    )
    parser.add_argument(
        "--executed-by",
        required=True,
        help="Execution owner identity (email/alias).",
    )
    parser.add_argument(
        "--approved-by",
        required=True,
        help="Approver identity (must be distinct from --executed-by).",
    )
    parser.add_argument(
        "--profile",
        default=EXPECTED_PROFILE,
        help="Evidence profile name.",
    )
    parser.add_argument(
        "--pytest-timeout-seconds",
        type=float,
        default=240.0,
        help="Timeout in seconds for each scenario pytest invocation.",
    )
    return parser.parse_args(argv)


def _validate_selector(selector: str) -> str:
    candidate = str(selector or "").strip()
    if not candidate or candidate.startswith("-") or not candidate.startswith("tests/"):
        raise ValueError(f"Invalid pytest selector: {selector!r}")
    return candidate


def _parse_positive_float_arg(value: float, *, field: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    if parsed <= 0.0:
        raise ValueError(f"{field} must be > 0")
    return parsed


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _protected_output_paths() -> set[Path]:
    repo_root = _repo_root()
    protected = {
        Path(__file__).resolve(),
        repo_root / "scripts" / "verify_enforcement_failure_injection_evidence.py",
        repo_root / "docs" / "ops" / "evidence" / "enforcement_failure_injection_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "enforcement_failure_injection_2026-02-27.json",
        repo_root / "docs" / "ops" / "evidence" / "enforcement_stress_artifact_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "enforcement_stress_artifact_2026-02-27.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_committee_packet_assumptions_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_committee_packet_assumptions_2026-02-28.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_guardrails_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_guardrails_2026-02-27.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_telemetry_snapshot_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_telemetry_snapshot_2026-02-28.json",
        repo_root / "docs" / "ops" / "evidence" / "pkg_fin_policy_decisions_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "pkg_fin_policy_decisions_2026-02-28.json",
        repo_root / "docs" / "ops" / "evidence" / "pricing_benchmark_register_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "pricing_benchmark_register_2026-02-27.json",
        repo_root / "docs" / "ops" / "evidence" / "valdrics_disposition_register_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "valdrics_disposition_register_2026-02-28.json",
    }
    for scenario in SCENARIOS:
        for selector in scenario.selectors:
            selector_path = selector.split("::", 1)[0].strip()
            if selector_path:
                protected.add((repo_root / selector_path).resolve())
    return protected


def _resolve_output_path(value: Path | str) -> Path:
    raw = Path(str(value)).expanduser()
    if raw.is_absolute():
        resolved = raw.resolve()
    else:
        resolved = (_repo_root() / raw).resolve()
        try:
            resolved.relative_to(_repo_root())
        except ValueError as exc:
            raise ValueError("output must stay within repo root when relative") from exc
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"output must be a file path: {resolved.as_posix()}")
    if resolved in _protected_output_paths():
        raise ValueError(
            "output must not overwrite failure-injection source, verifier, selector, or template files"
        )
    return resolved


def _ensure_output_parent_dir(output_path: Path) -> None:
    current = output_path.parent
    while True:
        if current.exists():
            if not current.is_dir():
                raise ValueError(
                    f"output parent must be a directory path: {current.as_posix()}"
                )
            return
        if current == current.parent:
            return
        current = current.parent


def _run_scenario(
    scenario: FailureScenario,
    *,
    cwd: Path,
    timeout_seconds: float = 240.0,
) -> tuple[dict[str, object], bool]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "--no-cov",
        "-q",
        *(_validate_selector(selector) for selector in scenario.selectors),
    ]
    subprocess_env = os.environ.copy()
    subprocess_env.pop("DATABASE_URL", None)
    subprocess_env.pop("DB_SSL_MODE", None)
    subprocess_env.pop("PGSSLMODE", None)
    subprocess_env["TESTING"] = "true"
    subprocess_env["DEBUG"] = "false"
    started = time.perf_counter()
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
            env=subprocess_env,
            timeout=timeout_seconds,
        )  # nosec B603 - pytest invocation uses static repo-local selectors
        duration_seconds = round(time.perf_counter() - started, 3)
        passed = result.returncode == 0
        scenario_payload = {
            "id": scenario.scenario_id,
            "status": "pass" if passed else "fail",
            "duration_seconds": max(duration_seconds, 0.001),
            "checks": list(scenario.checks),
            "evidence_refs": list(scenario.selectors),
            "command": " ".join(command),
            "result_tail": "\n".join(
                (result.stdout or "").strip().splitlines()[-10:]
                + (result.stderr or "").strip().splitlines()[-10:]
            ).strip(),
        }
        return scenario_payload, passed
    except subprocess.TimeoutExpired as exc:
        duration_seconds = round(time.perf_counter() - started, 3)
        scenario_payload = {
            "id": scenario.scenario_id,
            "status": "fail",
            "duration_seconds": max(duration_seconds, 0.001),
            "checks": list(scenario.checks),
            "evidence_refs": list(scenario.selectors),
            "command": " ".join(command),
            "result_tail": f"timeout after {timeout_seconds:.1f}s ({exc})",
        }
        return scenario_payload, False


def generate_evidence(
    *,
    output: Path,
    executed_by: str,
    approved_by: str,
    profile: str,
    cwd: Path,
    timeout_seconds: float = 240.0,
) -> tuple[dict[str, object], bool]:
    normalized_executed_by = executed_by.strip()
    normalized_approved_by = approved_by.strip()
    normalized_profile = str(profile or "").strip()
    output_path = _resolve_output_path(output)
    _ensure_output_parent_dir(output_path)
    if not normalized_executed_by or not normalized_approved_by:
        raise ValueError("executed_by and approved_by must be non-empty")
    if normalized_executed_by == normalized_approved_by:
        raise ValueError("executed_by and approved_by must be distinct")
    if not normalized_profile:
        raise ValueError("profile must be non-empty")
    if normalized_profile != EXPECTED_PROFILE:
        raise ValueError(f"profile must equal {EXPECTED_PROFILE!r}")

    scenario_rows: list[dict[str, object]] = []
    passed_count = 0
    for scenario in SCENARIOS:
        payload, passed = _run_scenario(
            scenario,
            cwd=cwd,
            timeout_seconds=timeout_seconds,
        )
        scenario_rows.append(payload)
        if passed:
            passed_count += 1

    total = len(scenario_rows)
    failed = total - passed_count
    overall_passed = failed == 0

    artifact: dict[str, object] = {
        "profile": normalized_profile,
        "runner": "staged_failure_injection",
        "execution_class": "staged",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "executed_by": normalized_executed_by,
        "approved_by": normalized_approved_by,
        "scenarios": scenario_rows,
        "summary": {
            "total_scenarios": total,
            "passed_scenarios": passed_count,
            "failed_scenarios": failed,
            "overall_passed": overall_passed,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    return artifact, overall_passed


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    pytest_timeout_seconds = _parse_positive_float_arg(
        float(args.pytest_timeout_seconds),
        field="pytest_timeout_seconds",
    )
    output_path = _resolve_output_path(Path(args.output))
    _ensure_output_parent_dir(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=output_path.parent,
        prefix=f".{output_path.stem}.",
        suffix=f"{output_path.suffix}.tmp",
        delete=False,
    ) as handle:
        staged_output_path = Path(handle.name)
    try:
        artifact, passed = generate_evidence(
            output=staged_output_path,
            executed_by=str(args.executed_by),
            approved_by=str(args.approved_by),
            profile=str(args.profile),
            cwd=Path(__file__).resolve().parents[1],
            timeout_seconds=pytest_timeout_seconds,
        )
        verify_evidence(
            evidence_path=staged_output_path,
            expected_profile=EXPECTED_PROFILE,
            max_artifact_age_hours=4.0,
        )
        staged_output_path.replace(output_path)
    except Exception:
        staged_output_path.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        raise
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
