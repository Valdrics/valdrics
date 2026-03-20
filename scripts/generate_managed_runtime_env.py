#!/usr/bin/env python3
"""Generate staging/production managed-runtime env scaffolds plus an unresolved-value report."""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import tempfile
from pathlib import Path
import re
import secrets
import sys
from typing import Any
from urllib.parse import urlparse

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import render_env


DEFAULT_TEMPLATE_PATH = Path(".env.example")
DEFAULT_OUTPUT_DIR = Path(".runtime")
PLACEHOLDER_PREFIX = "REPLACE_WITH_"
DEFAULT_LLM_PROVIDER = "groq"
SUPPORTED_ENVIRONMENTS = ("staging", "production")
SUPPORTED_LLM_PROVIDERS = ("groq", "openai", "claude", "google")

DECLARED_EXTERNAL_VALUE_KEYS = (
    "API_URL",
    "FRONTEND_URL",
    "CORS_ORIGINS",
    "DATABASE_URL",
    "REDIS_URL",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_JWT_SECRET",
    "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN",
    "PAYSTACK_SECRET_KEY",
    "PAYSTACK_PUBLIC_KEY",
    "SENTRY_DSN",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "TRUSTED_PROXY_CIDRS",
)
RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS = (
    "API_URL",
    "FRONTEND_URL",
    "DATABASE_URL",
    "REDIS_URL",
    "SUPABASE_JWT_SECRET",
    "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN",
    "PAYSTACK_SECRET_KEY",
    "PAYSTACK_PUBLIC_KEY",
    "SENTRY_DSN",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "TRUSTED_PROXY_CIDRS",
)
DERIVED_EXTERNAL_KEYS = ("CORS_ORIGINS",)
DECLARED_NONBLOCKING_EXTERNAL_KEYS = ("SUPABASE_URL", "SUPABASE_ANON_KEY")

INTERNAL_SECRET_KEYS = (
    "CSRF_SECRET_KEY",
    "ENCRYPTION_KEY",
    "KDF_SALT",
    "ADMIN_API_KEY",
    "INTERNAL_JOB_SECRET",
    "INTERNAL_METRICS_AUTH_TOKEN",
    "ENFORCEMENT_APPROVAL_TOKEN_SECRET",
    "ENFORCEMENT_EXPORT_SIGNING_SECRET",
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_default_path(path: Path) -> Path:
    return (_repo_root() / path).resolve()


def _resolve_cli_path(path: Path, *, field_name: str) -> Path:
    raw = Path(path).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    resolved = (_repo_root() / raw).resolve()
    try:
        resolved.relative_to(_repo_root())
    except ValueError as exc:
        raise ValueError(f"{field_name} must stay within repo root when relative") from exc
    return resolved


def _protected_output_paths() -> set[Path]:
    repo_root = _repo_root()
    return {
        Path(__file__).resolve(),
        repo_root / ".env.example",
        repo_root / "scripts" / "validate_runtime_env.py",
        repo_root / "docs" / "ops" / "evidence" / "enforcement_failure_injection_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "enforcement_failure_injection_2026-02-27.json",
        repo_root / "docs" / "ops" / "evidence" / "enforcement_stress_artifact_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "enforcement_stress_artifact_2026-02-27.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_committee_packet_assumptions_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_committee_packet_assumptions_2026-02-28.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_guardrails_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_guardrails_2026-02-27.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_telemetry_snapshot_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "finance_telemetry_snapshot_2026-02-28.json",
        repo_root / "docs" / "ops" / "feature_enforceability_matrix_2026-02-27.json",
        repo_root / "docs" / "ops" / "key-rotation-drill-2026-02-27.md",
        repo_root / "docs" / "ops" / "evidence" / "pkg_fin_policy_decisions_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "pkg_fin_policy_decisions_2026-02-28.json",
        repo_root / "docs" / "ops" / "evidence" / "pricing_benchmark_register_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "pricing_benchmark_register_2026-02-27.json",
        repo_root / "docs" / "ops" / "evidence" / "valdrics_disposition_register_TEMPLATE.json",
        repo_root / "docs" / "ops" / "evidence" / "valdrics_disposition_register_2026-02-28.json",
    }


def _ensure_parent_dir(path: Path, *, field_name: str) -> None:
    current = path.parent
    while True:
        if current.exists():
            if not current.is_dir():
                raise ValueError(
                    f"{field_name} parent must be a directory path: {current.as_posix()}"
                )
            return
        if current == current.parent:
            return
        current = current.parent


def _stage_text_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.stem}.",
        suffix=f"{path.suffix}.tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
    return temp_path


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


