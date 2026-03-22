"""Verify repository root hygiene for release automation."""

from __future__ import annotations

import argparse
import fnmatch
from dataclasses import dataclass
from pathlib import Path
from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)


PROHIBITED_ROOT_PATTERNS: tuple[str, ...] = (
    "artifact.json",
    "codealike.json",
    "coverage-enterprise-gate.xml",
    "inspect_httpx.py",
    "full_test_output.log",
    "test_results.log",
    "feedback.md",
    "useLanding.md",
    "test_*.sqlite",
    "test_*.sqlite-shm",
    "test_*.sqlite-wal",
    "valdrics_local*.sqlite3",
    "valdrics_local*.sqlite3-journal",
    "valdrics_local*.sqlite3-shm",
    "valdrics_local*.sqlite3-wal",
    "valdrics_local*.sqlite3.bootstrap.lock",
)


@dataclass(frozen=True)
class RootHygieneViolation:
    name: str
    pattern: str


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_root(path: Path) -> Path:
    return resolve_cli_path_from_root(_repo_root(), path, field_name="root")


def _validate_root(root: Path) -> None:
    if not root.exists():
        raise ValueError(f"root does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"root must be a directory: {root}")


def collect_root_hygiene_violations(
    root: Path, *, prohibited_patterns: tuple[str, ...] = PROHIBITED_ROOT_PATTERNS
) -> tuple[RootHygieneViolation, ...]:
    _validate_root(root)
    violations: list[RootHygieneViolation] = []
    for child in root.iterdir():
        if not child.is_file():
            continue
        for pattern in prohibited_patterns:
            if fnmatch.fnmatch(child.name, pattern):
                violations.append(
                    RootHygieneViolation(name=child.name, pattern=pattern)
                )
                break
    return tuple(sorted(violations, key=lambda item: item.name))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail when prohibited artifacts are present in repository root."
    )
    parser.add_argument(
        "--root",
        default=str(_repo_root()),
        help="Repository root path (defaults to current repository).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        root = _resolve_root(Path(str(args.root)))
        violations = collect_root_hygiene_violations(root)
    except ValueError as exc:
        print(f"[repo-root-hygiene] failed: {exc}")
        return 2
    if not violations:
        print(f"[repo-root-hygiene] ok root={root}")
        return 0

    print(f"[repo-root-hygiene] found {len(violations)} prohibited root file(s):")
    for violation in violations:
        print(
            f" - {violation.name} (matched pattern {violation.pattern!r}); "
            "move to docs/ or remove from repository root."
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
