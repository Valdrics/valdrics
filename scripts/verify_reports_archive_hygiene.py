#!/usr/bin/env python3
"""Prevent historical report packs from drifting back into the active tree."""

from __future__ import annotations

import argparse
from pathlib import Path
import re

from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)


DEFAULT_ROOT = _repo_root_for(__file__)
PROHIBITED_ACTIVE_REPORT_PATHS = {
    "reports/production_fixes": (
        "Historical production hardening pack belongs under "
        "reports/archive/2026-q1/production_fixes/."
    ),
}
PROHIBITED_ACTIVE_REPORT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^reports/audit/(?!archive/).+_\d{4}-\d{2}-\d{2}\.(?:md|csv|json)$"),
        "Historical dated audit snapshots belong under reports/archive/<quarter>/audit/ "
        "or reports/audit/archive/.",
    ),
)


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_root(path: Path) -> Path:
    return resolve_cli_path_from_root(_repo_root(), path, field_name="root")


def _validate_root(root: Path) -> None:
    if not root.exists():
        raise ValueError(f"root does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"root must be a directory: {root}")


def verify_reports_archive_hygiene(*, root: Path) -> list[str]:
    _validate_root(root)
    errors: list[str] = []

    for path_str, replacement in sorted(PROHIBITED_ACTIVE_REPORT_PATHS.items()):
        if (root / path_str).exists():
            errors.append(
                f"{path_str}: prohibited active duplicate/orphan report pack. "
                f"{replacement}"
            )

    reports_root = root / "reports"
    if not reports_root.exists():
        return errors

    for candidate in reports_root.rglob("*"):
        if not candidate.is_file():
            continue
        rel = candidate.relative_to(root).as_posix()
        for pattern, replacement in PROHIBITED_ACTIVE_REPORT_PATTERNS:
            if pattern.match(rel):
                errors.append(
                    f"{rel}: prohibited active duplicate/orphan historical report. "
                    f"{replacement}"
                )
                break

    return sorted(errors)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail when historical report packs drift back into the active tree."
    )
    parser.add_argument(
        "--root",
        default=str(DEFAULT_ROOT),
        help="Repository root path (defaults to current repository).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        root = _resolve_root(Path(str(args.root)))
        errors = verify_reports_archive_hygiene(root=root)
    except ValueError as exc:
        print(f"[reports-archive-hygiene] failed: {exc}")
        return 2

    if not errors:
        print(f"[reports-archive-hygiene] ok root={root}")
        return 0

    print(
        f"[reports-archive-hygiene] found {len(errors)} prohibited active report path(s):"
    )
    for error in errors:
        print(f" - {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
