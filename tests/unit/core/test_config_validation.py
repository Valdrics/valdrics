"""
Tests for app/shared/core/config.py - Configuration management
"""

import pytest
from unittest.mock import patch
from pydantic import ValidationError
from app.shared.core.config import Settings

FAKE_PAYSTACK_SECRET_KEY = "example_paystack_secret_TEST_KEY_NOT_REAL_1234567890"
FAKE_PAYSTACK_PUBLIC_KEY = "example_paystack_public_TEST_KEY_NOT_REAL_1234567890"
FAKE_SUPABASE_SECRET = "x" * 32
FAKE_CSRF_SECRET = "c" * 32
FAKE_ENCRYPTION_KEY = "k" * 32
FAKE_ENFORCEMENT_APPROVAL_SECRET = "a" * 48
FAKE_ENFORCEMENT_EXPORT_SECRET = "e" * 48
FAKE_API_URL = "https://api.example.com"
FAKE_FRONTEND_URL = "https://app.example.com"
# Base64 for 'KDF_SALT_FOR_TESTING_32_BYTES_OK' (32 bytes)
FAKE_KDF_SALT = "S0RGX1NBTFRfRk9SX1RFU1RJTkdfMzJfQllURVNfT0s="
FAKE_GCP_PROJECT_ID = "valdrics-prod"
FAKE_GCP_REGION = "us-central1"
FAKE_GCP_TASK_QUEUE = "valdrics-managed-work"
FAKE_GCP_TASKS_INVOKER = "tasks-invoker@valdrics-prod.iam.gserviceaccount.com"
FAKE_GCP_SCHEDULER_INVOKER = "scheduler-invoker@valdrics-prod.iam.gserviceaccount.com"
FAKE_GCP_CLOUD_RUN_SERVICE_NAME = "valdrics-api"
FAKE_GCP_CLOUD_RUN_BATCH_JOB_NAME = "valdrics-batch"
FAKE_GCP_INTERNAL_BASE_URL = "https://valdrics-api-xyz.run.app"


def strict_managed_production_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "ENVIRONMENT": "production",
        "DATABASE_URL": "postgresql+asyncpg://test",
        "API_URL": FAKE_API_URL,
        "FRONTEND_URL": FAKE_FRONTEND_URL,
        "PLATFORM_RUNTIME_PROFILE": "gcp",
        "OBSERVABILITY_BACKEND": "gcp",
        "PUBLIC_API_RATE_LIMITING_BACKEND": "cloudflare",
        "RATELIMIT_ENABLED": False,
        "GCP_PROJECT_ID": FAKE_GCP_PROJECT_ID,
        "GCP_REGION": FAKE_GCP_REGION,
        "GCP_CLOUD_TASKS_QUEUE": FAKE_GCP_TASK_QUEUE,
        "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL": FAKE_GCP_TASKS_INVOKER,
        "GCP_CLOUD_RUN_BATCH_JOB_NAME": FAKE_GCP_CLOUD_RUN_BATCH_JOB_NAME,
        "GCP_CLOUD_RUN_SERVICE_NAME": FAKE_GCP_CLOUD_RUN_SERVICE_NAME,
        "GCP_INTERNAL_BASE_URL": FAKE_GCP_INTERNAL_BASE_URL,
        "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS": [
            FAKE_GCP_TASKS_INVOKER,
            FAKE_GCP_SCHEDULER_INVOKER,
        ],
        "SUPABASE_JWT_SECRET": FAKE_SUPABASE_SECRET,
        "ENCRYPTION_KEY": FAKE_ENCRYPTION_KEY,
        "CSRF_SECRET_KEY": FAKE_CSRF_SECRET,
        "KDF_SALT": FAKE_KDF_SALT,
        "DEBUG": False,
        "TESTING": False,
        "DB_SSL_MODE": "require",
        "ADMIN_API_KEY": "a" * 32,
        "GROQ_API_KEY": "g" * 32,
        "PAYSTACK_SECRET_KEY": FAKE_PAYSTACK_SECRET_KEY,
        "PAYSTACK_PUBLIC_KEY": FAKE_PAYSTACK_PUBLIC_KEY,
        "ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION": True,
        "ENFORCEMENT_APPROVAL_TOKEN_SECRET": FAKE_ENFORCEMENT_APPROVAL_SECRET,
        "ENFORCEMENT_EXPORT_SIGNING_SECRET": FAKE_ENFORCEMENT_EXPORT_SECRET,
    }
    base.update(overrides)
    return base


