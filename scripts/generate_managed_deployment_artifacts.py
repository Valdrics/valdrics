#!/usr/bin/env python3
"""Generate deployment-ready Koyeb and future-scale Helm/EKS artifacts."""

from __future__ import annotations

import argparse
import ipaddress
import json
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlparse

import yaml

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import parse_env_file


DEFAULT_OUTPUT_ROOT = Path(".runtime/deploy")
PLACEHOLDER_PREFIX = "REPLACE_WITH_"
SUPPORTED_ENVIRONMENTS = ("staging", "production")
DEFAULT_KOYEB_IMAGE_REGISTRY = "ghcr.io/valdrics"
DEFAULT_RELEASE_TAG = "REPLACE_WITH_RELEASE_TAG"
DEFAULT_API_IMAGE_DIGEST = "REPLACE_WITH_API_IMAGE_DIGEST"
DEFAULT_DASHBOARD_IMAGE_DIGEST = "REPLACE_WITH_DASHBOARD_IMAGE_DIGEST"
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
RUNTIME_BLOCKER_KEYS = (
    "API_URL",
    "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN",
    "DATABASE_URL",
    "FRONTEND_URL",
    "OTEL_EXPORTER_OTLP_ENDPOINT",
    "PAYSTACK_PUBLIC_KEY",
    "PAYSTACK_SECRET_KEY",
    "REDIS_URL",
    "SENTRY_DSN",
    "SUPABASE_JWT_SECRET",
    "TRUSTED_PROXY_CIDRS",
)
KOYEB_SHARED_SECRET_NAMES = {
    "DATABASE_URL": "valdrics-database-url",
    "REDIS_URL": "valdrics-redis-url",
    "SUPABASE_JWT_SECRET": "valdrics-jwt-secret",
    "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN": "valdrics-aws-trust-principal-arn",
    "ENFORCEMENT_APPROVAL_TOKEN_SECRET": "valdrics-enforcement-approval-token-secret",
    "ENFORCEMENT_EXPORT_SIGNING_SECRET": "valdrics-enforcement-export-signing-secret",
    "OTEL_EXPORTER_OTLP_ENDPOINT": "valdrics-otlp-endpoint",
    "ENCRYPTION_KEY": "valdrics-encryption-key",
    "KDF_SALT": "valdrics-kdf-salt",
    "CSRF_SECRET_KEY": "valdrics-csrf-secret",
    "ADMIN_API_KEY": "valdrics-admin-api-key",
    "PAYSTACK_SECRET_KEY": "valdrics-paystack-secret",
    "PAYSTACK_PUBLIC_KEY": "valdrics-paystack-public",
    "SENTRY_DSN": "valdrics-sentry-dsn",
}
KOYEB_API_ONLY_SECRET_NAMES = {
    "TRUSTED_PROXY_CIDRS": "valdrics-trusted-proxy-cidrs",
    "INTERNAL_METRICS_AUTH_TOKEN": "valdrics-internal-metrics-token",
    "INTERNAL_JOB_SECRET": "valdrics-internal-job-secret",
}
KOYEB_OPTIONAL_SHARED_SECRET_NAMES = {
    "FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK": "valdrics-forecaster-break-glass-enabled",
    "FORECASTER_BREAK_GLASS_REASON": "valdrics-forecaster-break-glass-reason",
    "FORECASTER_BREAK_GLASS_EXPIRES_AT": "valdrics-forecaster-break-glass-expires-at",
    "ALLOW_INSECURE_OUTBOUND_TLS": "valdrics-outbound-tls-break-glass-enabled",
    "OUTBOUND_TLS_BREAK_GLASS_REASON": "valdrics-outbound-tls-break-glass-reason",
    "OUTBOUND_TLS_BREAK_GLASS_EXPIRES_AT": "valdrics-outbound-tls-break-glass-expires-at",
}
HELM_INLINE_ENV_KEYS = (
    "ENVIRONMENT",
    "LOG_LEVEL",
    "WEB_CONCURRENCY",
    "ENABLE_SCHEDULER",
    "LLM_PROVIDER",
    "EXPOSE_API_DOCUMENTATION_PUBLICLY",
    "OTEL_LOGS_EXPORT_ENABLED",
    "SAAS_STRICT_INTEGRATIONS",
    "TRUST_PROXY_HEADERS",
    "APP_RUNTIME_DATA_DIR",
    "CORS_ORIGINS",
)
HELM_SECRET_EXCLUDED_KEYS = frozenset(HELM_INLINE_ENV_KEYS) | {
    "API_URL",
    "FRONTEND_URL",
    "ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION",
    "APP_NAME",
    "DEBUG",
    "POSTGRES_DB",
    "POSTGRES_PASSWORD",
    "POSTGRES_USER",
    "SUPABASE_URL",
    "TESTING",
}
TERRAFORM_BASE_REQUIRED_INPUTS = ("external_id", "valdrics_account_id")
FORECASTER_BREAK_GLASS_KEYS = (
    "FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK",
    "FORECASTER_BREAK_GLASS_REASON",
    "FORECASTER_BREAK_GLASS_EXPIRES_AT",
)
OUTBOUND_TLS_BREAK_GLASS_KEYS = (
    "ALLOW_INSECURE_OUTBOUND_TLS",
    "OUTBOUND_TLS_BREAK_GLASS_REASON",
    "OUTBOUND_TLS_BREAK_GLASS_EXPIRES_AT",
)
KOYEB_DASHBOARD_PUBLIC_ENV_KEYS = (
    "PUBLIC_API_URL",
    "PUBLIC_SUPABASE_URL",
    "PUBLIC_SUPABASE_ANON_KEY",
)


