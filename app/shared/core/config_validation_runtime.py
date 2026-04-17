"""Runtime-safety configuration validators kept separate from core secrets checks."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import ipaddress
from urllib.parse import urlparse

from app.shared.core.config_validation_placeholders import (
    require_no_managed_placeholder,
)
from app.shared.core.cors_policy import validate_strict_cors_allowed_origins
from app.shared.orchestration.contracts import (
    platform_runtime_profile,
    PlatformRuntimeProfile,
)


def _is_truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_environment(value: object) -> str:
    return str(value or "").strip().lower()


def _strict_environment(
    settings_obj: object, *, env_production: str, env_staging: str
) -> bool:
    return _normalize_environment(getattr(settings_obj, "ENVIRONMENT", "")) in {
        env_production,
        env_staging,
    }


def _public_api_rate_limiting_backend(settings_obj: object) -> str:
    return (
        str(
            getattr(settings_obj, "PUBLIC_API_RATE_LIMITING_BACKEND", "cloudflare")
            or "cloudflare"
        )
        .strip()
        .lower()
    )


def _parse_break_glass_expiry(raw_value: object) -> datetime:
    normalized = str(raw_value or "").strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timezone offset required")
    return parsed.astimezone(timezone.utc)


def _validate_break_glass_window(
    *,
    enabled: bool,
    reason: object,
    expires_at: object,
    max_duration_hours: object,
    strict_env: bool,
    setting_prefix: str,
) -> None:
    if not strict_env or not enabled:
        return

    reason_text = str(reason or "").strip()
    if len(reason_text) < 10:
        raise ValueError(
            f"{setting_prefix}_REASON must be configured (min 10 chars) when {setting_prefix}=true in staging/production."
        )

    expires_text = str(expires_at or "").strip()
    if not expires_text:
        raise ValueError(
            f"{setting_prefix}_EXPIRES_AT must be configured (ISO-8601 with timezone) when {setting_prefix}=true in staging/production."
        )

    try:
        expires_dt = _parse_break_glass_expiry(expires_text)
    except ValueError as exc:
        raise ValueError(
            f"{setting_prefix}_EXPIRES_AT must be a valid ISO-8601 timestamp with timezone."
        ) from exc

    now_utc = datetime.now(timezone.utc)
    if expires_dt <= now_utc:
        raise ValueError(f"{setting_prefix}_EXPIRES_AT must be in the future.")

    max_duration_candidate = max_duration_hours
    if isinstance(max_duration_candidate, bool):
        raise ValueError(
            f"{setting_prefix}_MAX_DURATION_HOURS must be a positive integer."
        )
    try:
        if isinstance(max_duration_candidate, (bytes, bytearray)):
            max_hours = int(max_duration_candidate.decode().strip())
        elif isinstance(max_duration_candidate, str):
            max_hours = int(max_duration_candidate.strip())
        elif isinstance(max_duration_candidate, int):
            max_hours = max_duration_candidate
        else:
            max_hours = int(str(max_duration_candidate).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{setting_prefix}_MAX_DURATION_HOURS must be a positive integer."
        ) from exc
    if max_hours < 1:
        raise ValueError(f"{setting_prefix}_MAX_DURATION_HOURS must be >= 1.")
    if expires_dt > now_utc + timedelta(hours=max_hours):
        raise ValueError(
            f"{setting_prefix}_EXPIRES_AT exceeds the configured max break-glass window of {max_hours} hour(s)."
        )


def _validate_strict_public_url(url: object, *, name: str) -> None:
    candidate = str(url or "").strip()
    if not candidate:
        raise ValueError(f"{name} must be configured in staging/production.")
    require_no_managed_placeholder(candidate, name=name)

    parsed = urlparse(candidate)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(
            f"{name} must use an explicit https:// URL in staging/production."
        )
    if parsed.username or parsed.password:
        raise ValueError(f"{name} must not include embedded credentials.")
    if parsed.query or parsed.fragment:
        raise ValueError(f"{name} must not include query strings or fragments.")

    hostname = str(parsed.hostname or "").strip().lower()
    if not hostname or hostname == "localhost":
        raise ValueError(f"{name} must not point at localhost in staging/production.")

    try:
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        return

    if (
        host_ip.is_private
        or host_ip.is_loopback
        or host_ip.is_link_local
        or host_ip.is_multicast
        or host_ip.is_unspecified
        or host_ip.is_reserved
    ):
        raise ValueError(
            f"{name} must not resolve to a private or non-routable IP in staging/production."
        )


def validate_turnstile_config(
    settings_obj: object, *, env_production: str, env_staging: str
) -> None:
    """Validate Turnstile anti-bot controls for public/auth surfaces."""
    timeout_seconds = float(getattr(settings_obj, "TURNSTILE_TIMEOUT_SECONDS", 0))
    if timeout_seconds <= 0:
        raise ValueError("TURNSTILE_TIMEOUT_SECONDS must be > 0.")
    if timeout_seconds > 15:
        raise ValueError("TURNSTILE_TIMEOUT_SECONDS must be <= 15.")

    verify_url = (
        str(getattr(settings_obj, "TURNSTILE_VERIFY_URL", "") or "").strip().lower()
    )
    if not verify_url.startswith("https://"):
        raise ValueError("TURNSTILE_VERIFY_URL must use https://.")

    turnstile_required = (
        bool(getattr(settings_obj, "TURNSTILE_REQUIRE_PUBLIC_ASSESSMENT", False))
        or bool(getattr(settings_obj, "TURNSTILE_REQUIRE_SSO_DISCOVERY", False))
        or bool(getattr(settings_obj, "TURNSTILE_REQUIRE_ONBOARD", False))
        or bool(getattr(settings_obj, "TURNSTILE_REQUIRE_PUBLIC_SALES_INTAKE", False))
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
    if not _is_truthy(getattr(settings_obj, "SAAS_STRICT_INTEGRATIONS", False)):
        return

    environment = _normalize_environment(getattr(settings_obj, "ENVIRONMENT", ""))
    if environment not in {"production", "staging"} and not is_production:
        return

    violations: list[str] = []
    direct_env_fields = (
        "SLACK_CHANNEL_ID",
        "JIRA_BASE_URL",
        "JIRA_EMAIL",
        "JIRA_API_TOKEN",
        "JIRA_PROJECT_KEY",
        "GITHUB_ACTIONS_OWNER",
        "GITHUB_ACTIONS_REPO",
        "GITHUB_ACTIONS_WORKFLOW_ID",
        "GITHUB_ACTIONS_TOKEN",
        "GITLAB_CI_PROJECT_ID",
        "GITLAB_CI_TRIGGER_TOKEN",
        "GENERIC_CI_WEBHOOK_URL",
        "GENERIC_CI_WEBHOOK_BEARER_TOKEN",
    )
    for field_name in direct_env_fields:
        value = getattr(settings_obj, field_name, None)
        if isinstance(value, str):
            if value.strip():
                violations.append(field_name)
        elif value is not None:
            violations.append(field_name)

    feature_toggles = (
        "GITHUB_ACTIONS_ENABLED",
        "GITLAB_CI_ENABLED",
        "GENERIC_CI_WEBHOOK_ENABLED",
    )
    for field_name in feature_toggles:
        if _is_truthy(getattr(settings_obj, field_name, False)):
            violations.append(field_name)

    if violations:
        violation_text = ", ".join(sorted(set(violations)))
        raise ValueError(
            "SAAS_STRICT_INTEGRATIONS forbids env-based workflow and routing settings "
            f"in staging/production: {violation_text}."
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
            raise ValueError(
                f"TRUSTED_PROXY_CIDRS contains invalid CIDR: {cidr}"
            ) from exc

    environment = _normalize_environment(getattr(settings_obj, "ENVIRONMENT", ""))
    if (
        bool(getattr(settings_obj, "TRUST_PROXY_HEADERS", False))
        and environment in {env_production, env_staging}
        and not trusted_proxy_cidrs
    ):
        raise ValueError(
            "TRUSTED_PROXY_CIDRS must be configured when TRUST_PROXY_HEADERS=true in staging/production."
        )

    strict_env = environment in {env_production, env_staging}

    if strict_env:
        runtime_profile = platform_runtime_profile(settings_obj)
        public_rate_limit_backend = _public_api_rate_limiting_backend(settings_obj)

        if runtime_profile is PlatformRuntimeProfile.GCP:
            required_gcp_values = {
                "GCP_PROJECT_ID": getattr(settings_obj, "GCP_PROJECT_ID", None),
                "GCP_REGION": getattr(settings_obj, "GCP_REGION", None),
                "GCP_CLOUD_TASKS_QUEUE": getattr(
                    settings_obj, "GCP_CLOUD_TASKS_QUEUE", None
                ),
                "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL": getattr(
                    settings_obj, "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL", None
                ),
                "GCP_CLOUD_RUN_SERVICE_NAME": getattr(
                    settings_obj, "GCP_CLOUD_RUN_SERVICE_NAME", None
                ),
                "GCP_CLOUD_RUN_BATCH_JOB_NAME": getattr(
                    settings_obj, "GCP_CLOUD_RUN_BATCH_JOB_NAME", None
                ),
            }
            for field_name, raw_value in required_gcp_values.items():
                value = str(raw_value or "").strip()
                if not value:
                    raise ValueError(
                        f"{field_name} must be configured when PLATFORM_RUNTIME_PROFILE=gcp in staging/production."
                    )
                require_no_managed_placeholder(value, name=field_name)

            internal_base_url_value = str(
                getattr(settings_obj, "GCP_INTERNAL_BASE_URL", "") or ""
            ).strip()
            if internal_base_url_value:
                _validate_strict_public_url(
                    internal_base_url_value,
                    name="GCP_INTERNAL_BASE_URL",
                )

            internal_auth_audience_value = str(
                getattr(settings_obj, "GCP_INTERNAL_AUTH_AUDIENCE", "") or ""
            ).strip()
            if internal_auth_audience_value:
                _validate_strict_public_url(
                    internal_auth_audience_value,
                    name="GCP_INTERNAL_AUTH_AUDIENCE",
                )
                api_url_value = str(getattr(settings_obj, "API_URL", "") or "").strip()
                if internal_auth_audience_value.rstrip("/") != api_url_value.rstrip(
                    "/"
                ):
                    raise ValueError(
                        "GCP_INTERNAL_AUTH_AUDIENCE must match API_URL in the supported "
                        "Cloudflare-fronted GCP runtime profile because Cloud Run custom "
                        "audiences are provisioned for the public API URL."
                    )

            allowed_service_accounts = [
                str(email or "").strip().lower()
                for email in getattr(
                    settings_obj, "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS", []
                )
                if str(email or "").strip()
            ]
            if not allowed_service_accounts:
                raise ValueError(
                    "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS must be configured when PLATFORM_RUNTIME_PROFILE=gcp in staging/production."
                )

        if public_rate_limit_backend == "cloudflare":
            if bool(getattr(settings_obj, "RATELIMIT_ENABLED", False)):
                raise ValueError(
                    "RATELIMIT_ENABLED must be false when PUBLIC_API_RATE_LIMITING_BACKEND=cloudflare in staging/production."
                )
            api_url = str(getattr(settings_obj, "API_URL", "") or "").strip().lower()
            if api_url.endswith(".run.app") or ".run.app/" in api_url:
                raise ValueError(
                    "API_URL must use the Cloudflare-proxied custom hostname when PUBLIC_API_RATE_LIMITING_BACKEND=cloudflare."
                )
            internal_base_url = internal_base_url_value.lower().rstrip("/")
            if internal_base_url and internal_base_url == api_url.rstrip("/"):
                raise ValueError(
                    "GCP_INTERNAL_BASE_URL must target the direct Cloud Run service URL, not API_URL, when PUBLIC_API_RATE_LIMITING_BACKEND=cloudflare."
                )

        admin_api_key = getattr(settings_obj, "ADMIN_API_KEY", None)
        if not admin_api_key or len(str(admin_api_key)) < 32:
            raise ValueError("ADMIN_API_KEY must be >= 32 chars in staging/production.")

        internal_metrics_auth_token = str(
            getattr(settings_obj, "INTERNAL_METRICS_AUTH_TOKEN", "") or ""
        ).strip()
        if internal_metrics_auth_token and len(internal_metrics_auth_token) < 32:
            raise ValueError(
                "INTERNAL_METRICS_AUTH_TOKEN must be >= 32 chars when configured."
            )

        if (
            runtime_profile is PlatformRuntimeProfile.GCP
            and public_rate_limit_backend != "cloudflare"
        ):
            raise ValueError(
                "PUBLIC_API_RATE_LIMITING_BACKEND must be cloudflare for the supported managed GCP profile."
            )
        if runtime_profile is PlatformRuntimeProfile.GCP and bool(
            getattr(settings_obj, "RATELIMIT_ENABLED", False)
        ):
            raise ValueError(
                "RATELIMIT_ENABLED must be false for the supported managed GCP profile; public API throttling is delegated to Cloudflare edge."
            )

        _validate_strict_public_url(
            getattr(settings_obj, "API_URL", None),
            name="API_URL",
        )
        _validate_strict_public_url(
            getattr(settings_obj, "FRONTEND_URL", None),
            name="FRONTEND_URL",
        )

        _validate_break_glass_window(
            enabled=_is_truthy(
                getattr(settings_obj, "ALLOW_INSECURE_OUTBOUND_TLS", False)
            ),
            reason=getattr(settings_obj, "OUTBOUND_TLS_BREAK_GLASS_REASON", None),
            expires_at=getattr(
                settings_obj, "OUTBOUND_TLS_BREAK_GLASS_EXPIRES_AT", None
            ),
            max_duration_hours=getattr(
                settings_obj,
                "OUTBOUND_TLS_BREAK_GLASS_MAX_DURATION_HOURS",
                24,
            ),
            strict_env=True,
            setting_prefix="OUTBOUND_TLS_BREAK_GLASS",
        )

        audit_retention_days = int(
            getattr(settings_obj, "AUDIT_LOG_RETENTION_DAYS", 0) or 0
        )
        if audit_retention_days < 1:
            raise ValueError("AUDIT_LOG_RETENTION_DAYS must be >= 1.")

        setattr(
            settings_obj,
            "CORS_ORIGINS",
            validate_strict_cors_allowed_origins(
                list(getattr(settings_obj, "CORS_ORIGINS", []) or []),
                frontend_url=str(getattr(settings_obj, "FRONTEND_URL", "") or ""),
            ),
        )


def validate_remediation_guardrails(
    settings_obj: object,
    *,
    env_production: str,
    env_staging: str,
) -> None:
    """Validate safety guardrail configuration for remediation execution."""
    normalized_scope = (
        str(
            getattr(settings_obj, "REMEDIATION_KILL_SWITCH_SCOPE", "tenant") or "tenant"
        )
        .strip()
        .lower()
    )
    if normalized_scope not in {"tenant", "global"}:
        raise ValueError(
            "REMEDIATION_KILL_SWITCH_SCOPE must be one of: tenant, global."
        )
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

    approval_token_secret = str(
        getattr(settings_obj, "ENFORCEMENT_APPROVAL_TOKEN_SECRET", "") or ""
    ).strip()
    environment = _normalize_environment(getattr(settings_obj, "ENVIRONMENT", ""))
    strict_env = environment in {"production", "staging"}
    if strict_env and len(approval_token_secret) < 32:
        raise ValueError(
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET must be configured and >= 32 chars "
            "in staging/production."
        )
    if approval_token_secret and len(approval_token_secret) < 32:
        raise ValueError(
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET must be >= 32 chars when provided."
        )

    export_signing_secret = str(
        getattr(settings_obj, "ENFORCEMENT_EXPORT_SIGNING_SECRET", "") or ""
    ).strip()
    if strict_env and len(export_signing_secret) < 32:
        raise ValueError(
            "ENFORCEMENT_EXPORT_SIGNING_SECRET must be configured and >= 32 chars "
            "in staging/production."
        )
    if export_signing_secret and len(export_signing_secret) < 32:
        raise ValueError(
            "ENFORCEMENT_EXPORT_SIGNING_SECRET must be >= 32 chars when provided."
        )

    export_signing_kid = str(
        getattr(settings_obj, "ENFORCEMENT_EXPORT_SIGNING_KID", "") or ""
    ).strip()
    if export_signing_kid and len(export_signing_kid) > 64:
        raise ValueError("ENFORCEMENT_EXPORT_SIGNING_KID must be <= 64 chars.")

    if (
        getattr(settings_obj, "ENFORCEMENT_RESERVATION_RECONCILIATION_SLA_SECONDS", 0)
        < 60
    ):
        raise ValueError(
            "ENFORCEMENT_RESERVATION_RECONCILIATION_SLA_SECONDS must be >= 60."
        )
    if (
        getattr(settings_obj, "ENFORCEMENT_RESERVATION_RECONCILIATION_SLA_SECONDS", 0)
        > 604800
    ):
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
    if (
        getattr(settings_obj, "ENFORCEMENT_RECONCILIATION_EXCEPTION_SCAN_LIMIT", 0)
        > 1000
    ):
        raise ValueError(
            "ENFORCEMENT_RECONCILIATION_EXCEPTION_SCAN_LIMIT must be <= 1000."
        )
    if (
        getattr(settings_obj, "ENFORCEMENT_RECONCILIATION_DRIFT_ALERT_THRESHOLD_USD", 0)
        < 0
    ):
        raise ValueError(
            "ENFORCEMENT_RECONCILIATION_DRIFT_ALERT_THRESHOLD_USD must be >= 0."
        )
    if (
        getattr(
            settings_obj, "ENFORCEMENT_RECONCILIATION_DRIFT_ALERT_EXCEPTION_COUNT", 0
        )
        < 1
    ):
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
