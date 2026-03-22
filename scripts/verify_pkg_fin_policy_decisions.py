#!/usr/bin/env python3
"""Validate PKG/FIN policy decision evidence for release and pricing changes."""

from __future__ import annotations

import argparse
from pathlib import Path
from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)

from scripts.pkg_fin_policy_decisions_constants import REQUIRED_DECISION_BACKLOG_IDS
from scripts.pkg_fin_policy_decisions_core import verify_evidence


# Re-export for downstream tests and scripts.
__all__ = ["REQUIRED_DECISION_BACKLOG_IDS", "verify_evidence", "main"]


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_evidence_path(path: Path) -> Path:
    resolved = resolve_cli_path_from_root(_repo_root(), path, field_name="evidence_path")
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"evidence_path must be a file: {resolved}")
    return resolved


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Verify PKG/FIN policy decision evidence artifact used for "
            "pricing and packaging motions."
        )
    )
    parser.add_argument(
        "--evidence-path",
        required=True,
        help="Path to PKG/FIN policy decision evidence JSON.",
    )
    parser.add_argument(
        "--max-artifact-age-hours",
        type=float,
        default=None,
        help="Optional max age of artifact in hours.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        evidence_path = _resolve_evidence_path(Path(str(args.evidence_path)))
        verify_evidence(
            evidence_path=evidence_path,
            max_artifact_age_hours=(
                float(args.max_artifact_age_hours)
                if args.max_artifact_age_hours is not None
                else None
            ),
        )
    except (FileNotFoundError, ValueError) as exc:
        print(f"[pkg-fin-policy-decisions] failed: {exc}")
        return 2
    print(f"PKG/FIN policy decision evidence verified: {evidence_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
