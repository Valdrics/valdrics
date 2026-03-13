from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.generate_managed_deployment_artifacts import (
    generate_managed_deployment_artifacts,
)


def _write_env(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_generate_managed_deployment_artifacts_outputs_platform_ready_bundle(
    tmp_path: Path,
) -> None:
    runtime_env = tmp_path / "production.env"
    output_dir = tmp_path / "deploy" / "production"
    _write_env(
        runtime_env,
        [
            "ENVIRONMENT=production",
            "ENABLE_SCHEDULER=true",
            "WEB_CONCURRENCY=2",
            "API_URL=https://api.runtime.example",
            "FRONTEND_URL=https://console.other-example.com",
            "LOG_LEVEL=INFO",
            "LLM_PROVIDER=openai",
            "OPENAI_API_KEY=sk-openai-live-key",
            "EXPOSE_API_DOCUMENTATION_PUBLICLY=false",
            "OTEL_LOGS_EXPORT_ENABLED=true",
            "SAAS_STRICT_INTEGRATIONS=true",
            "TRUST_PROXY_HEADERS=true",
            "CORS_ORIGINS='[\"https://console.other-example.com\"]'",
            "APP_RUNTIME_DATA_DIR=/tmp/valdrics",
            "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
            "REDIS_URL=redis://redis.example.com:6379/0",
            "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=arn:aws:iam::123456789012:role/ValdricsControlPlane",
            "OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com:4317",
            "PAYSTACK_SECRET_KEY=sk_live_runtime_paystack_key",
            "PAYSTACK_PUBLIC_KEY=pk_live_runtime_paystack_key",
            "SENTRY_DSN=https://key@example.com/1",
            "TRUSTED_PROXY_CIDRS='[\"203.0.113.10/32\"]'",
            "ENCRYPTION_KEY=ci-encryption-key-32-chars-min-00000000",
            "KDF_SALT=MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
            "CSRF_SECRET_KEY=ci-csrf-secret-key-32-chars-min-000000",
            "ADMIN_API_KEY=ci-admin-api-key-32-chars-min-0000000",
            "INTERNAL_JOB_SECRET=ci-internal-job-secret-32-chars-min-000",
            "INTERNAL_METRICS_AUTH_TOKEN=ci-internal-metrics-token-32-chars-000",
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET=ci-enforcement-approval-token-secret-32-chars",
            "ENFORCEMENT_EXPORT_SIGNING_SECRET=ci-enforcement-export-signing-secret-32-char",
        ],
    )

    report = generate_managed_deployment_artifacts(
        environment="production",
        runtime_env_file=runtime_env,
        output_dir=output_dir,
    )

    api_manifest = _load_yaml(output_dir / "koyeb-api.yaml")
    worker_manifest = _load_yaml(output_dir / "koyeb-worker.yaml")
    koyeb_secrets = json.loads((output_dir / "koyeb-secrets.json").read_text(encoding="utf-8"))
    helm_values = _load_yaml(output_dir / "helm-values.yaml")
    helm_secret = json.loads((output_dir / "aws-runtime-secret.json").read_text(encoding="utf-8"))
    terraform_tfvars = json.loads(
        (output_dir / "terraform.runtime.auto.tfvars.json").read_text(encoding="utf-8")
    )

    assert report["ready_for_koyeb"] is True
    assert report["ready_for_helm"] is True
    assert report["runtime_validation_blockers"] == []
    assert api_manifest["name"] == "valdrics-api"
    assert worker_manifest["name"] == "valdrics-worker"
    assert worker_manifest["definition"]["command"][0:3] == [
        "celery",
        "-A",
        "app.shared.core.celery_app:celery_app",
    ]

    api_env = {item["name"]: item.get("secret") or item.get("value") for item in api_manifest["definition"]["env"]}
    worker_env = {item["name"]: item.get("secret") or item.get("value") for item in worker_manifest["definition"]["env"]}
    assert api_env["INTERNAL_JOB_SECRET"] == "valdrics-internal-job-secret"
    assert api_env["OPENAI_API_KEY"] == "valdrics-openai-key"
    assert (
        api_env["AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN"]
        == "valdrics-aws-trust-principal-arn"
    )
    assert worker_env["OPENAI_API_KEY"] == "valdrics-openai-key"
    assert (
        worker_env["AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN"]
        == "valdrics-aws-trust-principal-arn"
    )
    assert "INTERNAL_METRICS_AUTH_TOKEN" not in worker_env

    assert koyeb_secrets["valdrics-internal-job-secret"] == "ci-internal-job-secret-32-chars-min-000"
    assert koyeb_secrets["valdrics-openai-key"] == "sk-openai-live-key"
    assert (
        koyeb_secrets["valdrics-aws-trust-principal-arn"]
        == "arn:aws:iam::123456789012:role/ValdricsControlPlane"
    )
    assert "valdrics-forecaster-break-glass-enabled" not in koyeb_secrets
    assert "valdrics-outbound-tls-break-glass-enabled" not in koyeb_secrets
    assert helm_values["global"]["apiHostOverride"] == "api.runtime.example"
    assert helm_values["global"]["frontendHostOverride"] == "console.other-example.com"
    assert helm_values["externalSecrets"]["remoteSecretKey"] == "/valdrics/prod/app-runtime"
    assert helm_secret["DATABASE_URL"].startswith("postgresql+asyncpg://postgres:")
    assert helm_secret["INTERNAL_JOB_SECRET"] == "ci-internal-job-secret-32-chars-min-000"
    assert "API_URL" not in helm_secret
    assert "SUPABASE_URL" not in helm_secret
    assert terraform_tfvars["environment"] == "prod"
    assert terraform_tfvars["runtime_secret_name"] == "/valdrics/prod/app-runtime"
    assert terraform_tfvars["enable_secret_rotation"] is True
    assert "external_id" in report["terraform_remaining_inputs"]


def test_generate_managed_deployment_artifacts_reports_placeholder_blockers_for_staging(
    tmp_path: Path,
) -> None:
    runtime_env = tmp_path / "staging.env"
    output_dir = tmp_path / "deploy" / "staging"
    _write_env(
        runtime_env,
        [
            "ENVIRONMENT=staging",
            "ENABLE_SCHEDULER=true",
            "WEB_CONCURRENCY=2",
            "API_URL=https://REPLACE_WITH_API_DOMAIN",
            "FRONTEND_URL=https://REPLACE_WITH_FRONTEND_DOMAIN",
            "LOG_LEVEL=INFO",
            "LLM_PROVIDER=groq",
            "GROQ_API_KEY=REPLACE_WITH_GROQ_API_KEY",
            "EXPOSE_API_DOCUMENTATION_PUBLICLY=false",
            "OTEL_LOGS_EXPORT_ENABLED=true",
            "SAAS_STRICT_INTEGRATIONS=true",
            "TRUST_PROXY_HEADERS=true",
            "CORS_ORIGINS='[\"https://REPLACE_WITH_FRONTEND_DOMAIN\"]'",
            "APP_RUNTIME_DATA_DIR=/tmp/valdrics",
            "DATABASE_URL=postgresql+asyncpg://REPLACE_WITH_DB_USER:REPLACE_WITH_DB_PASSWORD@REPLACE_WITH_DB_HOST:5432/postgres",
            "REDIS_URL=redis://REPLACE_WITH_REDIS_HOST:6379/0",
            "SUPABASE_JWT_SECRET=REPLACE_WITH_SUPABASE_JWT_SECRET_MINIMUM_32_CHARS_VALUE",
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=arn:aws:iam::123456789012:role/REPLACE_WITH_VALDRICS_CONTROL_PLANE_ROLE",
            "OTEL_EXPORTER_OTLP_ENDPOINT=https://REPLACE_WITH_OTEL_COLLECTOR:4317",
            "PAYSTACK_SECRET_KEY=sk_live_REPLACE_WITH_PAYSTACK_SECRET_KEY",
            "PAYSTACK_PUBLIC_KEY=pk_live_REPLACE_WITH_PAYSTACK_PUBLIC_KEY",
            "SENTRY_DSN=https://REPLACE_WITH_SENTRY_KEY@REPLACE_WITH_SENTRY_HOST/REPLACE_WITH_SENTRY_PROJECT",
            "TRUSTED_PROXY_CIDRS='[\"REPLACE_WITH_TRUSTED_PROXY_CIDR\"]'",
            "ENCRYPTION_KEY=ci-encryption-key-32-chars-min-00000000",
            "KDF_SALT=MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
            "CSRF_SECRET_KEY=ci-csrf-secret-key-32-chars-min-000000",
            "ADMIN_API_KEY=ci-admin-api-key-32-chars-min-0000000",
            "INTERNAL_JOB_SECRET=ci-internal-job-secret-32-chars-min-000",
            "INTERNAL_METRICS_AUTH_TOKEN=ci-internal-metrics-token-32-chars-000",
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET=ci-enforcement-approval-token-secret-32-chars",
            "ENFORCEMENT_EXPORT_SIGNING_SECRET=ci-enforcement-export-signing-secret-32-char",
        ],
    )

    report = generate_managed_deployment_artifacts(
        environment="staging",
        runtime_env_file=runtime_env,
        output_dir=output_dir,
    )
    api_manifest = _load_yaml(output_dir / "koyeb-api.yaml")

    assert report["ready_for_koyeb"] is False
    assert report["ready_for_helm"] is False
    assert "DATABASE_URL" in report["runtime_validation_blockers"]
    assert "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN" in report["runtime_validation_blockers"]
    assert "valdrics-groq-key-staging" in report["koyeb_secret_names"]
    assert "valdrics-aws-trust-principal-arn-staging" in report["koyeb_secret_names"]
    assert "valdrics-forecaster-break-glass-enabled-staging" not in report["koyeb_secret_names"]
    assert report["helm_external_secret_remote_key"] == "/valdrics/staging/app-runtime"
    assert api_manifest["name"] == "valdrics-api-staging"
    assert "valdrics-internal-job-secret-staging" in report["koyeb_secret_names"]
