from functools import lru_cache
import re
import sys
from threading import Lock
from urllib.parse import urlparse
import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from app.shared.core.runtime_paths import DEFAULT_ENV_FILE
from app.shared.core.config_validation import (
    validate_all_config as _validate_all_config_impl,
    validate_billing_config as _validate_billing_config_impl,
    validate_core_secrets as _validate_core_secrets_impl,
    validate_database_config as _validate_database_config_impl,
    validate_enforcement_guardrails as _validate_enforcement_guardrails_impl,
    validate_environment_safety as _validate_environment_safety_impl,
    validate_integration_config as _validate_integration_config_impl,
    validate_llm_config as _validate_llm_config_impl,
    validate_remediation_guardrails as _validate_remediation_guardrails_impl,
    validate_turnstile_config as _validate_turnstile_config_impl,
)
from app.shared.core.config_validation_observability import (
    validate_observability_config as _validate_observability_config_impl,
)
from app.shared.core.config_sections_core import CoreRuntimeSettings
from app.shared.core.config_sections_governance import GovernanceSettings
from app.shared.core.config_sections_integrations import IntegrationSettings
from app.shared.core.config_sections_security import SecuritySettings

# Environment Constants (Finding #10)
ENV_PRODUCTION, ENV_STAGING = "production", "staging"
ENV_DEVELOPMENT, ENV_LOCAL = "development", "local"


@lru_cache
def get_settings() -> "Settings":
    """Returns a singleton instance of the application settings."""
    # Production-grade: do not generate security-sensitive secrets at runtime.
    # Require explicit configuration via environment / .env for all non-test runs.
    return Settings()


SETTINGS_RELOAD_CACHE_REFRESH_RECOVERABLE_EXCEPTIONS = (
    ImportError,
    AttributeError,
    RuntimeError,
    TypeError,
    ValueError,
)
_settings_reload_lock = Lock()


def reload_settings_from_environment() -> "Settings":
    """
    Atomically refresh the cached settings from current environment values.

    The singleton is updated in place so modules that captured the settings
    object during import still observe refreshed values after reload.
    """
    logger = structlog.get_logger()
    with _settings_reload_lock:
        logger.debug("settings_reload_started")
        current = get_settings()
        refreshed = Settings()
        for field_name in refreshed.model_dump().keys():
            setattr(current, field_name, getattr(refreshed, field_name))
        try:
            from app.shared.core.security import EncryptionKeyManager

            EncryptionKeyManager.clear_key_caches(warm=True)
            from app.models._encryption import clear_encryption_key_cache

            clear_encryption_key_cache()
            app_main_module = sys.modules.get("app.main")
            if app_main_module is not None:
                refresh_app_metadata = getattr(
                    app_main_module,
                    "refresh_fastapi_app_metadata",
                    None,
                )
                if callable(refresh_app_metadata):
                    refresh_app_metadata(current)
        except (
            SETTINGS_RELOAD_CACHE_REFRESH_RECOVERABLE_EXCEPTIONS
        ) as cache_exc:  # pragma: no cover - defensive path
            logger.warning("settings_reload_cache_refresh_failed", error=str(cache_exc))
        logger.debug("settings_reload_completed")
        return current


