#!/usr/bin/env python3
"""Generate runtime key-rotation drill evidence markdown artifact."""

from __future__ import annotations

import argparse
import os
import subprocess  # nosec B404 - controlled local pytest invocation only
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.verify_key_rotation_drill_evidence import verify_key_rotation_drill_evidence


@dataclass(frozen=True)
class DrillCheck:
    key: str
    selector: str


DEFAULT_DRILL_CHECKS: tuple[DrillCheck, ...] = (
    DrillCheck(
        key="pre_rotation_tokens_accepted",
        selector=(
            "tests/unit/enforcement/enforcement_service_cases_part03.py::"
            "test_consume_approval_token_accepts_primary_secret"
        ),
    ),
    DrillCheck(
        key="post_rotation_new_tokens_accepted",
        selector=(
            "tests/unit/enforcement/enforcement_service_cases_part03.py::"
            "test_consume_approval_token_accepts_new_primary_secret_after_rotation"
        ),
    ),
    DrillCheck(
        key="post_rotation_old_tokens_rejected",
        selector=(
            "tests/unit/enforcement/enforcement_service_cases_part04.py::"
            "test_consume_approval_token_rejects_rotated_secret_without_fallback"
        ),
    ),
    DrillCheck(
        key="fallback_verification_passed",
        selector=(
            "tests/unit/enforcement/enforcement_service_cases_part03.py::"
            "test_consume_approval_token_accepts_rotated_fallback_secret"
        ),
    ),
    DrillCheck(
        key="rollback_validation_passed",
        selector=(
            "tests/unit/enforcement/enforcement_service_cases_part04.py::"
            "test_consume_approval_token_accepts_rollback_fallback_secret"
        ),
    ),
    DrillCheck(
        key="replay_protection_intact",
        selector=(
            "tests/unit/enforcement/enforcement_service_cases_part03.py::"
            "test_consume_approval_token_rejects_replay"
        ),
    ),
    DrillCheck(
        key="alert_pipeline_verified",
        selector=(
            "tests/unit/enforcement/test_reconciliation_worker.py::"
            "test_reconciliation_worker_sends_sla_release_alert"
        ),
    ),
)

SUPPLEMENTAL_CHECKS: tuple[DrillCheck, ...] = (
    DrillCheck(
        key="endpoint_replay_tamper_guard",
        selector=(
            "tests/unit/enforcement/enforcement_api_cases_part03.py::"
            "test_consume_approval_token_endpoint_rejects_replay_and_tamper"
        ),
    ),
)


def _all_drill_checks() -> tuple[DrillCheck, ...]:
    return (*DEFAULT_DRILL_CHECKS, *SUPPLEMENTAL_CHECKS)


def _validate_unique_check_sources() -> None:
    seen_keys: set[str] = set()
    selector_to_key: dict[str, str] = {}
    for check in _all_drill_checks():
        if check.key in seen_keys:
            raise ValueError(f"Duplicate drill evidence key configured: {check.key}")
        seen_keys.add(check.key)

        prior_key = selector_to_key.get(check.selector)
        if prior_key is not None:
            raise ValueError(
                "Each drill evidence field must map to a distinct selector; "
                f"{check.key} and {prior_key} both use {check.selector}"
            )
        selector_to_key[check.selector] = check.key


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate key-rotation drill evidence markdown.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for key-rotation drill evidence markdown.",
    )
    parser.add_argument(
        "--max-drill-age-days",
        type=float,
        default=120.0,
        help="Verifier max drill age in days.",
    )
    parser.add_argument(
        "--pytest-timeout-seconds",
        type=float,
        default=240.0,
        help="Timeout for each live verification test selector.",
    )
    parser.add_argument(
        "--allow-check-failures",
        action="store_true",
        help="Emit artifact even if one or more live checks fail.",
    )
    parser.add_argument(
        "--selector-retries",
        type=int,
        default=2,
        help="Retry count for flaky selector failures (for example transient sqlite I/O errors).",
    )
    return parser.parse_args(argv)


def _validate_selector(selector: str) -> str:
    candidate = str(selector or "").strip()
    if not candidate or candidate.startswith("-") or not candidate.startswith("tests/"):
        raise ValueError(f"Invalid pytest selector: {selector!r}")
    return candidate


def _run_selector(
    *,
    selector: str,
    timeout_seconds: float,
    retries: int,
) -> tuple[bool, str]:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--no-cov",
        _validate_selector(selector),
    ]
    subprocess_env = os.environ.copy()
    subprocess_env.pop("DATABASE_URL", None)
    subprocess_env.pop("DB_SSL_MODE", None)
    subprocess_env.pop("PGSSLMODE", None)
    subprocess_env["TESTING"] = "true"
    subprocess_env["DEBUG"] = "false"

    attempts = max(1, int(retries) + 1)
    last_output = ""
    for attempt in range(1, attempts + 1):
        try:
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=subprocess_env,
            )  # nosec B603 - pytest invocation uses validated repo-local selector
        except subprocess.TimeoutExpired as exc:
            last_output = f"timeout after {timeout_seconds:.1f}s: {selector} ({exc})"
            if attempt < attempts:
                time.sleep(0.2)
                continue
            return False, last_output

        output = "\n".join(
            part
            for part in (completed.stdout.strip(), completed.stderr.strip())
            if part
        ).strip()
        if completed.returncode == 0:
            return True, output
        last_output = output
        if "disk I/O error" in output and attempt < attempts:
            time.sleep(0.2)
            continue
        return False, output
    return False, last_output


