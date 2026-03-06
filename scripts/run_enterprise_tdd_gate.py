"""Run enterprise hardening TDD release gate commands in CI/local automation."""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from collections.abc import Sequence
from pathlib import Path

from scripts.enterprise_tdd_gate_config import *  # noqa: F403
from scripts.enterprise_tdd_gate_commands import build_gate_commands
from scripts import enterprise_tdd_gate_coverage as _coverage

compute_coverage_subset_from_xml = _coverage.compute_coverage_subset_from_xml
verify_coverage_subset_from_xml = _coverage.verify_coverage_subset_from_xml
_parse_coverage_report_args = _coverage.parse_coverage_report_args


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _format_command(cmd: Sequence[str]) -> str:
    return " ".join(shlex.quote(part) for part in cmd)


def run_gate(*, dry_run: bool) -> int:
    commands = build_gate_commands()
    repo_root = _repo_root()
    coverage_xml_path = repo_root / "coverage-enterprise-gate.xml"
    coverage_data_path = repo_root / ".coverage.enterprise-gate"
    if not dry_run:
        coverage_data_path.unlink(missing_ok=True)
        # Remove stale artifacts so root-hygiene prechecks stay deterministic.
        coverage_xml_path.unlink(missing_ok=True)
    command_env = os.environ.copy()
    command_env["COVERAGE_FILE"] = str(coverage_data_path)
    # Enforce deterministic release-gate behavior regardless of ambient shell values.
    # Some local profiles export non-boolean DEBUG values (for example "release"),
    # which can break pydantic settings parsing in pytest bootstrap.
    command_env["DEBUG"] = "false"
    try:
        for cmd in commands:
            rendered = _format_command(cmd)
            print(f"[enterprise-gate] {rendered}")
            if dry_run:
                continue
            try:
                subprocess.run(cmd, check=True, env=command_env)
            except subprocess.CalledProcessError:
                coverage_args = _parse_coverage_report_args(cmd)
                if coverage_args is None:
                    raise
                include_patterns, fail_under = coverage_args
                label = ",".join(include_patterns)
                verify_coverage_subset_from_xml(
                    xml_path=coverage_xml_path,
                    include_patterns=include_patterns,
                    fail_under=fail_under,
                    label=label,
                    repo_root=repo_root,
                )
    finally:
        if not dry_run:
            coverage_data_path.unlink(missing_ok=True)
            coverage_xml_path.unlink(missing_ok=True)
    return 0


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run enterprise hardening TDD release-blocking gate."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing them.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    return run_gate(dry_run=bool(args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