class Settings(
    CoreRuntimeSettings,
    SecuritySettings,
    IntegrationSettings,
    GovernanceSettings,
    BaseSettings,
):
    """
    Main configuration for Valdrics AI.
    Uses Pydantic-Settings for environment variable parsing from .env.
    """

    @field_validator("ENVIRONMENT", mode="before")
    @classmethod
    def _normalize_environment(cls, value: object) -> str:
        normalized = str(value or "").strip().lower()
        allowed = {"production", "staging", "development", "local", "test"}
        if normalized not in allowed:
            allowed_text = ", ".join(sorted(allowed))
            raise ValueError(f"ENVIRONMENT must be one of: {allowed_text}")
        return normalized

    @field_validator("PLATFORM_RUNTIME_PROFILE", mode="before")
    @classmethod
    def _normalize_platform_runtime_profile(cls, value: object) -> str:
        normalized = str(value or "gcp").strip().lower()
        allowed = {"gcp"}
        if normalized not in allowed:
            allowed_text = ", ".join(sorted(allowed))
            raise ValueError(f"PLATFORM_RUNTIME_PROFILE must be one of: {allowed_text}")
        return normalized

    @field_validator("OBSERVABILITY_BACKEND", mode="before")
    @classmethod
    def _normalize_observability_backend(cls, value: object) -> str:
        normalized = str(value or "gcp").strip().lower()
        if normalized != "gcp":
            raise ValueError("OBSERVABILITY_BACKEND must be gcp.")
        return normalized

    @field_validator("PUBLIC_API_RATE_LIMITING_BACKEND", mode="before")
    @classmethod
    def _normalize_public_api_rate_limiting_backend(cls, value: object) -> str:
        normalized = str(value or "cloudflare").strip().lower()
        if normalized != "cloudflare":
            raise ValueError("PUBLIC_API_RATE_LIMITING_BACKEND must be cloudflare.")
        return normalized

    @field_validator("AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN", mode="before")
    @classmethod
    def _normalize_aws_assume_role_trust_principal_arn(
        cls, value: object
    ) -> str | None:
        normalized = str(value or "").strip()
        if not normalized:
            return None
        arn_pattern = re.compile(
            r"^arn:(aws|aws-us-gov|aws-cn):iam::\d{12}:(root|role\/[\w+=,.@\-_/]+|user\/[\w+=,.@\-_/]+)$"
        )
        if not arn_pattern.fullmatch(normalized):
            raise ValueError(
                "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN must be an IAM principal ARN "
                "(role, user, or account root)."
            )
        return normalized

    @field_validator("CLOUDFORMATION_TEMPLATE_URL", mode="before")
    @classmethod
    def _normalize_cloudformation_template_url(cls, value: object) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            return ""
        parsed = urlparse(normalized)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(
                "CLOUDFORMATION_TEMPLATE_URL must be an explicit http(s) URL."
            )
        if parsed.username or parsed.password:
            raise ValueError(
                "CLOUDFORMATION_TEMPLATE_URL must not include credentials."
            )
        if parsed.query or parsed.fragment:
            raise ValueError(
                "CLOUDFORMATION_TEMPLATE_URL must not include query strings or fragments."
            )
        return normalized.rstrip("/")

    @model_validator(mode="after")
    def validate_all_config(self) -> "Settings":
        """
        PRODUCTION-GRADE: Centralized validation orchestrator.
        Groups validation by concern for clarity and specificity.
        """
        _validate_all_config_impl(
            self,
            env_production=ENV_PRODUCTION,
            env_staging=ENV_STAGING,
        )
        return self

    def _validate_core_secrets(self) -> None:
        """Validate critical security primitives (SEC-01/SEC-02/SEC-06)."""
        _validate_core_secrets_impl(self)

    def _validate_database_config(self) -> None:
        """Validate database and cache connectivity settings."""
        _validate_database_config_impl(self, is_production=self.is_production)

    def _validate_llm_config(self) -> None:
        """Validate LLM provider key posture and abuse bounds."""
        _validate_llm_config_impl(self, is_production=self.is_production)

    def _validate_billing_config(self) -> None:
        """Validate billing/provider credentials and webhook allowlist."""
        _validate_billing_config_impl(self, is_production=self.is_production)

    def _validate_turnstile_config(self) -> None:
        """Validate Turnstile anti-bot controls for public/auth surfaces."""
        _validate_turnstile_config_impl(
            self,
            env_production=ENV_PRODUCTION,
            env_staging=ENV_STAGING,
        )

    def _validate_integration_config(self) -> None:
        """Validate SaaS integration strict-mode constraints."""
        _validate_integration_config_impl(self, is_production=self.is_production)

    def _validate_environment_safety(self) -> None:
        """Validate network and deployment safety (SEC-A1/SEC-A2)."""
        _validate_environment_safety_impl(
            self,
            env_production=ENV_PRODUCTION,
            env_staging=ENV_STAGING,
        )

    def _validate_observability_config(self) -> None:
        """Validate observability sink posture for strict environments."""
        _validate_observability_config_impl(
            self,
            env_production=ENV_PRODUCTION,
            env_staging=ENV_STAGING,
        )

    def _validate_remediation_guardrails(self) -> None:
        """Validate remediation kill-switch and scope guardrails."""
        _validate_remediation_guardrails_impl(
            self,
            env_production=ENV_PRODUCTION,
            env_staging=ENV_STAGING,
        )

    def _validate_enforcement_guardrails(self) -> None:
        """Validate enforcement gate runtime safety controls."""
        _validate_enforcement_guardrails_impl(self)

    model_config = SettingsConfigDict(
        env_file=str(DEFAULT_ENV_FILE),
        env_ignore_empty=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        """
        True only when ENVIRONMENT is explicitly set to 'production'.
        This is used for high-security gates and billing enforcement.
        Note: Staging/Development use DEBUG=False but are NOT 'production'.
        """
        return self.ENVIRONMENT == "production"

    @property
    def is_strict_environment(self) -> bool:
        """True for staging/production where enterprise controls must fail closed."""
        return self.ENVIRONMENT in {ENV_STAGING, ENV_PRODUCTION}
