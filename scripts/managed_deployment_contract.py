"""Shared contract constants/helpers for managed runtime, migration, and deployment tooling."""

from __future__ import annotations

from collections.abc import Mapping


PLACEHOLDER_PREFIX = "REPLACE_WITH_"
SUPPORTED_ENVIRONMENTS = ("staging", "production")

DEFAULT_LLM_PROVIDER = "groq"
SUPPORTED_LLM_PROVIDERS = ("groq", "openai", "claude", "google")
LLM_PROVIDER_ENV_KEY = {
    "groq": "GROQ_API_KEY",
    "openai": "OPENAI_API_KEY",
    "claude": "CLAUDE_API_KEY",
    "google": "GOOGLE_API_KEY",
}
LLM_PROVIDER_SECRET_NAME = {
    "groq": "valdrics-groq-key",
    "openai": "valdrics-openai-key",
    "claude": "valdrics-claude-key",
    "google": "valdrics-google-key",
}

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

SUPPORTED_DB_SSL_MODES = ("disable", "require", "verify-ca", "verify-full")
MIGRATION_BASE_REQUIRED_OPERATOR_INPUT_KEYS = ("DATABASE_URL",)

RUNTIME_BLOCKER_KEYS = RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS
KOYEB_DASHBOARD_PUBLIC_ENV_KEYS = (
    "PUBLIC_API_URL",
    "PUBLIC_SUPABASE_ANON_KEY",
    "PUBLIC_SUPABASE_URL",
)
TERRAFORM_BASE_REQUIRED_INPUTS = ("external_id", "valdrics_account_id")


def contains_placeholder(value: str | None) -> bool:
    return PLACEHOLDER_PREFIX in str(value or "")


def selected_llm_provider(values: Mapping[str, object]) -> str:
    normalized = str(values.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER) or "").strip().lower()
    if normalized not in LLM_PROVIDER_ENV_KEY:
        raise ValueError(
            "LLM_PROVIDER must be one of: " + ", ".join(sorted(LLM_PROVIDER_ENV_KEY))
        )
    return normalized


def selected_llm_provider_env_key(values: Mapping[str, object]) -> str:
    return LLM_PROVIDER_ENV_KEY[selected_llm_provider(values)]


def identify_runtime_unresolved_keys(
    values: Mapping[str, object],
    candidate_keys: tuple[str, ...],
) -> list[str]:
    unresolved: list[str] = []
    for key in candidate_keys:
        value = str(values.get(key, "") or "").strip()
        if not value or contains_placeholder(value):
            unresolved.append(key)

    provider_key = selected_llm_provider_env_key(values)
    provider_value = str(values.get(provider_key, "") or "").strip()
    if not provider_value or contains_placeholder(provider_value):
        unresolved.append(provider_key)

    return sorted(set(unresolved))


def required_runtime_operator_input_keys(values: Mapping[str, object]) -> list[str]:
    required_keys = list(RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS)
    required_keys.append(selected_llm_provider_env_key(values))
    return sorted(set(required_keys))


def required_migration_operator_input_keys(values: Mapping[str, object]) -> list[str]:
    required_keys = list(MIGRATION_BASE_REQUIRED_OPERATOR_INPUT_KEYS)
    db_ssl_mode = str(values.get("DB_SSL_MODE", "require") or "require").strip().lower()
    if db_ssl_mode in {"verify-ca", "verify-full"}:
        required_keys.append("DB_SSL_CA_CERT_PATH")
    return required_keys