def _default_aws_assume_role_trust_principal_arn() -> str:
    return "arn:aws:iam::123456789012:role/REPLACE_WITH_VALDRICS_CONTROL_PLANE_ROLE"


def _default_redis_url() -> str:
    return "redis://REPLACE_WITH_REDIS_HOST:6379/0"


def _default_sentry_dsn() -> str:
    return (
        "https://REPLACE_WITH_SENTRY_KEY@REPLACE_WITH_SENTRY_HOST/"
        "REPLACE_WITH_SENTRY_PROJECT"
    )


def _default_otel_endpoint() -> str:
    return "https://REPLACE_WITH_OTEL_COLLECTOR:4317"


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
            raise ValueError(f"trusted_proxy_cidrs contains invalid CIDR: {cidr}") from exc
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
        raise ValueError(f"{field_name} must use an explicit https:// URL in staging/production.")
    if parsed.username or parsed.password:
        raise ValueError(f"{field_name} must not include embedded credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{field_name} must not include query strings or fragments.")

    hostname = str(parsed.hostname or "").strip().lower()
    if not hostname or hostname == "localhost":
        raise ValueError(f"{field_name} must not point at localhost in staging/production.")

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
) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    if environment == "production" and not normalized.startswith(required_prefix):
        raise ValueError(
            f"{field_name} must be a live key ({required_prefix}...) in production."
        )
    return normalized