class TestSettingsValidation:
    """Test settings validation and security checks."""

    def test_enforce_rls_in_tests_default_enabled(self):
        settings = Settings(TESTING=True, _env_file=None)
        assert settings.ENFORCE_RLS_IN_TESTS is True

    def test_settings_missing_required_fields(self):
        """Test validation when required fields are missing."""
        # Ensure no env vars interfere and defaults apply
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(_env_file=None)
            assert "CSRF_SECRET_KEY must be set" in str(exc.value)

    def test_settings_rejects_noncanonical_app_name(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    APP_NAME="Valdrics AI",
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    DB_SSL_MODE="disable",
                    _env_file=None,
                )
            assert (
                "APP_NAME must be set to the canonical product name 'Valdrics'."
                in str(exc.value)
            )

    def test_settings_rejects_weak_blind_index_kdf_iterations(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    BLIND_INDEX_KDF_ITERATIONS=1000,
                    _env_file=None,
                )
            assert "BLIND_INDEX_KDF_ITERATIONS must be >= 10000" in str(exc.value)

    def test_settings_rejects_non_monotonic_analysis_rate_limits(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    ANALYSIS_RATE_LIMIT_FREE_PER_HOUR=5,
                    ANALYSIS_RATE_LIMIT_STARTER_PER_HOUR=4,
                    DB_SSL_MODE="disable",
                    _env_file=None,
                )

            assert (
                "ANALYSIS_RATE_LIMIT_STARTER_PER_HOUR must be >= free tier analysis limit."
                in str(exc.value)
            )

    def test_settings_invalid_ssl_mode(self):
        """Test validation with invalid SSL mode."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    ENVIRONMENT="production",
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    DEBUG=False,
                    TESTING=False,
                    GROQ_API_KEY="g" * 32,
                    DB_SSL_MODE="invalid_mode",
                    ENFORCEMENT_APPROVAL_TOKEN_SECRET=FAKE_ENFORCEMENT_APPROVAL_SECRET,
                    ENFORCEMENT_EXPORT_SIGNING_SECRET=FAKE_ENFORCEMENT_EXPORT_SECRET,
                    _env_file=None,
                )
            assert "DB_SSL_MODE must be secure in production" in str(exc.value)

    def test_settings_rejects_public_api_documentation_in_strict_env(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    EXPOSE_API_DOCUMENTATION_PUBLICLY=True,
                    **strict_managed_production_kwargs(),
                    _env_file=None,
                )

            assert "EXPOSE_API_DOCUMENTATION_PUBLICLY" in str(exc.value)

    def test_settings_production_ssl_require_without_ca(self):
        """Test production SSL requirement without CA certificate."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    **strict_managed_production_kwargs(
                        DB_SSL_MODE="verify-ca",
                        DB_SSL_CA_CERT_PATH=None,  # Missing CA cert
                    ),
                    _env_file=None,
                )

            assert "DB_SSL_CA_CERT_PATH" in str(exc.value)
            assert "mandatory" in str(exc.value)

    def test_settings_production_ssl_verify_ca_success(self):
        """Test successful SSL verification in production."""
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                **strict_managed_production_kwargs(
                    DB_SSL_MODE="verify-ca",
                    DB_SSL_CA_CERT_PATH="/path/to/ca.crt",
                ),
                _env_file=None,
            )

            assert settings.DB_SSL_MODE == "verify-ca"
            assert settings.is_production is True

    def test_settings_development_ssl_disable_allowed(self):
        """Test SSL disable allowed in development."""
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                DATABASE_URL="sqlite+aiosqlite:///:memory:",
                SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                KDF_SALT=FAKE_KDF_SALT,
                DEBUG=True,  # Development mode
                DB_SSL_MODE="disable",
                _env_file=None,
            )

            assert settings.DB_SSL_MODE == "disable"
            assert settings.is_production is False

    def test_settings_rejects_invalid_aws_trust_principal_arn(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    DB_SSL_MODE="disable",
                    AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN="not-an-arn",
                    _env_file=None,
                )

            assert "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN" in str(exc.value)

    def test_settings_rejects_invalid_cloudformation_template_url(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    DB_SSL_MODE="disable",
                    CLOUDFORMATION_TEMPLATE_URL="javascript:alert(1)",
                    _env_file=None,
                )

            assert "CLOUDFORMATION_TEMPLATE_URL" in str(exc.value)

    def test_settings_accepts_local_sqlite_bootstrap_in_local_runtime(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                ENVIRONMENT="local",
                DATABASE_URL="sqlite+aiosqlite:///./valdrics_local_dev.sqlite3",
                SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                KDF_SALT=FAKE_KDF_SALT,
                TESTING=False,
                LOCAL_SQLITE_BOOTSTRAP=True,
                DB_SSL_MODE="disable",
                _env_file=None,
            )

            assert settings.LOCAL_SQLITE_BOOTSTRAP is True

    def test_settings_rejects_local_sqlite_bootstrap_in_testing(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    ENVIRONMENT="local",
                    DATABASE_URL="sqlite+aiosqlite:///./valdrics_local_dev.sqlite3",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    TESTING=True,
                    LOCAL_SQLITE_BOOTSTRAP=True,
                    DB_SSL_MODE="disable",
                    _env_file=None,
                )

            assert "LOCAL_SQLITE_BOOTSTRAP requires TESTING=false" in str(exc.value)

    def test_settings_rejects_local_sqlite_bootstrap_for_non_sqlite_database(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    ENVIRONMENT="local",
                    DATABASE_URL="postgresql+asyncpg://test",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    TESTING=False,
                    LOCAL_SQLITE_BOOTSTRAP=True,
                    DB_SSL_MODE="disable",
                    _env_file=None,
                )

            assert "LOCAL_SQLITE_BOOTSTRAP requires DATABASE_URL to use sqlite" in str(
                exc.value
            )

    def test_settings_admin_api_key_validation(self):
        """Test admin API key validation in production."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    **strict_managed_production_kwargs(
                        DATABASE_URL="sqlite+aiosqlite:///:memory:",
                        ADMIN_API_KEY="short",  # Too short
                    ),
                    _env_file=None,
                )

            assert "ADMIN_API_KEY" in str(exc.value)
            assert ">= 32 chars" in str(exc.value)

    def test_settings_rejects_invalid_kill_switch_scope(self):
        """Kill switch scope must be explicitly tenant or global."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    REMEDIATION_KILL_SWITCH_SCOPE="org",
                    GROQ_API_KEY="g" * 32,
                    _env_file=None,
                )

            assert "REMEDIATION_KILL_SWITCH_SCOPE must be one of" in str(exc.value)

    def test_settings_blocks_global_kill_switch_scope_in_production_without_override(
        self,
    ):
        """Production/staging must not use global scope unless explicitly overridden."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    REMEDIATION_KILL_SWITCH_SCOPE="global",
                    REMEDIATION_KILL_SWITCH_ALLOW_GLOBAL_SCOPE=False,
                    **strict_managed_production_kwargs(),
                    _env_file=None,
                )

            assert (
                "REMEDIATION_KILL_SWITCH_SCOPE=global requires "
                "REMEDIATION_KILL_SWITCH_ALLOW_GLOBAL_SCOPE=true"
            ) in str(exc.value)

    def test_settings_cors_origins_localhost_rejected_in_production(self):
        """Strict environments must reject localhost/browser-dev origins."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    CORS_ORIGINS=["http://localhost:3000", "https://example.com"],
                    **strict_managed_production_kwargs(
                        DATABASE_URL="sqlite+aiosqlite:///:memory:"
                    ),
                    _env_file=None,
                )

            assert "CORS_ORIGINS" in str(exc.value)
            assert "localhost" in str(exc.value)

    def test_settings_frontend_url_requires_https_in_production(self):
        """Strict environments must reject non-HTTPS frontend URLs."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    **strict_managed_production_kwargs(
                        DATABASE_URL="sqlite+aiosqlite:///:memory:",
                        FRONTEND_URL="http://example.com",  # HTTP instead of HTTPS
                    ),
                    _env_file=None,
                )
            assert "FRONTEND_URL must use an explicit https:// URL" in str(exc.value)

    def test_settings_llm_provider_key_missing(self):
        """Test validation when LLM provider is set but key is missing."""
        # Ensure env vars don't provide key and we don't load from .env
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    ENVIRONMENT="production",
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    LLM_PROVIDER="openai",
                    OPENAI_API_KEY=None,
                    DEBUG=False,  # Strict validation in prod
                    TESTING=False,
                    PAYSTACK_SECRET_KEY=FAKE_PAYSTACK_SECRET_KEY,
                    PAYSTACK_PUBLIC_KEY=FAKE_PAYSTACK_PUBLIC_KEY,
                    ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION=True,
                    ENFORCEMENT_APPROVAL_TOKEN_SECRET=FAKE_ENFORCEMENT_APPROVAL_SECRET,
                    ENFORCEMENT_EXPORT_SIGNING_SECRET=FAKE_ENFORCEMENT_EXPORT_SECRET,
                    _env_file=None,  # Ignore .env
                )

            assert "its API key is missing" in str(exc.value)

    def test_settings_llm_provider_key_present(self):
        """Test successful validation when LLM provider key is present."""
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                DATABASE_URL="sqlite+aiosqlite:///:memory:",
                SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                KDF_SALT=FAKE_KDF_SALT,
                LLM_PROVIDER="openai",
                OPENAI_API_KEY="sk-test-key",
                _env_file=None,
            )

            assert settings.LLM_PROVIDER == "openai"
            assert settings.OPENAI_API_KEY == "sk-test-key"

    def test_settings_is_production_property(self):
        """Test is_production property logic."""
        with patch.dict("os.environ", {}, clear=True):
            # Debug=True should be non-production
            settings_debug = Settings(
                DATABASE_URL="sqlite+aiosqlite:///:memory:",
                SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                KDF_SALT=FAKE_KDF_SALT,
                DEBUG=True,
                DB_SSL_MODE="disable",
                _env_file=None,
            )
            assert settings_debug.is_production is False

            # Debug=False should be production
            settings_prod = Settings(
                **strict_managed_production_kwargs(
                    DATABASE_URL="sqlite+aiosqlite:///:memory:"
                ),
                _env_file=None,
            )
            assert settings_prod.is_production is True

    def test_settings_default_values(self):
        """Test default values for optional settings."""
        # Use _env_file=None to ignore .env default overrides if any
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                DATABASE_URL="sqlite+aiosqlite:///:memory:",
                SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                KDF_SALT=FAKE_KDF_SALT,
                DB_SSL_MODE="require",
                GROQ_API_KEY="g" * 32,
                TESTING=False,
                _env_file=None,
            )

            # Check default values
            assert settings.LLM_PROVIDER == "groq"
            assert settings.OPENAI_API_KEY is None
            assert settings.CORS_ORIGINS == []
            assert settings.FRONTEND_URL == "http://localhost:5174"
            assert settings.ADMIN_API_KEY is None

    def test_settings_saas_strict_integrations_blocks_env_integration_config_in_production(
        self,
    ):
        """Strict SaaS mode must reject env-based workflow/notification config in production."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    SAAS_STRICT_INTEGRATIONS=True,
                    SLACK_CHANNEL_ID="C0123456789",
                    **strict_managed_production_kwargs(),
                    _env_file=None,
                )
            assert (
                "SAAS_STRICT_INTEGRATIONS forbids env-based workflow and routing settings"
                in str(exc.value)
            )

    def test_settings_saas_strict_integrations_allows_shared_slack_bot_token(self):
        """Strict SaaS mode may keep shared Slack bot token while blocking env routing config."""
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                SAAS_STRICT_INTEGRATIONS=True,
                SLACK_BOT_TOKEN="xoxb-shared-token",
                **strict_managed_production_kwargs(),
                _env_file=None,
            )
            assert settings.SAAS_STRICT_INTEGRATIONS is True

    def test_settings_production_null_pool_requires_external_pooler_ack(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    DB_USE_NULL_POOL=True,
                    DB_EXTERNAL_POOLER=False,
                    **strict_managed_production_kwargs(),
                    _env_file=None,
                )
            assert "DB_USE_NULL_POOL=true requires DB_EXTERNAL_POOLER=true" in str(
                exc.value
            )

    def test_settings_production_requires_cloudflare_public_rate_limiting(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    **strict_managed_production_kwargs(
                        PUBLIC_API_RATE_LIMITING_BACKEND="redis",
                    ),
                    _env_file=None,
                )
            assert "PUBLIC_API_RATE_LIMITING_BACKEND must be cloudflare" in str(
                exc.value
            )

    def test_settings_production_rejects_enabled_app_rate_limiter(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    **strict_managed_production_kwargs(
                        PUBLIC_API_RATE_LIMITING_BACKEND="cloudflare",
                        RATELIMIT_ENABLED=True,
                    ),
                    _env_file=None,
                )
            assert (
                "RATELIMIT_ENABLED must be false when PUBLIC_API_RATE_LIMITING_BACKEND=cloudflare"
                in str(exc.value)
            )

    def test_settings_production_allows_supported_cloudflare_profile(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                **strict_managed_production_kwargs(
                    PUBLIC_API_RATE_LIMITING_BACKEND="cloudflare",
                    RATELIMIT_ENABLED=False,
                ),
                _env_file=None,
            )
            assert settings.PUBLIC_API_RATE_LIMITING_BACKEND == "cloudflare"

    def test_settings_gcp_cloudflare_profile_allows_supported_managed_contract(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                ENVIRONMENT="production",
                DATABASE_URL="postgresql+asyncpg://test",
                API_URL=FAKE_API_URL,
                FRONTEND_URL=FAKE_FRONTEND_URL,
                PLATFORM_RUNTIME_PROFILE="gcp",
                OBSERVABILITY_BACKEND="gcp",
                PUBLIC_API_RATE_LIMITING_BACKEND="cloudflare",
                RATELIMIT_ENABLED=False,
                GCP_PROJECT_ID="valdrics-prod",
                GCP_REGION="us-central1",
                GCP_CLOUD_TASKS_QUEUE="valdrics-managed-work",
                GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL=(
                    "tasks-invoker@valdrics-prod.iam.gserviceaccount.com"
                ),
                GCP_CLOUD_RUN_BATCH_JOB_NAME="valdrics-batch",
                GCP_CLOUD_RUN_SERVICE_NAME="valdrics-api",
                GCP_INTERNAL_BASE_URL="https://valdrics-api-xyz.run.app",
                GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS=[
                    "tasks-invoker@valdrics-prod.iam.gserviceaccount.com",
                    "scheduler-invoker@valdrics-prod.iam.gserviceaccount.com",
                ],
                SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                KDF_SALT=FAKE_KDF_SALT,
                DEBUG=False,
                TESTING=False,
                DB_SSL_MODE="require",
                ADMIN_API_KEY="a" * 32,
                GROQ_API_KEY="g" * 32,
                PAYSTACK_SECRET_KEY=FAKE_PAYSTACK_SECRET_KEY,
                PAYSTACK_PUBLIC_KEY=FAKE_PAYSTACK_PUBLIC_KEY,
                ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION=True,
                TRUST_PROXY_HEADERS=True,
                TRUSTED_PROXY_CIDRS=["203.0.113.10/32"],
                ENFORCEMENT_APPROVAL_TOKEN_SECRET=FAKE_ENFORCEMENT_APPROVAL_SECRET,
                ENFORCEMENT_EXPORT_SIGNING_SECRET=FAKE_ENFORCEMENT_EXPORT_SECRET,
                _env_file=None,
            )

        assert settings.PUBLIC_API_RATE_LIMITING_BACKEND == "cloudflare"
        assert settings.RATELIMIT_ENABLED is False

    def test_settings_gcp_cloudflare_profile_rejects_enabled_app_rate_limiter(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    ENVIRONMENT="production",
                    DATABASE_URL="postgresql+asyncpg://test",
                    API_URL=FAKE_API_URL,
                    FRONTEND_URL=FAKE_FRONTEND_URL,
                    PLATFORM_RUNTIME_PROFILE="gcp",
                    OBSERVABILITY_BACKEND="gcp",
                    PUBLIC_API_RATE_LIMITING_BACKEND="cloudflare",
                    RATELIMIT_ENABLED=True,
                    GCP_PROJECT_ID="valdrics-prod",
                    GCP_REGION="us-central1",
                    GCP_CLOUD_TASKS_QUEUE="valdrics-managed-work",
                    GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL=(
                        "tasks-invoker@valdrics-prod.iam.gserviceaccount.com"
                    ),
                    GCP_CLOUD_RUN_BATCH_JOB_NAME="valdrics-batch",
                    GCP_CLOUD_RUN_SERVICE_NAME="valdrics-api",
                    GCP_INTERNAL_BASE_URL="https://valdrics-api-xyz.run.app",
                    GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS=[
                        "tasks-invoker@valdrics-prod.iam.gserviceaccount.com",
                        "scheduler-invoker@valdrics-prod.iam.gserviceaccount.com",
                    ],
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    DEBUG=False,
                    TESTING=False,
                    DB_SSL_MODE="require",
                    ADMIN_API_KEY="a" * 32,
                    GROQ_API_KEY="g" * 32,
                    PAYSTACK_SECRET_KEY=FAKE_PAYSTACK_SECRET_KEY,
                    PAYSTACK_PUBLIC_KEY=FAKE_PAYSTACK_PUBLIC_KEY,
                    ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION=True,
                    TRUST_PROXY_HEADERS=True,
                    TRUSTED_PROXY_CIDRS=["203.0.113.10/32"],
                    ENFORCEMENT_APPROVAL_TOKEN_SECRET=FAKE_ENFORCEMENT_APPROVAL_SECRET,
                    ENFORCEMENT_EXPORT_SIGNING_SECRET=FAKE_ENFORCEMENT_EXPORT_SECRET,
                    _env_file=None,
                )

        assert "RATELIMIT_ENABLED must be false" in str(exc.value)

    def test_settings_gcp_cloudflare_profile_rejects_internal_auth_audience_drift(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    ENVIRONMENT="production",
                    DATABASE_URL="postgresql+asyncpg://test",
                    API_URL=FAKE_API_URL,
                    FRONTEND_URL=FAKE_FRONTEND_URL,
                    PLATFORM_RUNTIME_PROFILE="gcp",
                    OBSERVABILITY_BACKEND="gcp",
                    PUBLIC_API_RATE_LIMITING_BACKEND="cloudflare",
                    RATELIMIT_ENABLED=False,
                    GCP_PROJECT_ID="valdrics-prod",
                    GCP_REGION="us-central1",
                    GCP_CLOUD_TASKS_QUEUE="valdrics-managed-work",
                    GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL=(
                        "tasks-invoker@valdrics-prod.iam.gserviceaccount.com"
                    ),
                    GCP_CLOUD_RUN_BATCH_JOB_NAME="valdrics-batch",
                    GCP_CLOUD_RUN_SERVICE_NAME="valdrics-api",
                    GCP_INTERNAL_BASE_URL="https://valdrics-api-xyz.run.app",
                    GCP_INTERNAL_AUTH_AUDIENCE="https://internal.valdrics.example",
                    GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS=[
                        "tasks-invoker@valdrics-prod.iam.gserviceaccount.com",
                        "scheduler-invoker@valdrics-prod.iam.gserviceaccount.com",
                    ],
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    DEBUG=False,
                    TESTING=False,
                    DB_SSL_MODE="require",
                    ADMIN_API_KEY="a" * 32,
                    GROQ_API_KEY="g" * 32,
                    PAYSTACK_SECRET_KEY=FAKE_PAYSTACK_SECRET_KEY,
                    PAYSTACK_PUBLIC_KEY=FAKE_PAYSTACK_PUBLIC_KEY,
                    ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION=True,
                    TRUST_PROXY_HEADERS=True,
                    TRUSTED_PROXY_CIDRS=["203.0.113.10/32"],
                    ENFORCEMENT_APPROVAL_TOKEN_SECRET=FAKE_ENFORCEMENT_APPROVAL_SECRET,
                    ENFORCEMENT_EXPORT_SIGNING_SECRET=FAKE_ENFORCEMENT_EXPORT_SECRET,
                    _env_file=None,
                )

        assert "GCP_INTERNAL_AUTH_AUDIENCE must match API_URL" in str(exc.value)

    def test_settings_gcp_cloudflare_profile_rejects_run_app_origin(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    ENVIRONMENT="production",
                    DATABASE_URL="postgresql+asyncpg://test",
                    API_URL="https://valdrics-api-xyz.run.app",
                    FRONTEND_URL=FAKE_FRONTEND_URL,
                    PLATFORM_RUNTIME_PROFILE="gcp",
                    OBSERVABILITY_BACKEND="gcp",
                    PUBLIC_API_RATE_LIMITING_BACKEND="cloudflare",
                    RATELIMIT_ENABLED=False,
                    GCP_PROJECT_ID="valdrics-prod",
                    GCP_REGION="us-central1",
                    GCP_CLOUD_TASKS_QUEUE="valdrics-managed-work",
                    GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL=(
                        "tasks-invoker@valdrics-prod.iam.gserviceaccount.com"
                    ),
                    GCP_CLOUD_RUN_BATCH_JOB_NAME="valdrics-batch",
                    GCP_CLOUD_RUN_SERVICE_NAME="valdrics-api",
                    GCP_INTERNAL_BASE_URL="https://valdrics-api-xyz.run.app",
                    GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS=[
                        "tasks-invoker@valdrics-prod.iam.gserviceaccount.com",
                        "scheduler-invoker@valdrics-prod.iam.gserviceaccount.com",
                    ],
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    DEBUG=False,
                    TESTING=False,
                    DB_SSL_MODE="require",
                    ADMIN_API_KEY="a" * 32,
                    GROQ_API_KEY="g" * 32,
                    PAYSTACK_SECRET_KEY=FAKE_PAYSTACK_SECRET_KEY,
                    PAYSTACK_PUBLIC_KEY=FAKE_PAYSTACK_PUBLIC_KEY,
                    ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION=True,
                    TRUST_PROXY_HEADERS=True,
                    TRUSTED_PROXY_CIDRS=["203.0.113.10/32"],
                    ENFORCEMENT_APPROVAL_TOKEN_SECRET=FAKE_ENFORCEMENT_APPROVAL_SECRET,
                    ENFORCEMENT_EXPORT_SIGNING_SECRET=FAKE_ENFORCEMENT_EXPORT_SECRET,
                    _env_file=None,
                )

        assert "Cloudflare-proxied custom hostname" in str(exc.value)

    def test_settings_rejects_short_enforcement_fallback_signing_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    GROQ_API_KEY="g" * 32,
                    ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS=["short-key"],
                    _env_file=None,
                )
            assert (
                "ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS key must be >= 32"
                in str(exc.value)
            )

    def test_settings_rejects_short_enforcement_approval_token_secret(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    GROQ_API_KEY="g" * 32,
                    ENFORCEMENT_APPROVAL_TOKEN_SECRET="short-key",
                    _env_file=None,
                )
            assert "ENFORCEMENT_APPROVAL_TOKEN_SECRET must be >= 32 chars" in str(
                exc.value
            )

    def test_settings_accepts_enforcement_approval_token_secret(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                DATABASE_URL="sqlite+aiosqlite:///:memory:",
                SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                KDF_SALT=FAKE_KDF_SALT,
                GROQ_API_KEY="g" * 32,
                ENFORCEMENT_APPROVAL_TOKEN_SECRET="a" * 48,
                _env_file=None,
            )
            assert settings.ENFORCEMENT_APPROVAL_TOKEN_SECRET == "a" * 48

    def test_settings_accepts_enforcement_fallback_signing_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                DATABASE_URL="sqlite+aiosqlite:///:memory:",
                SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                KDF_SALT=FAKE_KDF_SALT,
                GROQ_API_KEY="g" * 32,
                ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS=[
                    "f" * 32,
                    "g" * 40,
                ],
                _env_file=None,
            )
            assert settings.ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS == [
                "f" * 32,
                "g" * 40,
            ]

    def test_settings_rejects_invalid_enforcement_global_gate_cap(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    GROQ_API_KEY="g" * 32,
                    ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP=0,
                    _env_file=None,
                )
            assert "ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP must be >= 1" in str(
                exc.value
            )

    def test_settings_accepts_enforcement_global_gate_cap(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                DATABASE_URL="sqlite+aiosqlite:///:memory:",
                SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                KDF_SALT=FAKE_KDF_SALT,
                GROQ_API_KEY="g" * 32,
                ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP=2500,
                _env_file=None,
            )
            assert settings.ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP == 2500

    def test_settings_rejects_short_enforcement_export_signing_secret(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    DATABASE_URL="sqlite+aiosqlite:///:memory:",
                    SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                    ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                    CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                    KDF_SALT=FAKE_KDF_SALT,
                    GROQ_API_KEY="g" * 32,
                    ENFORCEMENT_EXPORT_SIGNING_SECRET="short-secret",
                    _env_file=None,
                )
            assert "ENFORCEMENT_EXPORT_SIGNING_SECRET must be >= 32 chars" in str(
                exc.value
            )

    def test_settings_accepts_enforcement_export_signing_controls(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                DATABASE_URL="sqlite+aiosqlite:///:memory:",
                SUPABASE_JWT_SECRET=FAKE_SUPABASE_SECRET,
                ENCRYPTION_KEY=FAKE_ENCRYPTION_KEY,
                CSRF_SECRET_KEY=FAKE_CSRF_SECRET,
                KDF_SALT=FAKE_KDF_SALT,
                GROQ_API_KEY="g" * 32,
                ENFORCEMENT_EXPORT_SIGNING_SECRET="x" * 48,
                ENFORCEMENT_EXPORT_SIGNING_KID="enf-export-v2",
                _env_file=None,
            )
            assert settings.ENFORCEMENT_EXPORT_SIGNING_SECRET == "x" * 48
            assert settings.ENFORCEMENT_EXPORT_SIGNING_KID == "enf-export-v2"

    def test_settings_require_enforcement_signing_keys_in_production(self):
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValidationError) as exc:
                Settings(
                    **strict_managed_production_kwargs(
                        ENFORCEMENT_APPROVAL_TOKEN_SECRET="",
                        ENFORCEMENT_EXPORT_SIGNING_SECRET="",
                    ),
                    _env_file=None,
                )
            assert "ENFORCEMENT_APPROVAL_TOKEN_SECRET" in str(exc.value)

    def test_settings_accept_production_enforcement_signing_keys(self):
        with patch.dict("os.environ", {}, clear=True):
            settings = Settings(
                **strict_managed_production_kwargs(
                    ENFORCEMENT_APPROVAL_TOKEN_SECRET="a" * 48,
                    ENFORCEMENT_EXPORT_SIGNING_SECRET="x" * 48,
                ),
                _env_file=None,
            )

            assert settings.ENFORCEMENT_APPROVAL_TOKEN_SECRET == "a" * 48
            assert settings.ENFORCEMENT_EXPORT_SIGNING_SECRET == "x" * 48
