#!/usr/bin/env python3
"""Verify required architecture decisions and scheduler sequence documentation."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

PLACEHOLDER_TOKEN_RE = re.compile(
    r"\b(todo|tbd|placeholder|replace(?:_|-)?me|changeme)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class DocumentRequirement:
    path: str
    required_tokens: tuple[str, ...]


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
        path="ADR-0007-redis-backed-circuit-breakers.md",
        required_tokens=(
            "## Context",
            "## Decision",
            "## Consequences",
            "Redis",
            "in-memory",
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
        path="ADR-0009-celery-redis-job-orchestration.md",
        required_tokens=(
            "## Context",
            "## Decision",
            "## Consequences",
            "Celery",
            "BackgroundTasks",
        ),
    ),
    DocumentRequirement(
        path="scheduler_orchestration_sequence.md",
        required_tokens=(
            "sequenceDiagram",
            "scheduler_tasks.py",
            "orchestrator.py",
            "## Concurrency and Deterministic Replay",
            "## Observability and Snapshot Stability",
            "## Failure Modes and Operational Misconfiguration Guards",
        ),
    ),
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
    return tuple(errors)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify required ADR coverage and scheduler orchestration sequence docs."
        )
    )
    parser.add_argument(
        "--docs-root",
        default=str(
            Path(__file__).resolve().parents[1] / "docs" / "architecture"
        ),
        help="Path to architecture docs directory.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    docs_root = Path(args.docs_root).resolve()
    errors = verify_architecture_docs(docs_root)
    if errors:
        print(
            "[verify_architecture_decision_records] "
            f"found {len(errors)} issue(s):"
        )
        for error in errors:
            print(f" - {error}")
        return 1
    print(
        "[verify_architecture_decision_records] ok "
        f"docs_root={docs_root}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

