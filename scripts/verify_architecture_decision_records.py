#!/usr/bin/env python3
"""Verify required architecture decisions and managed scheduler sequence documentation."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)

PLACEHOLDER_TOKEN_RE = re.compile(
    r"\b(todo|tbd|placeholder|replace(?:_|-)?me|changeme)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DocumentRequirement:
    path: str
    required_tokens: tuple[str, ...]
    forbidden_tokens: tuple[str, ...] = ()


REQUIRED_DOCUMENTS: tuple[DocumentRequirement, ...] = (
    DocumentRequirement(
        path="ADR-0005-paystack-over-stripe.md",
        required_tokens=(
            "## Context",
            "## Decision",
            "## Consequences",
            "Paystack",
            "Stripe",
        ),
    ),
    DocumentRequirement(
        path="ADR-0006-supabase-managed-auth-platform.md",
        required_tokens=(
            "## Context",
            "## Decision",
            "## Consequences",
            "Supabase",
            "self-hosted",
        ),
    ),
    DocumentRequirement(
        path="ADR-0008-codecarbon-emissions-observability.md",
        required_tokens=(
            "## Context",
            "## Decision",
            "## Consequences",
            "CodeCarbon",
            "emissions",
        ),
    ),
    DocumentRequirement(
        path="scheduler_orchestration_sequence.md",
        required_tokens=(
            "sequenceDiagram",
            "Cloud Scheduler",
            "Cloud Tasks",
            "Cloud Run Jobs",
            "managed_work_runners.py",
            "fail-closed",
            "## Repository-Managed Local Loop",
            "## Concurrency and Deterministic Replay",
            "## Observability and Snapshot Stability",
            "## Failure Modes and Operational Misconfiguration Guards",
        ),
        forbidden_tokens=(
            "Celery",
            "scheduler_tasks.py",
        ),
    ),
)


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_docs_root(value: str) -> Path:
    return resolve_cli_path_from_root(
        _repo_root(), Path(str(value)), field_name="docs_root"
    )


def verify_architecture_docs(docs_root: Path) -> tuple[str, ...]:
    errors: list[str] = []
    for requirement in REQUIRED_DOCUMENTS:
        path = docs_root / requirement.path
        if not path.exists():
            errors.append(f"missing architecture doc: {path.as_posix()}")
            continue
        text = path.read_text(encoding="utf-8")
        if PLACEHOLDER_TOKEN_RE.search(text):
            errors.append(f"placeholder token present in {path.as_posix()}")
        for token in requirement.required_tokens:
            if token not in text:
                errors.append(f"missing token in {path.as_posix()}: {token}")
        for token in requirement.forbidden_tokens:
            if token in text:
                errors.append(f"forbidden token present in {path.as_posix()}: {token}")
    return tuple(errors)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify required ADR coverage and managed scheduler orchestration sequence docs."
        )
    )
    parser.add_argument(
        "--docs-root",
        default=str(_repo_root() / "docs" / "architecture"),
        help="Path to architecture docs directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    docs_root = _resolve_docs_root(str(args.docs_root))
    if not docs_root.exists():
        print(
            f"[verify_architecture_decision_records] docs_root not found: {docs_root}"
        )
        return 2
    if not docs_root.is_dir():
        print(
            "[verify_architecture_decision_records] "
            f"docs_root must be a directory: {docs_root}"
        )
        return 2
    errors = verify_architecture_docs(docs_root)
    if errors:
        print(f"[verify_architecture_decision_records] found {len(errors)} issue(s):")
        for error in errors:
            print(f" - {error}")
        return 1
    print(f"[verify_architecture_decision_records] ok docs_root={docs_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
