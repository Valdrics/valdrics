from __future__ import annotations

import pytest

from scripts.managed_deployment_contract import (
    DECLARED_EXTERNAL_VALUE_KEYS,
    CLOUDFLARE_PAGES_PUBLIC_ENV_KEYS,
    GITHUB_RUNTIME_PLAIN_JSON_KEYS,
    GITHUB_RUNTIME_SECRET_JSON_KEYS,
    MIGRATION_BASE_REQUIRED_OPERATOR_INPUT_KEYS,
    RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS,
    TERRAFORM_BASE_REQUIRED_INPUTS,
    contains_placeholder,
    identify_runtime_unresolved_keys,
    required_migration_operator_input_keys,
    required_runtime_operator_input_keys,
    runtime_json_classification_errors,
    selected_llm_provider_env_key,
)


def test_runtime_contract_sets_are_stable() -> None:
    assert "API_URL" in DECLARED_EXTERNAL_VALUE_KEYS
    assert "SUPABASE_JWT_SECRET" in RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS
    assert "API_URL" in GITHUB_RUNTIME_PLAIN_JSON_KEYS
    assert "PAYSTACK_ACTIVATION_PENDING" in GITHUB_RUNTIME_PLAIN_JSON_KEYS
    assert "DATABASE_URL" in GITHUB_RUNTIME_SECRET_JSON_KEYS
    assert CLOUDFLARE_PAGES_PUBLIC_ENV_KEYS == (
        "PUBLIC_API_URL",
        "PUBLIC_SUPABASE_ANON_KEY",
        "PUBLIC_SUPABASE_URL",
    )
    assert TERRAFORM_BASE_REQUIRED_INPUTS == (
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
    assert MIGRATION_BASE_REQUIRED_OPERATOR_INPUT_KEYS == ("DATABASE_URL",)


def test_selected_llm_provider_env_key_reflects_provider_choice() -> None:
    assert selected_llm_provider_env_key({"LLM_PROVIDER": "groq"}) == "GROQ_API_KEY"
    assert selected_llm_provider_env_key({"LLM_PROVIDER": "openai"}) == "OPENAI_API_KEY"

    with pytest.raises(ValueError, match="LLM_PROVIDER must be one of"):
        selected_llm_provider_env_key({"LLM_PROVIDER": "unknown"})


def test_runtime_required_operator_input_keys_include_selected_provider() -> None:
    required = required_runtime_operator_input_keys({"LLM_PROVIDER": "claude"})

    assert "CLAUDE_API_KEY" in required
    assert "API_URL" in required
    assert "TRUSTED_PROXY_CIDRS" in required


def test_runtime_required_operator_input_keys_skip_paystack_when_activation_pending() -> (
    None
):
    required = required_runtime_operator_input_keys(
        {"LLM_PROVIDER": "groq", "PAYSTACK_ACTIVATION_PENDING": "true"}
    )

    assert "PAYSTACK_SECRET_KEY" not in required
    assert "PAYSTACK_PUBLIC_KEY" not in required
    assert "GROQ_API_KEY" in required


def test_identify_runtime_unresolved_keys_respects_placeholders_and_provider_key() -> (
    None
):
    values = {
        "LLM_PROVIDER": "google",
        "API_URL": "https://api.example.com",
        "FRONTEND_URL": "https://app.example.com",
        "DATABASE_URL": "postgresql+asyncpg://user:pass@db.example.com:5432/app",
        "GCP_PROJECT_ID": "valdrics-prod",
        "GCP_REGION": "us-central1",
        "GCP_CLOUD_TASKS_QUEUE": "valdrics-managed-work",
        "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL": (
            "tasks-invoker@valdrics-prod.iam.gserviceaccount.com"
        ),
        "GCP_CLOUD_RUN_SERVICE_NAME": "valdrics-api",
        "GCP_CLOUD_RUN_BATCH_JOB_NAME": "valdrics-batch",
        "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS": (
            '["tasks-invoker@valdrics-prod.iam.gserviceaccount.com",'
            '"scheduler-invoker@valdrics-prod.iam.gserviceaccount.com"]'
        ),
        "SUPABASE_JWT_SECRET": "REPLACE_WITH_SUPABASE_JWT_SECRET",
        "PAYSTACK_SECRET_KEY": "sk_live_123",
        "PAYSTACK_PUBLIC_KEY": "pk_live_123",
        "TRUSTED_PROXY_CIDRS": '["10.0.0.0/8"]',
        "GOOGLE_API_KEY": "REPLACE_WITH_GOOGLE_API_KEY",
    }

    unresolved = identify_runtime_unresolved_keys(
        values, RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS
    )

    assert unresolved == ["GOOGLE_API_KEY", "SUPABASE_JWT_SECRET"]


def test_identify_runtime_unresolved_keys_allows_pending_paystack_activation() -> None:
    values = {
        "LLM_PROVIDER": "groq",
        "API_URL": "https://api.example.com",
        "FRONTEND_URL": "https://app.example.com",
        "DATABASE_URL": "postgresql+asyncpg://user:pass@db.example.com:5432/app",
        "GCP_PROJECT_ID": "valdrics-prod",
        "GCP_REGION": "us-central1",
        "GCP_CLOUD_TASKS_QUEUE": "valdrics-managed-work",
        "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL": (
            "tasks-invoker@valdrics-prod.iam.gserviceaccount.com"
        ),
        "GCP_CLOUD_RUN_SERVICE_NAME": "valdrics-api",
        "GCP_CLOUD_RUN_BATCH_JOB_NAME": "valdrics-batch",
        "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS": (
            '["tasks-invoker@valdrics-prod.iam.gserviceaccount.com",'
            '"scheduler-invoker@valdrics-prod.iam.gserviceaccount.com"]'
        ),
        "SUPABASE_JWT_SECRET": "supabase-jwt-secret",
        "PAYSTACK_SECRET_KEY": "",
        "PAYSTACK_PUBLIC_KEY": "",
        "PAYSTACK_ACTIVATION_PENDING": "true",
        "TRUSTED_PROXY_CIDRS": '["10.0.0.0/8"]',
        "GROQ_API_KEY": "gsk_provider_key",
    }

    unresolved = identify_runtime_unresolved_keys(
        values, RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS
    )

    assert unresolved == []


def test_required_migration_operator_input_keys_expand_for_verified_ssl() -> None:
    assert required_migration_operator_input_keys({"DB_SSL_MODE": "require"}) == [
        "DATABASE_URL"
    ]
    assert required_migration_operator_input_keys({"DB_SSL_MODE": "verify-full"}) == [
        "DATABASE_URL",
        "DB_SSL_CA_CERT_PATH",
    ]


def test_contains_placeholder_detects_marker() -> None:
    assert contains_placeholder("REPLACE_WITH_DB_HOST")
    assert not contains_placeholder("postgresql://user:pass@db.example.com:5432/app")


def test_runtime_json_classification_errors_require_secret_and_plain_key_separation() -> (
    None
):
    errors = runtime_json_classification_errors(
        plain_keys=("API_URL", "DATABASE_URL"),
        secret_keys=("SUPABASE_JWT_SECRET", "FRONTEND_URL"),
    )

    assert errors == [
        "RUNTIME_PLAIN_ENV_JSON contains secret-classified keys that must stay in "
        "RUNTIME_SECRET_ENV_JSON: DATABASE_URL",
        "RUNTIME_SECRET_ENV_JSON contains plain-classified keys that must stay in "
        "RUNTIME_PLAIN_ENV_JSON: FRONTEND_URL",
    ]
