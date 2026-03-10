#!/usr/bin/env python3
"""Generate staging/production managed-runtime env scaffolds plus an unresolved-value report."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path
import secrets
import sys
from typing import Any

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
    "SUPABASE_JWT_SECRET",
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
    "PAYSTACK_SECRET_KEY",
    "PAYSTACK_PUBLIC_KEY",
    "SENTRY_DSN",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "TRUSTED_PROXY_CIDRS",
)
DERIVED_EXTERNAL_KEYS = ("CORS_ORIGINS",)
DECLARED_NONBLOCKING_EXTERNAL_KEYS = ("SUPABASE_URL",)

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


def _default_supabase_jwt_secret() -> str:
    return "REPLACE_WITH_SUPABASE_JWT_SECRET_MINIMUM_32_CHARS_VALUE"


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
    supabase_jwt_secret: str | None,
    llm_provider: str,
    llm_api_key: str | None,
    paystack_secret_key: str | None,
    paystack_public_key: str | None,
    sentry_dsn: str | None,
    otel_endpoint: str | None,
    trusted_proxy_cidrs: list[str] | None,
) -> dict[str, str]:
    resolved_api_url = api_url or _default_api_url()
    resolved_frontend_url = frontend_url or _default_frontend_url()

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
        "SUPABASE_JWT_SECRET": supabase_jwt_secret or _default_supabase_jwt_secret(),
        "CSRF_SECRET_KEY": _generate_hex(64),
        "ENCRYPTION_KEY": _generate_urlsafe_b64(32),
        "KDF_SALT": _generate_b64(32),
        "ADMIN_API_KEY": _generate_hex(64),
        "INTERNAL_JOB_SECRET": _generate_hex(64),
        "INTERNAL_METRICS_AUTH_TOKEN": _generate_hex(64),
        "ENFORCEMENT_APPROVAL_TOKEN_SECRET": _generate_hex(64),
        "ENFORCEMENT_EXPORT_SIGNING_SECRET": _generate_hex(64),
        "PAYSTACK_SECRET_KEY": paystack_secret_key or _default_paystack_secret_key(),
        "PAYSTACK_PUBLIC_KEY": paystack_public_key or _default_paystack_public_key(),
        "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY": "NGN",
        "PAYSTACK_ENABLE_USD_CHECKOUT": "false",
        "ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION": "false",
        "SAAS_STRICT_INTEGRATIONS": "true",
        "EXPOSE_API_DOCUMENTATION_PUBLICLY": "false",
        "OTEL_LOGS_EXPORT_ENABLED": "true",
        "OTEL_EXPORTER_OTLP_ENDPOINT": otel_endpoint or _default_otel_endpoint(),
        "SENTRY_DSN": sentry_dsn or _default_sentry_dsn(),
        "TRUST_PROXY_HEADERS": "true",
        "TRUSTED_PROXY_HOPS": "1",
        "TRUSTED_PROXY_CIDRS": _render_trusted_proxy_cidrs(trusted_proxy_cidrs),
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
    supabase_jwt_secret: str | None = None,
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
    if not template_path.exists():
        raise FileNotFoundError(f"Template file does not exist: {template_path.as_posix()}")

    overrides = _build_overrides(
        environment=normalized_environment,
        api_url=api_url,
        frontend_url=frontend_url,
        database_url=database_url,
        redis_url=redis_url,
        supabase_url=supabase_url,
        supabase_jwt_secret=supabase_jwt_secret,
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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")

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
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
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
    parser.add_argument("--supabase-jwt-secret", default=None)
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
    output_path = args.output_path or (
        DEFAULT_OUTPUT_DIR / f"{args.environment}.env"
    )
    report_path = args.report_path or (
        DEFAULT_OUTPUT_DIR / f"{args.environment}.report.json"
    )
    report = generate_managed_runtime_env(
        template_path=args.template_path.resolve(),
        output_path=output_path.resolve(),
        report_path=report_path.resolve(),
        environment=str(args.environment),
        api_url=args.api_url,
        frontend_url=args.frontend_url,
        database_url=args.database_url,
        redis_url=args.redis_url,
        supabase_url=args.supabase_url,
        supabase_jwt_secret=args.supabase_jwt_secret,
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