def _normalize_aws_principal_arn(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        raise ValueError("AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN must be a non-empty string")
    arn_pattern = re.compile(
        r"^arn:(aws|aws-us-gov|aws-cn):iam::\d{12}:(root|role\/[\w+=,.@\-_/]+|user\/[\w+=,.@\-_/]+)$"
    )
    if not arn_pattern.fullmatch(normalized):
        raise ValueError(
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN must be an IAM principal ARN "
            "(role, user, or account root)."
        )
    return normalized


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


def _build_overrides(
    *,
    environment: str,
    api_url: str | None,
    frontend_url: str | None,
    database_url: str | None,
    redis_url: str | None,
    supabase_url: str | None,
    supabase_anon_key: str | None,
    supabase_jwt_secret: str | None,
    aws_assume_role_trust_principal_arn: str | None,
    llm_provider: str,
    llm_api_key: str | None,
    paystack_secret_key: str | None,
    paystack_public_key: str | None,
    sentry_dsn: str | None,
    otel_endpoint: str | None,
    trusted_proxy_cidrs: list[str] | None,
) -> dict[str, str]:
    normalized_trusted_proxy_cidrs = _normalize_trusted_proxy_cidrs(trusted_proxy_cidrs)
    resolved_api_url = _normalize_strict_public_url(api_url, field_name="API_URL") or _default_api_url()
    resolved_frontend_url = (
        _normalize_strict_public_url(frontend_url, field_name="FRONTEND_URL")
        or _default_frontend_url()
    )
    normalized_sentry_dsn = _normalize_optional_http_url(
        sentry_dsn,
        field_name="SENTRY_DSN",
    )
    normalized_otel_endpoint = _normalize_optional_http_url(
        otel_endpoint,
        field_name="OTEL_EXPORTER_OTLP_ENDPOINT",
    )
    normalized_paystack_secret_key = _normalize_paystack_key(
        paystack_secret_key,
        field_name="PAYSTACK_SECRET_KEY",
        environment=environment,
        required_prefix="sk_live_",
    )
    normalized_paystack_public_key = _normalize_paystack_key(
        paystack_public_key,
        field_name="PAYSTACK_PUBLIC_KEY",
        environment=environment,
        required_prefix="pk_live_",
    )
    normalized_aws_assume_role_trust_principal_arn = _normalize_aws_principal_arn(
        aws_assume_role_trust_principal_arn
    )

    overrides: dict[str, str] = {
        "APP_NAME": "Valdrics",
        "DEBUG": "false",
        "TESTING": "false",
        "ENVIRONMENT": environment,
        "ENABLE_SCHEDULER": "true",
        "WEB_CONCURRENCY": "2",
        "APP_RUNTIME_DATA_DIR": "/tmp/valdrics",
        "API_URL": resolved_api_url,
        "FRONTEND_URL": resolved_frontend_url,
        "CORS_ORIGINS": _render_cors_origins(resolved_frontend_url),
        "DATABASE_URL": database_url or _default_database_url(),
        "DB_SSL_MODE": "require",
        "DB_USE_NULL_POOL": "false",
        "DB_EXTERNAL_POOLER": "false",
        "REDIS_URL": redis_url or _default_redis_url(),
        "SUPABASE_URL": supabase_url or _default_supabase_url(),
        "SUPABASE_ANON_KEY": supabase_anon_key or _default_supabase_anon_key(),
        "SUPABASE_JWT_SECRET": supabase_jwt_secret or _default_supabase_jwt_secret(),
        "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN": (
            normalized_aws_assume_role_trust_principal_arn
            or _default_aws_assume_role_trust_principal_arn()
        ),
        "CSRF_SECRET_KEY": _generate_hex(64),
        "ENCRYPTION_KEY": _generate_urlsafe_b64(32),
        "KDF_SALT": _generate_b64(32),
        "ADMIN_API_KEY": _generate_hex(64),
        "INTERNAL_JOB_SECRET": _generate_hex(64),
        "INTERNAL_METRICS_AUTH_TOKEN": _generate_hex(64),
        "ENFORCEMENT_APPROVAL_TOKEN_SECRET": _generate_hex(64),
        "ENFORCEMENT_EXPORT_SIGNING_SECRET": _generate_hex(64),
        "PAYSTACK_SECRET_KEY": normalized_paystack_secret_key or _default_paystack_secret_key(),
        "PAYSTACK_PUBLIC_KEY": normalized_paystack_public_key or _default_paystack_public_key(),
        "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY": "NGN",
        "PAYSTACK_ENABLE_USD_CHECKOUT": "false",
        "ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION": "false",
        "SAAS_STRICT_INTEGRATIONS": "true",
        "EXPOSE_API_DOCUMENTATION_PUBLICLY": "false",
        "OTEL_LOGS_EXPORT_ENABLED": "true",
        "OTEL_EXPORTER_OTLP_ENDPOINT": normalized_otel_endpoint or _default_otel_endpoint(),
        "SENTRY_DSN": normalized_sentry_dsn or _default_sentry_dsn(),
        "TRUST_PROXY_HEADERS": "true",
        "TRUSTED_PROXY_HOPS": "1",
        "TRUSTED_PROXY_CIDRS": _render_trusted_proxy_cidrs(normalized_trusted_proxy_cidrs),
        "CIRCUIT_BREAKER_DISTRIBUTED_STATE": "true",
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
    overrides.update(_build_llm_overrides(llm_provider, llm_api_key))
    return overrides


def _selected_llm_provider_key(values: dict[str, str]) -> str | None:
    llm_provider = str(values.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER) or "").strip().lower()
    return {
        "groq": "GROQ_API_KEY",
        "openai": "OPENAI_API_KEY",
        "claude": "CLAUDE_API_KEY",
        "google": "GOOGLE_API_KEY",
    }.get(llm_provider)


def _identify_unresolved_keys(values: dict[str, str], candidate_keys: tuple[str, ...]) -> list[str]:
    unresolved: list[str] = []
    for key in candidate_keys:
        value = str(values.get(key, "") or "").strip()
        if not value or PLACEHOLDER_PREFIX in value:
            unresolved.append(key)

    provider_key = _selected_llm_provider_key(values)
    if provider_key:
        provider_value = str(values.get(provider_key, "") or "").strip()
        if not provider_value or PLACEHOLDER_PREFIX in provider_value:
            unresolved.append(provider_key)

    return sorted(set(unresolved))


def _required_operator_input_keys(values: dict[str, str]) -> list[str]:
    required_keys = list(RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS)
    provider_key = _selected_llm_provider_key(values)
    if provider_key:
        required_keys.append(provider_key)
    return sorted(set(required_keys))


def _render_output(template_lines: list[str], overrides: dict[str, str]) -> str:
    rendered = render_env(template_lines, overrides)
    header = [
        "# Managed runtime environment scaffold.",
        "# Generated by scripts/generate_managed_runtime_env.py.",
        "# Internal application secrets in this file are freshly generated.",
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
    redis_url: str | None = None,
    supabase_url: str | None = None,
    supabase_anon_key: str | None = None,
    supabase_jwt_secret: str | None = None,
    aws_assume_role_trust_principal_arn: str | None = None,
    llm_provider: str = DEFAULT_LLM_PROVIDER,
    llm_api_key: str | None = None,
    paystack_secret_key: str | None = None,
    paystack_public_key: str | None = None,
    sentry_dsn: str | None = None,
    otel_endpoint: str | None = None,
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
    for field_name, resolved in (("output_path", output_resolved), ("report_path", report_resolved)):
        if resolved in protected_paths:
            raise ValueError(
                f"{field_name} must not overwrite runtime source, template, or validator files"
            )
    if not template_path.exists():
        raise FileNotFoundError(f"Template file does not exist: {template_path.as_posix()}")
    if not template_path.is_file():
        raise ValueError(f"template_path must be a file: {template_path.as_posix()}")
    if output_path.exists() and not output_path.is_file():
        raise ValueError(f"output_path must be a file path: {output_path.as_posix()}")
    if report_path.exists() and not report_path.is_file():
        raise ValueError(f"report_path must be a file path: {report_path.as_posix()}")
    _ensure_parent_dir(output_path, field_name="output_path")
    _ensure_parent_dir(report_path, field_name="report_path")

    overrides = _build_overrides(
        environment=normalized_environment,
        api_url=api_url,
        frontend_url=frontend_url,
        database_url=database_url,
        redis_url=redis_url,
        supabase_url=supabase_url,
        supabase_anon_key=supabase_anon_key,
        supabase_jwt_secret=supabase_jwt_secret,
        aws_assume_role_trust_principal_arn=aws_assume_role_trust_principal_arn,
        llm_provider=llm_provider,
        llm_api_key=llm_api_key,
        paystack_secret_key=paystack_secret_key,
        paystack_public_key=paystack_public_key,
        sentry_dsn=sentry_dsn,
        otel_endpoint=otel_endpoint,
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
    try:
        staged_report = _stage_text_file(
            report_path,
            json.dumps(report, indent=2, sort_keys=True),
        )
    except Exception:
        staged_output.unlink(missing_ok=True)
        raise
    try:
        staged_output.replace(output_path)
        staged_report.replace(report_path)
    except Exception:
        staged_output.unlink(missing_ok=True)
        staged_report.unlink(missing_ok=True)
        output_path.unlink(missing_ok=True)
        report_path.unlink(missing_ok=True)
        raise
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a managed-runtime env scaffold for staging or production. "
            "Internal secrets are generated; external provider values remain explicit placeholders unless provided."
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
    parser.add_argument("--redis-url", default=None)
    parser.add_argument("--supabase-url", default=None)
    parser.add_argument("--supabase-anon-key", default=None)
    parser.add_argument("--supabase-jwt-secret", default=None)
    parser.add_argument("--aws-assume-role-trust-principal-arn", default=None)
    parser.add_argument(
        "--llm-provider",
        default=DEFAULT_LLM_PROVIDER,
        choices=SUPPORTED_LLM_PROVIDERS,
    )
    parser.add_argument("--llm-api-key", default=None)
    parser.add_argument("--paystack-secret-key", default=None)
    parser.add_argument("--paystack-public-key", default=None)
    parser.add_argument("--sentry-dsn", default=None)
    parser.add_argument("--otel-endpoint", default=None)
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
        redis_url=args.redis_url,
        supabase_url=args.supabase_url,
        supabase_anon_key=args.supabase_anon_key,
        supabase_jwt_secret=args.supabase_jwt_secret,
        aws_assume_role_trust_principal_arn=args.aws_assume_role_trust_principal_arn,
        llm_provider=str(args.llm_provider),
        llm_api_key=args.llm_api_key,
        paystack_secret_key=args.paystack_secret_key,
        paystack_public_key=args.paystack_public_key,
        sentry_dsn=args.sentry_dsn,
        otel_endpoint=args.otel_endpoint,
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
