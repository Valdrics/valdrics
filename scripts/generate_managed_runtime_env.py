#!/usr/bin/env python3
"""Generate staging/production managed-runtime env scaffolds plus an unresolved-value report."""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
from pathlib import Path
import secrets
import sys
from typing import Any
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import (
    ensure_parent_dir as _ensure_parent_dir,
    parse_env_file,
    protected_output_paths_from_root as _protected_output_paths_from_root,
    render_env,
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root as _resolve_cli_path_from_root,
    resolve_default_path_from_root as _resolve_default_path_from_root,
    stage_text_file as _stage_text_file,
)
from scripts.managed_deployment_contract import (
    DECLARED_EXTERNAL_VALUE_KEYS,
    DECLARED_NONBLOCKING_EXTERNAL_KEYS,
    DEFAULT_LLM_PROVIDER,
    DERIVED_EXTERNAL_KEYS,
    INTERNAL_SECRET_KEYS,
    PLACEHOLDER_PREFIX,
    RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS,
    SUPPORTED_ENVIRONMENTS,
    SUPPORTED_LLM_PROVIDERS,
    identify_runtime_unresolved_keys as _identify_unresolved_keys,
    required_runtime_operator_input_keys as _required_operator_input_keys,
)

DEFAULT_TEMPLATE_PATH = Path(".env.example")
DEFAULT_OUTPUT_DIR = Path(".runtime")


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_default_path(path: Path) -> Path:
    return _resolve_default_path_from_root(_repo_root(), path)


def _resolve_cli_path(path: Path, *, field_name: str) -> Path:
    return _resolve_cli_path_from_root(_repo_root(), path, field_name=field_name)


def _protected_output_paths() -> set[Path]:
    return _protected_output_paths_from_root(
        _repo_root(),
        __file__,
        ".env.example",
        "scripts/validate_runtime_env.py",
        "docs/ops/feature_enforceability_matrix.json",
        "docs/ops/key-rotation-drill-2026-02-27.md",
    )


