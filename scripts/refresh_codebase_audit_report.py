#!/usr/bin/env python3
"""Refresh the checked-in codebase audit report from live repo facts."""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import (
    promote_staged_file,
    repo_root_for,
    resolve_cli_path_from_root,
    stage_json_file,
)
from scripts.verify_codebase_audit_report import (
    DEFAULT_REPORT,
    _derive_frontend_stack_phrase,
    collect_live_measured_facts,
    verify_audit_report,
)


DEFAULT_ROOT = repo_root_for(__file__)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object in {path.as_posix()}")
    return payload


def _replace_or_append(values: list[str], *, predicate: callable, replacement: str) -> list[str]:
    updated: list[str] = []
    replaced = False
    for item in values:
        if not replaced and predicate(item):
            updated.append(replacement)
            replaced = True
            continue
        updated.append(item)
    if not replaced:
        updated.append(replacement)
    return updated


def _replace_claim(
    claims: list[dict[str, Any]],
    *,
    match_claim: str,
    replacement: dict[str, Any],
) -> list[dict[str, Any]]:
    updated: list[dict[str, Any]] = []
    replaced = False
    for claim in claims:
        if not replaced and claim.get("claim") == match_claim:
            updated.append(replacement)
            replaced = True
            continue
        updated.append(claim)
    if not replaced:
        updated.append(replacement)
    return updated


def refresh_audit_report(
    *,
    root: Path,
    report_path: Path,
    snapshot_date: str | None = None,
    live_facts: dict[str, Any] | None = None,
    frontend_stack_phrase: str | None = None,
) -> dict[str, Any]:
    payload = _load_json(report_path)
    measured_facts = live_facts or collect_live_measured_facts(root=root)
    stack_phrase = frontend_stack_phrase or _derive_frontend_stack_phrase(root=root)
    refreshed_snapshot_date = snapshot_date or date.today().isoformat()

    payload["snapshot_date"] = refreshed_snapshot_date
    payload["measured_facts"] = measured_facts

    summary = payload.get("summary")
    if isinstance(summary, dict):
        important_corrections = summary.get("important_corrections")
        if isinstance(important_corrections, list):
            important_corrections = [str(item) for item in important_corrections]
            important_corrections = _replace_or_append(
                important_corrections,
                predicate=lambda item: item.startswith("Backend tests collected currently total "),
                replacement=(
                    "Backend tests collected currently total "
                    f"{measured_facts['backend_tests_collected']}, not 5358."
                ),
            )
            important_corrections = _replace_or_append(
                important_corrections,
                predicate=lambda item: item.startswith("Zombie detection plugin classes total "),
                replacement=(
                    "Zombie detection plugin classes total "
                    f"{measured_facts['zombie_plugin_classes']} across providers, not 11."
                ),
            )
            summary["important_corrections"] = important_corrections

        high_confidence_findings = summary.get("high_confidence_findings")
        if isinstance(high_confidence_findings, list):
            high_confidence_findings = [str(item) for item in high_confidence_findings]
            summary["high_confidence_findings"] = _replace_or_append(
                high_confidence_findings,
                predicate=lambda item: item.startswith("The dashboard uses "),
                replacement=f"The dashboard uses {stack_phrase}.",
            )

    confirmed_claims = payload.get("confirmed_claims")
    if isinstance(confirmed_claims, list):
        payload["confirmed_claims"] = _replace_claim(
            [claim for claim in confirmed_claims if isinstance(claim, dict)],
            match_claim="Frontend stack includes SvelteKit, Svelte 5, TypeScript, Tailwind CSS v4, Vitest, and Playwright.",
            replacement={
                "claim": f"Frontend stack includes {stack_phrase}.",
                "evidence": [{"path": "dashboard/package.json", "line": 1}],
            },
        )

    incorrect_claims = payload.get("incorrect_claims")
    if isinstance(incorrect_claims, list):
        refreshed_incorrect_claims = [claim for claim in incorrect_claims if isinstance(claim, dict)]
        refreshed_incorrect_claims = _replace_claim(
            refreshed_incorrect_claims,
            match_claim="Testing has 5,358 tests",
            replacement={
                "claim": "Testing has 5,358 tests",
                "correction": (
                    "A fresh backend collection run reported "
                    f"{measured_facts['backend_tests_collected']} tests collected."
                ),
                "evidence": [
                    {
                        "path": "pytest --collect-only",
                        "line": measured_facts["backend_tests_collected"],
                    }
                ],
            },
        )
        refreshed_incorrect_claims = _replace_claim(
            refreshed_incorrect_claims,
            match_claim="FinOps capabilities include 11 zombie detection plugins",
            replacement={
                "claim": "FinOps capabilities include 11 zombie detection plugins",
                "correction": (
                    "A structural scan found "
                    f"{measured_facts['zombie_plugin_classes']} ZombiePlugin subclasses "
                    "across provider adapters."
                ),
                "evidence": [{"path": "app/modules/optimization/adapters", "line": 1}],
            },
        )
        payload["incorrect_claims"] = refreshed_incorrect_claims

    staged_path = stage_json_file(report_path, payload, indent=2, sort_keys=True, trailing_newline=True)
    promote_staged_file(staged_path, report_path, cleanup_output_on_failure=True)
    return payload


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Refresh the checked-in codebase audit report from live repo facts."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repository root to measure.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=DEFAULT_REPORT,
        help="Audit report JSON file to refresh.",
    )
    parser.add_argument(
        "--snapshot-date",
        default=None,
        help="Override snapshot date (YYYY-MM-DD). Defaults to today.",
    )
    parser.add_argument(
        "--skip-verify",
        action="store_true",
        help="Skip post-refresh verification.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = resolve_cli_path_from_root(DEFAULT_ROOT, args.root, field_name="root")
    report_path = resolve_cli_path_from_root(root, args.report, field_name="report")

    refresh_audit_report(
        root=root,
        report_path=report_path,
        snapshot_date=args.snapshot_date,
    )

    if not args.skip_verify:
        errors = verify_audit_report(
            root=root,
            report_path=report_path,
            enforce_live_measured_facts=True,
        )
        if errors:
            print("[refresh-codebase-audit-report] FAILED")
            for error in errors:
                print(f"- {error}")
            return 1

    print(f"[refresh-codebase-audit-report] ok report={report_path.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
