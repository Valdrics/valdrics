"""Shared contract constants/helpers for managed runtime, migration, and deployment tooling."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


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
    "GCP_PROJECT_ID",
    "GCP_REGION",
    "GCP_CLOUD_TASKS_QUEUE",
    "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL",
    "GCP_CLOUD_RUN_SERVICE_NAME",
    "GCP_CLOUD_RUN_BATCH_JOB_NAME",
    "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "SUPABASE_JWT_SECRET",
    "PAYSTACK_SECRET_KEY",
    "PAYSTACK_PUBLIC_KEY",
    "TRUSTED_PROXY_CIDRS",
)

RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS = (
    "API_URL",
    "FRONTEND_URL",
    "DATABASE_URL",
    "GCP_PROJECT_ID",
    "GCP_REGION",
    "GCP_CLOUD_TASKS_QUEUE",
    "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL",
    "GCP_CLOUD_RUN_SERVICE_NAME",
    "GCP_CLOUD_RUN_BATCH_JOB_NAME",
    "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS",
    "SUPABASE_JWT_SECRET",
    "PAYSTACK_SECRET_KEY",
    "PAYSTACK_PUBLIC_KEY",
    "TRUSTED_PROXY_CIDRS",
)

DERIVED_EXTERNAL_KEYS = ("CORS_ORIGINS",)
DECLARED_NONBLOCKING_EXTERNAL_KEYS = (
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
)

GITHUB_RUNTIME_PLAIN_JSON_KEYS = (
    "ENVIRONMENT",
    "API_URL",
    "FRONTEND_URL",
    "CORS_ORIGINS",
    "GCP_PROJECT_ID",
    "GCP_REGION",
    "GCP_CLOUD_TASKS_QUEUE",
    "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL",
    "GCP_CLOUD_RUN_SERVICE_NAME",
    "GCP_CLOUD_RUN_BATCH_JOB_NAME",
    "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS",
    "TRUSTED_PROXY_CIDRS",
    "PLATFORM_RUNTIME_PROFILE",
    "OBSERVABILITY_BACKEND",
    "PUBLIC_API_RATE_LIMITING_BACKEND",
    "RATELIMIT_ENABLED",
    "SUPABASE_URL",
    "SUPABASE_ANON_KEY",
    "LLM_PROVIDER",
    "PAYSTACK_ACTIVATION_PENDING",
    "EXPOSE_API_DOCUMENTATION_PUBLICLY",
    "SAAS_STRICT_INTEGRATIONS",
    "TRUST_PROXY_HEADERS",
)

INTERNAL_SECRET_KEYS = (
    "CSRF_SECRET_KEY",
    "ENCRYPTION_KEY",
    "KDF_SALT",
    "ADMIN_API_KEY",
    "INTERNAL_METRICS_AUTH_TOKEN",
    "ENFORCEMENT_APPROVAL_TOKEN_SECRET",
    "ENFORCEMENT_EXPORT_SIGNING_SECRET",
)

GITHUB_RUNTIME_SECRET_JSON_KEYS = (
    "DATABASE_URL",
    "SUPABASE_JWT_SECRET",
    "PAYSTACK_SECRET_KEY",
    "PAYSTACK_PUBLIC_KEY",
    *INTERNAL_SECRET_KEYS,
    *tuple(LLM_PROVIDER_ENV_KEY.values()),
)

PAYSTACK_RUNTIME_KEY_NAMES = ("PAYSTACK_SECRET_KEY", "PAYSTACK_PUBLIC_KEY")

SUPPORTED_DB_SSL_MODES = ("disable", "require", "verify-ca", "verify-full")
MIGRATION_BASE_REQUIRED_OPERATOR_INPUT_KEYS = ("DATABASE_URL",)

RUNTIME_BLOCKER_KEYS = RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS
CLOUDFLARE_PAGES_PUBLIC_ENV_KEYS = (
    "PUBLIC_API_URL",
    "PUBLIC_SUPABASE_ANON_KEY",
    "PUBLIC_SUPABASE_URL",
)
TERRAFORM_BASE_REQUIRED_INPUTS = (
    "gcp_project_id",
    "gcp_region",
    "cloudflare_account_id",
    "cloudflare_zone_id",
    "cloudflare_pages_project_name",
    "cloudflare_pages_production_branch",
    "supabase_organization_id",
    "supabase_project_ref",
    "supabase_project_name",
    "supabase_region",
)


def contains_placeholder(value: str | None) -> bool:
    return PLACEHOLDER_PREFIX in str(value or "")


def _is_truthy(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def selected_llm_provider(values: Mapping[str, object]) -> str:
    normalized = (
        str(values.get("LLM_PROVIDER", DEFAULT_LLM_PROVIDER) or "").strip().lower()
    )
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
    paystack_activation_pending = _is_truthy(
        values.get("PAYSTACK_ACTIVATION_PENDING", False)
    )
    for key in candidate_keys:
        if paystack_activation_pending and key in PAYSTACK_RUNTIME_KEY_NAMES:
            continue
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
    if _is_truthy(values.get("PAYSTACK_ACTIVATION_PENDING", False)):
        required_keys = [
            key for key in required_keys if key not in PAYSTACK_RUNTIME_KEY_NAMES
        ]
    required_keys.append(selected_llm_provider_env_key(values))
    return sorted(set(required_keys))


def required_migration_operator_input_keys(values: Mapping[str, object]) -> list[str]:
    required_keys = list(MIGRATION_BASE_REQUIRED_OPERATOR_INPUT_KEYS)
    db_ssl_mode = str(values.get("DB_SSL_MODE", "require") or "require").strip().lower()
    if db_ssl_mode in {"verify-ca", "verify-full"}:
        required_keys.append("DB_SSL_CA_CERT_PATH")
    return required_keys


def runtime_json_classification_errors(
    plain_keys: Iterable[str],
    secret_keys: Iterable[str],
) -> list[str]:
    normalized_plain_keys = {
        str(key or "").strip() for key in plain_keys if str(key or "").strip()
    }
    normalized_secret_keys = {
        str(key or "").strip() for key in secret_keys if str(key or "").strip()
    }

    errors: list[str] = []
    secret_keys_in_plain = sorted(
        normalized_plain_keys & set(GITHUB_RUNTIME_SECRET_JSON_KEYS)
    )
    if secret_keys_in_plain:
        errors.append(
            "RUNTIME_PLAIN_ENV_JSON contains secret-classified keys that must stay in "
            "RUNTIME_SECRET_ENV_JSON: " + ", ".join(secret_keys_in_plain)
        )

    plain_keys_in_secret = sorted(
        normalized_secret_keys & set(GITHUB_RUNTIME_PLAIN_JSON_KEYS)
    )
    if plain_keys_in_secret:
        errors.append(
            "RUNTIME_SECRET_ENV_JSON contains plain-classified keys that must stay in "
            "RUNTIME_PLAIN_ENV_JSON: " + ", ".join(plain_keys_in_secret)
        )

    return errors
