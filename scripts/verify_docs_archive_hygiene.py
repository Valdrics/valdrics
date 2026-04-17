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
REGISTERED_ACTIVE_DATED_DOCS = {
    "docs/ops/enforcement_control_plane_gap_register_2026-02-23.md",
    "docs/ops/evidence/enforcement_failure_injection_2026-02-27.json",
    "docs/ops/evidence/enforcement_stress_artifact_2026-02-27.json",
    "docs/ops/evidence/finance_committee_packet_assumptions_2026-02-28.json",
    "docs/ops/evidence/finance_guardrails_2026-02-27.json",
    "docs/ops/evidence/finance_telemetry_snapshot_2026-02-28.json",
    "docs/ops/evidence/pkg_fin_operational_readiness_2026-03-01.json",
    "docs/ops/evidence/pkg_fin_policy_decisions_2026-02-28.json",
    "docs/ops/evidence/pricing_benchmark_register_2026-02-27.json",
    "docs/ops/evidence/valdrics_disposition_register_2026-02-28.json",
    "docs/ops/key-rotation-drill-2026-02-27.md",
}
WEAK_REFERENCE_PREFIXES = (
    "docs/ops/evidence/all_changes_inventory",
)
PROHIBITED_ACTIVE_DOCS = {
    "docs/incident_response_plan.md": "Use docs/runbooks/incident_response.md instead.",
    "docs/DEPRECATION_POLICY.md": (
        "Inactive policy narrative belongs under docs/archive/reference/."
    ),
    "docs/ZOMBIE_DETECTION_REFERENCE.md": (
        "The historical reference belongs under docs/archive/reference/."
    ),
    "docs/LOGIC_AND_PERFORMANCE_AUDIT.md": (
        "Historical audit snapshots belong under docs/archive/reviews/."
    ),
    "docs/evidence/ci-green-2026-02-27.md": (
        "Historical CI green-run promotion packet belongs under docs/archive/evidence/2026-q1/."
    ),
    "docs/ops/drills/enforcement_incident_drill_2026-02-23.md": (
        "Historical enforcement incident drill record belongs under docs/archive/ops/2026-q1/drills/."
    ),
    "docs/ops/enforcement_stress_evidence_2026-02-25.md": (
        "Use docs/ops/enforcement_stress_evidence.md for the canonical active protocol."
    ),
    "docs/ops/enforcement_post_closure_sanity_2026-02-26.md": (
        "Use docs/ops/enforcement_post_closure_sanity.md for the canonical active policy."
    ),
    "docs/ops/enforcement_failure_injection_matrix_2026-02-25.md": (
        "Use docs/ops/enforcement_failure_injection_matrix.md for the canonical active matrix."
    ),
    "docs/ops/benchmark_alignment_profiles_2026-02-27.md": (
        "Use docs/ops/benchmark_alignment_profiles.md for the canonical active benchmark profile."
    ),
    "docs/ops/alert-evidence-2026-02-25.md": (
        "Use docs/ops/alert-evidence.md for the canonical active evidence contract."
    ),
    "docs/ops/feature_enforceability_matrix_2026-02-27.json": (
        "Use docs/ops/feature_enforceability_matrix.json for the canonical active matrix."
    ),
    "docs/security/jwt_bcp_checklist_2026-02-27.json": (
        "Use docs/security/jwt_bcp_checklist.json for the canonical active checklist."
    ),
    "docs/security/ssdf_traceability_matrix_2026-02-25.json": (
        "Use docs/security/ssdf_traceability_matrix.json for the canonical active matrix."
    ),
    "docs/ops/landing_funnel_alerting_2026-03-10.md": (
        "Use docs/ops/landing_funnel_alerting.md for the canonical active contract."
    ),
    "docs/ops/incident_response_runbook.md": (
        "Use docs/runbooks/incident_response.md for the canonical active incident runbook."
    ),
    "docs/guides/aws_scp_setup.md": (
        "Legacy AWS SCP setup guidance is not part of the current active docs surface; archive it under docs/archive/reference/ or remove it."
    ),
    "docs/guides/cicd_security.md": (
        "Legacy CI/CD hardening narrative is superseded by active workflow/runbook contracts; archive it under docs/archive/reference/ or remove it."
    ),
    "docs/architecture/identity_blueprint.md": (
        "Historical identity reference belongs under docs/archive/reference/2026-q2/architecture/."
    ),
    "docs/architecture/discovery_wizard.md": (
        "Historical discovery wizard note belongs under docs/archive/reference/2026-q2/architecture/."
    ),
    "docs/product/personas.md": (
        "Historical product persona note belongs under docs/archive/reference/2026-q2/product/."
    ),
    "docs/runbooks/aws_first_operator_flow.md": (
        "Provider-specific AWS tenant smoke belongs under docs/archive/runbooks/2026-q2/."
    ),
    "docs/ops/landing_page_audit_closure_2026-03-02.md": (
        "Historical landing audit closure belongs under docs/archive/ops/2026-q1/."
    ),
    "docs/ops/pricing_packaging_correction_closure_2026-03-09.md": (
        "Historical pricing/package correction closure belongs under docs/archive/ops/2026-q1/."
    ),
}
PROHIBITED_ACTIVE_DOC_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^docs/ops/all_changes_categorization_\d{4}-\d{2}-\d{2}(?:_followup)?\.md$"),
        "Dated change-categorization snapshots belong under docs/archive/ops/<quarter>/.",
    ),
    (
        re.compile(
            r"^docs/ops/evidence/all_changes_inventory(?:_followup2?|)?_\d{4}-\d{2}-\d{2}\.txt$"
        ),
        "Historical all-changes inventory snapshots belong under docs/archive/ops/<quarter>/evidence/.",
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


def _is_weak_reference(relative_path: str) -> bool:
    return relative_path.startswith(WEAK_REFERENCE_PREFIXES)


def verify_docs_archive_hygiene(*, root: Path) -> list[str]:
    _validate_root(root)
    errors: list[str] = []
    prohibited_active_matches: set[str] = set()

    for path_str, replacement in sorted(PROHIBITED_ACTIVE_DOCS.items()):
        if (root / path_str).exists():
            prohibited_active_matches.add(path_str)
            errors.append(
                f"{path_str}: prohibited active duplicate/orphan doc. {replacement}"
            )

    docs_root = root / "docs"
    if docs_root.exists():
        for candidate in docs_root.rglob("*"):
            if not candidate.is_file():
                continue
            rel = candidate.relative_to(root).as_posix()
            if rel.startswith("docs/archive/"):
                continue
            for pattern, replacement in PROHIBITED_ACTIVE_DOC_PATTERNS:
                if pattern.match(rel):
                    prohibited_active_matches.add(rel)
                    errors.append(
                        f"{rel}: prohibited active duplicate/orphan doc. {replacement}"
                    )
                    break

    search_index = _build_search_index(root)
    dated_candidates: list[Path] = []
    dated_set: set[str] = set()
    for candidate in _dated_docs(root):
        rel = candidate.relative_to(root).as_posix()
        if rel in prohibited_active_matches:
            continue
        if rel not in REGISTERED_ACTIVE_DATED_DOCS:
            errors.append(
                f"{rel}: active dated doc is not explicitly registered; "
                "archive it or add it to REGISTERED_ACTIVE_DATED_DOCS."
            )
            continue
        dated_candidates.append(candidate)
        dated_set.add(rel)

    strong_references_by_doc: dict[str, list[str]] = {}
    dated_neighbors: dict[str, set[str]] = {rel: set() for rel in dated_set}
    for candidate in dated_candidates:
        rel = candidate.relative_to(root).as_posix()
        references = [
            ref
            for ref in _repo_references(root, candidate, search_index=search_index)
            if not _is_weak_reference(ref)
        ]
        strong_references_by_doc[rel] = references
        for ref in references:
            if ref in dated_set:
                dated_neighbors[rel].add(ref)
                dated_neighbors[ref].add(rel)

    component_by_doc: dict[str, frozenset[str]] = {}
    remaining = set(dated_set)
    while remaining:
        start = remaining.pop()
        stack = [start]
        component = {start}
        while stack:
            current = stack.pop()
            for neighbor in dated_neighbors[current]:
                if neighbor in component:
                    continue
                component.add(neighbor)
                remaining.discard(neighbor)
                stack.append(neighbor)
        frozen_component = frozenset(component)
        for member in component:
            component_by_doc[member] = frozen_component

    component_supported: dict[frozenset[str], bool] = {}
    for component in set(component_by_doc.values()):
        component_supported[component] = any(
            ref not in component
            for member in component
            for ref in strong_references_by_doc[member]
        )

    for rel in strong_references_by_doc:
        component = component_by_doc[rel]
        supported = component_supported[component]
        if not supported:
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
