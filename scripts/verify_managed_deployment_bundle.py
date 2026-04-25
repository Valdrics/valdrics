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

from scripts.env_generation_common import (
    parse_env_file,
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)
from scripts.generate_managed_deployment_artifacts import (
    _artifact_output_paths,
    _is_valid_promotion_ref,
    _json_placeholder_blockers,
    _placeholder_keys,
    _runtime_blockers,
    _terraform_remaining_inputs,
)
from scripts.generate_managed_migration_env import _migration_blockers
from scripts.generate_managed_runtime_env import (
    DECLARED_EXTERNAL_VALUE_KEYS,
    RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS,
)
from scripts.managed_deployment_contract import (
    SUPPORTED_ENVIRONMENTS,
    identify_runtime_unresolved_keys as _identify_unresolved_keys,
    required_migration_operator_input_keys as _migration_required_operator_input_keys,
    required_runtime_operator_input_keys as _runtime_required_operator_input_keys,
)
from scripts.verify_technology_value_contract import (
    TechnologyValueContractVerificationError,
    verify_contract_and_receipts,
)

EXPECTED_DEPLOYMENT_ARTIFACT_KEYS = (
    "unified_platform_manifest",
    "secret_manager_runtime_secrets",
    "cloudflare_pages_env_json",
    "artifact_registry_release_metadata",
    "terraform_runtime_tfvars",
    "technology_value_receipt_json",
    "operator_handoff_markdown",
)
NON_SECRET_RELEASE_ARTIFACT_KEYS = (
    "unified_platform_manifest",
    "cloudflare_pages_env_json",
    "artifact_registry_release_metadata",
    "technology_value_receipt_json",
    "operator_handoff_markdown",
)
FULL_BUNDLE_ARTIFACT_KEYS_REQUIRED_ON_DISK = (
    "unified_platform_manifest",
    "secret_manager_runtime_secrets",
    "cloudflare_pages_env_json",
    "artifact_registry_release_metadata",
    "terraform_runtime_tfvars",
    "technology_value_receipt_json",
)
EXPECTED_DEPLOYMENT_ARTIFACT_FILENAMES = {
    artifact_key: artifact_path.name
    for artifact_key, artifact_path in zip(
        EXPECTED_DEPLOYMENT_ARTIFACT_KEYS,
        (
            *_artifact_output_paths(Path("/tmp/verify-managed-deployment-bundle"))[:5],
            Path("/tmp/verify-managed-deployment-bundle/technology-value-admission-receipt.json"),
            Path("/tmp/verify-managed-deployment-bundle/operator-handoff.md"),
        ),
        strict=True,
    )
}


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_report_path(path: Path) -> Path:
    resolved = resolve_cli_path_from_root(_repo_root(), path, field_name="report paths")
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"report paths must be file paths: {resolved}")
    return resolved


def _normalize_path(path_value: str | Path, *, base_dir: Path) -> Path:
    path = Path(path_value)
    if not path.is_absolute():
        path = (base_dir / path).resolve()
    return path


