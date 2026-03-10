#!/usr/bin/env python3
"""Generate deployment-ready Koyeb and Helm/EKS artifacts from a managed runtime env."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
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


def _string_value(values: dict[str, str], key: str, default: str = "") -> str:
    return str(values.get(key, default) or default)


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


def _runtime_blockers(values: dict[str, str]) -> list[str]:
    blockers: list[str] = []
    for key in RUNTIME_BLOCKER_KEYS:
        value = _string_value(values, key).strip()
        if not value or _contains_placeholder(value):
            blockers.append(key)

    provider_key = _selected_llm_provider_env_key(values)
    provider_value = _string_value(values, provider_key).strip()
    if not provider_value or _contains_placeholder(provider_value):
        blockers.append(provider_key)

    return sorted(set(blockers))


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
        value = _string_value(values, key).strip()
        if not value:
            continue
        entries.append({"name": key, "value": value})
    return entries


def _koyeb_manifest(values: dict[str, str], *, environment: str, component: str) -> dict[str, Any]:
    is_api = component == "api"
    manifest: dict[str, Any] = {
        "name": _koyeb_name(environment, component),
        "type": "WEB" if is_api else "WORKER",
        "definition": {
            "git": {
                "repository": "github.com/Valdrics-AI/valdrics",
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
            "uv",
            "run",
            "celery",
            "-A",
            "app.shared.core.celery_app:celery_app",
            "worker",
            "-l",
            "info",
        ]
    return manifest


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

    values = parse_env_file(runtime_env_file)
    runtime_blockers = _runtime_blockers(values)
    helm_values = _helm_values(values, environment=normalized_environment)
    helm_secret_payload = _helm_runtime_secret_payload(values)
    koyeb_secret_payload = _koyeb_secret_payload(values, environment=normalized_environment)
    terraform_runtime_json = json.dumps(helm_secret_payload, sort_keys=True)

    output_dir.mkdir(parents=True, exist_ok=True)
    koyeb_api_path = output_dir / "koyeb-api.yaml"
    koyeb_worker_path = output_dir / "koyeb-worker.yaml"
    koyeb_secrets_path = output_dir / "koyeb-secrets.json"
    helm_values_path = output_dir / "helm-values.yaml"
    helm_secret_path = output_dir / "aws-runtime-secret.json"
    terraform_tfvars_path = output_dir / "terraform.runtime.auto.tfvars.json"
    report_path = output_dir / "deployment.report.json"

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
        "helm_runtime_secret_keys": sorted(helm_secret_payload),
        "helm_runtime_secret_value_blockers": _placeholder_keys(helm_secret_payload),
        "helm_external_secret_remote_key": _remote_secret_key(normalized_environment),
        "terraform_runtime_tfvars_path": terraform_tfvars_path.as_posix(),
        "terraform_remaining_inputs": terraform_remaining_inputs,
        "artifacts": {
            "koyeb_api_manifest": koyeb_api_path.as_posix(),
            "koyeb_worker_manifest": koyeb_worker_path.as_posix(),
            "koyeb_secret_payload": koyeb_secrets_path.as_posix(),
            "helm_values": helm_values_path.as_posix(),
            "helm_runtime_secret_json": helm_secret_path.as_posix(),
        },
        "ready_for_koyeb": not runtime_blockers and not _placeholder_keys(koyeb_secret_payload),
        "ready_for_helm": not runtime_blockers and not _placeholder_keys(helm_secret_payload),
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deployment artifacts for Koyeb and Helm/EKS from a managed runtime env file."
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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    runtime_env_file = args.runtime_env_file or Path(".runtime") / f"{args.environment}.env"
    output_dir = args.output_dir or DEFAULT_OUTPUT_ROOT / str(args.environment)
    report = generate_managed_deployment_artifacts(
        environment=str(args.environment),
        runtime_env_file=runtime_env_file.resolve(),
        output_dir=output_dir.resolve(),
    )
    print(
        "[managed-deployment-artifacts] ok "
        f"environment={report['environment']} "
        f"output_dir={report['output_dir']} "
        f"runtime_blockers={len(report['runtime_validation_blockers'])} "
        f"koyeb_ready={report['ready_for_koyeb']} "
        f"helm_ready={report['ready_for_helm']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