def _string_value(values: dict[str, str], key: str, default: str = "") -> str:
    return str(values.get(key, default) or default)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _resolve_default_path(path: Path) -> Path:
    return (_repo_root() / path).resolve()


def _resolve_cli_path(path: Path) -> Path:
    raw = Path(path).expanduser()
    if raw.is_absolute():
        return raw.resolve()
    return (_repo_root() / raw).resolve()


def _selected_llm_provider(values: dict[str, str]) -> str:
    normalized = _string_value(values, "LLM_PROVIDER", "groq").strip().lower()
    if normalized not in LLM_PROVIDER_ENV_KEY:
        raise ValueError(
            "LLM_PROVIDER must be one of: "
            + ", ".join(sorted(LLM_PROVIDER_ENV_KEY))
        )
    return normalized


def _selected_llm_provider_env_key(values: dict[str, str]) -> str:
    return LLM_PROVIDER_ENV_KEY[_selected_llm_provider(values)]


def _contains_placeholder(value: str) -> bool:
    return PLACEHOLDER_PREFIX in str(value or "")


def _is_truthy(value: str) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def _include_forecaster_break_glass(values: dict[str, str]) -> bool:
    return _is_truthy(_string_value(values, "FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK")) or any(
        _string_value(values, key).strip()
        for key in ("FORECASTER_BREAK_GLASS_REASON", "FORECASTER_BREAK_GLASS_EXPIRES_AT")
    )


def _include_outbound_tls_break_glass(values: dict[str, str]) -> bool:
    return _is_truthy(_string_value(values, "ALLOW_INSECURE_OUTBOUND_TLS")) or any(
        _string_value(values, key).strip()
        for key in ("OUTBOUND_TLS_BREAK_GLASS_REASON", "OUTBOUND_TLS_BREAK_GLASS_EXPIRES_AT")
    )


def _is_valid_strict_public_url(value: str) -> bool:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return False

    parsed = urlparse(candidate)
    if parsed.scheme != "https" or not parsed.netloc:
        return False
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        return False

    hostname = str(parsed.hostname or "").strip().lower()
    if not hostname or hostname == "localhost":
        return False

    try:
        host_ip = ipaddress.ip_address(hostname)
    except ValueError:
        return True

    return not (
        host_ip.is_private
        or host_ip.is_loopback
        or host_ip.is_link_local
        or host_ip.is_multicast
        or host_ip.is_unspecified
        or host_ip.is_reserved
    )


def _is_valid_http_url(value: str) -> bool:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return False
    return candidate.startswith(("http://", "https://"))


def _has_valid_trusted_proxy_cidrs(value: str) -> bool:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return False
    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return False
    if not isinstance(parsed, list) or not parsed:
        return False
    for raw in parsed:
        cidr = str(raw or "").strip()
        if not cidr:
            return False
        try:
            ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            return False
    return True


def _is_valid_aws_principal_arn(value: str) -> bool:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return False
    arn_pattern = re.compile(
        r"^arn:(aws|aws-us-gov|aws-cn):iam::\d{12}:(root|role\/[\w+=,.@\\-_/]+|user\/[\w+=,.@\\-_/]+)$"
    )
    return bool(arn_pattern.fullmatch(candidate))


