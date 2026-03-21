#!/usr/bin/env python3
"""Prevent dated and duplicate docs clutter from creeping back into the active tree."""

from __future__ import annotations

import argparse
from pathlib import Path
from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)
import re
from typing import Iterable


DEFAULT_ROOT = _repo_root_for(__file__)
DATED_DOC_PATTERN = re.compile(r"(?:^|[_-])\d{4}-\d{2}-\d{2}(?:[_-]|$)")
TEXT_EXTENSIONS = {
    ".md",
    ".json",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".mjs",
    ".cjs",
    ".svelte",
    ".yml",
    ".yaml",
    ".toml",
    ".txt",
}
SKIP_DIRECTORIES = {
    ".git",
    ".venv",
    ".runtime",
    "node_modules",
    "dashboard/node_modules",
    "dashboard/.svelte-kit",
    "dashboard/build",
    "dashboard/playwright-report",
    "dashboard/test-results",
    "docs/archive",
    "dist",
    "build",
    "htmlcov",
    "reports",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
}
ALLOWED_ORPHANED_DATED_DOC_PREFIXES = (
    "docs/evidence/",
    "docs/ops/evidence/",
)
ALLOWED_ORPHANED_DATED_DOCS = {
    "docs/security/jwt_bcp_checklist_2026-02-27.json",
    "docs/security/ssdf_traceability_matrix_2026-02-25.json",
    "docs/security/ssdf_traceability_matrix_2026-02-25.md",
}
PROHIBITED_ACTIVE_DOCS = {
    "docs/incident_response_plan.md": "Use docs/runbooks/incident_response.md instead.",
    "docs/ZOMBIE_DETECTION_REFERENCE.md": (
        "The historical reference belongs under docs/archive/reference/."
    ),
    "docs/LOGIC_AND_PERFORMANCE_AUDIT.md": (
        "Historical audit snapshots belong under docs/archive/reviews/."
    ),
}


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_root(path: Path) -> Path:
    return resolve_cli_path_from_root(_repo_root(), path, field_name="root")


def _validate_root(root: Path) -> None:
    if not root.exists():
        raise ValueError(f"root does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"root must be a directory: {root}")


def _iter_text_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(
            rel == skipped or rel.startswith(f"{skipped}/")
            for skipped in SKIP_DIRECTORIES
        ):
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue
        yield path


def _dated_docs(root: Path) -> list[Path]:
    docs_root = root / "docs"
    if not docs_root.exists():
        return []
    candidates: list[Path] = []
    for path in docs_root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".json"}:
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith("docs/archive/"):
            continue
        if DATED_DOC_PATTERN.search(path.stem):
            candidates.append(path)
    return sorted(candidates)


def _build_search_index(root: Path) -> list[tuple[str, str]]:
    indexed: list[tuple[str, str]] = []
    for candidate in _iter_text_files(root):
        rel = candidate.relative_to(root).as_posix()
        if rel.startswith("docs/archive/"):
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        indexed.append((rel, text))
    return indexed


def _repo_references(
    root: Path,
    target: Path,
    *,
    search_index: list[tuple[str, str]],
) -> list[str]:
    relative_target = target.relative_to(root).as_posix()
    matches: list[str] = []
    target_resolved = target.resolve()
    for rel, text in search_index:
        if (root / rel).resolve() == target_resolved:
            continue
        if relative_target in text:
            matches.append(rel)
    return sorted(matches)


def verify_docs_archive_hygiene(*, root: Path) -> list[str]:
    _validate_root(root)
    errors: list[str] = []

    for path_str, replacement in sorted(PROHIBITED_ACTIVE_DOCS.items()):
        if (root / path_str).exists():
            errors.append(
                f"{path_str}: prohibited active duplicate/orphan doc. {replacement}"
            )

    search_index = _build_search_index(root)
    for candidate in _dated_docs(root):
        rel = candidate.relative_to(root).as_posix()
        if rel in ALLOWED_ORPHANED_DATED_DOCS:
            continue
        if rel.startswith(ALLOWED_ORPHANED_DATED_DOC_PREFIXES):
            continue
        references = _repo_references(root, candidate, search_index=search_index)
        if not references:
            errors.append(
                f"{rel}: orphaned dated doc should be archived or referenced explicitly."
            )

    return errors


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail when orphaned dated docs or prohibited active duplicate docs reappear."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repository root (default: auto-detected).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        errors = verify_docs_archive_hygiene(root=_resolve_root(args.root))
    except ValueError as exc:
        print(f"[docs-archive-hygiene] failed: {exc}")
        return 2
    if errors:
        print("Documentation archive hygiene violations detected:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Documentation archive hygiene verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
