#!/usr/bin/env python3
"""Render a single operator-facing handoff from managed deployment reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import (
    ensure_parent_dir,
    promote_staged_file,
    protected_output_paths_from_root,
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
    resolve_output_path_from_root,
    stage_text_file,
)
from scripts.managed_deployment_contract import SUPPORTED_ENVIRONMENTS
from scripts.verify_managed_deployment_bundle import (
    verify_managed_deployment_bundle as _verify_managed_deployment_bundle,
)


CURRENT_PROFILE_NAME = "Koyeb managed services with immutable image promotion"
FUTURE_SCALE_PROFILE_NAME = "Helm + Terraform (AWS/EKS)"


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_report_path(path: Path, *, field_name: str) -> Path:
    resolved = resolve_cli_path_from_root(_repo_root(), path, field_name=field_name)
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"{field_name} must be file paths: {resolved.as_posix()}")
    return resolved


def _normalize_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path.as_posix()}.")
    return payload


def _status(flag: bool) -> str:
    return "READY" if flag else "BLOCKED"


def _render_items(items: list[str], *, prefix: str = "- ") -> list[str]:
    if not items:
        return [f"{prefix}None"]
    return [f"{prefix}`{item}`" for item in items]


def _render_handoff_markdown(
    *,
    environment: str,
    runtime_report_path: Path,
    migration_report_path: Path,
    deployment_report_path: Path,
    runtime_report: dict[str, Any],
    migration_report: dict[str, Any],
    deployment_report: dict[str, Any],
) -> str:
    runtime_blockers = _normalize_strings(runtime_report.get("runtime_validation_blockers"))
    migration_blockers = _normalize_strings(
        migration_report.get("migration_validation_blockers")
    )
    dashboard_blockers = _normalize_strings(
        deployment_report.get("koyeb_dashboard_public_env_blockers")
    )
    release_blockers = _normalize_strings(
        deployment_report.get("koyeb_release_value_blockers")
    )
    terraform_inputs = _normalize_strings(
        deployment_report.get("terraform_remaining_inputs")
    )
    koyeb_secret_blockers = _normalize_strings(
        deployment_report.get("koyeb_secret_value_blockers")
    )
    helm_secret_blockers = _normalize_strings(
        deployment_report.get("helm_runtime_secret_value_blockers")
    )
    nonblocking_placeholders = _normalize_strings(
        runtime_report.get("declared_but_not_runtime_required")
    )

    runtime_ready = bool(runtime_report.get("validation_ready"))
    migration_ready = bool(migration_report.get("migration_ready"))
    koyeb_ready = bool(deployment_report.get("ready_for_koyeb"))
    koyeb_release_ready = bool(deployment_report.get("ready_for_koyeb_release"))
    helm_ready = bool(deployment_report.get("ready_for_helm"))
    future_scale_ready = migration_ready and helm_ready and not terraform_inputs

    lines = [
        f"# Managed Deployment Handoff: {environment}",
        "",
        "This file is derived from the verified managed deployment reports.",
        "It is an operator summary, not the canonical source of truth.",
        "",
        "## Status",
        "",
        f"- Runtime env validation: {_status(runtime_ready)}",
        f"- Migration env validation: {_status(migration_ready)}",
        f"- Current supported profile (`{CURRENT_PROFILE_NAME}`): {_status(koyeb_release_ready and migration_ready)}",
        f"- Koyeb service deploy contract: {_status(koyeb_ready)}",
        f"- Koyeb immutable release contract: {_status(koyeb_release_ready)}",
        f"- Future scale profile (`{FUTURE_SCALE_PROFILE_NAME}`): {_status(future_scale_ready)}",
        "",
        "## Source Reports",
        "",
        f"- Runtime report: `{runtime_report_path}`",
        f"- Migration report: `{migration_report_path}`",
        f"- Deployment report: `{deployment_report_path}`",
        "",
        "## Root Operator Gaps",
        "",
        f"### Runtime env blockers in `{runtime_report.get('output_path', '')}`",
        *_render_items(runtime_blockers),
        "",
        f"### Migration env blockers in `{migration_report.get('output_path', '')}`",
        *_render_items(migration_blockers),
        "",
        "### Dashboard public env blockers in "
        f"`{deployment_report.get('artifacts', {}).get('koyeb_dashboard_env_json', '')}`",
        *_render_items(dashboard_blockers),
        "",
        "### Immutable release blockers in "
        f"`{deployment_report.get('artifacts', {}).get('koyeb_release_metadata', '')}`",
        *_render_items(release_blockers),
        "",
        "### Terraform inputs still required outside generated env",
        *_render_items(terraform_inputs),
        "",
        "## Derived Deployment Gaps",
        "",
        "### Koyeb secret payload blockers in "
        f"`{deployment_report.get('artifacts', {}).get('koyeb_secret_payload', '')}`",
        *_render_items(koyeb_secret_blockers),
        "",
        "### Helm runtime secret blockers in "
        f"`{deployment_report.get('artifacts', {}).get('helm_runtime_secret_json', '')}`",
        *_render_items(helm_secret_blockers),
        "",
        "## Declared Non-Blocking External Placeholders",
        "",
        *_render_items(nonblocking_placeholders),
        "",
        "## Verification Commands",
        "",
        f"- Runtime validation: `{runtime_report.get('validation_command', '')}`",
        f"- Migration validation: `{migration_report.get('validation_command', '')}`",
        f"- Migration apply: `{migration_report.get('migration_command', '')}`",
        "- Bundle verification: "
        f"`uv run python scripts/verify_managed_deployment_bundle.py --environment {environment}`",
        "",
        "Regenerate this handoff after any runtime env, migration env, or deployment artifact change.",
        "",
    ]
    return "\n".join(lines)


def render_managed_deployment_handoff(
    *,
    environment: str,
    runtime_report_path: Path,
    migration_report_path: Path,
    deployment_report_path: Path,
    output_path: Path,
) -> Path:
    normalized_environment = str(environment or "").strip().lower()
    if normalized_environment not in SUPPORTED_ENVIRONMENTS:
        raise ValueError(
            "environment must be one of: " + ", ".join(SUPPORTED_ENVIRONMENTS)
        )

    verification_errors = _verify_managed_deployment_bundle(
        environment=normalized_environment,
        runtime_report_path=runtime_report_path,
        migration_report_path=migration_report_path,
        deployment_report_path=deployment_report_path,
    )
    if verification_errors:
        raise ValueError(
            "cannot render managed deployment handoff for incoherent bundle:\n- "
            + "\n- ".join(verification_errors)
        )

    runtime_report = _load_json(runtime_report_path)
    migration_report = _load_json(migration_report_path)
    deployment_report = _load_json(deployment_report_path)
    content = _render_handoff_markdown(
        environment=normalized_environment,
        runtime_report_path=runtime_report_path,
        migration_report_path=migration_report_path,
        deployment_report_path=deployment_report_path,
        runtime_report=runtime_report,
        migration_report=migration_report,
        deployment_report=deployment_report,
    )
    staged_path = stage_text_file(output_path, content)
    promote_staged_file(staged_path, output_path, cleanup_output_on_failure=True)
    return output_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render a single operator-facing managed deployment handoff "
            "from verified runtime, migration, and deployment reports."
        )
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=SUPPORTED_ENVIRONMENTS,
    )
    parser.add_argument(
        "--runtime-report",
        type=Path,
        default=None,
        help="Path to runtime report JSON (default: .runtime/<environment>.report.json).",
    )
    parser.add_argument(
        "--migration-report",
        type=Path,
        default=None,
        help="Path to migration report JSON (default: .runtime/<environment>.migrate.report.json).",
    )
    parser.add_argument(
        "--deployment-report",
        type=Path,
        default=None,
        help="Path to deployment report JSON (default: .runtime/deploy/<environment>/deployment.report.json).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Path to rendered handoff markdown "
            "(default: .runtime/deploy/<environment>/operator-handoff.md)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    environment = str(args.environment).strip().lower()
    repo_root = _repo_root()
    try:
        runtime_report = _resolve_report_path(
            args.runtime_report or Path(".runtime") / f"{environment}.report.json",
            field_name="runtime report",
        )
        migration_report = _resolve_report_path(
            args.migration_report or Path(".runtime") / f"{environment}.migrate.report.json",
            field_name="migration report",
        )
        deployment_report = _resolve_report_path(
            args.deployment_report
            or Path(".runtime/deploy") / environment / "deployment.report.json",
            field_name="deployment report",
        )
        protected_paths = protected_output_paths_from_root(
            repo_root,
            __file__,
            runtime_report,
            migration_report,
            deployment_report,
        )
        output_path = resolve_output_path_from_root(
            repo_root,
            args.output or Path(".runtime/deploy") / environment / "operator-handoff.md",
            field_name="output",
            protected_paths=protected_paths,
            protected_error=(
                "output must not overwrite script sources, verified reports, or checked-in evidence"
            ),
        )
        ensure_parent_dir(output_path, field_name="output")
    except ValueError as exc:
        print(f"[managed-deployment-handoff] failed: {exc}")
        return 2

    try:
        rendered_path = render_managed_deployment_handoff(
            environment=environment,
            runtime_report_path=runtime_report,
            migration_report_path=migration_report,
            deployment_report_path=deployment_report,
            output_path=output_path,
        )
    except ValueError as exc:
        print(f"[managed-deployment-handoff] failed: {exc}")
        return 1

    print(
        "[managed-deployment-handoff] ok "
        f"environment={environment} "
        f"output={rendered_path.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
