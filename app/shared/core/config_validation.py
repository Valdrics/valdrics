"""Validation and normalization helpers for application settings."""

from __future__ import annotations

import base64
import binascii
import ipaddress

import structlog


def normalize_branding(settings_obj: object) -> None:
    """Normalize legacy product names to canonical Valdrics branding."""
    token = str(getattr(settings_obj, "APP_NAME", "") or "").strip().lower()
    legacy_names = {
        "valdrics",
        "valdrics",
        "valdrics-ai",
        "valdrics",
        "valdrics ai",
    }
    if token in legacy_names:
        structlog.get_logger().warning(
            "legacy_app_name_normalized",
            provided_app_name=getattr(settings_obj, "APP_NAME", None),
            normalized_app_name="Valdrics",
        )
        setattr(settings_obj, "APP_NAME", "Valdrics")


def validate_core_secrets(settings_obj: object) -> None:
    """Validate critical security primitives (CSRF, encryption keys, KDF)."""
    critical_keys = {
        "CSRF_SECRET_KEY": getattr(settings_obj, "CSRF_SECRET_KEY", None),
        "ENCRYPTION_KEY": getattr(settings_obj, "ENCRYPTION_KEY", None),
        "SUPABASE_JWT_SECRET": getattr(settings_obj, "SUPABASE_JWT_SECRET", None),
    }

    for name, value in critical_keys.items():
        if not value or len(value) < 32:
            raise ValueError(f"{name} must be set to a secure value (>= 32 chars).")

    csrf_value = str(getattr(settings_obj, "CSRF_SECRET_KEY", "") or "").strip().lower()
    if csrf_value in {
        "dev_secret_key_change_me_in_prod",
        "change_me",
        "changeme",
        "default",
        "csrf_secret_key",
    }:
        raise ValueError(
            "SECURITY ERROR: CSRF_SECRET_KEY must be set to a non-default secure value."
        )

    kdf_salt = getattr(settings_obj, "KDF_SALT", None)
    if not kdf_salt:
        raise ValueError("KDF_SALT must be set (base64-encoded random 32 bytes).")
    try:
        decoded_salt = base64.b64decode(kdf_salt)
        if len(decoded_salt) != 32:
            raise ValueError("KDF_SALT must decode to exactly 32 bytes.")
    except (binascii.Error, TypeError, ValueError) as exc:
        raise ValueError("KDF_SALT must be valid base64.") from exc

    if getattr(settings_obj, "ENCRYPTION_KEY_CACHE_TTL_SECONDS", 0) < 60:
        raise ValueError("ENCRYPTION_KEY_CACHE_TTL_SECONDS must be >= 60.")
    if getattr(settings_obj, "ENCRYPTION_KEY_CACHE_MAX_SIZE", 0) < 10:
        raise ValueError("ENCRYPTION_KEY_CACHE_MAX_SIZE must be >= 10.")
    if getattr(settings_obj, "BLIND_INDEX_KDF_ITERATIONS", 0) < 10000:
        raise ValueError("BLIND_INDEX_KDF_ITERATIONS must be >= 10000.")


def validate_database_config(settings_obj: object, *, is_production: bool) -> None:
    """Validate database and redis connectivity settings."""
    if is_production:
        if not getattr(settings_obj, "DATABASE_URL", None):
            raise ValueError("DATABASE_URL is required in production.")

        db_ssl_mode = getattr(settings_obj, "DB_SSL_MODE", "")
        if db_ssl_mode not in ["require", "verify-ca", "verify-full"]:
            raise ValueError(
                f"SECURITY ERROR: DB_SSL_MODE must be secure in production (current: {db_ssl_mode})."
            )
        if db_ssl_mode in {"verify-ca", "verify-full"} and not getattr(
            settings_obj, "DB_SSL_CA_CERT_PATH", None
        ):
            raise ValueError(
                "DB_SSL_CA_CERT_PATH is mandatory when DB_SSL_MODE is verify-ca or verify-full in production."
            )
        if getattr(settings_obj, "DB_USE_NULL_POOL", False) and not getattr(
            settings_obj, "DB_EXTERNAL_POOLER", False
        ):
            raise ValueError(
                "DB_USE_NULL_POOL=true requires DB_EXTERNAL_POOLER=true in production."
            )

    if (
        not getattr(settings_obj, "REDIS_URL", None)
        and getattr(settings_obj, "REDIS_HOST", None)
        and getattr(settings_obj, "REDIS_PORT", None)
    ):
        setattr(
            settings_obj,
            "REDIS_URL",
            f"redis://{getattr(settings_obj, 'REDIS_HOST')}:{getattr(settings_obj, 'REDIS_PORT')}",
        )

    if getattr(settings_obj, "DB_SLOW_QUERY_THRESHOLD_SECONDS", 0) <= 0:
        raise ValueError("DB_SLOW_QUERY_THRESHOLD_SECONDS must be > 0.")