def _path_within(path: Path, *, base_dir: Path) -> bool:
    try:
        path.resolve().relative_to(base_dir.resolve())
    except ValueError:
        return False
    return True


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
    allow_non_secret_artifact_bundle: bool = False,
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
    technology_value_contract_path = resolve_cli_path_from_root(
        _repo_root(),
        Path(str(deployment_report.get("technology_value_contract_path", ""))),
        field_name="technology_value_contract_path",
    )
    deployment_output_dir = _normalize_path(
        deployment_report.get("output_dir", ""),
        base_dir=deployment_report_path.parent,
    )

    report_consistency_error_count = len(errors)
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
    if not allow_non_secret_artifact_bundle:
        _expect(
            deployment_runtime_env_path.exists(),
            (
                "missing deployment runtime env file: "
                f"{deployment_runtime_env_path.as_posix()}"
            ),
            errors=errors,
        )
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

    if len(errors) > report_consistency_error_count:
        return errors

    if allow_non_secret_artifact_bundle:
        expected_runtime_blockers = _sorted_strings(
            runtime_report.get("runtime_validation_blockers")
        )
        expected_runtime_declared = _sorted_strings(
            runtime_report.get("declared_external_placeholders")
        )
        expected_runtime_required = _sorted_strings(
            runtime_report.get("required_operator_input_keys")
        )
        _expect(
            _sorted_strings(runtime_report.get("unresolved_external_keys"))
            == expected_runtime_declared,
            "runtime report unresolved_external_keys must match declared_external_placeholders",
            errors=errors,
        )
        _expect(
            set(expected_runtime_blockers).issubset(set(expected_runtime_required)),
            "runtime report runtime_validation_blockers must stay within required_operator_input_keys",
            errors=errors,
        )
        _expect(
            bool(runtime_report.get("validation_ready"))
            == (not expected_runtime_blockers),
            "runtime report validation_ready does not match runtime blockers",
            errors=errors,
        )
        _expect(
            not expected_runtime_blockers,
            (
                "runtime report still contains unresolved runtime_validation_blockers "
                f"in the non-secret release artifact bundle: {expected_runtime_blockers!r}"
            ),
            errors=errors,
        )

        expected_migration_blockers = _sorted_strings(
            migration_report.get("migration_validation_blockers")
        )
        expected_migration_required = _sorted_strings(
            migration_report.get("required_operator_input_keys")
        )
        _expect(
            set(expected_migration_blockers).issubset(set(expected_migration_required)),
            "migration report migration_validation_blockers must stay within required_operator_input_keys",
            errors=errors,
        )
        _expect(
            bool(migration_report.get("migration_ready"))
            == (not expected_migration_blockers),
            "migration report migration_ready does not match migration blockers",
            errors=errors,
        )
        _expect(
            not expected_migration_blockers,
            (
                "migration report still contains unresolved migration_validation_blockers "
                f"in the non-secret release artifact bundle: {expected_migration_blockers!r}"
            ),
            errors=errors,
        )

        expected_deployment_blockers = expected_runtime_blockers
        _expect(
            _sorted_strings(deployment_report.get("runtime_validation_blockers"))
            == expected_deployment_blockers,
            (
                "deployment report runtime blockers drift from runtime report: "
                f"expected {expected_deployment_blockers!r}, "
                f"got {_sorted_strings(deployment_report.get('runtime_validation_blockers'))!r}"
            ),
            errors=errors,
        )
    else:
        runtime_values = parse_env_file(runtime_env_path)
        migration_values = parse_env_file(migration_env_path)
        _expect(
            str(runtime_values.get("ENVIRONMENT", "")).strip().lower()
            == normalized_environment,
            (
                f"runtime env ENVIRONMENT mismatch in {runtime_env_path.as_posix()}: "
                f"expected {normalized_environment!r}"
            ),
            errors=errors,
        )
        _expect(
            str(migration_values.get("ENVIRONMENT", "")).strip().lower()
            == normalized_environment,
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
        expected_runtime_required = _runtime_required_operator_input_keys(
            runtime_values
        )

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
            bool(runtime_report.get("validation_ready"))
            == (not expected_runtime_blockers),
            "runtime report validation_ready does not match runtime blockers",
            errors=errors,
        )

        expected_migration_blockers = _migration_blockers(migration_values)
        expected_migration_required = _migration_required_operator_input_keys(
            migration_values
        )
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
            bool(migration_report.get("migration_ready"))
            == (not expected_migration_blockers),
            "migration report migration_ready does not match migration blockers",
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

    artifacts = deployment_report.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append("deployment report artifacts must be a JSON object")
        return errors

    seen_artifact_paths: dict[Path, str] = {}
    artifact_keys_required_on_disk = (
        FULL_BUNDLE_ARTIFACT_KEYS_REQUIRED_ON_DISK
        if not allow_non_secret_artifact_bundle
        else NON_SECRET_RELEASE_ARTIFACT_KEYS
    )
    for artifact_key in EXPECTED_DEPLOYMENT_ARTIFACT_KEYS:
        artifact_path = artifacts.get(artifact_key)
        _expect(
            bool(artifact_path),
            f"deployment report missing artifact path for {artifact_key}",
            errors=errors,
        )
        if artifact_path:
            resolved = _normalize_path(
                str(artifact_path),
                base_dir=deployment_report_path.parent,
            )
            previous_key = seen_artifact_paths.get(resolved)
            _expect(
                previous_key is None,
                (
                    "deployment artifact paths must be distinct: "
                    f"{artifact_key} collides with {previous_key} at {resolved.as_posix()}"
                ),
                errors=errors,
            )
            seen_artifact_paths.setdefault(resolved, artifact_key)
            _expect(
                _path_within(resolved, base_dir=deployment_output_dir),
                (
                    "deployment artifact path must stay within deployment output_dir: "
                    f"{resolved.as_posix()} not under {deployment_output_dir.as_posix()}"
                ),
                errors=errors,
            )
            _expect(
                resolved.name == EXPECTED_DEPLOYMENT_ARTIFACT_FILENAMES[artifact_key],
                (
                    "deployment artifact path has unexpected filename for "
                    f"{artifact_key}: {resolved.name!r} != "
                    f"{EXPECTED_DEPLOYMENT_ARTIFACT_FILENAMES[artifact_key]!r}"
                ),
                errors=errors,
            )
            _expect(
                resolved.exists() or artifact_key not in artifact_keys_required_on_disk,
                (
                    f"deployment artifact missing on disk: {resolved.as_posix()}"
                    if artifact_key in artifact_keys_required_on_disk
                    else (
                        "deployment artifact path is recorded but not present in the "
                        "non-secret release artifact bundle: "
                        f"{resolved.as_posix()}"
                    )
                ),
                errors=errors,
            )

    terraform_tfvars_path = _normalize_path(
        deployment_report.get("terraform_runtime_tfvars_path", ""),
        base_dir=deployment_report_path.parent,
    )
    _expect(
        _path_within(terraform_tfvars_path, base_dir=deployment_output_dir),
        (
            "terraform runtime tfvars must stay within deployment output_dir: "
            f"{terraform_tfvars_path.as_posix()} not under {deployment_output_dir.as_posix()}"
        ),
        errors=errors,
    )
    if not allow_non_secret_artifact_bundle:
        _expect(
            terraform_tfvars_path.exists(),
            f"missing terraform runtime tfvars: {terraform_tfvars_path.as_posix()}",
            errors=errors,
        )
    if errors:
        return errors

    unified_platform_manifest_path = _normalize_path(
        str(artifacts["unified_platform_manifest"]),
        base_dir=deployment_report_path.parent,
    )
    secret_manager_runtime_path = _normalize_path(
        str(artifacts["secret_manager_runtime_secrets"]),
        base_dir=deployment_report_path.parent,
    )
    cloudflare_pages_env_path = _normalize_path(
        str(artifacts["cloudflare_pages_env_json"]),
        base_dir=deployment_report_path.parent,
    )
    artifact_registry_release_path = _normalize_path(
        str(artifacts["artifact_registry_release_metadata"]),
        base_dir=deployment_report_path.parent,
    )
    technology_value_receipt_path = _normalize_path(
        str(artifacts["technology_value_receipt_json"]),
        base_dir=deployment_report_path.parent,
    )

    unified_platform_manifest = _load_json(unified_platform_manifest_path)
    cloudflare_pages_env = _load_json(cloudflare_pages_env_path)
    artifact_registry_release = _load_json(artifact_registry_release_path)
    _expect(
        str(unified_platform_manifest.get("environment", "") or "").strip().lower()
        == normalized_environment,
        (
            "unified platform manifest environment mismatch: "
            f"expected {normalized_environment!r}"
        ),
        errors=errors,
    )
    _expect(
        str(unified_platform_manifest.get("strategy", "") or "").strip()
        == "unified_platform_managed_release",
        "unified platform manifest strategy must be unified_platform_managed_release",
        errors=errors,
    )

    expected_cloudflare_blockers = _placeholder_keys(
        {str(key): str(value) for key, value in cloudflare_pages_env.items()}
    )
    expected_release_blockers = sorted(
        set(_json_placeholder_blockers(artifact_registry_release))
    )
    if allow_non_secret_artifact_bundle:
        expected_secret_keys = _sorted_strings(
            deployment_report.get("secret_manager_secret_keys")
        )
        expected_secret_blockers = _sorted_strings(
            deployment_report.get("secret_manager_secret_value_blockers")
        )
        expected_terraform_remaining_inputs = _sorted_strings(
            deployment_report.get("terraform_remaining_inputs")
        )
        expected_terraform_value_blockers = _sorted_strings(
            deployment_report.get("terraform_value_blockers")
        )
        _expect(
            bool(expected_secret_keys),
            "deployment report secret_manager_secret_keys must stay non-empty for the non-secret release artifact bundle",
            errors=errors,
        )
        _expect(
            not expected_secret_blockers,
            (
                "deployment report still contains secret_manager_secret_value_blockers "
                f"in the non-secret release artifact bundle: {expected_secret_blockers!r}"
            ),
            errors=errors,
        )
        _expect(
            not expected_terraform_remaining_inputs,
            (
                "deployment report still contains terraform_remaining_inputs "
                f"in the non-secret release artifact bundle: {expected_terraform_remaining_inputs!r}"
            ),
            errors=errors,
        )
        _expect(
            not expected_terraform_value_blockers,
            (
                "deployment report still contains terraform_value_blockers "
                f"in the non-secret release artifact bundle: {expected_terraform_value_blockers!r}"
            ),
            errors=errors,
        )
    else:
        secret_manager_runtime_payload = _load_json(secret_manager_runtime_path)
        terraform_tfvars_payload = _load_json(terraform_tfvars_path)
        expected_secret_blockers = _placeholder_keys(
            {
                str(key): str(value)
                for key, value in secret_manager_runtime_payload.items()
            }
        )
        expected_terraform_remaining_inputs = _terraform_remaining_inputs(
            terraform_tfvars_payload
        )
        expected_terraform_value_blockers = sorted(
            set(_json_placeholder_blockers(terraform_tfvars_payload))
        )

        _expect(
            _sorted_strings(deployment_report.get("secret_manager_secret_keys"))
            == sorted(str(key) for key in secret_manager_runtime_payload),
            "deployment report secret_manager_secret_keys drift from generated secret payload",
            errors=errors,
        )
        _expect(
            _sorted_strings(
                deployment_report.get("secret_manager_secret_value_blockers")
            )
            == expected_secret_blockers,
            (
                "deployment report secret_manager_secret_value_blockers drift from generated secret payload: "
                f"expected {expected_secret_blockers!r}, "
                f"got {_sorted_strings(deployment_report.get('secret_manager_secret_value_blockers'))!r}"
            ),
            errors=errors,
        )
    _expect(
        technology_value_contract_path.exists(),
        (
            "Technology Value Contract referenced by deployment report is missing: "
            f"{technology_value_contract_path.as_posix()}"
        ),
        errors=errors,
    )
    _expect(
        technology_value_contract_path.is_file(),
        (
            "Technology Value Contract referenced by deployment report must be a file: "
            f"{technology_value_contract_path.as_posix()}"
        ),
        errors=errors,
    )
    try:
        verify_contract_and_receipts(
            contract_path=technology_value_contract_path,
            receipt_paths=[technology_value_receipt_path],
        )
    except TechnologyValueContractVerificationError as exc:
        errors.append(f"technology value receipt verification failed: {exc}")
    _expect(
        _sorted_strings(deployment_report.get("cloudflare_pages_public_env_keys"))
        == sorted(str(key) for key in cloudflare_pages_env),
        "deployment report cloudflare_pages_public_env_keys drift from generated Cloudflare Pages env payload",
        errors=errors,
    )
    _expect(
        _sorted_strings(deployment_report.get("cloudflare_pages_public_env_blockers"))
        == expected_cloudflare_blockers,
        (
            "deployment report cloudflare_pages_public_env_blockers drift from generated Cloudflare Pages env payload: "
            f"expected {expected_cloudflare_blockers!r}, "
            f"got {_sorted_strings(deployment_report.get('cloudflare_pages_public_env_blockers'))!r}"
        ),
        errors=errors,
    )
    _expect(
        _sorted_strings(
            deployment_report.get("artifact_registry_release_value_blockers")
        )
        == expected_release_blockers,
        (
            "deployment report artifact_registry_release_value_blockers drift from generated Artifact Registry metadata: "
            f"expected {expected_release_blockers!r}, "
            f"got {_sorted_strings(deployment_report.get('artifact_registry_release_value_blockers'))!r}"
        ),
        errors=errors,
    )
    _expect(
        _sorted_strings(deployment_report.get("terraform_remaining_inputs"))
        == expected_terraform_remaining_inputs,
        (
            "deployment report terraform_remaining_inputs drift from generated Terraform tfvars: "
            f"expected {expected_terraform_remaining_inputs!r}, "
            f"got {_sorted_strings(deployment_report.get('terraform_remaining_inputs'))!r}"
        ),
        errors=errors,
    )
    _expect(
        _sorted_strings(deployment_report.get("terraform_value_blockers"))
        == expected_terraform_value_blockers,
        (
            "deployment report terraform_value_blockers drift from generated Terraform tfvars: "
            f"expected {expected_terraform_value_blockers!r}, "
            f"got {_sorted_strings(deployment_report.get('terraform_value_blockers'))!r}"
        ),
        errors=errors,
    )
    _expect(
        bool(deployment_report.get("ready_for_unified_platform"))
        == (
            not expected_deployment_blockers
            and not expected_secret_blockers
            and not expected_cloudflare_blockers
            and not expected_release_blockers
        ),
        "deployment report ready_for_unified_platform does not match blockers",
        errors=errors,
    )
    _expect(
        bool(deployment_report.get("ready_for_release_promotion"))
        == (
            not expected_release_blockers
            and _is_valid_promotion_ref(
                str(artifact_registry_release["services"]["api"]["promotion_ref"])
            )
            and _is_valid_promotion_ref(
                str(artifact_registry_release["services"]["batch"]["promotion_ref"])
            )
        ),
        "deployment report ready_for_release_promotion does not match blockers",
        errors=errors,
    )
    _expect(
        bool(deployment_report.get("ready_for_terraform"))
        == (not expected_terraform_value_blockers),
        "deployment report ready_for_terraform does not match blockers",
        errors=errors,
    )
    if not allow_non_secret_artifact_bundle:
        _expect(
            str(terraform_tfvars_payload.get("environment", "") or "").strip().lower()
            == normalized_environment,
            (
                "terraform runtime tfvars environment mismatch: "
                f"expected {normalized_environment!r}"
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
    try:
        runtime_report = _resolve_report_path(
            args.runtime_report or Path(".runtime") / f"{environment}.report.json"
        )
        migration_report = _resolve_report_path(
            args.migration_report
            or Path(".runtime") / f"{environment}.migrate.report.json"
        )
        deployment_report = _resolve_report_path(
            args.deployment_report
            or Path(".runtime/deploy") / environment / "deployment.report.json"
        )
    except ValueError as exc:
        print(f"[managed-deployment-bundle] failed: {exc}")
        return 2

    errors = verify_managed_deployment_bundle(
        environment=environment,
        runtime_report_path=runtime_report,
        migration_report_path=migration_report,
        deployment_report_path=deployment_report,
    )
    if errors:
        print("Managed deployment bundle verification failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(
        "[managed-deployment-bundle] ok "
        f"environment={environment} "
        f"runtime_report={runtime_report.as_posix()} "
        f"migration_report={migration_report.as_posix()} "
        f"deployment_report={deployment_report.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
