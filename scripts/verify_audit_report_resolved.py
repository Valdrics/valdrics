"""Validate resolved audit findings against enforceable repository controls."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from scripts.audit_report_controls_registry import (
    FINDING_INDEX,
    FINDING_ORDER,
    run_checks,
)
from scripts.audit_report_controls_core import read_text

DEFAULT_REPORT_PATH = Path(
    "/home/daretechie/.gemini/antigravity/brain/"
    "dba19da4-0271-4686-88fd-9bc5a2b3dbfe/audit_report.md.resolved"
)
REPORT_FINDING_PATTERN = re.compile(r"^###\s+([CHML]-\d{2}):", re.MULTILINE)
REPORT_GENERIC_FINDING_PATTERN = re.compile(r"^###\s+([A-Z]+-\d{2}):", re.MULTILINE)


def parse_report_findings(report_path: Path) -> tuple[str, ...]:
    text = read_text(report_path)
    return tuple(REPORT_FINDING_PATTERN.findall(text))


def parse_generic_report_findings(report_path: Path) -> tuple[str, ...]:
    text = read_text(report_path)
    return tuple(REPORT_GENERIC_FINDING_PATTERN.findall(text))


def validate_report_scope(
    *,
    report_findings: tuple[str, ...],
    expected_findings: tuple[str, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    report_set = set(report_findings)
    expected_set = set(expected_findings)
    missing = sorted(expected_set - report_set)
    if missing:
        errors.append("report missing expected finding headings: " + ", ".join(missing))
    return tuple(errors)


def validate_generic_report_findings(
    *,
    report_findings: tuple[str, ...],
) -> tuple[str, ...]:
    errors: list[str] = []
    if not report_findings:
        errors.append("report contains no recognizable finding headings.")
        return tuple(errors)
    duplicates = sorted(
        finding_id
        for finding_id in set(report_findings)
        if report_findings.count(finding_id) > 1
    )
    if duplicates:
        errors.append("report has duplicate finding headings: " + ", ".join(duplicates))
    return tuple(errors)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate resolved audit findings against repository controls."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path("."),
        help="Repository root path.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path to the markdown audit report to validate (can be outside repo).",
    )
    parser.add_argument(
        "--allow-missing-report",
        action="store_true",
        help="Do not fail when --report-path does not exist.",
    )
    parser.add_argument(
        "--skip-report-check",
        action="store_true",
        help="Skip parsing/validating report headings and run controls only.",
    )
    parser.add_argument(
        "--finding",
        action="append",
        default=[],
        help="Restrict checks to specific finding id(s), e.g. --finding C-01.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()

    selected = tuple(args.finding) if args.finding else FINDING_ORDER
    unknown = [finding for finding in selected if finding not in FINDING_INDEX]
    if unknown:
        print("Unknown finding id(s): " + ", ".join(sorted(unknown)))
        return 2

    report_errors: list[str] = []
    if not args.skip_report_check:
        report_path = args.report_path
        if not report_path.exists():
            if not args.allow_missing_report:
                print(
                    f"[audit-report] missing report file: {report_path.as_posix()} "
                    "(pass --allow-missing-report to continue without heading validation)."
                )
                return 2
            report_errors.append(
                f"report not found (skipped heading validation): {report_path.as_posix()}"
            )
        else:
            report_findings = parse_report_findings(report_path)
            if report_findings:
                report_errors.extend(
                    validate_report_scope(
                        report_findings=report_findings,
                        expected_findings=selected,
                    )
                )
            else:
                generic_report_findings = parse_generic_report_findings(report_path)
                if generic_report_findings:
                    report_errors.extend(
                        validate_generic_report_findings(
                            report_findings=generic_report_findings
                        )
                    )
                else:
                    report_errors.append(
                        "report contains no recognizable finding headings."
                    )

    failures, passes = run_checks(repo_root=repo_root, finding_ids=selected)
    if report_errors:
        failures = tuple(f"[report] {error}" for error in report_errors) + failures

    if failures:
        print("[audit-report] FAILED")
        for failure in failures:
            print(f"- {failure}")
        print(
            f"[audit-report] summary passed={len(passes)} failed={len(failures)} "
            f"checked={len(selected)}"
        )
        return 1

    print(
        "[audit-report] ok "
        f"passed={len(passes)} checked={len(selected)} repo_root={repo_root.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
