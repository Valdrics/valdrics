#!/usr/bin/env python3
"""Generate runtime Valdrics disposition register evidence artifact."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from scripts.verify_valdrics_disposition_freshness import (
    DEFAULT_REQUIRED_FINDING_IDS,
    verify_disposition_register,
)


@dataclass(frozen=True)
class RuntimeProbe:
    probe_id: str
    command: tuple[str, ...]


RUNTIME_PROBES: tuple[RuntimeProbe, ...] = (
    RuntimeProbe(
        probe_id="adapter_coverage",
        command=(sys.executable, "scripts/verify_adapter_test_coverage.py"),
    ),
    RuntimeProbe(
        probe_id="module_size_budget",
        command=(
            sys.executable,
            "scripts/verify_python_module_size_budget.py",
            "--enforcement-mode",
            "strict",
        ),
    ),
    RuntimeProbe(
        probe_id="dependency_locking",
        command=(sys.executable, "scripts/verify_dependency_locking.py"),
    ),
    RuntimeProbe(
        probe_id="env_hygiene",
        command=(sys.executable, "scripts/verify_env_hygiene.py"),
    ),
    RuntimeProbe(
        probe_id="audit_controls",
        command=(
            sys.executable,
            "scripts/verify_audit_report_resolved.py",
            "--skip-report-check",
        ),
    ),
)

FINDING_PROBE_MAP: dict[str, tuple[str, ...]] = {
    "VAL-ADAPT-001": ("adapter_coverage", "module_size_budget"),
    "VAL-ADAPT-002+": ("module_size_budget", "audit_controls"),
    "VAL-DB-002": ("env_hygiene", "audit_controls"),
    "VAL-DB-003": ("dependency_locking", "audit_controls"),
    "VAL-DB-004": ("audit_controls",),
    "VAL-API-001": ("audit_controls",),
    "VAL-API-002": ("audit_controls",),
    "VAL-API-004": ("env_hygiene", "audit_controls"),
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Valdrics disposition register JSON artifact.",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Output path for Valdrics disposition register JSON.",
    )
    parser.add_argument(
        "--max-artifact-age-days",
        type=float,
        default=45.0,
        help="Verifier max artifact age in days.",
    )
    parser.add_argument(
        "--max-review-window-days",
        type=float,
        default=120.0,
        help="Verifier max review window in days.",
    )
    parser.add_argument(
        "--probe-timeout-seconds",
        type=float,
        default=180.0,
        help="Timeout for each runtime probe command.",
    )
    parser.add_argument(
        "--source-audit-path",
        default="runtime://ci/deep_debt_audit_2026-03-05",
        help="Audit source reference recorded in the artifact.",
    )
    return parser.parse_args(argv)


def _owner_for(finding_id: str) -> str:
    if finding_id.startswith("VAL-DB"):
        return "platform-database@valdrics.local"
    if finding_id.startswith("VAL-API"):
        return "platform-security@valdrics.local"
    return "platform-architecture@valdrics.local"


def _build_disposition(finding_id: str, *, review_by: str) -> dict[str, Any]:
    status = "documented_exception"
    disposition: dict[str, Any] = {
        "finding_id": finding_id,
        "status": status,
        "owner": _owner_for(finding_id),
        "review_by": review_by,
        "rationale": (
            f"{finding_id} is tracked under runtime governance with explicit risk disposition."
        ),
        "exit_criteria": (
            f"{finding_id} closure requires validated remediation evidence in release gates."
        ),
    }
    if status == "planned_refactor":
        disposition["backlog_ref"] = finding_id
    return disposition


def _run_probe(
    *,
    command: tuple[str, ...],
    timeout_seconds: float,
) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            list(command),
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return False, f"timeout after {timeout_seconds:.1f}s ({exc})"

    combined_output = "\n".join(
        part for part in (completed.stdout.strip(), completed.stderr.strip()) if part
    ).strip()
    return completed.returncode == 0, combined_output


def _collect_probe_results(*, timeout_seconds: float) -> dict[str, dict[str, Any]]:
    results: dict[str, dict[str, Any]] = {}
    for probe in RUNTIME_PROBES:
        passed, output = _run_probe(
            command=probe.command,
            timeout_seconds=timeout_seconds,
        )
        results[probe.probe_id] = {
            "probe_id": probe.probe_id,
            "command": " ".join(probe.command),
            "passed": bool(passed),
            "output_excerpt": output[:1200],
        }
    return results


def _disposition_from_probe_results(
    *,
    finding_id: str,
    review_by: str,
    probe_results: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    disposition = _build_disposition(finding_id, review_by=review_by)
    mapped_probes = FINDING_PROBE_MAP.get(finding_id, ())
    mapped_results = [probe_results.get(probe_id, {}) for probe_id in mapped_probes]
    all_passed = bool(mapped_results) and all(
        bool(item.get("passed")) for item in mapped_results
    )

    if all_passed:
        disposition["status"] = "documented_exception"
        disposition["rationale"] = (
            f"{finding_id} is governed by live controls "
            f"({', '.join(mapped_probes)}) and currently passes runtime validation."
        )
        disposition["exit_criteria"] = (
            "Maintain probe pass state in release pipelines; "
            "convert disposition to closed once audit confirms sustained pass trend."
        )
    else:
        failed_probe_ids = [
            item.get("probe_id", "unknown")
            for item in mapped_results
            if not bool(item.get("passed"))
        ]
        disposition["status"] = "planned_refactor"
        disposition["backlog_ref"] = finding_id
        disposition["rationale"] = (
            f"{finding_id} has failing runtime probes: {', '.join(failed_probe_ids) or 'none'}."
        )
        disposition["exit_criteria"] = (
            "Resolve failing probes and require two consecutive passing release runs "
            "before downgrading from planned_refactor."
        )
    disposition["control_probe_ids"] = list(mapped_probes)
    return disposition


def _build_payload(
    *,
    source_audit_path: str,
    probe_timeout_seconds: float,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    review_by = (now.date() + timedelta(days=30)).isoformat()
    probe_results = _collect_probe_results(timeout_seconds=probe_timeout_seconds)
    return {
        "captured_at": now.isoformat(),
        "source_audit_path": source_audit_path,
        "runtime_probe_results": [probe_results[key] for key in sorted(probe_results)],
        "dispositions": [
            _disposition_from_probe_results(
                finding_id=finding_id,
                review_by=review_by,
                probe_results=probe_results,
            )
            for finding_id in DEFAULT_REQUIRED_FINDING_IDS
        ],
    }


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    payload = _build_payload(
        source_audit_path=str(args.source_audit_path).strip(),
        probe_timeout_seconds=float(args.probe_timeout_seconds),
    )
    output_path = Path(str(args.output))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    verify_disposition_register(
        register_path=output_path,
        max_artifact_age_days=float(args.max_artifact_age_days),
        max_review_window_days=float(args.max_review_window_days),
    )
    print(f"Generated Valdrics disposition register: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