def _has_minimum_length(value: str, *, minimum: int) -> bool:
    candidate = str(value or "").strip()
    if not candidate or _contains_placeholder(candidate):
        return False
    return len(candidate) >= minimum


def _runtime_blockers(values: dict[str, str]) -> list[str]:
    blockers: list[str] = []
    for key in RUNTIME_BLOCKER_KEYS:
        value = _string_value(values, key).strip()
        if not value or _contains_placeholder(value):
            blockers.append(key)

    for key in ("API_URL", "FRONTEND_URL"):
        value = _string_value(values, key).strip()
        if value and not _contains_placeholder(value) and not _is_valid_strict_public_url(value):
            blockers.append(key)

    for key in ("OTEL_EXPORTER_OTLP_ENDPOINT", "SENTRY_DSN"):
        value = _string_value(values, key).strip()
        if value and not _contains_placeholder(value) and not _is_valid_http_url(value):
            blockers.append(key)

    trusted_proxy_cidrs = _string_value(values, "TRUSTED_PROXY_CIDRS").strip()
    if (
        trusted_proxy_cidrs
        and not _contains_placeholder(trusted_proxy_cidrs)
        and not _has_valid_trusted_proxy_cidrs(trusted_proxy_cidrs)
    ):
        blockers.append("TRUSTED_PROXY_CIDRS")

    aws_trust_principal_arn = _string_value(values, "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN").strip()
    if (
        aws_trust_principal_arn
        and not _contains_placeholder(aws_trust_principal_arn)
        and not _is_valid_aws_principal_arn(aws_trust_principal_arn)
    ):
        blockers.append("AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN")

    admin_api_key = _string_value(values, "ADMIN_API_KEY").strip()
    if admin_api_key and not _contains_placeholder(admin_api_key) and not _has_minimum_length(
        admin_api_key,
        minimum=32,
    ):
        blockers.append("ADMIN_API_KEY")

    environment = _string_value(values, "ENVIRONMENT").strip().lower()
    if environment == "production":
        paystack_secret_key = _string_value(values, "PAYSTACK_SECRET_KEY").strip()
        if (
            paystack_secret_key
            and not _contains_placeholder(paystack_secret_key)
            and not paystack_secret_key.startswith("sk_live_")
        ):
            blockers.append("PAYSTACK_SECRET_KEY")

        paystack_public_key = _string_value(values, "PAYSTACK_PUBLIC_KEY").strip()
        if (
            paystack_public_key
            and not _contains_placeholder(paystack_public_key)
            and not paystack_public_key.startswith("pk_live_")
        ):
            blockers.append("PAYSTACK_PUBLIC_KEY")

    internal_metrics_auth_token = _string_value(values, "INTERNAL_METRICS_AUTH_TOKEN").strip()
    if (
        internal_metrics_auth_token
        and not _contains_placeholder(internal_metrics_auth_token)
        and not _has_minimum_length(internal_metrics_auth_token, minimum=32)
    ):
        blockers.append("INTERNAL_METRICS_AUTH_TOKEN")

    provider_key = _selected_llm_provider_env_key(values)
    provider_value = _string_value(values, provider_key).strip()
    if not provider_value or _contains_placeholder(provider_value):
        blockers.append(provider_key)

    return sorted(set(blockers))


def _artifact_output_paths(output_dir: Path) -> tuple[Path, ...]:
    return (
        output_dir / "koyeb-api.yaml",
        output_dir / "koyeb-worker.yaml",
        output_dir / "koyeb-secrets.json",
        output_dir / "koyeb-dashboard-env.json",
        output_dir / "koyeb-release.json",
        output_dir / "helm-values.yaml",
        output_dir / "aws-runtime-secret.json",
        output_dir / "terraform.runtime.auto.tfvars.json",
        output_dir / "deployment.report.json",
    )


def _ensure_output_dir_parent(output_dir: Path) -> None:
    current = output_dir
    while True:
        if current.exists():
            if not current.is_dir():
                raise ValueError(
                    f"output_dir parent must be a directory path: {current.as_posix()}"
                )
            return
        if current == current.parent:
            return
        current = current.parent


def _koyeb_name(environment: str, component: str) -> str:
    base = f"valdrics-{component}"
    if environment == "production":
        return base
    return f"{base}-{environment}"


