#!/usr/bin/env python3
"""Verify that managed runtime, migration, and deployment artifacts stay coherent."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import parse_env_file
from scripts.generate_managed_deployment_artifacts import (
    _placeholder_keys,
    _runtime_blockers,
)
from scripts.generate_managed_migration_env import (
    _migration_blockers,
    _required_operator_input_keys as _migration_required_operator_input_keys,
)
from scripts.generate_managed_runtime_env import (
    DECLARED_EXTERNAL_VALUE_KEYS,
    RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS,
    _identify_unresolved_keys,
    _required_operator_input_keys as _runtime_required_operator_input_keys,
)


SUPPORTED_ENVIRONMENTS = ("staging", "production")
EXPECTED_DEPLOYMENT_ARTIFACT_KEYS = (
    "koyeb_api_manifest",
    "koyeb_worker_manifest",
    "koyeb_secret_payload",
    "helm_values",
    "helm_runtime_secret_json",
)


def _normalize_path(path_value: str | Path, *, base_dir: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected JSON object in {path.as_posix()}.")
    return payload


def _sorted_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def _expect(condition: bool, message: str, *, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def verify_managed_deployment_bundle(
    *,
    environment: str,
    runtime_report_path: Path,
    migration_report_path: Path,
    deployment_report_path: Path,
) -> list[str]:
    normalized_environment = str(environment or "").strip().lower()
    if normalized_environment not in SUPPORTED_ENVIRONMENTS:
        raise ValueError(
            "environment must be one of: " + ", ".join(SUPPORTED_ENVIRONMENTS)
        )

    errors: list[str] = []

    for label, path in (
        ("runtime report", runtime_report_path),
        ("migration report", migration_report_path),
        ("deployment report", deployment_report_path),
    ):
        _expect(path.exists(), f"missing {label}: {path.as_posix()}", errors=errors)
    if errors:
        return errors

    runtime_report = _load_json(runtime_report_path)
    migration_report = _load_json(migration_report_path)
    deployment_report = _load_json(deployment_report_path)

    for label, report, report_path in (
        ("runtime", runtime_report, runtime_report_path),
        ("migration", migration_report, migration_report_path),
        ("deployment", deployment_report, deployment_report_path),
    ):
        report_environment = str(report.get("environment", "") or "").strip().lower()
        _expect(
            report_environment == normalized_environment,
            (
                f"{label} report environment mismatch: "
                f"expected {normalized_environment!r}, got {report_environment!r} "
                f"({report_path.as_posix()})"
            ),
            errors=errors,
        )

    runtime_env_path = _normalize_path(
        runtime_report.get("output_path", ""),
        base_dir=runtime_report_path.parent,
    )
    migration_env_path = _normalize_path(
        migration_report.get("output_path", ""),
        base_dir=migration_report_path.parent,
    )
    deployment_runtime_env_path = _normalize_path(
        deployment_report.get("runtime_env_file", ""),
        base_dir=deployment_report_path.parent,
    )
    deployment_output_dir = _normalize_path(
        deployment_report.get("output_dir", ""),
        base_dir=deployment_report_path.parent,
    )

    report_consistency_error_count = len(errors)
    _expect(
        runtime_env_path.exists(),
        f"missing runtime env file: {runtime_env_path.as_posix()}",
        errors=errors,
    )
    _expect(
        migration_env_path.exists(),
        f"missing migration env file: {migration_env_path.as_posix()}",
        errors=errors,
    )
    _expect(
        deployment_runtime_env_path.exists(),
        f"missing deployment runtime env file: {deployment_runtime_env_path.as_posix()}",
        errors=errors,
    )
    _expect(
        deployment_output_dir.exists(),
        f"missing deployment output dir: {deployment_output_dir.as_posix()}",
        errors=errors,
    )
    _expect(
        deployment_runtime_env_path.resolve() == runtime_env_path.resolve(),
        (
            "deployment report runtime_env_file must match runtime report output_path: "
            f"{deployment_runtime_env_path.as_posix()} != {runtime_env_path.as_posix()}"
        ),
        errors=errors,
    )
    _expect(
        deployment_output_dir.resolve() == deployment_report_path.parent.resolve(),
        (
            "deployment report output_dir must match deployment report parent directory: "
            f"{deployment_output_dir.as_posix()} != {deployment_report_path.parent.as_posix()}"
        ),
        errors=errors,
    )

    if len(errors) > report_consistency_error_count:
        return errors

    runtime_values = parse_env_file(runtime_env_path)
    migration_values = parse_env_file(migration_env_path)
    _expect(
        str(runtime_values.get("ENVIRONMENT", "")).strip().lower() == normalized_environment,
        (
            f"runtime env ENVIRONMENT mismatch in {runtime_env_path.as_posix()}: "
            f"expected {normalized_environment!r}"
        ),
        errors=errors,
    )
    _expect(
        str(migration_values.get("ENVIRONMENT", "")).strip().lower() == normalized_environment,
        (
            f"migration env ENVIRONMENT mismatch in {migration_env_path.as_posix()}: "
            f"expected {normalized_environment!r}"
        ),
        errors=errors,
    )

    expected_runtime_blockers = _identify_unresolved_keys(
        runtime_values,
        RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS,
    )
    expected_runtime_declared = _identify_unresolved_keys(
        runtime_values,
        DECLARED_EXTERNAL_VALUE_KEYS,
    )
    expected_runtime_required = _runtime_required_operator_input_keys(runtime_values)

    _expect(
        _sorted_strings(runtime_report.get("runtime_validation_blockers"))
        == expected_runtime_blockers,
        (
            "runtime report blockers drift from runtime env: "
            f"expected {expected_runtime_blockers!r}, "
            f"got {_sorted_strings(runtime_report.get('runtime_validation_blockers'))!r}"
        ),
        errors=errors,
    )
    _expect(
        _sorted_strings(runtime_report.get("declared_external_placeholders"))
        == expected_runtime_declared,
        (
            "runtime report declared placeholders drift from runtime env: "
            f"expected {expected_runtime_declared!r}, "
            f"got {_sorted_strings(runtime_report.get('declared_external_placeholders'))!r}"
        ),
        errors=errors,
    )
    _expect(
        _sorted_strings(runtime_report.get("unresolved_external_keys"))
        == expected_runtime_declared,
        (
            "runtime report unresolved_external_keys drift from runtime env: "
            f"expected {expected_runtime_declared!r}, "
            f"got {_sorted_strings(runtime_report.get('unresolved_external_keys'))!r}"
        ),
        errors=errors,
    )
    _expect(
        _sorted_strings(runtime_report.get("required_operator_input_keys"))
        == expected_runtime_required,
        (
            "runtime report required_operator_input_keys drift from runtime env: "
            f"expected {expected_runtime_required!r}, "
            f"got {_sorted_strings(runtime_report.get('required_operator_input_keys'))!r}"
        ),
        errors=errors,
    )
    _expect(
        bool(runtime_report.get("validation_ready")) == (not expected_runtime_blockers),
        "runtime report validation_ready does not match runtime blockers",
        errors=errors,
    )

    expected_migration_blockers = _migration_blockers(migration_values)
    expected_migration_required = _migration_required_operator_input_keys(migration_values)
    _expect(
        _sorted_strings(migration_report.get("migration_validation_blockers"))
        == expected_migration_blockers,
        (
            "migration report blockers drift from migration env: "
            f"expected {expected_migration_blockers!r}, "
            f"got {_sorted_strings(migration_report.get('migration_validation_blockers'))!r}"
        ),
        errors=errors,
    )
    _expect(
        _sorted_strings(migration_report.get("required_operator_input_keys"))
        == expected_migration_required,
        (
            "migration report required_operator_input_keys drift from migration env: "
            f"expected {expected_migration_required!r}, "
            f"got {_sorted_strings(migration_report.get('required_operator_input_keys'))!r}"
        ),
        errors=errors,
    )
    _expect(
        bool(migration_report.get("migration_ready")) == (not expected_migration_blockers),
        "migration report migration_ready does not match migration blockers",
        errors=errors,
    )

    allowed_migration_only_keys = {"DB_SSL_CA_CERT_PATH"}
    _expect(
        set(expected_migration_blockers).issubset(
            set(expected_runtime_blockers) | allowed_migration_only_keys
        ),
        (
            "migration blockers must be explained by runtime blockers or DB_SSL_CA_CERT_PATH: "
            f"{expected_migration_blockers!r} vs {expected_runtime_blockers!r}"
        ),
        errors=errors,
    )

    expected_deployment_blockers = _runtime_blockers(runtime_values)
    _expect(
        _sorted_strings(deployment_report.get("runtime_validation_blockers"))
        == expected_deployment_blockers,
        (
            "deployment report runtime blockers drift from runtime env: "
            f"expected {expected_deployment_blockers!r}, "
            f"got {_sorted_strings(deployment_report.get('runtime_validation_blockers'))!r}"
        ),
        errors=errors,
    )
    _expect(
        expected_deployment_blockers == expected_runtime_blockers,
        (
            "runtime and deployment blocker models disagree: "
            f"{expected_runtime_blockers!r} != {expected_deployment_blockers!r}"
        ),
        errors=errors,
    )

    artifacts = deployment_report.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("deployment report artifacts must be a JSON object")
        return errors
    for artifact_key in EXPECTED_DEPLOYMENT_ARTIFACT_KEYS:
        artifact_path = artifacts.get(artifact_key)
        _expect(
            bool(artifact_path),
            f"deployment report missing artifact path for {artifact_key}",
            errors=errors,
        )
        if artifact_path:
            resolved = _normalize_path(str(artifact_path), base_dir=deployment_report_path.parent)
            _expect(
                resolved.exists(),
                f"deployment artifact missing on disk: {resolved.as_posix()}",
                errors=errors,
            )

    terraform_tfvars_path = _normalize_path(
        deployment_report.get("terraform_runtime_tfvars_path", ""),
        base_dir=deployment_report_path.parent,
    )
    _expect(
        terraform_tfvars_path.exists(),
        f"missing terraform runtime tfvars: {terraform_tfvars_path.as_posix()}",
        errors=errors,
    )
    if errors:
        return errors

    koyeb_secret_payload_path = _normalize_path(
        str(artifacts["koyeb_secret_payload"]),
        base_dir=deployment_report_path.parent,
    )
    helm_secret_payload_path = _normalize_path(
        str(artifacts["helm_runtime_secret_json"]),
        base_dir=deployment_report_path.parent,
    )

    koyeb_secret_payload = _load_json(koyeb_secret_payload_path)
    helm_secret_payload = _load_json(helm_secret_payload_path)
    terraform_tfvars_payload = _load_json(terraform_tfvars_path)

    expected_koyeb_blockers = _placeholder_keys(
        {str(key): str(value) for key, value in koyeb_secret_payload.items()}
    )
    expected_helm_blockers = _placeholder_keys(
        {str(key): str(value) for key, value in helm_secret_payload.items()}
    )

    _expect(
        _sorted_strings(deployment_report.get("koyeb_secret_names"))
        == sorted(str(key) for key in koyeb_secret_payload),
        "deployment report koyeb_secret_names drift from generated secret payload",
        errors=errors,
    )
    _expect(
        _sorted_strings(deployment_report.get("helm_runtime_secret_keys"))
        == sorted(str(key) for key in helm_secret_payload),
        "deployment report helm_runtime_secret_keys drift from generated runtime secret payload",
        errors=errors,
    )
    _expect(
        _sorted_strings(deployment_report.get("koyeb_secret_value_blockers"))
        == expected_koyeb_blockers,
        (
            "deployment report koyeb_secret_value_blockers drift from generated secret payload: "
            f"expected {expected_koyeb_blockers!r}, "
            f"got {_sorted_strings(deployment_report.get('koyeb_secret_value_blockers'))!r}"
        ),
        errors=errors,
    )
    _expect(
        _sorted_strings(deployment_report.get("helm_runtime_secret_value_blockers"))
        == expected_helm_blockers,
        (
            "deployment report helm_runtime_secret_value_blockers drift from generated runtime secret payload: "
            f"expected {expected_helm_blockers!r}, "
            f"got {_sorted_strings(deployment_report.get('helm_runtime_secret_value_blockers'))!r}"
        ),
        errors=errors,
    )
    _expect(
        bool(deployment_report.get("ready_for_koyeb"))
        == (not expected_deployment_blockers and not expected_koyeb_blockers),
        "deployment report ready_for_koyeb does not match blockers",
        errors=errors,
    )
    _expect(
        bool(deployment_report.get("ready_for_helm"))
        == (not expected_deployment_blockers and not expected_helm_blockers),
        "deployment report ready_for_helm does not match blockers",
        errors=errors,
    )

    expected_terraform_environment = "prod" if normalized_environment == "production" else normalized_environment
    _expect(
        str(terraform_tfvars_payload.get("environment", "") or "").strip().lower()
        == expected_terraform_environment,
        (
            "terraform runtime tfvars environment mismatch: "
            f"expected {expected_terraform_environment!r}"
        ),
        errors=errors,
    )

    return errors


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that managed runtime, migration, and deployment artifacts "
            "for an environment are mutually coherent and ready for operator review."
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    environment = str(args.environment)
    runtime_report = args.runtime_report or Path(".runtime") / f"{environment}.report.json"
    migration_report = args.migration_report or Path(".runtime") / f"{environment}.migrate.report.json"
    deployment_report = (
        args.deployment_report
        or Path(".runtime/deploy") / environment / "deployment.report.json"
    )

    errors = verify_managed_deployment_bundle(
        environment=environment,
        runtime_report_path=runtime_report.resolve(),
        migration_report_path=migration_report.resolve(),
        deployment_report_path=deployment_report.resolve(),
    )
    if errors:
        print("Managed deployment bundle verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "[managed-deployment-bundle] ok "
        f"environment={environment} "
        f"runtime_report={runtime_report.resolve().as_posix()} "
        f"migration_report={migration_report.resolve().as_posix()} "
        f"deployment_report={deployment_report.resolve().as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