def validate_llm_config(settings_obj: object, *, is_production: bool) -> None:
    """Validate LLM provider credentials and abuse guardrail bounds."""
    provider_keys = {
        "openai": getattr(settings_obj, "OPENAI_API_KEY", None),
        "claude": getattr(settings_obj, "CLAUDE_API_KEY", None),
        "anthropic": getattr(settings_obj, "ANTHROPIC_API_KEY", None)
        or getattr(settings_obj, "CLAUDE_API_KEY", None),
        "google": getattr(settings_obj, "GOOGLE_API_KEY", None),
        "groq": getattr(settings_obj, "GROQ_API_KEY", None),
    }

    llm_provider = getattr(settings_obj, "LLM_PROVIDER", None)
    if llm_provider in provider_keys and not provider_keys[llm_provider]:
        if is_production:
            raise ValueError(
                f"LLM_PROVIDER is '{llm_provider}' but its API key is missing."
            )
        structlog.get_logger().info(
            "llm_provider_key_missing_non_prod", provider=llm_provider
        )

    if getattr(settings_obj, "LLM_GLOBAL_ABUSE_PER_MINUTE_CAP", 0) < 1:
        raise ValueError("LLM_GLOBAL_ABUSE_PER_MINUTE_CAP must be >= 1.")
    if getattr(settings_obj, "LLM_GLOBAL_ABUSE_PER_MINUTE_CAP", 0) > 100000:
        raise ValueError("LLM_GLOBAL_ABUSE_PER_MINUTE_CAP must be <= 100000.")
    if getattr(settings_obj, "LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD", 0) < 1:
        raise ValueError("LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD must be >= 1.")
    if getattr(settings_obj, "LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD", 0) > 10000:
        raise ValueError(
            "LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD must be <= 10000."
        )
    if getattr(settings_obj, "LLM_GLOBAL_ABUSE_BLOCK_SECONDS", 0) < 30:
        raise ValueError("LLM_GLOBAL_ABUSE_BLOCK_SECONDS must be >= 30.")
    if getattr(settings_obj, "LLM_GLOBAL_ABUSE_BLOCK_SECONDS", 0) > 86400:
        raise ValueError("LLM_GLOBAL_ABUSE_BLOCK_SECONDS must be <= 86400.")


def validate_billing_config(settings_obj: object, *, is_production: bool) -> None:
    """Validate Paystack credentials and webhook allowlist configuration."""
    default_currency = str(
        getattr(settings_obj, "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY", "NGN") or "NGN"
    ).strip().upper()
    if default_currency not in {"NGN", "USD"}:
        raise ValueError("PAYSTACK_DEFAULT_CHECKOUT_CURRENCY must be one of: NGN, USD.")

    if is_production:
        paystack_secret = getattr(settings_obj, "PAYSTACK_SECRET_KEY", None)
        if not paystack_secret or str(paystack_secret).startswith("sk_test"):
            raise ValueError(
                "PAYSTACK_SECRET_KEY must be a live key (sk_live_...) in production."
            )
        if not getattr(settings_obj, "PAYSTACK_PUBLIC_KEY", None):
            raise ValueError("PAYSTACK_PUBLIC_KEY is required in production.")
        if default_currency == "USD" and not getattr(
            settings_obj, "PAYSTACK_ENABLE_USD_CHECKOUT", False
        ):
            raise ValueError(
                "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY cannot be USD when PAYSTACK_ENABLE_USD_CHECKOUT is false."
            )

    paystack_webhook_ips = [
        str(value).strip()
        for value in getattr(settings_obj, "PAYSTACK_WEBHOOK_ALLOWED_IPS", [])
        if str(value).strip()
    ]
    if not paystack_webhook_ips:
        raise ValueError("PAYSTACK_WEBHOOK_ALLOWED_IPS must contain at least one IP.")

    for ip_value in paystack_webhook_ips:
        try:
            ipaddress.ip_address(ip_value)
        except ValueError as exc:
            raise ValueError(
                "PAYSTACK_WEBHOOK_ALLOWED_IPS contains invalid IP address: "
                f"{ip_value}"
            ) from exc