def _generate_hex(length: int = 64) -> str:
    return secrets.token_hex(max(1, length // 2))


def _generate_urlsafe_b64(byte_count: int = 32) -> str:
    return base64.urlsafe_b64encode(secrets.token_bytes(byte_count)).decode("utf-8")


def _generate_b64(byte_count: int = 32) -> str:
    return base64.b64encode(secrets.token_bytes(byte_count)).decode("utf-8")


def _placeholder(name: str, *, prefix: str = PLACEHOLDER_PREFIX) -> str:
    return f"{prefix}{name}"


def _default_api_url() -> str:
    return "https://REPLACE_WITH_API_DOMAIN"


def _default_frontend_url() -> str:
    return "https://REPLACE_WITH_FRONTEND_DOMAIN"


def _default_database_url() -> str:
    return (
        "postgresql+asyncpg://REPLACE_WITH_DB_USER:"
        "REPLACE_WITH_DB_PASSWORD@REPLACE_WITH_DB_HOST:5432/postgres"
    )


def _default_supabase_url() -> str:
    return "https://REPLACE_WITH_SUPABASE_PROJECT.supabase.co"


def _default_supabase_anon_key() -> str:
    return "REPLACE_WITH_SUPABASE_ANON_KEY"


def _default_supabase_jwt_secret() -> str:
    return "REPLACE_WITH_SUPABASE_JWT_SECRET_MINIMUM_32_CHARS_VALUE"


def _default_gcp_project_id() -> str:
    return "REPLACE_WITH_GCP_PROJECT_ID"


def _default_gcp_region() -> str:
    return "REPLACE_WITH_GCP_REGION"


def _default_gcp_cloud_tasks_queue() -> str:
    return "valdrics-managed-work"


def _default_gcp_cloud_tasks_invoker_service_account_email() -> str:
    return "REPLACE_WITH_GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL"


def _default_gcp_cloud_run_service_name() -> str:
    return "valdrics-api"


def _default_gcp_cloud_run_batch_job_name() -> str:
    return "valdrics-batch"


def _default_gcp_internal_allowed_service_accounts() -> str:
    return json.dumps(
        [
            "REPLACE_WITH_GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL",
            "REPLACE_WITH_GCP_CLOUD_SCHEDULER_INVOKER_SERVICE_ACCOUNT_EMAIL",
        ],
        separators=(",", ":"),
    )


def _default_paystack_secret_key() -> str:
    return "sk_live_REPLACE_WITH_PAYSTACK_SECRET_KEY"


def _default_paystack_public_key() -> str:
    return "pk_live_REPLACE_WITH_PAYSTACK_PUBLIC_KEY"


def _render_cors_origins(frontend_url: str) -> str:
    return json.dumps([frontend_url], separators=(",", ":"))


def _render_trusted_proxy_cidrs(cidrs: list[str] | None) -> str:
    if cidrs:
        return json.dumps(cidrs, separators=(",", ":"))
    return json.dumps([_placeholder("TRUSTED_PROXY_CIDR")], separators=(",", ":"))


def _normalize_trusted_proxy_cidrs(cidrs: list[str] | None) -> list[str] | None:
    if cidrs is None:
        return None
    normalized: list[str] = []
    for raw in cidrs:
        cidr = str(raw or "").strip()
        if not cidr:
            raise ValueError("trusted_proxy_cidrs entries must be non-empty")
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError as exc:
            raise ValueError(
                f"trusted_proxy_cidrs contains invalid CIDR: {cidr}"
            ) from exc
        normalized.append(cidr)
    return normalized


def _normalize_strict_public_url(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty https:// URL")

    parsed = urlparse(normalized)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(
            f"{field_name} must use an explicit https:// URL in staging/production."
        )
    if parsed.username or parsed.password:
        raise ValueError(f"{field_name} must not include embedded credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{field_name} must not include query strings or fragments.")

    hostname = str(parsed.hostname or "").strip().lower()
    if not hostname or hostname == "localhost":
        raise ValueError(
            f"{field_name} must not point at localhost in staging/production."
        )

    try:
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        return normalized

    if (
        host_ip.is_private
        or host_ip.is_loopback
        or host_ip.is_link_local
        or host_ip.is_multicast
        or host_ip.is_unspecified
        or host_ip.is_reserved
    ):
        raise ValueError(
            f"{field_name} must not resolve to a private or non-routable IP in staging/production."
        )
    return normalized


def _normalize_optional_http_url(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty URL")
    if not normalized.startswith(("http://", "https://")):
        raise ValueError(f"{field_name} must use an explicit http:// or https:// URL.")
    return normalized


def _normalize_paystack_key(
    value: str | None,
    *,
    field_name: str,
    environment: str,
    required_prefix: str,
    require_live: bool = True,
) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    if (
        require_live
        and environment == "production"
        and not normalized.startswith(required_prefix)
    ):
        raise ValueError(
            f"{field_name} must be a live key ({required_prefix}...) in production."
        )
    return normalized


def _is_live_paystack_key(value: str | None, *, required_prefix: str) -> bool:
    normalized = str(value or "").strip()
    return bool(
        normalized
        and normalized.startswith(required_prefix)
        and PLACEHOLDER_PREFIX not in normalized
    )


def _parse_optional_bool(value: str | None, *, field_name: str) -> bool | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{field_name} must be a boolean value.")


def _build_llm_overrides(provider: str, provider_api_key: str | None) -> dict[str, str]:
    normalized = str(provider or DEFAULT_LLM_PROVIDER).strip().lower()
    if normalized not in SUPPORTED_LLM_PROVIDERS:
        raise ValueError(
            "llm provider must be one of: " + ", ".join(SUPPORTED_LLM_PROVIDERS)
        )

    overrides = {
        "LLM_PROVIDER": normalized,
        "GROQ_API_KEY": "",
        "OPENAI_API_KEY": "",
        "CLAUDE_API_KEY": "",
        "GOOGLE_API_KEY": "",
    }

    provider_key_name = {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "CLAUDE_API_KEY",
        "google": "GOOGLE_API_KEY",
    }[normalized]
    overrides[provider_key_name] = provider_api_key or _placeholder(provider_key_name)
    return overrides


def _existing_value(existing_values: dict[str, str] | None, key: str) -> str | None:
    if not existing_values:
        return None
    candidate = str(existing_values.get(key, "") or "").strip()
    return candidate or None


def _existing_or_default(
    existing_values: dict[str, str] | None,
    key: str,
    default: str,
) -> str:
    return _existing_value(existing_values, key) or default


def _existing_trusted_proxy_cidrs(
    existing_values: dict[str, str] | None,
) -> list[str] | None:
    candidate = _existing_value(existing_values, "TRUSTED_PROXY_CIDRS")
    if candidate is None or PLACEHOLDER_PREFIX in candidate:
        return None
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if not isinstance(parsed, list):
        return None
    return [str(item) for item in parsed]


def _build_overrides(
    *,
    environment: str,
    existing_values: dict[str, str] | None,
    api_url: str | None,
    frontend_url: str | None,
    database_url: str | None,
    supabase_url: str | None,
    supabase_anon_key: str | None,
    supabase_jwt_secret: str | None,
    gcp_project_id: str | None,
    gcp_region: str | None,
    gcp_cloud_tasks_queue: str | None,
    gcp_cloud_tasks_invoker_service_account_email: str | None,
    gcp_cloud_run_service_name: str | None,
    gcp_cloud_run_batch_job_name: str | None,
    gcp_internal_allowed_service_accounts: list[str] | None,
    llm_provider: str | None,
    llm_api_key: str | None,
    paystack_secret_key: str | None,
    paystack_public_key: str | None,
    trusted_proxy_cidrs: list[str] | None,
) -> dict[str, str]:
    normalized_trusted_proxy_cidrs = _normalize_trusted_proxy_cidrs(
        trusted_proxy_cidrs
        if trusted_proxy_cidrs is not None
        else _existing_trusted_proxy_cidrs(existing_values)
    )
    resolved_api_url = (
        _normalize_strict_public_url(
            api_url or _existing_value(existing_values, "API_URL"),
            field_name="API_URL",
        )
        or _default_api_url()
    )
    resolved_frontend_url = (
        _normalize_strict_public_url(
            frontend_url or _existing_value(existing_values, "FRONTEND_URL"),
            field_name="FRONTEND_URL",
        )
        or _default_frontend_url()
    )
    raw_paystack_secret_key = paystack_secret_key or _existing_value(
        existing_values, "PAYSTACK_SECRET_KEY"
    )
    raw_paystack_public_key = paystack_public_key or _existing_value(
        existing_values, "PAYSTACK_PUBLIC_KEY"
    )
    explicit_paystack_activation_pending = _parse_optional_bool(
        _existing_value(existing_values, "PAYSTACK_ACTIVATION_PENDING"),
        field_name="PAYSTACK_ACTIVATION_PENDING",
    )
    paystack_live_keys_configured = _is_live_paystack_key(
        raw_paystack_secret_key,
        required_prefix="sk_live_",
    ) and _is_live_paystack_key(
        raw_paystack_public_key,
        required_prefix="pk_live_",
    )
    paystack_activation_pending = (
        explicit_paystack_activation_pending
        if explicit_paystack_activation_pending is not None
        else environment == "production" and not paystack_live_keys_configured
    )

    normalized_paystack_secret_key = _normalize_paystack_key(
        raw_paystack_secret_key,
        field_name="PAYSTACK_SECRET_KEY",
        environment=environment,
        required_prefix="sk_live_",
        require_live=not paystack_activation_pending,
    )
    normalized_paystack_public_key = _normalize_paystack_key(
        raw_paystack_public_key,
        field_name="PAYSTACK_PUBLIC_KEY",
        environment=environment,
        required_prefix="pk_live_",
        require_live=not paystack_activation_pending,
    )
    normalized_llm_provider = (
        str(
            llm_provider
            or _existing_value(existing_values, "LLM_PROVIDER")
            or DEFAULT_LLM_PROVIDER
        )
        .strip()
        .lower()
    )
    llm_provider_key_name = {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "CLAUDE_API_KEY",
        "google": "GOOGLE_API_KEY",
    }.get(normalized_llm_provider, "GROQ_API_KEY")
    resolved_llm_api_key = llm_api_key or _existing_value(
        existing_values, llm_provider_key_name
    )

    overrides: dict[str, str] = {
        "APP_NAME": "Valdrics",
        "DEBUG": "false",
        "TESTING": "false",
        "ENVIRONMENT": environment,
        "APP_RUNTIME_DATA_DIR": "/tmp/valdrics",
        "API_URL": resolved_api_url,
        "PLATFORM_RUNTIME_PROFILE": "gcp",
        "OBSERVABILITY_BACKEND": "gcp",
        "PUBLIC_API_RATE_LIMITING_BACKEND": "cloudflare",
        "RATELIMIT_ENABLED": "false",
        "FRONTEND_URL": resolved_frontend_url,
        "GCP_PROJECT_ID": gcp_project_id
        or _existing_or_default(
            existing_values, "GCP_PROJECT_ID", _default_gcp_project_id()
        ),
        "GCP_REGION": gcp_region
        or _existing_or_default(existing_values, "GCP_REGION", _default_gcp_region()),
        "GCP_CLOUD_TASKS_QUEUE": gcp_cloud_tasks_queue
        or _existing_or_default(
            existing_values,
            "GCP_CLOUD_TASKS_QUEUE",
            _default_gcp_cloud_tasks_queue(),
        ),
        "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL": (
            gcp_cloud_tasks_invoker_service_account_email
            or _existing_or_default(
                existing_values,
                "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL",
                _default_gcp_cloud_tasks_invoker_service_account_email(),
            )
        ),
        "GCP_CLOUD_RUN_SERVICE_NAME": gcp_cloud_run_service_name
        or _existing_or_default(
            existing_values,
            "GCP_CLOUD_RUN_SERVICE_NAME",
            _default_gcp_cloud_run_service_name(),
        ),
        "GCP_CLOUD_RUN_BATCH_JOB_NAME": gcp_cloud_run_batch_job_name
        or _existing_or_default(
            existing_values,
            "GCP_CLOUD_RUN_BATCH_JOB_NAME",
            _default_gcp_cloud_run_batch_job_name(),
        ),
        "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS": (
            json.dumps(gcp_internal_allowed_service_accounts, separators=(",", ":"))
            if gcp_internal_allowed_service_accounts
            else _existing_or_default(
                existing_values,
                "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS",
                _default_gcp_internal_allowed_service_accounts(),
            )
        ),
        "CORS_ORIGINS": _render_cors_origins(resolved_frontend_url),
        "DATABASE_URL": database_url
        or _existing_or_default(
            existing_values, "DATABASE_URL", _default_database_url()
        ),
        "DB_SSL_MODE": "require",
        "DB_USE_NULL_POOL": "false",
        "DB_EXTERNAL_POOLER": "false",
        "SUPABASE_URL": supabase_url
        or _existing_or_default(
            existing_values, "SUPABASE_URL", _default_supabase_url()
        ),
        "SUPABASE_ANON_KEY": supabase_anon_key
        or _existing_or_default(
            existing_values, "SUPABASE_ANON_KEY", _default_supabase_anon_key()
        ),
        "SUPABASE_JWT_SECRET": supabase_jwt_secret
        or _existing_or_default(
            existing_values, "SUPABASE_JWT_SECRET", _default_supabase_jwt_secret()
        ),
        "CSRF_SECRET_KEY": _existing_or_default(
            existing_values, "CSRF_SECRET_KEY", _generate_hex(64)
        ),
        "ENCRYPTION_KEY": _existing_or_default(
            existing_values, "ENCRYPTION_KEY", _generate_urlsafe_b64(32)
        ),
        "KDF_SALT": _existing_or_default(
            existing_values, "KDF_SALT", _generate_b64(32)
        ),
        "ADMIN_API_KEY": _existing_or_default(
            existing_values, "ADMIN_API_KEY", _generate_hex(64)
        ),
        "INTERNAL_METRICS_AUTH_TOKEN": _existing_or_default(
            existing_values, "INTERNAL_METRICS_AUTH_TOKEN", _generate_hex(64)
        ),
        "ENFORCEMENT_APPROVAL_TOKEN_SECRET": _existing_or_default(
            existing_values, "ENFORCEMENT_APPROVAL_TOKEN_SECRET", _generate_hex(64)
        ),
        "ENFORCEMENT_EXPORT_SIGNING_SECRET": _existing_or_default(
            existing_values, "ENFORCEMENT_EXPORT_SIGNING_SECRET", _generate_hex(64)
        ),
        "PAYSTACK_SECRET_KEY": (
            normalized_paystack_secret_key
            if not paystack_activation_pending
            or _is_live_paystack_key(
                normalized_paystack_secret_key,
                required_prefix="sk_live_",
            )
            else ""
        )
        or ("" if paystack_activation_pending else _default_paystack_secret_key()),
        "PAYSTACK_PUBLIC_KEY": (
            normalized_paystack_public_key
            if not paystack_activation_pending
            or _is_live_paystack_key(
                normalized_paystack_public_key,
                required_prefix="pk_live_",
            )
            else ""
        )
        or ("" if paystack_activation_pending else _default_paystack_public_key()),
        "PAYSTACK_ACTIVATION_PENDING": "true"
        if paystack_activation_pending
        else "false",
        "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY": "NGN",
        "PAYSTACK_ENABLE_USD_CHECKOUT": "false",
        "ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION": "false",
        "SAAS_STRICT_INTEGRATIONS": "true",
        "EXPOSE_API_DOCUMENTATION_PUBLICLY": "false",
        "TRUST_PROXY_HEADERS": "true",
        "TRUSTED_PROXY_HOPS": "1",
        "TRUSTED_PROXY_CIDRS": _render_trusted_proxy_cidrs(
            normalized_trusted_proxy_cidrs
        ),
        "FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK": "false",
        "FORECASTER_BREAK_GLASS_REASON": "",
        "FORECASTER_BREAK_GLASS_EXPIRES_AT": "",
        "ALLOW_INSECURE_OUTBOUND_TLS": "false",
        "OUTBOUND_TLS_BREAK_GLASS_REASON": "",
        "OUTBOUND_TLS_BREAK_GLASS_EXPIRES_AT": "",
        "SLACK_CHANNEL_ID": "",
        "JIRA_BASE_URL": "",
        "JIRA_EMAIL": "",
        "JIRA_API_TOKEN": "",
        "JIRA_PROJECT_KEY": "",
        "GITHUB_ACTIONS_OWNER": "",
        "GITHUB_ACTIONS_REPO": "",
        "GITHUB_ACTIONS_WORKFLOW_ID": "",
        "GITHUB_ACTIONS_TOKEN": "",
        "GITHUB_ACTIONS_ENABLED": "",
        "GITLAB_CI_PROJECT_ID": "",
        "GITLAB_CI_TRIGGER_TOKEN": "",
        "GITLAB_CI_ENABLED": "",
        "GENERIC_CI_WEBHOOK_URL": "",
        "GENERIC_CI_WEBHOOK_BEARER_TOKEN": "",
        "GENERIC_CI_WEBHOOK_ENABLED": "",
    }
    overrides.update(
        _build_llm_overrides(normalized_llm_provider, resolved_llm_api_key)
    )
    return overrides


def _render_output(template_lines: list[str], overrides: dict[str, str]) -> str:
    rendered = render_env(template_lines, overrides)
    header = [
        "# Managed runtime environment scaffold.",
        "# Generated by scripts/generate_managed_runtime_env.py.",
        "# Existing values are preserved on regeneration unless you explicitly override them.",
        "# Values containing REPLACE_WITH_ must be replaced with live operator/provider values before deployment.",
        "",
    ]
    return "\n".join(header + rendered.splitlines())


def generate_managed_runtime_env(
    *,
    template_path: Path,
    output_path: Path,
    report_path: Path,
    environment: str,
    api_url: str | None = None,
    frontend_url: str | None = None,
    database_url: str | None = None,
    supabase_url: str | None = None,
    supabase_anon_key: str | None = None,
    supabase_jwt_secret: str | None = None,
    gcp_project_id: str | None = None,
    gcp_region: str | None = None,
    gcp_cloud_tasks_queue: str | None = None,
    gcp_cloud_tasks_invoker_service_account_email: str | None = None,
    gcp_cloud_run_service_name: str | None = None,
    gcp_cloud_run_batch_job_name: str | None = None,
    gcp_internal_allowed_service_accounts: list[str] | None = None,
    llm_provider: str | None = None,
    llm_api_key: str | None = None,
    paystack_secret_key: str | None = None,
    paystack_public_key: str | None = None,
    trusted_proxy_cidrs: list[str] | None = None,
) -> dict[str, Any]:
    normalized_environment = str(environment or "").strip().lower()
    if normalized_environment not in SUPPORTED_ENVIRONMENTS:
        raise ValueError(
            "environment must be one of: " + ", ".join(SUPPORTED_ENVIRONMENTS)
        )
    template_resolved = template_path.resolve()
    output_resolved = output_path.resolve()
    report_resolved = report_path.resolve()
    if len({template_resolved, output_resolved, report_resolved}) != 3:
        raise ValueError(
            "template_path, output_path, and report_path must be different files"
        )
    protected_paths = _protected_output_paths()
    for field_name, resolved in (
        ("output_path", output_resolved),
        ("report_path", report_resolved),
    ):
        if resolved in protected_paths:
            raise ValueError(
                f"{field_name} must not overwrite runtime source, template, or validator files"
            )
    if not template_path.exists():
        raise FileNotFoundError(
            f"Template file does not exist: {template_path.as_posix()}"
        )
    if not template_path.is_file():
        raise ValueError(f"template_path must be a file: {template_path.as_posix()}")
    if output_path.exists() and not output_path.is_file():
        raise ValueError(f"output_path must be a file path: {output_path.as_posix()}")
    if report_path.exists() and not report_path.is_file():
        raise ValueError(f"report_path must be a file path: {report_path.as_posix()}")
    _ensure_parent_dir(output_path, field_name="output_path")
    _ensure_parent_dir(report_path, field_name="report_path")

    existing_values = parse_env_file(output_path) if output_path.exists() else {}

    overrides = _build_overrides(
        environment=normalized_environment,
        existing_values=existing_values,
        api_url=api_url,
        frontend_url=frontend_url,
        database_url=database_url,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
        supabase_jwt_secret=supabase_jwt_secret,
        gcp_project_id=gcp_project_id,
        gcp_region=gcp_region,
        gcp_cloud_tasks_queue=gcp_cloud_tasks_queue,
        gcp_cloud_tasks_invoker_service_account_email=(
            gcp_cloud_tasks_invoker_service_account_email
        ),
        gcp_cloud_run_service_name=gcp_cloud_run_service_name,
        gcp_cloud_run_batch_job_name=gcp_cloud_run_batch_job_name,
        gcp_internal_allowed_service_accounts=gcp_internal_allowed_service_accounts,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        paystack_secret_key=paystack_secret_key,
        paystack_public_key=paystack_public_key,
        trusted_proxy_cidrs=trusted_proxy_cidrs,
    )
    rendered = _render_output(
        template_path.read_text(encoding="utf-8").splitlines(),
        overrides,
    )

    declared_external_placeholders = _identify_unresolved_keys(
        overrides,
        DECLARED_EXTERNAL_VALUE_KEYS,
    )
    runtime_validation_blockers = _identify_unresolved_keys(
        overrides,
        RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS,
    )
    report = {
        "environment": normalized_environment,
        "output_path": output_path.as_posix(),
        "resolved_public_runtime_values": {
            "API_URL": overrides["API_URL"],
            "FRONTEND_URL": overrides["FRONTEND_URL"],
        },
        "generated_internal_secret_keys": list(INTERNAL_SECRET_KEYS),
        "required_operator_input_keys": _required_operator_input_keys(overrides),
        "unresolved_external_keys": declared_external_placeholders,
        "declared_external_placeholders": declared_external_placeholders,
        "runtime_validation_blockers": runtime_validation_blockers,
        "declared_but_not_runtime_required": list(DECLARED_NONBLOCKING_EXTERNAL_KEYS),
        "derived_external_keys": list(DERIVED_EXTERNAL_KEYS),
        "validation_ready": not runtime_validation_blockers,
        "validation_command": (
            "uv run python scripts/validate_runtime_env.py "
            f"--environment {normalized_environment} --env-file {output_path.as_posix()}"
        ),
        "migration_command": "uv run alembic upgrade head",
    }
    staged_output = _stage_text_file(output_path, rendered)
    staged_report: Path | None = None
    promotion_completed = False
    try:
        staged_report = _stage_text_file(
            report_path,
            json.dumps(report, indent=2, sort_keys=True),
        )
        staged_output.replace(output_path)
        staged_report.replace(report_path)
        promotion_completed = True
    finally:
        if not promotion_completed:
            staged_output.unlink(missing_ok=True)
            if staged_report is not None:
                staged_report.unlink(missing_ok=True)
            output_path.unlink(missing_ok=True)
            report_path.unlink(missing_ok=True)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a managed-runtime env scaffold for staging or production. "
            "Existing values are preserved on regeneration; unresolved provider inputs remain explicit placeholders unless provided."
        )
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=SUPPORTED_ENVIRONMENTS,
        help="Target environment to scaffold.",
    )
    parser.add_argument(
        "--template-path",
        type=Path,
        default=DEFAULT_TEMPLATE_PATH,
        help="Path to source template file (default: .env.example).",
    )
    parser.add_argument(
        "--output-path",
        type=Path,
        default=None,
        help="Path for generated env file (default: .runtime/<environment>.env).",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=None,
        help="Path for generated JSON report (default: .runtime/<environment>.report.json).",
    )
    parser.add_argument("--api-url", default=None)
    parser.add_argument("--frontend-url", default=None)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--supabase-url", default=None)
    parser.add_argument("--supabase-anon-key", default=None)
    parser.add_argument("--supabase-jwt-secret", default=None)
    parser.add_argument("--gcp-project-id", default=None)
    parser.add_argument("--gcp-region", default=None)
    parser.add_argument("--gcp-cloud-tasks-queue", default=None)
    parser.add_argument("--gcp-cloud-tasks-invoker-service-account-email", default=None)
    parser.add_argument("--gcp-cloud-run-service-name", default=None)
    parser.add_argument("--gcp-cloud-run-batch-job-name", default=None)
    parser.add_argument(
        "--gcp-internal-allowed-service-account",
        action="append",
        dest="gcp_internal_allowed_service_accounts",
        default=None,
        help=(
            "Allowed internal Google service account email. "
            "Provide more than once for multiple values."
        ),
    )
    parser.add_argument(
        "--llm-provider",
        default=None,
        choices=SUPPORTED_LLM_PROVIDERS,
    )
    parser.add_argument("--llm-api-key", default=None)
    parser.add_argument("--paystack-secret-key", default=None)
    parser.add_argument("--paystack-public-key", default=None)
    parser.add_argument(
        "--trusted-proxy-cidr",
        action="append",
        dest="trusted_proxy_cidrs",
        default=None,
        help="Trusted proxy CIDR. Provide more than once for multiple values.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    template_path = (
        _resolve_default_path(DEFAULT_TEMPLATE_PATH)
        if args.template_path == DEFAULT_TEMPLATE_PATH
        else _resolve_cli_path(args.template_path, field_name="template_path")
    )
    output_path = (
        _resolve_default_path(DEFAULT_OUTPUT_DIR / f"{args.environment}.env")
        if args.output_path is None
        else _resolve_cli_path(args.output_path, field_name="output_path")
    )
    report_path = (
        _resolve_default_path(DEFAULT_OUTPUT_DIR / f"{args.environment}.report.json")
        if args.report_path is None
        else _resolve_cli_path(args.report_path, field_name="report_path")
    )
    report = generate_managed_runtime_env(
        template_path=template_path,
        output_path=output_path,
        report_path=report_path,
        environment=str(args.environment),
        api_url=args.api_url,
        frontend_url=args.frontend_url,
        database_url=args.database_url,
        supabase_url=args.supabase_url,
        supabase_anon_key=args.supabase_anon_key,
        supabase_jwt_secret=args.supabase_jwt_secret,
        gcp_project_id=args.gcp_project_id,
        gcp_region=args.gcp_region,
        gcp_cloud_tasks_queue=args.gcp_cloud_tasks_queue,
        gcp_cloud_tasks_invoker_service_account_email=(
            args.gcp_cloud_tasks_invoker_service_account_email
        ),
        gcp_cloud_run_service_name=args.gcp_cloud_run_service_name,
        gcp_cloud_run_batch_job_name=args.gcp_cloud_run_batch_job_name,
        gcp_internal_allowed_service_accounts=(
            args.gcp_internal_allowed_service_accounts
        ),
        llm_provider=args.llm_provider,
        llm_api_key=args.llm_api_key,
        paystack_secret_key=args.paystack_secret_key,
        paystack_public_key=args.paystack_public_key,
        trusted_proxy_cidrs=args.trusted_proxy_cidrs,
    )
    print(
        "[managed-runtime-env] ok "
        f"environment={report['environment']} "
        f"output={report['output_path']} "
        f"validation_ready={report['validation_ready']} "
        f"runtime_blockers={len(report['runtime_validation_blockers'])} "
        f"declared_placeholders={len(report['declared_external_placeholders'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
