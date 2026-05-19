#!/usr/bin/env python3
"""Generate deployment artifacts for the unified GCP/Cloudflare/Supabase platform."""

from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any, Mapping
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import (
    parse_env_file,
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root as _resolve_cli_path_from_root,
    resolve_default_path_from_root as _resolve_default_path_from_root,
)
from scripts.managed_deployment_contract import (
    CLOUDFLARE_PAGES_PUBLIC_ENV_KEYS,
    PAYSTACK_RUNTIME_KEY_NAMES,
    RUNTIME_BLOCKER_KEYS,
    SUPPORTED_ENVIRONMENTS,
    TERRAFORM_BASE_REQUIRED_INPUTS,
    contains_placeholder as _contains_placeholder,
    selected_llm_provider as _selected_llm_provider_shared,
    selected_llm_provider_env_key as _selected_llm_provider_env_key,
)
from scripts.technology_value_contract_receipts import (
    DEFAULT_DEPLOYMENT_TVC_BY_ENV,
    DEFAULT_GIT_SHA,
    build_managed_deployment_admission_receipt,
    load_technology_value_contract,
)
from scripts.verify_technology_value_contract import verify_contract_and_receipts

DEFAULT_OUTPUT_ROOT = Path(".runtime/deploy")
DEFAULT_RELEASE_TAG = "REPLACE_WITH_RELEASE_TAG"
DEFAULT_API_PROMOTION_REF = "REPLACE_WITH_API_PROMOTION_REF"
DEFAULT_BATCH_PROMOTION_REF = "REPLACE_WITH_BATCH_PROMOTION_REF"

DEPLOYMENT_PLAIN_ENV_KEYS = (
    "ENVIRONMENT",
    "API_URL",
    "FRONTEND_URL",
    "LOG_LEVEL",
    "PLATFORM_RUNTIME_PROFILE",
    "OBSERVABILITY_BACKEND",
    "PUBLIC_API_RATE_LIMITING_BACKEND",
    "RATELIMIT_ENABLED",
    "LLM_PROVIDER",
    "PAYSTACK_ACTIVATION_PENDING",
    "EXPOSE_API_DOCUMENTATION_PUBLICLY",
    "SAAS_STRICT_INTEGRATIONS",
    "TRUST_PROXY_HEADERS",
    "CORS_ORIGINS",
    "APP_RUNTIME_DATA_DIR",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
)

DEPLOYMENT_SECRET_EXCLUDED_KEYS = frozenset(DEPLOYMENT_PLAIN_ENV_KEYS) | {
    "ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION",
    "APP_NAME",
    "APP_VERSION",
    "DEBUG",
    "INTERNAL_JOB_SECRET",
    "WEB_CONCURRENCY",
    "GCP_CLOUD_RUN_BATCH_JOB_NAME",
    "GCP_CLOUD_RUN_SERVICE_NAME",
    "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL",
    "GCP_CLOUD_TASKS_QUEUE",
    "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS",
    "GCP_INTERNAL_AUTH_AUDIENCE",
    "GCP_INTERNAL_BASE_URL",
    "GCP_PROJECT_ID",
    "GCP_REGION",
    "OBSERVABILITY_BACKEND",
    "PLATFORM_RUNTIME_PROFILE",
    "POSTGRES_DB",
    "POSTGRES_PASSWORD",
    "POSTGRES_USER",
    "SUPABASE_ANON_KEY",
    "SUPABASE_URL",
    "TESTING",
}

GITHUB_ENVIRONMENT_VARIABLE_REQUIREMENTS = (
    "GCP_PROJECT_ID",
    "GCP_REGION",
    "API_URL",
    "FRONTEND_URL",
    "CLOUDFLARE_ACCOUNT_ID",
    "CLOUDFLARE_ZONE_ID",
    "CLOUDFLARE_PAGES_PROJECT_NAME",
    "CLOUDFLARE_PAGES_PRODUCTION_BRANCH",
    "SUPABASE_ORGANIZATION_ID",
    "SUPABASE_PROJECT_NAME",
    "SUPABASE_REGION",
    "RUNTIME_PLAIN_ENV_JSON",
)