def validate_turnstile_config(
    settings_obj: object, *, env_production: str, env_staging: str
) -> None:
    """Validate Turnstile anti-bot controls for public/auth surfaces."""
    timeout_seconds = float(getattr(settings_obj, "TURNSTILE_TIMEOUT_SECONDS", 0))
    if timeout_seconds <= 0:
        raise ValueError("TURNSTILE_TIMEOUT_SECONDS must be > 0.")
    if timeout_seconds > 15:
        raise ValueError("TURNSTILE_TIMEOUT_SECONDS must be <= 15.")

    verify_url = str(getattr(settings_obj, "TURNSTILE_VERIFY_URL", "") or "").strip().lower()
    if not verify_url.startswith("https://"):
        raise ValueError("TURNSTILE_VERIFY_URL must use https://.")

    turnstile_required = (
        bool(getattr(settings_obj, "TURNSTILE_REQUIRE_PUBLIC_ASSESSMENT", False))
        or bool(getattr(settings_obj, "TURNSTILE_REQUIRE_SSO_DISCOVERY", False))
        or bool(getattr(settings_obj, "TURNSTILE_REQUIRE_ONBOARD", False))
    )

    environment = getattr(settings_obj, "ENVIRONMENT", "")
    if (
        bool(getattr(settings_obj, "TURNSTILE_ENABLED", False))
        and turnstile_required
        and environment in {env_production, env_staging}
    ):
        secret = str(getattr(settings_obj, "TURNSTILE_SECRET_KEY", "") or "").strip()
        if len(secret) < 16:
            raise ValueError(
                "TURNSTILE_SECRET_KEY must be configured when Turnstile is enabled in staging/production."
            )
        if bool(getattr(settings_obj, "TURNSTILE_FAIL_OPEN", False)):
            raise ValueError("TURNSTILE_FAIL_OPEN must be false in staging/production.")


def validate_integration_config(settings_obj: object, *, is_production: bool) -> None:
    """Validate SaaS integration strict mode constraints."""
    if bool(getattr(settings_obj, "SAAS_STRICT_INTEGRATIONS", False)):
        sconf = [
            getattr(settings_obj, "SLACK_CHANNEL_ID", None),
            getattr(settings_obj, "JIRA_BASE_URL", None),
            getattr(settings_obj, "GITHUB_ACTIONS_TOKEN", None),
        ]
        if any(sconf) and is_production:
            raise ValueError(
                "SAAS_STRICT_INTEGRATIONS forbids env-based settings in production."
            )


def validate_environment_safety(
    settings_obj: object,
    *,
    env_production: str,
    env_staging: str,
) -> None:
    """Validate network/deployment safety requirements and warnings."""
    trusted_proxy_hops = int(getattr(settings_obj, "TRUSTED_PROXY_HOPS", 0))
    if trusted_proxy_hops < 1 or trusted_proxy_hops > 5:
        raise ValueError("TRUSTED_PROXY_HOPS must be between 1 and 5.")

    trusted_proxy_cidrs = [
        str(cidr).strip()
        for cidr in getattr(settings_obj, "TRUSTED_PROXY_CIDRS", [])
        if str(cidr).strip()
    ]
    for cidr in trusted_proxy_cidrs:
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError as exc:
            raise ValueError(f"TRUSTED_PROXY_CIDRS contains invalid CIDR: {cidr}") from exc

    environment = getattr(settings_obj, "ENVIRONMENT", "")
    if (
        bool(getattr(settings_obj, "TRUST_PROXY_HEADERS", False))
        and environment in {env_production, env_staging}
        and not trusted_proxy_cidrs
    ):
        raise ValueError(
            "TRUSTED_PROXY_CIDRS must be configured when TRUST_PROXY_HEADERS=true in staging/production."
        )

    if bool(getattr(settings_obj, "is_production", False)) or environment == env_staging:
        admin_api_key = getattr(settings_obj, "ADMIN_API_KEY", None)
        if not admin_api_key or len(str(admin_api_key)) < 32:
            raise ValueError("ADMIN_API_KEY must be >= 32 chars in staging/production.")

        web_concurrency_raw = str(
            getattr(settings_obj, "WEB_CONCURRENCY", 1) or 1
        ).strip()
        try:
            web_concurrency = int(web_concurrency_raw)
        except (TypeError, ValueError):
            web_concurrency = 1

        if web_concurrency > 1 and (
            not bool(getattr(settings_obj, "CIRCUIT_BREAKER_DISTRIBUTED_STATE", False))
            or not getattr(settings_obj, "REDIS_URL", None)
        ):
            raise ValueError(
                "WEB_CONCURRENCY > 1 requires CIRCUIT_BREAKER_DISTRIBUTED_STATE=true "
                "and REDIS_URL configured in staging/production."
            )

        if (
            bool(getattr(settings_obj, "RATELIMIT_ENABLED", False))
            and not getattr(settings_obj, "REDIS_URL", None)
            and not bool(getattr(settings_obj, "ALLOW_IN_MEMORY_RATE_LIMITS", False))
        ):
            raise ValueError(
                "REDIS_URL is required for distributed rate limiting in "
                "staging/production. Set ALLOW_IN_MEMORY_RATE_LIMITS=true only "
                "for temporary break-glass usage."
            )

        logger = structlog.get_logger()
        cors_origins = getattr(settings_obj, "CORS_ORIGINS", [])
        if any("localhost" in o or "127.0.0.1" in o for o in cors_origins):
            logger.warning("cors_localhost_in_production")

        for url in [getattr(settings_obj, "API_URL", None), getattr(settings_obj, "FRONTEND_URL", None)]:
            if url and str(url).startswith("http://"):
                logger.warning("insecure_url_in_production", url=url)