def _koyeb_secret_name(environment: str, base_name: str) -> str:
    if environment == "production":
        return base_name
    return f"{base_name}-{environment}"


def _koyeb_secret_entries(values: dict[str, str], *, environment: str, component: str) -> list[dict[str, str]]:
    entries: list[dict[str, str]] = []

    for key, base_name in KOYEB_SHARED_SECRET_NAMES.items():
        value = _string_value(values, key).strip()
        if not value:
            continue
        entries.append({"name": key, "secret": _koyeb_secret_name(environment, base_name)})

    provider_key = _selected_llm_provider_env_key(values)
    provider_secret_name = _koyeb_secret_name(
        environment,
        LLM_PROVIDER_SECRET_NAME[_selected_llm_provider(values)],
    )
    entries.append({"name": provider_key, "secret": provider_secret_name})

    if component == "api":
        for key, base_name in KOYEB_API_ONLY_SECRET_NAMES.items():
            value = _string_value(values, key).strip()
            if not value:
                continue
            entries.append(
                {"name": key, "secret": _koyeb_secret_name(environment, base_name)}
            )

    optional_groups = {
        **{
            key: _include_forecaster_break_glass(values)
            for key in FORECASTER_BREAK_GLASS_KEYS
        },
        **{
            key: _include_outbound_tls_break_glass(values)
            for key in OUTBOUND_TLS_BREAK_GLASS_KEYS
        },
    }
    for key, base_name in KOYEB_OPTIONAL_SHARED_SECRET_NAMES.items():
        if not optional_groups.get(key, False):
            continue
        entries.append({"name": key, "secret": _koyeb_secret_name(environment, base_name)})

    return entries


def _koyeb_value_entries(values: dict[str, str], *, component: str) -> list[dict[str, str]]:
    ordered_keys = [
        "ENVIRONMENT",
        "ENABLE_SCHEDULER",
        "WEB_CONCURRENCY",
        "API_URL",
        "FRONTEND_URL",
        "LOG_LEVEL",
        "LLM_PROVIDER",
        "EXPOSE_API_DOCUMENTATION_PUBLICLY",
        "OTEL_LOGS_EXPORT_ENABLED",
        "SAAS_STRICT_INTEGRATIONS",
        "TRUST_PROXY_HEADERS",
        "CORS_ORIGINS",
        "APP_RUNTIME_DATA_DIR",
    ]
    if component == "worker":
        ordered_keys = [
            key
            for key in ordered_keys
            if key
            not in {
                "WEB_CONCURRENCY",
                "EXPOSE_API_DOCUMENTATION_PUBLICLY",
                "SAAS_STRICT_INTEGRATIONS",
                "TRUST_PROXY_HEADERS",
            }
        ]

    entries: list[dict[str, str]] = []
    for key in ordered_keys:
        if component == "worker" and key == "ENABLE_SCHEDULER":
            value = "false"
        else:
            value = _string_value(values, key).strip()
        if not value:
            continue
        entries.append({"name": key, "value": value})
    return entries


def _koyeb_manifest(
    values: dict[str, str], *, environment: str, component: str
) -> dict[str, Any]:
    is_api = component == "api"
    manifest: dict[str, Any] = {
        "name": _koyeb_name(environment, component),
        "type": "WEB" if is_api else "WORKER",
        "definition": {
            "git": {
                "repository": "github.com/Valdrics/valdrics",
                "branch": "main",
                "builder": "docker",
                "dockerfile": "Dockerfile",
            },
            "scaling": {
                "min": 2 if is_api else 1,
                "max": 3 if is_api else 2,
                "targets": {"cpu": {"value": 70}},
            },
            "instance_type": "micro",
            "env": _koyeb_value_entries(values, component=component)
            + _koyeb_secret_entries(values, environment=environment, component=component),
        },
    }
    if is_api:
        manifest["definition"]["ports"] = [{"port": 8000, "protocol": "http"}]
        manifest["definition"]["routes"] = [{"path": "/", "port": 8000}]
        manifest["definition"]["health_checks"] = [
            {
                "type": "http",
                "path": "/health/live",
                "port": 8000,
                "interval_seconds": 30,
                "timeout_seconds": 10,
                "healthy_threshold": 2,
                "unhealthy_threshold": 3,
            }
        ]
    else:
        manifest["definition"]["command"] = [
            "celery",
            "-A",
            "app.shared.core.celery_app:celery_app",
            "worker",
            "-l",
            "info",
        ]
    return manifest