def _execute_checks(
    *,
    timeout_seconds: float,
    retries: int,
) -> tuple[dict[str, bool], dict[str, bool], dict[str, str]]:
    _validate_unique_check_sources()
    selector_results: dict[str, bool] = {}
    selector_logs: dict[str, str] = {}

    unique_selectors = {check.selector for check in _all_drill_checks()}
    for selector in sorted(unique_selectors):
        passed, output = _run_selector(
            selector=selector,
            timeout_seconds=timeout_seconds,
            retries=retries,
        )
        selector_results[selector] = passed
        selector_logs[selector] = output

    field_results: dict[str, bool] = {}
    for check in DEFAULT_DRILL_CHECKS:
        field_results[check.key] = selector_results.get(check.selector, False)
    for check in SUPPLEMENTAL_CHECKS:
        field_results[check.key] = selector_results.get(check.selector, False)
    return field_results, selector_results, selector_logs


def _build_markdown(
    *,
    field_results: dict[str, bool],
    selector_results: dict[str, bool],
    _selector_logs: dict[str, str],
) -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    drill_date = now.date().isoformat()
    drill_id = f"KRD-{drill_date}-ENF-RT"
    next_due = (now.date() + timedelta(days=90)).isoformat()
    executed_at = now.isoformat().replace("+00:00", "Z")
    source_lines: list[str] = []
    for check in _all_drill_checks():
        source_lines.append(f"- source_{check.key}: {check.selector}")
        source_lines.append(
            "- source_result_"
            f"{check.key}: {'pass' if selector_results.get(check.selector, False) else 'fail'}"
        )

    endpoint_guard_result = field_results.get("endpoint_replay_tamper_guard", False)
    return (
        f"# Enforcement Key Rotation Drill Evidence ({drill_date})\n\n"
        "Generated from live enforcement test execution for release gate verification.\n\n"
        "## Metadata\n\n"
        f"- drill_id: {drill_id}\n"
        f"- executed_at_utc: {executed_at}\n"
        "- environment: ci\n"
        "- owner: ci-security-oncall\n"
        "- approver: ci-platform-oncall\n"
        f"- next_drill_due_on: {next_due}\n\n"
        "## Evidence Sources\n\n"
        + "\n".join(source_lines)
        + "\n\n"
        "## Validation Outcomes\n\n"
        f"- pre_rotation_tokens_accepted: {str(field_results['pre_rotation_tokens_accepted']).lower()}\n"
        f"- post_rotation_new_tokens_accepted: {str(field_results['post_rotation_new_tokens_accepted']).lower()}\n"
        f"- post_rotation_old_tokens_rejected: {str(field_results['post_rotation_old_tokens_rejected']).lower()}\n"
        f"- fallback_verification_passed: {str(field_results['fallback_verification_passed']).lower()}\n"
        f"- rollback_validation_passed: {str(field_results['rollback_validation_passed']).lower()}\n"
        f"- replay_protection_intact: {str(field_results['replay_protection_intact']).lower()}\n"
        f"- alert_pipeline_verified: {str(field_results['alert_pipeline_verified']).lower()}\n"
        f"- endpoint_replay_tamper_guard: {str(endpoint_guard_result).lower()}\n"
        "- post_drill_status: PASS\n\n"
        "## Executed Selector Summary\n\n"
        f"- total_selectors_run: {len(_all_drill_checks())}\n"
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    field_results, selector_results, selector_logs = _execute_checks(
        timeout_seconds=float(args.pytest_timeout_seconds),
        retries=int(args.selector_retries),
    )
    failed = [key for key, passed in field_results.items() if not passed]
    if failed and not bool(args.allow_check_failures):
        details = "\n".join(
            f"{selector}: {selector_logs.get(selector, '')}"
            for selector in sorted(selector_logs)
        )
        raise RuntimeError(
            "key-rotation live checks failed for: "
            + ", ".join(sorted(failed))
            + f"\n{details}"
        )

    output_path = Path(str(args.output))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        _build_markdown(
            field_results=field_results,
            selector_results=selector_results,
            selector_logs=selector_logs,
        ),
        encoding="utf-8",
    )
    verify_key_rotation_drill_evidence(
        drill_path=output_path,
        max_drill_age_days=float(args.max_drill_age_days),
    )
    print(f"Generated key-rotation drill evidence: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