def validate_remediation_guardrails(
    settings_obj: object,
    *,
    env_production: str,
    env_staging: str,
) -> None:
    """Validate safety guardrail configuration for remediation execution."""
    normalized_scope = str(
        getattr(settings_obj, "REMEDIATION_KILL_SWITCH_SCOPE", "tenant") or "tenant"
    ).strip().lower()
    if normalized_scope not in {"tenant", "global"}:
        raise ValueError("REMEDIATION_KILL_SWITCH_SCOPE must be one of: tenant, global.")
    setattr(settings_obj, "REMEDIATION_KILL_SWITCH_SCOPE", normalized_scope)

    if (
        getattr(settings_obj, "ENVIRONMENT", "") in {env_production, env_staging}
        and normalized_scope == "global"
        and not bool(
            getattr(settings_obj, "REMEDIATION_KILL_SWITCH_ALLOW_GLOBAL_SCOPE", False)
        )
    ):
        raise ValueError(
            "REMEDIATION_KILL_SWITCH_SCOPE=global requires "
            "REMEDIATION_KILL_SWITCH_ALLOW_GLOBAL_SCOPE=true in staging/production."
        )


def validate_enforcement_guardrails(settings_obj: object) -> None:
    """Validate enforcement gate runtime safety controls."""
    if getattr(settings_obj, "ENFORCEMENT_GATE_TIMEOUT_SECONDS", 0) <= 0:
        raise ValueError("ENFORCEMENT_GATE_TIMEOUT_SECONDS must be > 0.")
    if getattr(settings_obj, "ENFORCEMENT_GATE_TIMEOUT_SECONDS", 0) > 30:
        raise ValueError("ENFORCEMENT_GATE_TIMEOUT_SECONDS must be <= 30.")
    if getattr(settings_obj, "ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP", 0) < 1:
        raise ValueError("ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP must be >= 1.")
    if getattr(settings_obj, "ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP", 0) > 100000:
        raise ValueError("ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP must be <= 100000.")

    export_signing_secret = str(
        getattr(settings_obj, "ENFORCEMENT_EXPORT_SIGNING_SECRET", "") or ""
    ).strip()
    if export_signing_secret and len(export_signing_secret) < 32:
        raise ValueError(
            "ENFORCEMENT_EXPORT_SIGNING_SECRET must be >= 32 chars when provided."
        )

    export_signing_kid = str(
        getattr(settings_obj, "ENFORCEMENT_EXPORT_SIGNING_KID", "") or ""
    ).strip()
    if export_signing_kid and len(export_signing_kid) > 64:
        raise ValueError("ENFORCEMENT_EXPORT_SIGNING_KID must be <= 64 chars.")

    if getattr(settings_obj, "ENFORCEMENT_RESERVATION_RECONCILIATION_SLA_SECONDS", 0) < 60:
        raise ValueError(
            "ENFORCEMENT_RESERVATION_RECONCILIATION_SLA_SECONDS must be >= 60."
        )
    if getattr(settings_obj, "ENFORCEMENT_RESERVATION_RECONCILIATION_SLA_SECONDS", 0) > 604800:
        raise ValueError(
            "ENFORCEMENT_RESERVATION_RECONCILIATION_SLA_SECONDS must be <= 604800."
        )
    if getattr(settings_obj, "ENFORCEMENT_RECONCILIATION_SWEEP_MAX_RELEASES", 0) < 1:
        raise ValueError("ENFORCEMENT_RECONCILIATION_SWEEP_MAX_RELEASES must be >= 1.")
    if getattr(settings_obj, "ENFORCEMENT_RECONCILIATION_SWEEP_MAX_RELEASES", 0) > 1000:
        raise ValueError(
            "ENFORCEMENT_RECONCILIATION_SWEEP_MAX_RELEASES must be <= 1000."
        )
    if getattr(settings_obj, "ENFORCEMENT_RECONCILIATION_EXCEPTION_SCAN_LIMIT", 0) < 1:
        raise ValueError(
            "ENFORCEMENT_RECONCILIATION_EXCEPTION_SCAN_LIMIT must be >= 1."
        )
    if getattr(settings_obj, "ENFORCEMENT_RECONCILIATION_EXCEPTION_SCAN_LIMIT", 0) > 1000:
        raise ValueError(
            "ENFORCEMENT_RECONCILIATION_EXCEPTION_SCAN_LIMIT must be <= 1000."
        )
    if getattr(settings_obj, "ENFORCEMENT_RECONCILIATION_DRIFT_ALERT_THRESHOLD_USD", 0) < 0:
        raise ValueError(
            "ENFORCEMENT_RECONCILIATION_DRIFT_ALERT_THRESHOLD_USD must be >= 0."
        )
    if getattr(settings_obj, "ENFORCEMENT_RECONCILIATION_DRIFT_ALERT_EXCEPTION_COUNT", 0) < 1:
        raise ValueError(
            "ENFORCEMENT_RECONCILIATION_DRIFT_ALERT_EXCEPTION_COUNT must be >= 1."
        )
    if getattr(settings_obj, "ENFORCEMENT_EXPORT_MAX_DAYS", 0) < 1:
        raise ValueError("ENFORCEMENT_EXPORT_MAX_DAYS must be >= 1.")
    if getattr(settings_obj, "ENFORCEMENT_EXPORT_MAX_DAYS", 0) > 3650:
        raise ValueError("ENFORCEMENT_EXPORT_MAX_DAYS must be <= 3650.")
    if getattr(settings_obj, "ENFORCEMENT_EXPORT_MAX_ROWS", 0) < 1:
        raise ValueError("ENFORCEMENT_EXPORT_MAX_ROWS must be >= 1.")
    if getattr(settings_obj, "ENFORCEMENT_EXPORT_MAX_ROWS", 0) > 50000:
        raise ValueError("ENFORCEMENT_EXPORT_MAX_ROWS must be <= 50000.")

    fallback_signing_keys = list(
        getattr(settings_obj, "ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS", []) or []
    )
    if len(fallback_signing_keys) > 5:
        raise ValueError(
            "ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS must contain at most 5 keys."
        )
    for fallback_secret in fallback_signing_keys:
        if len(str(fallback_secret or "").strip()) < 32:
            raise ValueError(
                "Each ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS key must be >= 32 chars."
            )


