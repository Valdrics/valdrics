#!/usr/bin/env python3
"""Render a cross-environment blocker summary from verified managed deployment reports."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
from typing import Any, Callable

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
from scripts.verify_managed_deployment_bundle import (
    verify_managed_deployment_bundle as _verify_managed_deployment_bundle,
)


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path.as_posix()}.")
    return payload


def _normalize_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _default_runtime_report(environment: str) -> Path:
    return Path(".runtime") / f"{environment}.report.json"


def _default_migration_report(environment: str) -> Path:
    return Path(".runtime") / f"{environment}.migrate.report.json"


def _default_deployment_report(environment: str) -> Path:
    return Path(".runtime/deploy") / environment / "deployment.report.json"


def _ordered_normalized_items(
    items: list[str], normalize: Callable[[str], str]
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for item in items:
        normalized = normalize(item)
        if not normalized or normalized in seen:
            continue
        ordered.append(normalized)
        seen.add(normalized)
    return ordered


def _render_items(items: list[str], *, prefix: str = "- ") -> list[str]:
    if not items:
        return [f"{prefix}None"]
    return [f"{prefix}`{item}`" for item in items]


def _status(flag: bool) -> str:
    return "READY" if flag else "BLOCKED"


@dataclass(frozen=True)
class EnvironmentReports:
    environment: str
    runtime_report_path: Path
    migration_report_path: Path
    deployment_report_path: Path
    runtime_report: dict[str, Any]
    migration_report: dict[str, Any]
    deployment_report: dict[str, Any]


@dataclass(frozen=True)
class BlockerCategory:
    title: str
    report_kind: str
    key: str
    normalize: Callable[[str], str] = str
    note: str | None = None


BLOCKER_CATEGORIES: tuple[BlockerCategory, ...] = (
    BlockerCategory(
        title="Runtime env blockers",
        report_kind="runtime",
        key="runtime_validation_blockers",
    ),
    BlockerCategory(
        title="Migration env blockers",
        report_kind="migration",
        key="migration_validation_blockers",
    ),
    BlockerCategory(
        title="Cloudflare Pages public env blockers",
        report_kind="deployment",
        key="cloudflare_pages_public_env_blockers",
    ),
    BlockerCategory(
        title="Artifact Registry release blockers",
        report_kind="deployment",
        key="artifact_registry_release_value_blockers",
    ),
    BlockerCategory(
        title="Secret Manager runtime payload blockers",
        report_kind="deployment",
        key="secret_manager_secret_value_blockers",
    ),
    BlockerCategory(
        title="Terraform inputs outside generated env",
        report_kind="deployment",
        key="terraform_remaining_inputs",
    ),
)


def _resolve_report_path(root: Path, path: Path, *, field_name: str) -> Path:
    resolved = resolve_cli_path_from_root(root, path, field_name=field_name)
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"{field_name} must be a file path: {resolved.as_posix()}")
    return resolved


def _verified_environment_reports(
    *,
    root: Path,
    environment: str,
    runtime_report_path: Path,
    migration_report_path: Path,
    deployment_report_path: Path,
    allow_non_secret_artifact_bundle: bool,
) -> EnvironmentReports:
    runtime_report = _resolve_report_path(
        root, runtime_report_path, field_name=f"{environment}_runtime_report_path"
    )
    migration_report = _resolve_report_path(
        root, migration_report_path, field_name=f"{environment}_migration_report_path"
    )
    deployment_report = _resolve_report_path(
        root, deployment_report_path, field_name=f"{environment}_deployment_report_path"
    )

    verification_errors = _verify_managed_deployment_bundle(
        environment=environment,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        allow_non_secret_artifact_bundle=allow_non_secret_artifact_bundle,
    )
    if verification_errors:
        raise ValueError(
            f"cannot render blocker summary for {environment} bundle:\n- "
            + "\n- ".join(verification_errors)
        )

    return EnvironmentReports(
        environment=environment,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
        runtime_report=_load_json(runtime_report),
        migration_report=_load_json(migration_report),
        deployment_report=_load_json(deployment_report),
    )


def _report_payload(reports: EnvironmentReports, report_kind: str) -> dict[str, Any]:
    if report_kind == "runtime":
        return reports.runtime_report
    if report_kind == "migration":
        return reports.migration_report
    if report_kind == "deployment":
        return reports.deployment_report
    raise ValueError(f"unsupported report kind: {report_kind}")


def _category_lists(
    category: BlockerCategory,
    staging: EnvironmentReports,
    production: EnvironmentReports,
) -> tuple[list[str], list[str], list[str]]:
    staging_items = _ordered_normalized_items(
        _normalize_strings(
            _report_payload(staging, category.report_kind).get(category.key)
        ),
        category.normalize,
    )
    production_items = _ordered_normalized_items(
        _normalize_strings(
            _report_payload(production, category.report_kind).get(category.key)
        ),
        category.normalize,
    )
    staging_set = set(staging_items)
    production_set = set(production_items)
    shared = [item for item in staging_items if item in production_set]
    staging_only = [item for item in staging_items if item not in production_set]
    production_only = [item for item in production_items if item not in staging_set]
    return shared, staging_only, production_only


def _render_category_section(
    heading: str,
    *,
    categories: tuple[BlockerCategory, ...],
    staging: EnvironmentReports,
    production: EnvironmentReports,
    mode: str,
) -> list[str]:
    lines = [heading, ""]
    for category in categories:
        shared, staging_only, production_only = _category_lists(
            category, staging, production
        )
        if mode == "shared":
            items = shared
        elif mode == "staging":
            items = staging_only
        elif mode == "production":
            items = production_only
        else:
            raise ValueError(f"unsupported render mode: {mode}")
        lines.append(f"### {category.title}")
        if category.note:
            lines.append("")
            lines.append(category.note)
        lines.extend(["", *_render_items(items), ""])
    return lines


def _render_summary_markdown(
    *,
    staging: EnvironmentReports,
    production: EnvironmentReports,
) -> str:
    lines = [
        "# Managed Release Blocker Summary",
        "",
        "This file is derived from the verified staging and production managed deployment bundles.",
        "It highlights shared operator blockers versus environment-specific gaps.",
        "",
        "## Source Reports",
        "",
        f"### {staging.environment}",
        f"- Runtime report: `{staging.runtime_report_path}`",
        f"- Migration report: `{staging.migration_report_path}`",
        f"- Deployment report: `{staging.deployment_report_path}`",
        "",
        f"### {production.environment}",
        f"- Runtime report: `{production.runtime_report_path}`",
        f"- Migration report: `{production.migration_report_path}`",
        f"- Deployment report: `{production.deployment_report_path}`",
        "",
        "## Environment Status",
        "",
        f"- `{staging.environment}`: runtime env {_status(bool(staging.runtime_report.get('validation_ready')))}, "
        f"migration env {_status(bool(staging.migration_report.get('migration_ready')))}, "
        f"unified runtime {_status(bool(staging.deployment_report.get('ready_for_unified_platform')))}, "
        f"artifact promotion {_status(bool(staging.deployment_report.get('ready_for_release_promotion')))}, "
        f"terraform {_status(bool(staging.deployment_report.get('ready_for_terraform')))}",
        f"- `{production.environment}`: runtime env {_status(bool(production.runtime_report.get('validation_ready')))}, "
        f"migration env {_status(bool(production.migration_report.get('migration_ready')))}, "
        f"unified runtime {_status(bool(production.deployment_report.get('ready_for_unified_platform')))}, "
        f"artifact promotion {_status(bool(production.deployment_report.get('ready_for_release_promotion')))}, "
        f"terraform {_status(bool(production.deployment_report.get('ready_for_terraform')))}",
        "",
        *_render_category_section(
            "## Shared Blockers",
            categories=BLOCKER_CATEGORIES,
            staging=staging,
            production=production,
            mode="shared",
        ),
        *_render_category_section(
            "## Staging-Only Blockers",
            categories=BLOCKER_CATEGORIES,
            staging=staging,
            production=production,
            mode="staging",
        ),
        *_render_category_section(
            "## Production-Only Blockers",
            categories=BLOCKER_CATEGORIES,
            staging=staging,
            production=production,
            mode="production",
        ),
        "Refresh this summary after any runtime env, migration env, or deployment artifact change.",
        "",
    ]
    return "\n".join(lines)


def render_managed_release_blocker_summary(
    *,
    root: Path,
    staging_runtime_report_path: Path,
    staging_migration_report_path: Path,
    staging_deployment_report_path: Path,
    production_runtime_report_path: Path,
    production_migration_report_path: Path,
    production_deployment_report_path: Path,
    output_path: Path,
    allow_non_secret_artifact_bundle: bool = False,
) -> Path:
    repo_root = Path(root)
    staging = _verified_environment_reports(
        root=repo_root,
        environment="staging",
        runtime_report_path=staging_runtime_report_path,
        migration_report_path=staging_migration_report_path,
        deployment_report_path=staging_deployment_report_path,
        allow_non_secret_artifact_bundle=allow_non_secret_artifact_bundle,
    )
    production = _verified_environment_reports(
        root=repo_root,
        environment="production",
        runtime_report_path=production_runtime_report_path,
        migration_report_path=production_migration_report_path,
        deployment_report_path=production_deployment_report_path,
        allow_non_secret_artifact_bundle=allow_non_secret_artifact_bundle,
    )
    protected_paths = protected_output_paths_from_root(
        repo_root,
        __file__,
        ".runtime/deploy/staging/operator-handoff.md",
        ".runtime/deploy/production/operator-handoff.md",
    )
    resolved_output = resolve_output_path_from_root(
        repo_root,
        output_path,
        field_name="output_path",
        protected_paths=protected_paths,
        protected_error="output_path must not overwrite protected generated handoffs or source files",
    )
    ensure_parent_dir(resolved_output, field_name="output_path")
    content = _render_summary_markdown(staging=staging, production=production)
    staged_path = stage_text_file(resolved_output, content)
    promote_staged_file(staged_path, resolved_output, cleanup_output_on_failure=True)
    return resolved_output


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Render a cross-environment blocker summary from the verified staging "
            "and production managed deployment reports."
        )
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=_repo_root(),
        help="Repository root to resolve relative paths against.",
    )
    parser.add_argument(
        "--staging-runtime-report",
        type=Path,
        default=_default_runtime_report("staging"),
    )
    parser.add_argument(
        "--staging-migration-report",
        type=Path,
        default=_default_migration_report("staging"),
    )
    parser.add_argument(
        "--staging-deployment-report",
        type=Path,
        default=_default_deployment_report("staging"),
    )
    parser.add_argument(
        "--production-runtime-report",
        type=Path,
        default=_default_runtime_report("production"),
    )
    parser.add_argument(
        "--production-migration-report",
        type=Path,
        default=_default_migration_report("production"),
    )
    parser.add_argument(
        "--production-deployment-report",
        type=Path,
        default=_default_deployment_report("production"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".runtime/deploy/managed-release-blockers.md"),
    )
    parser.add_argument(
        "--non-secret-deployment-bundle",
        action="store_true",
        help=(
            "Verify staging and production inputs as downloaded non-secret deployment "
            "artifact bundles instead of requiring the full secret-bearing deploy workspace."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = resolve_cli_path_from_root(_repo_root(), args.root, field_name="root")
    try:
        rendered_path = render_managed_release_blocker_summary(
            root=root,
            staging_runtime_report_path=args.staging_runtime_report,
            staging_migration_report_path=args.staging_migration_report,
            staging_deployment_report_path=args.staging_deployment_report,
            production_runtime_report_path=args.production_runtime_report,
            production_migration_report_path=args.production_migration_report,
            production_deployment_report_path=args.production_deployment_report,
            output_path=args.output,
            allow_non_secret_artifact_bundle=bool(args.non_secret_deployment_bundle),
        )
    except (OSError, ValueError) as exc:
        print(f"[managed-release-blocker-summary] FAILED: {exc}")
        return 1
    print(f"[managed-release-blocker-summary] ok output={rendered_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
