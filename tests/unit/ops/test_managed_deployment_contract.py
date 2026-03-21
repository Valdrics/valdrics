from __future__ import annotations

import pytest

from scripts.managed_deployment_contract import (
    DECLARED_EXTERNAL_VALUE_KEYS,
    KOYEB_DASHBOARD_PUBLIC_ENV_KEYS,
    MIGRATION_BASE_REQUIRED_OPERATOR_INPUT_KEYS,
    RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS,
    TERRAFORM_BASE_REQUIRED_INPUTS,
    contains_placeholder,
    identify_runtime_unresolved_keys,
    required_migration_operator_input_keys,
    required_runtime_operator_input_keys,
    selected_llm_provider_env_key,
)


def test_runtime_contract_sets_are_stable() -> None:
    assert "API_URL" in DECLARED_EXTERNAL_VALUE_KEYS
    assert "SUPABASE_JWT_SECRET" in RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS
    assert KOYEB_DASHBOARD_PUBLIC_ENV_KEYS == (
        "PUBLIC_API_URL",
        "PUBLIC_SUPABASE_ANON_KEY",
        "PUBLIC_SUPABASE_URL",
    )
    assert TERRAFORM_BASE_REQUIRED_INPUTS == ("external_id", "valdrics_account_id")
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


def test_identify_runtime_unresolved_keys_respects_placeholders_and_provider_key() -> None:
    values = {
        "LLM_PROVIDER": "google",
        "API_URL": "https://api.example.com",
        "FRONTEND_URL": "https://app.example.com",
        "DATABASE_URL": "postgresql+asyncpg://user:pass@db.example.com:5432/app",
        "REDIS_URL": "redis://redis.example.com:6379/0",
        "SUPABASE_JWT_SECRET": "REPLACE_WITH_SUPABASE_JWT_SECRET",
        "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN": "arn:aws:iam::123456789012:role/control",
        "PAYSTACK_SECRET_KEY": "sk_live_123",
        "PAYSTACK_PUBLIC_KEY": "pk_live_123",
        "SENTRY_DSN": "https://key@example.ingest.sentry.io/1",
        "OTEL_EXPORTER_OTLP_ENDPOINT": "https://otel.example.com:4317",
        "TRUSTED_PROXY_CIDRS": '["10.0.0.0/8"]',
        "GOOGLE_API_KEY": "REPLACE_WITH_GOOGLE_API_KEY",
    }

    unresolved = identify_runtime_unresolved_keys(values, RUNTIME_VALIDATION_OPERATOR_INPUT_KEYS)

    assert unresolved == ["GOOGLE_API_KEY", "SUPABASE_JWT_SECRET"]


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