def validate_all_config(
    settings_obj: object,
    *,
    env_production: str,
    env_staging: str,
) -> None:
    """Run full multi-domain settings validation pipeline."""
    normalize_branding(settings_obj)

    if bool(getattr(settings_obj, "TESTING", False)) and getattr(
        settings_obj, "ENVIRONMENT", None
    ) in {env_production, env_staging}:
        raise ValueError(
            "TESTING must be false in staging/production runtime environments."
        )

    if bool(getattr(settings_obj, "TESTING", False)):
        return

    is_production = bool(getattr(settings_obj, "is_production", False))
    validate_core_secrets(settings_obj)
    validate_database_config(settings_obj, is_production=is_production)
    validate_llm_config(settings_obj, is_production=is_production)
    validate_billing_config(settings_obj, is_production=is_production)
    validate_integration_config(settings_obj, is_production=is_production)
    validate_turnstile_config(
        settings_obj,
        env_production=env_production,
        env_staging=env_staging,
    )
    validate_remediation_guardrails(
        settings_obj,
        env_production=env_production,
        env_staging=env_staging,
    )
    validate_enforcement_guardrails(settings_obj)
    validate_environment_safety(
        settings_obj,
        env_production=env_production,
        env_staging=env_staging,
    )


__all__ = [
    "normalize_branding",
    "validate_all_config",
    "validate_billing_config",
    "validate_core_secrets",
    "validate_database_config",
    "validate_enforcement_guardrails",
    "validate_environment_safety",
    "validate_integration_config",
    "validate_llm_config",
    "validate_remediation_guardrails",
    "validate_turnstile_config",
]