GITHUB_ENVIRONMENT_SECRET_REQUIREMENTS = (
    "CLOUDFLARE_API_TOKEN",
    "SUPABASE_ACCESS_TOKEN",
    "SUPABASE_DATABASE_PASSWORD",
    "RUNTIME_SECRET_ENV_JSON",
    "GCP_WORKLOAD_IDENTITY_PROVIDER",
    "GCP_DEPLOYER_SERVICE_ACCOUNT",
    "GCP_ARTIFACT_PUBLISHER_SERVICE_ACCOUNT",
)

MANAGED_OUTPUT_FILENAME_ALLOWLIST = frozenset(
    {
        "unified-platform-manifest.json",
        "secret-manager-runtime-secrets.json",
        "cloudflare-pages-env.json",
        "artifact-registry-release.json",
        "terraform.runtime.auto.tfvars.json",
        "deployment.report.json",
        # Rendered by scripts/render_managed_deployment_handoff.py and kept alongside
        # the generated deployment bundle for operator use.
        "operator-handoff.md",
        "technology-value-admission-receipt.json",
    }
)


def _string_value(values: dict[str, str], key: str, default: str = "") -> str:
    return str(values.get(key, default) or default)


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_default_path(path: Path) -> Path:
    return _resolve_default_path_from_root(_repo_root(), path)


def _resolve_cli_path(path: Path, *, field_name: str) -> Path:
    return _resolve_cli_path_from_root(_repo_root(), path, field_name=field_name)


def _protected_output_roots(repo_root: Path) -> tuple[Path, ...]:
    return (
        (repo_root / "app").resolve(),
        (repo_root / "docs").resolve(),
        (repo_root / "scripts").resolve(),
        (repo_root / "tests").resolve(),
        (repo_root / ".github").resolve(),
    )


def _selected_llm_provider(values: dict[str, str]) -> str:
    return _selected_llm_provider_shared(values)


def _is_valid_strict_public_url(value: str) -> bool:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return False

    parsed = urlparse(candidate)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False

    hostname = str(parsed.hostname or "").strip().lower()
    if not hostname or hostname == "localhost":
        return False

    try:
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        return True

    return not (
        host_ip.is_private
        or host_ip.is_loopback
        or host_ip.is_link_local
        or host_ip.is_multicast
        or host_ip.is_unspecified
        or host_ip.is_reserved
    )


def _is_valid_http_url(value: str) -> bool:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return False
    return candidate.startswith(("http://", "https://"))


def _has_valid_trusted_proxy_cidrs(value: str) -> bool:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return False
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, list) or not parsed:
        return False
    for raw in parsed:
        cidr = str(raw or "").strip()
        if not cidr:
            return False
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            return False
    return True


def _has_minimum_length(value: str, *, minimum: int) -> bool:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return False
    return len(candidate) >= minimum