def _koyeb_dashboard_public_env(values: dict[str, str]) -> dict[str, str]:
    api_url = _string_value(values, "API_URL").rstrip("/")
    return {
        "PUBLIC_API_URL": f"{api_url}/api/v1" if api_url else "",
        "PUBLIC_SUPABASE_URL": _string_value(values, "SUPABASE_URL").strip(),
        "PUBLIC_SUPABASE_ANON_KEY": _string_value(values, "SUPABASE_ANON_KEY").strip(),
    }


def _json_placeholder_blockers(payload: Any, *, path: str = "") -> list[str]:
    blockers: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_path = f"{path}.{key}" if path else str(key)
            blockers.extend(_json_placeholder_blockers(value, path=child_path))
        return blockers
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            child_path = f"{path}[{index}]"
            blockers.extend(_json_placeholder_blockers(value, path=child_path))
        return blockers
    if isinstance(payload, str):
        normalized = payload.strip()
        if not normalized or _contains_placeholder(normalized):
            blockers.append(path or "<root>")
    return blockers


def _normalize_image_digest(value: str, *, field_name: str, default: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        return default
    if _contains_placeholder(normalized):
        return normalized
    if not normalized.startswith("sha256:"):
        raise ValueError(f"{field_name} must be a sha256:<64-hex> digest.")
    digest_body = normalized.split("sha256:", 1)[1].strip()
    if len(digest_body) != 64 or any(ch not in "0123456789abcdef" for ch in digest_body):
        raise ValueError(f"{field_name} must be a sha256:<64-hex> digest.")
    return f"sha256:{digest_body}"


def _normalize_image_registry(value: str) -> str:
    normalized = str(value or "").strip().rstrip("/")
    if not normalized:
        raise ValueError("registry must be a non-empty container registry prefix.")
    if any(ch.isspace() for ch in normalized):
        raise ValueError("registry must not contain whitespace.")
    return normalized


def _koyeb_release_metadata(
    *,
    environment: str,
    registry: str,
    release_tag: str,
    api_image_digest: str,
    dashboard_image_digest: str,
) -> dict[str, Any]:
    normalized_registry = _normalize_image_registry(registry)
    normalized_release_tag = str(release_tag or "").strip() or DEFAULT_RELEASE_TAG
    normalized_api_digest = _normalize_image_digest(
        api_image_digest,
        field_name="api_image_digest",
        default=DEFAULT_API_IMAGE_DIGEST,
    )
    normalized_dashboard_digest = _normalize_image_digest(
        dashboard_image_digest,
        field_name="dashboard_image_digest",
        default=DEFAULT_DASHBOARD_IMAGE_DIGEST,
    )
    api_repository = f"{normalized_registry}/valdrics-api"
    dashboard_repository = f"{normalized_registry}/valdrics-dashboard"
    api_image = f"{api_repository}:{normalized_release_tag}"
    dashboard_image = f"{dashboard_repository}:{normalized_release_tag}"
    return {
        "strategy": "immutable_image_promotion",
        "environment": environment,
        "registry": normalized_registry,
        "release_tag": normalized_release_tag,
        "services": {
            "api": {
                "service_name": _koyeb_name(environment, "api"),
                "repository": api_repository,
                "image": api_image,
                "image_digest": normalized_api_digest,
                "promotion_ref": f"{api_repository}@{normalized_api_digest}",
                "port": 8000,
                "health_path": "/health/live",
            },
            "worker": {
                "service_name": _koyeb_name(environment, "worker"),
                "image": api_image,
                "image_digest": normalized_api_digest,
                "promotion_ref": f"{api_repository}@{normalized_api_digest}",
                "command": [
                    "celery",
                    "-A",
                    "app.shared.core.celery_app:celery_app",
                    "worker",
                    "-l",
                    "info",
                ],
            },
            "dashboard": {
                "service_name": _koyeb_name(environment, "dashboard"),
                "repository": dashboard_repository,
                "image": dashboard_image,
                "image_digest": normalized_dashboard_digest,
                "promotion_ref": f"{dashboard_repository}@{normalized_dashboard_digest}",
                "port": 3000,
                "health_path": "/",
            },
        },
    }


def _host_from_url(url: str, *, field_name: str) -> str:
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError(f"{field_name} must be a valid URL with a hostname.")
    return str(parsed.hostname).strip().lower()


def _helm_secret_name(environment: str) -> str:
    if environment == "production":
        return "valdrics-secrets"
    return f"valdrics-{environment}-secrets"


def _terraform_environment(environment: str) -> str:
    return "prod" if environment == "production" else environment


def _remote_secret_key(environment: str) -> str:
    return f"/valdrics/{_terraform_environment(environment)}/app-runtime"


def _helm_values(values: dict[str, str], *, environment: str) -> dict[str, Any]:
    api_host = _host_from_url(_string_value(values, "API_URL"), field_name="API_URL")
    frontend_host = _host_from_url(
        _string_value(values, "FRONTEND_URL"),
        field_name="FRONTEND_URL",
    )

    return {
        "global": {
            "apiHostOverride": api_host,
            "frontendHostOverride": frontend_host,
        },
        "env": {
            "ENVIRONMENT": _string_value(values, "ENVIRONMENT", environment),
            "LOG_LEVEL": _string_value(values, "LOG_LEVEL", "INFO"),
            "WEB_CONCURRENCY": _string_value(values, "WEB_CONCURRENCY", "2"),
            "ENABLE_SCHEDULER": _string_value(values, "ENABLE_SCHEDULER", "true"),
            "LLM_PROVIDER": _string_value(values, "LLM_PROVIDER", "groq"),
            "EXPOSE_API_DOCUMENTATION_PUBLICLY": _string_value(
                values,
                "EXPOSE_API_DOCUMENTATION_PUBLICLY",
                "false",
            ),
            "OTEL_LOGS_EXPORT_ENABLED": _string_value(
                values,
                "OTEL_LOGS_EXPORT_ENABLED",
                "true",
            ),
            "SAAS_STRICT_INTEGRATIONS": _string_value(
                values,
                "SAAS_STRICT_INTEGRATIONS",
                "true",
            ),
            "TRUST_PROXY_HEADERS": _string_value(
                values,
                "TRUST_PROXY_HEADERS",
                "true",
            ),
            "APP_RUNTIME_DATA_DIR": _string_value(
                values,
                "APP_RUNTIME_DATA_DIR",
                "/tmp/valdrics",
            ),
            "CORS_ORIGINS": _string_value(values, "CORS_ORIGINS"),
        },
        "externalSecrets": {
            "enabled": True,
            "remoteSecretKey": _remote_secret_key(environment),
            "target": {
                "name": _helm_secret_name(environment),
                "creationPolicy": "Owner",
                "deletionPolicy": "Retain",
            },
        },
        "existingSecrets": {
            "name": _helm_secret_name(environment),
        },
        "ingress": {
            "hosts": [
                {
                    "host": api_host,
                    "paths": [{"path": "/", "pathType": "Prefix"}],
                }
            ],
            "tls": [
                {
                    "secretName": f"{_koyeb_name(environment, 'api')}-tls",
                    "hosts": [api_host],
                }
            ],
        },
    }


def _helm_runtime_secret_payload(values: dict[str, str]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for key in sorted(values):
        if key in HELM_SECRET_EXCLUDED_KEYS:
            continue
        if key in FORECASTER_BREAK_GLASS_KEYS and not _include_forecaster_break_glass(values):
            continue
        if key in OUTBOUND_TLS_BREAK_GLASS_KEYS and not _include_outbound_tls_break_glass(values):
            continue
        value = _string_value(values, key)
        if value == "":
            continue
        payload[key] = value
    return payload


def _koyeb_secret_payload(values: dict[str, str], *, environment: str) -> dict[str, str]:
    payload: dict[str, str] = {}
    for entry in _koyeb_secret_entries(values, environment=environment, component="api"):
        payload[entry["secret"]] = _string_value(values, entry["name"])
    for entry in _koyeb_secret_entries(values, environment=environment, component="worker"):
        payload.setdefault(entry["secret"], _string_value(values, entry["name"]))
    return payload


def _placeholder_keys(payload: dict[str, str]) -> list[str]:
    return sorted(
        key for key, value in payload.items() if not str(value).strip() or _contains_placeholder(value)
    )


def generate_managed_deployment_artifacts(
    *,
    environment: str,
    runtime_env_file: Path,
    output_dir: Path,
    registry: str = DEFAULT_KOYEB_IMAGE_REGISTRY,
    release_tag: str = DEFAULT_RELEASE_TAG,
    api_image_digest: str = DEFAULT_API_IMAGE_DIGEST,
    dashboard_image_digest: str = DEFAULT_DASHBOARD_IMAGE_DIGEST,
) -> dict[str, Any]:
    normalized_environment = str(environment or "").strip().lower()
    if normalized_environment not in SUPPORTED_ENVIRONMENTS:
        raise ValueError(
            "environment must be one of: " + ", ".join(SUPPORTED_ENVIRONMENTS)
        )
    if not runtime_env_file.exists():
        raise FileNotFoundError(
            f"Runtime env file does not exist: {runtime_env_file.as_posix()}"
        )
    if not runtime_env_file.is_file():
        raise ValueError(f"runtime_env_file must be a file: {runtime_env_file.as_posix()}")
    if output_dir.exists() and not output_dir.is_dir():
        raise ValueError(f"output_dir must be a directory path: {output_dir.as_posix()}")
    _ensure_output_dir_parent(output_dir)
    runtime_env_resolved = runtime_env_file.resolve()
    for artifact_path in _artifact_output_paths(output_dir):
        if artifact_path.resolve() == runtime_env_resolved:
            raise ValueError(
                "runtime_env_file must not overwrite generated deployment artifacts"
            )

    values = parse_env_file(runtime_env_file)
    runtime_blockers = _runtime_blockers(values)
    helm_values = _helm_values(values, environment=normalized_environment)
    helm_secret_payload = _helm_runtime_secret_payload(values)
    koyeb_secret_payload = _koyeb_secret_payload(values, environment=normalized_environment)
    koyeb_dashboard_env = _koyeb_dashboard_public_env(values)
    koyeb_dashboard_env_blockers = _placeholder_keys(koyeb_dashboard_env)
    koyeb_release_metadata = _koyeb_release_metadata(
        environment=normalized_environment,
        registry=registry,
        release_tag=release_tag,
        api_image_digest=api_image_digest,
        dashboard_image_digest=dashboard_image_digest,
    )
    koyeb_release_value_blockers = sorted(
        set(_json_placeholder_blockers(koyeb_release_metadata))
    )
    terraform_runtime_json = json.dumps(helm_secret_payload, sort_keys=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    (
        koyeb_api_path,
        koyeb_worker_path,
        koyeb_secrets_path,
        koyeb_dashboard_env_path,
        koyeb_release_path,
        helm_values_path,
        helm_secret_path,
        terraform_tfvars_path,
        report_path,
    ) = _artifact_output_paths(output_dir)

    koyeb_api_path.write_text(
        yaml.safe_dump(
            _koyeb_manifest(values, environment=normalized_environment, component="api"),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    koyeb_worker_path.write_text(
        yaml.safe_dump(
            _koyeb_manifest(values, environment=normalized_environment, component="worker"),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    koyeb_secrets_path.write_text(
        json.dumps(koyeb_secret_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    koyeb_dashboard_env_path.write_text(
        json.dumps(koyeb_dashboard_env, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    koyeb_release_path.write_text(
        json.dumps(koyeb_release_metadata, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    helm_values_path.write_text(
        yaml.safe_dump(helm_values, sort_keys=False),
        encoding="utf-8",
    )
    helm_secret_path.write_text(
        json.dumps(helm_secret_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    terraform_tfvars_payload = {
        "environment": _terraform_environment(normalized_environment),
        "runtime_secret_name": _remote_secret_key(normalized_environment),
        "runtime_secret_initial_json": terraform_runtime_json,
        "enable_secret_rotation": normalized_environment == "production",
        "secret_rotation_lambda_arn": (
            "REPLACE_WITH_SECRET_ROTATION_LAMBDA_ARN"
            if normalized_environment == "production"
            else ""
        ),
    }
    terraform_tfvars_path.write_text(
        json.dumps(terraform_tfvars_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    terraform_remaining_inputs = list(TERRAFORM_BASE_REQUIRED_INPUTS)
    if normalized_environment == "production":
        terraform_remaining_inputs.append("secret_rotation_lambda_arn")

    report = {
        "environment": normalized_environment,
        "runtime_env_file": runtime_env_file.as_posix(),
        "output_dir": output_dir.as_posix(),
        "runtime_validation_blockers": runtime_blockers,
        "koyeb_secret_names": sorted(koyeb_secret_payload),
        "koyeb_secret_value_blockers": _placeholder_keys(koyeb_secret_payload),
        "koyeb_dashboard_public_env_keys": sorted(koyeb_dashboard_env),
        "koyeb_dashboard_public_env_blockers": koyeb_dashboard_env_blockers,
        "koyeb_release_value_blockers": koyeb_release_value_blockers,
        "helm_runtime_secret_keys": sorted(helm_secret_payload),
        "helm_runtime_secret_value_blockers": _placeholder_keys(helm_secret_payload),
        "helm_external_secret_remote_key": _remote_secret_key(normalized_environment),
        "terraform_runtime_tfvars_path": terraform_tfvars_path.as_posix(),
        "terraform_remaining_inputs": terraform_remaining_inputs,
        "artifacts": {
            "koyeb_api_manifest": koyeb_api_path.as_posix(),
            "koyeb_worker_manifest": koyeb_worker_path.as_posix(),
            "koyeb_secret_payload": koyeb_secrets_path.as_posix(),
            "koyeb_dashboard_env_json": koyeb_dashboard_env_path.as_posix(),
            "koyeb_release_metadata": koyeb_release_path.as_posix(),
            "helm_values": helm_values_path.as_posix(),
            "helm_runtime_secret_json": helm_secret_path.as_posix(),
        },
        "ready_for_koyeb": (
            not runtime_blockers
            and not _placeholder_keys(koyeb_secret_payload)
            and not koyeb_dashboard_env_blockers
        ),
        "ready_for_koyeb_release": (
            not runtime_blockers
            and not _placeholder_keys(koyeb_secret_payload)
            and not koyeb_dashboard_env_blockers
            and not koyeb_release_value_blockers
        ),
        "ready_for_helm": not runtime_blockers and not _placeholder_keys(helm_secret_payload),
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deployment artifacts for the Koyeb release path and the future Helm/EKS scale path from a managed runtime env file."
        )
    )
    parser.add_argument(
        "--environment",
        required=True,
        choices=SUPPORTED_ENVIRONMENTS,
    )
    parser.add_argument(
        "--runtime-env-file",
        type=Path,
        default=None,
        help="Runtime env file to consume (default: .runtime/<environment>.env).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory (default: .runtime/deploy/<environment>).",
    )
    parser.add_argument(
        "--registry",
        default=DEFAULT_KOYEB_IMAGE_REGISTRY,
        help="Container registry prefix for Koyeb immutable image promotion metadata.",
    )
    parser.add_argument(
        "--release-tag",
        default=DEFAULT_RELEASE_TAG,
        help="Immutable release tag recorded in the generated Koyeb release metadata.",
    )
    parser.add_argument(
        "--api-image-digest",
        default=DEFAULT_API_IMAGE_DIGEST,
        help=(
            "Digest-pinned GHCR reference for the shared API/worker image "
            "(format: sha256:<64-hex>)."
        ),
    )
    parser.add_argument(
        "--dashboard-image-digest",
        default=DEFAULT_DASHBOARD_IMAGE_DIGEST,
        help=(
            "Digest-pinned GHCR reference for the dashboard image "
            "(format: sha256:<64-hex>)."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    runtime_env_file = (
        _resolve_default_path(Path(".runtime") / f"{args.environment}.env")
        if args.runtime_env_file is None
        else _resolve_cli_path(args.runtime_env_file)
    )
    output_dir = (
        _resolve_default_path(DEFAULT_OUTPUT_ROOT / str(args.environment))
        if args.output_dir is None
        else _resolve_cli_path(args.output_dir)
    )
    report = generate_managed_deployment_artifacts(
        environment=str(args.environment),
        runtime_env_file=runtime_env_file,
        output_dir=output_dir,
        registry=str(args.registry),
        release_tag=str(args.release_tag),
        api_image_digest=str(args.api_image_digest),
        dashboard_image_digest=str(args.dashboard_image_digest),
    )
    print(
        "[managed-deployment-artifacts] ok "
        f"environment={report['environment']} "
        f"output_dir={report['output_dir']} "
        f"runtime_blockers={len(report['runtime_validation_blockers'])} "
        f"koyeb_ready={report['ready_for_koyeb']} "
        f"koyeb_release_ready={report['ready_for_koyeb_release']} "
        f"helm_ready={report['ready_for_helm']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
