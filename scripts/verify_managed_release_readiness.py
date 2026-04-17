#!/usr/bin/env python3
"""Run the managed release readiness gates as one operator-facing command."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
from typing import Callable
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import (
    parse_env_file,
    repo_root_for,
    resolve_cli_path_from_root,
    resolve_contained_repo_path_from_root,
)
from scripts.run_public_frontend_quality_gate import run_public_frontend_quality_gate
from scripts.verify_codebase_audit_report import verify_audit_report
from scripts.verify_dashboard_runtime_contract import verify_dashboard_runtime_contract
from scripts.verify_managed_deployment_bundle import verify_managed_deployment_bundle


DEFAULT_ROOT = repo_root_for(__file__)
SUPPORTED_ENVIRONMENTS = ("staging", "production")

DashboardRuntimeVerifier = Callable[..., list[str]]
BundleVerifier = Callable[..., list[str]]
PublicQualityRunner = Callable[..., None]
AuditReportVerifier = Callable[..., list[str]]
MANAGED_RELEASE_GATE_ERRORS = (
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
    subprocess.SubprocessError,
)


def _run_list_gate(
    gate_name: str,
    runner: Callable[..., list[str]],
    **kwargs: object,
) -> list[str]:
    try:
        return runner(**kwargs)
    except MANAGED_RELEASE_GATE_ERRORS as exc:  # pragma: no cover - defensive boundary
        return [f"{gate_name} failed unexpectedly: {exc}"]


def _default_report_path(environment: str, kind: str) -> Path:
    if kind == "audit":
        return Path(".runtime") / f"{environment}.audit.report.json"
    if kind == "runtime":
        return Path(".runtime") / f"{environment}.report.json"
    if kind == "migration":
        return Path(".runtime") / f"{environment}.migrate.report.json"
    if kind == "deployment":
        return Path(".runtime/deploy") / environment / "deployment.report.json"
    raise ValueError(f"unsupported report kind: {kind}")


def _is_placeholder_value(value: str) -> bool:
    normalized = str(value or "").strip()
    return not normalized or "REPLACE_WITH_" in normalized


def _derive_dashboard_url_from_runtime_report(
    *,
    repo_root: Path,
    runtime_report_path: Path,
) -> str | None:
    try:
        payload = json.loads(runtime_report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None

    resolved_public_runtime_values = payload.get("resolved_public_runtime_values")
    if isinstance(resolved_public_runtime_values, dict):
        frontend_url = str(
            resolved_public_runtime_values.get("FRONTEND_URL", "")
        ).strip()
        if not _is_placeholder_value(frontend_url):
            parsed = urlparse(frontend_url)
            if parsed.scheme in {"http", "https"} and parsed.netloc:
                return frontend_url

    output_path = payload.get("output_path")
    if not isinstance(output_path, str) or not output_path.strip():
        return None

    try:
        runtime_env_path = resolve_contained_repo_path_from_root(
            repo_root,
            output_path,
            field_name="runtime_report.output_path",
        )
    except ValueError:
        return None
    if not runtime_env_path.exists() or not runtime_env_path.is_file():
        return None

    frontend_url = parse_env_file(runtime_env_path).get("FRONTEND_URL", "").strip()
    if _is_placeholder_value(frontend_url):
        return None

    parsed = urlparse(frontend_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None
    return frontend_url


def verify_managed_release_readiness(
    *,
    environment: str,
    root: Path = DEFAULT_ROOT,
    audit_report_path: Path | None = None,
    runtime_report_path: Path | None = None,
    migration_report_path: Path | None = None,
    deployment_report_path: Path | None = None,
    dashboard_url: str | None = None,
    skip_dashboard_runtime: bool = False,
    reuse_built_dashboard_runtime: bool = False,
    skip_public_browser: bool = False,
    skip_webserver: bool = False,
    allow_non_secret_artifact_bundle: bool = False,
    audit_report_verifier: AuditReportVerifier = verify_audit_report,
    dashboard_runtime_verifier: DashboardRuntimeVerifier = verify_dashboard_runtime_contract,
    bundle_verifier: BundleVerifier = verify_managed_deployment_bundle,
    public_quality_runner: PublicQualityRunner = run_public_frontend_quality_gate,
) -> list[str]:
    normalized_environment = str(environment or "").strip().lower()
    if normalized_environment not in SUPPORTED_ENVIRONMENTS:
        raise ValueError(
            "environment must be one of: " + ", ".join(SUPPORTED_ENVIRONMENTS)
        )

    repo_root = Path(root)
    audit_report = resolve_cli_path_from_root(
        repo_root,
        audit_report_path or _default_report_path(normalized_environment, "audit"),
        field_name="audit_report_path",
    )
    runtime_report = resolve_cli_path_from_root(
        repo_root,
        runtime_report_path or _default_report_path(normalized_environment, "runtime"),
        field_name="runtime_report_path",
    )
    migration_report = resolve_cli_path_from_root(
        repo_root,
        migration_report_path
        or _default_report_path(normalized_environment, "migration"),
        field_name="migration_report_path",
    )
    deployment_report = resolve_cli_path_from_root(
        repo_root,
        deployment_report_path
        or _default_report_path(normalized_environment, "deployment"),
        field_name="deployment_report_path",
    )

    errors: list[str] = []

    errors.extend(
        _run_list_gate(
            "codebase audit verification",
            audit_report_verifier,
            root=repo_root,
            report_path=audit_report,
            enforce_live_measured_facts=True,
        )
    )

    normalized_dashboard_url = str(dashboard_url or "").strip()
    if not normalized_dashboard_url and not skip_public_browser:
        derived_dashboard_url = _derive_dashboard_url_from_runtime_report(
            repo_root=repo_root,
            runtime_report_path=runtime_report,
        )
        if derived_dashboard_url:
            normalized_dashboard_url = derived_dashboard_url
    parsed_dashboard_url = (
        urlparse(normalized_dashboard_url) if normalized_dashboard_url else None
    )
    dashboard_host = (
        (parsed_dashboard_url.hostname or "").strip().lower()
        if parsed_dashboard_url
        else ""
    )

    if (
        not skip_dashboard_runtime
        and skip_webserver
        and dashboard_host in {"127.0.0.1", "localhost"}
        and not reuse_built_dashboard_runtime
    ):
        errors.append(
            "reuse_built_dashboard_runtime is required when using --skip-webserver "
            "with a local dashboard_url because rebuilding invalidates the live preview assets."
        )
        return errors

    if not skip_dashboard_runtime:
        errors.extend(
            _run_list_gate(
                "dashboard runtime contract verification",
                dashboard_runtime_verifier,
                root=repo_root,
                build=not reuse_built_dashboard_runtime,
            )
        )

    errors.extend(
        _run_list_gate(
            "managed deployment bundle verification",
            bundle_verifier,
            environment=normalized_environment,
            runtime_report_path=runtime_report,
            migration_report_path=migration_report,
            deployment_report_path=deployment_report,
            allow_non_secret_artifact_bundle=allow_non_secret_artifact_bundle,
        )
    )

    if skip_public_browser:
        return errors

    if not normalized_dashboard_url:
        errors.append(
            "dashboard_url is required unless --skip-public-browser is used, or "
            "FRONTEND_URL is set to a live http(s) value in the managed runtime env."
        )
        return errors

    try:
        public_quality_runner(
            dashboard_url=normalized_dashboard_url,
            skip_webserver=skip_webserver,
        )
    except subprocess.CalledProcessError as exc:
        errors.append(
            "public frontend quality gate failed: "
            f"command={exc.cmd!r} returncode={exc.returncode}"
        )

    return errors


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the managed release readiness gates: codebase audit verification, "
            "dashboard runtime contract, deployment bundle verification, and optionally "
            "the public browser gate."
        )
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=SUPPORTED_ENVIRONMENTS,
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repository root to verify.",
    )
    parser.add_argument(
        "--audit-report",
        type=Path,
        default=None,
        help="Override codebase audit report path.",
    )
    parser.add_argument(
        "--runtime-report",
        type=Path,
        default=None,
        help="Override runtime report path.",
    )
    parser.add_argument(
        "--migration-report",
        type=Path,
        default=None,
        help="Override migration report path.",
    )
    parser.add_argument(
        "--deployment-report",
        type=Path,
        default=None,
        help="Override deployment report path.",
    )
    parser.add_argument(
        "--dashboard-url",
        default=None,
        help=(
            "Deployed dashboard URL for the public browser gate. Optional when the "
            "managed runtime env already contains a live FRONTEND_URL."
        ),
    )
    parser.add_argument(
        "--skip-dashboard-runtime",
        action="store_true",
        help="Skip the dashboard container runtime contract verification.",
    )
    parser.add_argument(
        "--reuse-built-dashboard-runtime",
        action="store_true",
        help=(
            "Verify the dashboard runtime contract against existing build artifacts instead "
            "of rebuilding first. Required when reusing a local vite preview URL."
        ),
    )
    parser.add_argument(
        "--skip-public-browser",
        action="store_true",
        help="Skip the public browser quality gate.",
    )
    parser.add_argument(
        "--skip-webserver",
        action="store_true",
        help="Pass through to the public browser gate to reuse an existing dashboard URL.",
    )
    parser.add_argument(
        "--non-secret-deployment-bundle",
        action="store_true",
        help=(
            "Verify the downloaded non-secret deployment artifact bundle instead of "
            "requiring the full secret-bearing deploy workspace."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = resolve_cli_path_from_root(DEFAULT_ROOT, args.root, field_name="root")
    errors = verify_managed_release_readiness(
        environment=args.environment,
        root=root,
        audit_report_path=args.audit_report,
        runtime_report_path=args.runtime_report,
        migration_report_path=args.migration_report,
        deployment_report_path=args.deployment_report,
        dashboard_url=args.dashboard_url,
        skip_dashboard_runtime=bool(args.skip_dashboard_runtime),
        reuse_built_dashboard_runtime=bool(args.reuse_built_dashboard_runtime),
        skip_public_browser=bool(args.skip_public_browser),
        skip_webserver=bool(args.skip_webserver),
        allow_non_secret_artifact_bundle=bool(args.non_secret_deployment_bundle),
    )
    if errors:
        print("[managed-release-readiness] FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("[managed-release-readiness] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