def _is_truthy(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _runtime_blockers(values: dict[str, str]) -> list[str]:
    blockers: list[str] = []
    paystack_activation_pending = _is_truthy(
        _string_value(values, "PAYSTACK_ACTIVATION_PENDING")
    )
    for key in RUNTIME_BLOCKER_KEYS:
        if paystack_activation_pending and key in PAYSTACK_RUNTIME_KEY_NAMES:
            continue
        value = _string_value(values, key).strip()
        if not value or _contains_placeholder(value):
            blockers.append(key)

    for key in ("API_URL", "FRONTEND_URL"):
        value = _string_value(values, key).strip()
        if (
            value
            and not _contains_placeholder(value)
            and not _is_valid_strict_public_url(value)
        ):
            blockers.append(key)

    trusted_proxy_cidrs = _string_value(values, "TRUSTED_PROXY_CIDRS").strip()
    if (
        trusted_proxy_cidrs
        and not _contains_placeholder(trusted_proxy_cidrs)
        and not _has_valid_trusted_proxy_cidrs(trusted_proxy_cidrs)
    ):
        blockers.append("TRUSTED_PROXY_CIDRS")

    admin_api_key = _string_value(values, "ADMIN_API_KEY").strip()
    if (
        admin_api_key
        and not _contains_placeholder(admin_api_key)
        and not _has_minimum_length(admin_api_key, minimum=32)
    ):
        blockers.append("ADMIN_API_KEY")

    internal_metrics_auth_token = _string_value(
        values, "INTERNAL_METRICS_AUTH_TOKEN"
    ).strip()
    if (
        internal_metrics_auth_token
        and not _contains_placeholder(internal_metrics_auth_token)
        and not _has_minimum_length(internal_metrics_auth_token, minimum=32)
    ):
        blockers.append("INTERNAL_METRICS_AUTH_TOKEN")

    paystack_secret_key = _string_value(values, "PAYSTACK_SECRET_KEY").strip()
    if (
        paystack_secret_key
        and not _contains_placeholder(paystack_secret_key)
        and not paystack_secret_key.startswith("sk_")
    ):
        blockers.append("PAYSTACK_SECRET_KEY")

    paystack_public_key = _string_value(values, "PAYSTACK_PUBLIC_KEY").strip()
    if (
        paystack_public_key
        and not _contains_placeholder(paystack_public_key)
        and not paystack_public_key.startswith("pk_")
    ):
        blockers.append("PAYSTACK_PUBLIC_KEY")

    provider_key = _selected_llm_provider_env_key(values)
    provider_value = _string_value(values, provider_key).strip()
    if not provider_value or _contains_placeholder(provider_value):
        blockers.append(provider_key)

    return sorted(set(blockers))


def _artifact_output_paths(output_dir: Path) -> tuple[Path, ...]:
    return (
        output_dir / "unified-platform-manifest.json",
        output_dir / "secret-manager-runtime-secrets.json",
        output_dir / "cloudflare-pages-env.json",
        output_dir / "artifact-registry-release.json",
        output_dir / "terraform.runtime.auto.tfvars.json",
        output_dir / "technology-value-admission-receipt.json",
        output_dir / "deployment.report.json",
    )


def _resolve_technology_value_contract_path(
    *,
    environment: str,
    contract_path: Path | None,
) -> Path:
    candidate = (
        _resolve_cli_path(contract_path, field_name="technology_value_contract_path")
        if contract_path is not None
        else _resolve_default_path(DEFAULT_DEPLOYMENT_TVC_BY_ENV[environment])
    )
    if not candidate.exists():
        raise FileNotFoundError(
            f"Technology Value Contract does not exist: {candidate.as_posix()}"
        )
    if not candidate.is_file():
        raise ValueError(
            f"technology_value_contract_path must be a file: {candidate.as_posix()}"
        )
    return candidate


def _prune_unmanaged_output_files(output_dir: Path) -> None:
    if not output_dir.exists():
        return
    for candidate in output_dir.iterdir():
        if not candidate.is_file() and not candidate.is_symlink():
            continue
        if candidate.name in MANAGED_OUTPUT_FILENAME_ALLOWLIST:
            continue
        candidate.unlink()


def _ensure_output_dir_parent(output_dir: Path) -> None:
    current = output_dir
    while True:
        if current.exists():
            if not current.is_dir():
                raise ValueError(
                    f"output_dir parent must be a directory path: {current.as_posix()}"
                )
            return
        if current == current.parent:
            return
        current = current.parent


def _cloud_run_runtime_plain_env(
    values: dict[str, str], *, environment: str
) -> dict[str, str]:
    plain_env: dict[str, str] = {
        "ENVIRONMENT": environment,
        "PLATFORM_RUNTIME_PROFILE": "gcp",
        "OBSERVABILITY_BACKEND": "gcp",
    }
    for key in DEPLOYMENT_PLAIN_ENV_KEYS:
        if key in plain_env:
            continue
        value = _string_value(values, key).strip()
        if value:
            plain_env[key] = value
    return plain_env


def _secret_manager_runtime_payload(values: dict[str, str]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for key in sorted(values):
        if key in DEPLOYMENT_SECRET_EXCLUDED_KEYS:
            continue
        value = _string_value(values, key).strip()
        if not value:
            continue
        payload[key] = value
    return payload


def _cloudflare_pages_public_env(values: dict[str, str]) -> dict[str, str]:
    api_url = _string_value(values, "API_URL").rstrip("/")
    return {
        "PUBLIC_API_URL": f"{api_url}/api/v1" if api_url else "",
        "PUBLIC_SUPABASE_URL": _string_value(values, "SUPABASE_URL").strip(),
        "PUBLIC_SUPABASE_ANON_KEY": _string_value(values, "SUPABASE_ANON_KEY").strip(),
    }


def supabase_project_ref_from_url(value: str) -> str:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return ""
    parsed = urlparse(candidate)
    hostname = str(parsed.hostname or "").strip().lower()
    if not hostname.endswith(".supabase.co"):
        return ""
    project_ref = hostname.removesuffix(".supabase.co").strip()
    if not project_ref or "." in project_ref:
        return ""
    return project_ref


def _json_placeholder_blockers(payload: Any, *, path: str = "") -> list[str]:
    blockers: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}" if path else str(key)
            blockers.extend(_json_placeholder_blockers(value, path=child_path))
        return blockers
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            child_path = f"{path}[{index}]"
            blockers.extend(_json_placeholder_blockers(value, path=child_path))
        return blockers
    if isinstance(payload, str):
        normalized = payload.strip()
        if not normalized or _contains_placeholder(normalized):
            blockers.append(path or "<root>")
    return blockers


def _placeholder_keys(payload: dict[str, str]) -> list[str]:
    return sorted(
        key
        for key, value in payload.items()
        if not str(value).strip() or _contains_placeholder(value)
    )


def _resolved_or_placeholder(value: str | None, *, placeholder_name: str) -> str:
    normalized = str(value or "").strip()
    if normalized:
        return normalized
    return f"REPLACE_WITH_{placeholder_name}"


def _terraform_remaining_inputs(payload: Mapping[str, Any]) -> list[str]:
    remaining: list[str] = []
    for key in TERRAFORM_BASE_REQUIRED_INPUTS:
        value = str(payload.get(key, "") or "").strip()
        if not value or _contains_placeholder(value):
            remaining.append(key)
    return sorted(remaining)


def _is_valid_promotion_ref(value: str) -> bool:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return False
    if "@" not in candidate:
        return False
    repository, digest = candidate.rsplit("@", 1)
    if not repository or "/" not in repository:
        return False
    if not digest.startswith("sha256:"):
        return False
    digest_body = digest.split("sha256:", 1)[1].strip()
    return len(digest_body) == 64 and all(
        ch in "0123456789abcdef" for ch in digest_body
    )


def _artifact_registry_release_metadata(
    *,
    environment: str,
    release_tag: str,
    api_promotion_ref: str,
    batch_promotion_ref: str,
) -> dict[str, Any]:
    normalized_release_tag = str(release_tag or "").strip() or DEFAULT_RELEASE_TAG
    normalized_api_ref = (
        str(api_promotion_ref or "").strip() or DEFAULT_API_PROMOTION_REF
    )
    normalized_batch_ref = (
        str(batch_promotion_ref or "").strip() or DEFAULT_BATCH_PROMOTION_REF
    )
    return {
        "strategy": "immutable_artifact_registry_promotion",
        "environment": environment,
        "release_tag": normalized_release_tag,
        "services": {
            "api": {
                "runtime": "google_cloud_run",
                "promotion_ref": normalized_api_ref,
            },
            "batch": {
                "runtime": "google_cloud_run_jobs",
                "promotion_ref": normalized_batch_ref,
            },
        },
    }


def _unified_platform_manifest(
    *,
    environment: str,
    release_tag: str,
    api_promotion_ref: str,
    batch_promotion_ref: str,
    runtime_plain_env: dict[str, str],
    cloudflare_pages_env: dict[str, str],
) -> dict[str, Any]:
    return {
        "strategy": "unified_platform_managed_release",
        "environment": environment,
        "release_tag": release_tag,
        "source_of_truth": {
            "infrastructure": "terraform",
            "schema": "alembic",
            "deployment_pipeline": "github_actions",
            "observability": "google_cloud_operations",
        },
        "backend": {
            "runtime": "google_cloud_run",
            "api_service_name": "valdrics-api",
            "batch_job_name": "valdrics-batch",
            "tasks_queue_name": "valdrics-managed-work",
            "scheduler_owner": "cloud_scheduler",
            "api_promotion_ref": api_promotion_ref,
            "batch_promotion_ref": batch_promotion_ref,
            "runtime_plain_env": runtime_plain_env,
        },
        "frontend": {
            "runtime": "cloudflare_pages",
            "public_env": cloudflare_pages_env,
        },
        "data_platform": {
            "database": "supabase_postgres",
            "auth": "supabase_auth",
            "storage": "supabase_storage",
        },
    }


def generate_managed_deployment_artifacts(
    *,
    environment: str,
    runtime_env_file: Path,
    output_dir: Path,
    release_tag: str = DEFAULT_RELEASE_TAG,
    api_promotion_ref: str = DEFAULT_API_PROMOTION_REF,
    batch_promotion_ref: str = DEFAULT_BATCH_PROMOTION_REF,
    gcp_project_id: str | None = None,
    gcp_region: str | None = None,
    cloudflare_account_id: str | None = None,
    cloudflare_zone_id: str | None = None,
    cloudflare_pages_project_name: str | None = None,
    cloudflare_pages_production_branch: str | None = None,
    supabase_organization_id: str | None = None,
    supabase_project_name: str | None = None,
    supabase_region: str | None = None,
    technology_value_contract_path: Path | None = None,
    git_sha: str = DEFAULT_GIT_SHA,
) -> dict[str, Any]:
    normalized_environment = str(environment or "").strip().lower()
    if normalized_environment not in SUPPORTED_ENVIRONMENTS:
        raise ValueError(
            "environment must be one of: " + ", ".join(SUPPORTED_ENVIRONMENTS)
        )
    if not runtime_env_file.exists():
        raise FileNotFoundError(
            f"Runtime env file does not exist: {runtime_env_file.as_posix()}"
        )
    if not runtime_env_file.is_file():
        raise ValueError(
            f"runtime_env_file must be a file: {runtime_env_file.as_posix()}"
        )
    normalized_git_sha = str(git_sha or "").strip() or DEFAULT_GIT_SHA
    if len(normalized_git_sha) < 7 or any(
        ch not in "0123456789abcdef" for ch in normalized_git_sha.lower()
    ):
        raise ValueError("git_sha must be a hexadecimal git revision")
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(
            f"output_dir must be a directory path: {output_dir.as_posix()}"
        )
    _ensure_output_dir_parent(output_dir)
    output_dir_resolved = output_dir.resolve()
    for protected_root in _protected_output_roots(_repo_root()):
        try:
            output_dir_resolved.relative_to(protected_root)
        except ValueError:
            continue
        raise ValueError(
            "output_dir must not point inside source, test, workflow, or checked-in documentation roots"
        )

    runtime_env_resolved = runtime_env_file.resolve()
    for artifact_path in _artifact_output_paths(output_dir):
        if artifact_path.resolve() == runtime_env_resolved:
            raise ValueError(
                "runtime_env_file must not overwrite generated deployment artifacts"
            )
    resolved_technology_value_contract_path = _resolve_technology_value_contract_path(
        environment=normalized_environment,
        contract_path=technology_value_contract_path,
    )
    technology_value_contract = load_technology_value_contract(
        resolved_technology_value_contract_path
    )

    values = parse_env_file(runtime_env_file)
    runtime_blockers = _runtime_blockers(values)
    runtime_plain_env = _cloud_run_runtime_plain_env(
        values, environment=normalized_environment
    )
    secret_manager_runtime_payload = _secret_manager_runtime_payload(values)
    cloudflare_pages_env = _cloudflare_pages_public_env(values)
    cloudflare_pages_env_blockers = _placeholder_keys(cloudflare_pages_env)

    effective_batch_ref = (
        str(batch_promotion_ref or "").strip() or DEFAULT_BATCH_PROMOTION_REF
    )
    if effective_batch_ref == DEFAULT_BATCH_PROMOTION_REF and (
        str(api_promotion_ref or "").strip()
        and str(api_promotion_ref or "").strip() != DEFAULT_API_PROMOTION_REF
    ):
        effective_batch_ref = str(api_promotion_ref).strip()

    artifact_registry_release = _artifact_registry_release_metadata(
        environment=normalized_environment,
        release_tag=release_tag,
        api_promotion_ref=api_promotion_ref,
        batch_promotion_ref=effective_batch_ref,
    )
    artifact_registry_release_blockers = sorted(
        set(_json_placeholder_blockers(artifact_registry_release))
    )

    unified_platform_manifest = _unified_platform_manifest(
        environment=normalized_environment,
        release_tag=str(release_tag or "").strip() or DEFAULT_RELEASE_TAG,
        api_promotion_ref=artifact_registry_release["services"]["api"]["promotion_ref"],
        batch_promotion_ref=artifact_registry_release["services"]["batch"][
            "promotion_ref"
        ],
        runtime_plain_env=runtime_plain_env,
        cloudflare_pages_env=cloudflare_pages_env,
    )

    terraform_tfvars_payload = {
        "environment": normalized_environment,
        "gcp_project_id": _resolved_or_placeholder(
            gcp_project_id,
            placeholder_name="GCP_PROJECT_ID",
        ),
        "gcp_region": _resolved_or_placeholder(
            gcp_region,
            placeholder_name="GCP_REGION",
        ),
        "cloudflare_account_id": _resolved_or_placeholder(
            cloudflare_account_id,
            placeholder_name="CLOUDFLARE_ACCOUNT_ID",
        ),
        "cloudflare_zone_id": _resolved_or_placeholder(
            cloudflare_zone_id,
            placeholder_name="CLOUDFLARE_ZONE_ID",
        ),
        "cloudflare_pages_project_name": _resolved_or_placeholder(
            cloudflare_pages_project_name,
            placeholder_name="CLOUDFLARE_PAGES_PROJECT_NAME",
        ),
        "cloudflare_pages_production_branch": _resolved_or_placeholder(
            cloudflare_pages_production_branch,
            placeholder_name="CLOUDFLARE_PAGES_PRODUCTION_BRANCH",
        ),
        "supabase_organization_id": _resolved_or_placeholder(
            supabase_organization_id,
            placeholder_name="SUPABASE_ORGANIZATION_ID",
        ),
        "supabase_project_ref": _resolved_or_placeholder(
            supabase_project_ref_from_url(_string_value(values, "SUPABASE_URL")),
            placeholder_name="SUPABASE_PROJECT_REF",
        ),
        "supabase_project_name": _resolved_or_placeholder(
            supabase_project_name,
            placeholder_name="SUPABASE_PROJECT_NAME",
        ),
        "supabase_region": _resolved_or_placeholder(
            supabase_region,
            placeholder_name="SUPABASE_REGION",
        ),
        "api_url": _string_value(values, "API_URL").strip(),
        "frontend_url": _string_value(values, "FRONTEND_URL").strip(),
        "api_image": artifact_registry_release["services"]["api"]["promotion_ref"],
        "batch_job_image": artifact_registry_release["services"]["batch"][
            "promotion_ref"
        ],
        "runtime_plain_env": runtime_plain_env,
        "runtime_secret_env": secret_manager_runtime_payload,
    }
    terraform_remaining_inputs = _terraform_remaining_inputs(terraform_tfvars_payload)
    terraform_value_blockers = sorted(
        set(_json_placeholder_blockers(terraform_tfvars_payload))
    )

    (
        unified_platform_manifest_path,
        secret_manager_runtime_path,
        cloudflare_pages_env_path,
        artifact_registry_release_path,
        terraform_tfvars_path,
        technology_value_receipt_path,
        report_path,
    ) = _artifact_output_paths(output_dir)
    operator_handoff_path = output_dir / "operator-handoff.md"

    secret_manager_secret_keys = sorted(secret_manager_runtime_payload)
    secret_manager_secret_value_blockers = _placeholder_keys(
        secret_manager_runtime_payload
    )

    report = {
        "environment": normalized_environment,
        "runtime_env_file": runtime_env_file.as_posix(),
        "output_dir": output_dir.as_posix(),
        "technology_value_contract_path": resolved_technology_value_contract_path.as_posix(),
        "runtime_validation_blockers": runtime_blockers,
        "secret_manager_secret_keys": secret_manager_secret_keys,
        "secret_manager_secret_value_blockers": secret_manager_secret_value_blockers,
        "cloudflare_pages_public_env_keys": list(CLOUDFLARE_PAGES_PUBLIC_ENV_KEYS),
        "cloudflare_pages_public_env_blockers": cloudflare_pages_env_blockers,
        "artifact_registry_release_value_blockers": artifact_registry_release_blockers,
        "terraform_runtime_tfvars_path": terraform_tfvars_path.as_posix(),
        "terraform_remaining_inputs": terraform_remaining_inputs,
        "terraform_value_blockers": terraform_value_blockers,
        "github_environment_variable_requirements": list(
            GITHUB_ENVIRONMENT_VARIABLE_REQUIREMENTS
        ),
        "github_environment_secret_requirements": list(
            GITHUB_ENVIRONMENT_SECRET_REQUIREMENTS
        ),
        "artifacts": {
            "unified_platform_manifest": unified_platform_manifest_path.as_posix(),
            "secret_manager_runtime_secrets": secret_manager_runtime_path.as_posix(),
            "cloudflare_pages_env_json": cloudflare_pages_env_path.as_posix(),
            "artifact_registry_release_metadata": (
                artifact_registry_release_path.as_posix()
            ),
            "terraform_runtime_tfvars": terraform_tfvars_path.as_posix(),
            "technology_value_receipt_json": technology_value_receipt_path.as_posix(),
            "operator_handoff_markdown": operator_handoff_path.as_posix(),
        },
        "ready_for_unified_platform": (
            not runtime_blockers
            and not secret_manager_secret_value_blockers
            and not cloudflare_pages_env_blockers
            and not artifact_registry_release_blockers
        ),
        "ready_for_release_promotion": (
            not artifact_registry_release_blockers
            and _is_valid_promotion_ref(
                artifact_registry_release["services"]["api"]["promotion_ref"]
            )
            and _is_valid_promotion_ref(
                artifact_registry_release["services"]["batch"]["promotion_ref"]
            )
        ),
        "ready_for_terraform": not terraform_value_blockers,
    }
    technology_value_receipt = build_managed_deployment_admission_receipt(
        contract=technology_value_contract,
        environment=normalized_environment,
        release_tag=str(release_tag or "").strip() or DEFAULT_RELEASE_TAG,
        git_sha=normalized_git_sha.lower(),
        deployment_report=report,
        evidence_refs=[
            runtime_env_file.as_posix(),
            unified_platform_manifest_path.as_posix(),
            artifact_registry_release_path.as_posix(),
            report_path.as_posix(),
        ],
    )

    artifact_contents = {
        unified_platform_manifest_path.name: json.dumps(
            unified_platform_manifest, indent=2, sort_keys=True
        ),
        secret_manager_runtime_path.name: json.dumps(
            secret_manager_runtime_payload, indent=2, sort_keys=True
        ),
        cloudflare_pages_env_path.name: json.dumps(
            cloudflare_pages_env, indent=2, sort_keys=True
        ),
        artifact_registry_release_path.name: json.dumps(
            artifact_registry_release, indent=2, sort_keys=True
        ),
        terraform_tfvars_path.name: json.dumps(
            terraform_tfvars_payload, indent=2, sort_keys=True
        ),
        technology_value_receipt_path.name: json.dumps(
            technology_value_receipt, indent=2, sort_keys=True
        ),
        report_path.name: json.dumps(report, indent=2, sort_keys=True),
    }

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent)
    )
    promoted_paths: list[Path] = []
    promotion_completed = False
    try:
        staged_paths: list[tuple[Path, Path]] = []
        for final_path in _artifact_output_paths(output_dir):
            staged_path = staging_dir / final_path.name
            staged_path.write_text(
                artifact_contents[final_path.name],
                encoding="utf-8",
            )
            staged_paths.append((staged_path, final_path))

        staged_receipt_path = next(
            staged_path
            for staged_path, final_path in staged_paths
            if final_path.name == technology_value_receipt_path.name
        )
        verify_contract_and_receipts(
            contract_path=resolved_technology_value_contract_path,
            receipt_paths=[staged_receipt_path],
        )

        output_dir.mkdir(parents=True, exist_ok=True)
        for staged_path, final_path in staged_paths:
            staged_path.replace(final_path)
            promoted_paths.append(final_path)
        promotion_completed = True
        _prune_unmanaged_output_files(output_dir)
    finally:
        if not promotion_completed:
            for final_path in promoted_paths:
                final_path.unlink(missing_ok=True)
        shutil.rmtree(staging_dir, ignore_errors=True)

    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deployment artifacts for the unified platform "
            "(Cloud Run, Cloud Tasks, Cloud Scheduler, Cloudflare Pages, Supabase)."
        )
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=SUPPORTED_ENVIRONMENTS,
    )
    parser.add_argument(
        "--runtime-env-file",
        type=Path,
        default=None,
        help="Runtime env file to consume (default: .runtime/<environment>.env).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: .runtime/deploy/<environment>).",
    )
    parser.add_argument(
        "--release-tag",
        default=DEFAULT_RELEASE_TAG,
        help="Immutable release tag recorded in the generated Artifact Registry metadata.",
    )
    parser.add_argument(
        "--api-promotion-ref",
        default=DEFAULT_API_PROMOTION_REF,
        help=(
            "Digest-pinned Artifact Registry ref for the API service "
            "(format: <repo>@sha256:<64-hex>)."
        ),
    )
    parser.add_argument(
        "--batch-promotion-ref",
        default=DEFAULT_BATCH_PROMOTION_REF,
        help=(
            "Digest-pinned Artifact Registry ref for the Cloud Run batch job. "
            "Defaults to the API promotion ref when omitted."
        ),
    )
    parser.add_argument("--gcp-project-id", default=None)
    parser.add_argument("--gcp-region", default=None)
    parser.add_argument("--cloudflare-account-id", default=None)
    parser.add_argument("--cloudflare-zone-id", default=None)
    parser.add_argument("--cloudflare-pages-project-name", default=None)
    parser.add_argument("--cloudflare-pages-production-branch", default=None)
    parser.add_argument("--supabase-organization-id", default=None)
    parser.add_argument("--supabase-project-name", default=None)
    parser.add_argument("--supabase-region", default=None)
    parser.add_argument(
        "--technology-value-contract-path",
        type=Path,
        default=None,
        help=(
            "Optional path to an environment-specific Technology Value Contract. "
            "Defaults to contracts/examples/unified-platform-deploy-<environment>.yaml."
        ),
    )
    parser.add_argument(
        "--git-sha",
        default=DEFAULT_GIT_SHA,
        help="Git SHA recorded in the generated TVC admission receipt.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    runtime_env_file = (
        _resolve_default_path(Path(".runtime") / f"{args.environment}.env")
        if args.runtime_env_file is None
        else _resolve_cli_path(args.runtime_env_file, field_name="runtime_env_file")
    )
    output_dir = (
        _resolve_default_path(DEFAULT_OUTPUT_ROOT / str(args.environment))
        if args.output_dir is None
        else _resolve_cli_path(args.output_dir, field_name="output_dir")
    )
    report = generate_managed_deployment_artifacts(
        environment=str(args.environment),
        runtime_env_file=runtime_env_file,
        output_dir=output_dir,
        release_tag=str(args.release_tag),
        api_promotion_ref=str(args.api_promotion_ref),
        batch_promotion_ref=str(args.batch_promotion_ref),
        gcp_project_id=args.gcp_project_id,
        gcp_region=args.gcp_region,
        cloudflare_account_id=args.cloudflare_account_id,
        cloudflare_zone_id=args.cloudflare_zone_id,
        cloudflare_pages_project_name=args.cloudflare_pages_project_name,
        cloudflare_pages_production_branch=args.cloudflare_pages_production_branch,
        supabase_organization_id=args.supabase_organization_id,
        supabase_project_name=args.supabase_project_name,
        supabase_region=args.supabase_region,
        technology_value_contract_path=args.technology_value_contract_path,
        git_sha=str(args.git_sha),
    )
    print(
        "[managed-deployment-artifacts] ok "
        f"environment={report['environment']} "
        f"output_dir={report['output_dir']} "
        f"runtime_blockers={len(report['runtime_validation_blockers'])} "
        f"unified_ready={report['ready_for_unified_platform']} "
        f"release_ready={report['ready_for_release_promotion']} "
        f"terraform_ready={report['ready_for_terraform']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
