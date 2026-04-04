from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

import scripts.generate_managed_deployment_artifacts as managed_deployment_generator
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
            "SUPABASE_URL=https://example.supabase.co",
            "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
            "SUPABASE_ANON_KEY=ci-public-supabase-anon-key",
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
        release_tag="2026.03.18",
        api_image_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        dashboard_image_digest="sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )

    api_manifest = _load_yaml(output_dir / "koyeb-api.yaml")
    worker_manifest = _load_yaml(output_dir / "koyeb-worker.yaml")
    koyeb_secrets = json.loads(
        (output_dir / "koyeb-secrets.json").read_text(encoding="utf-8")
    )
    koyeb_dashboard_env = json.loads(
        (output_dir / "koyeb-dashboard-env.json").read_text(encoding="utf-8")
    )
    koyeb_release = json.loads(
        (output_dir / "koyeb-release.json").read_text(encoding="utf-8")
    )
    helm_values = _load_yaml(output_dir / "helm-values.yaml")
    helm_secret = json.loads(
        (output_dir / "aws-runtime-secret.json").read_text(encoding="utf-8")
    )
    terraform_tfvars = json.loads(
        (output_dir / "terraform.runtime.auto.tfvars.json").read_text(encoding="utf-8")
    )

    assert report["ready_for_koyeb"] is True
    assert report["ready_for_koyeb_release"] is True
    assert report["ready_for_helm"] is True
    assert report["runtime_validation_blockers"] == []
    assert api_manifest["name"] == "valdrics-api"
    assert worker_manifest["name"] == "valdrics-worker"
    assert (
        api_manifest["definition"]["git"]["repository"]
        == "github.com/Valdrics/valdrics"
    )
    assert (
        worker_manifest["definition"]["git"]["repository"]
        == "github.com/Valdrics/valdrics"
    )
    assert worker_manifest["definition"]["command"][0:3] == [
        "celery",
        "-A",
        "app.shared.core.celery_app:celery_app",
    ]

    api_env = {
        item["name"]: item.get("secret") or item.get("value")
        for item in api_manifest["definition"]["env"]
    }
    worker_env = {
        item["name"]: item.get("secret") or item.get("value")
        for item in worker_manifest["definition"]["env"]
    }
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
    assert worker_env["ENABLE_SCHEDULER"] == "false"
    assert "INTERNAL_METRICS_AUTH_TOKEN" not in worker_env

    assert (
        koyeb_secrets["valdrics-internal-job-secret"]
        == "ci-internal-job-secret-32-chars-min-000"
    )
    assert koyeb_secrets["valdrics-openai-key"] == "sk-openai-live-key"
    assert (
        koyeb_secrets["valdrics-aws-trust-principal-arn"]
        == "arn:aws:iam::123456789012:role/ValdricsControlPlane"
    )
    assert "valdrics-forecaster-break-glass-enabled" not in koyeb_secrets
    assert "valdrics-outbound-tls-break-glass-enabled" not in koyeb_secrets
    assert koyeb_dashboard_env["PUBLIC_API_URL"] == "https://api.runtime.example/api/v1"
    assert koyeb_dashboard_env["ORIGIN"] == "https://console.other-example.com"
    assert koyeb_dashboard_env["PUBLIC_SUPABASE_URL"] == "https://example.supabase.co"
    assert (
        koyeb_dashboard_env["PUBLIC_SUPABASE_ANON_KEY"] == "ci-public-supabase-anon-key"
    )
    assert koyeb_release["strategy"] == "immutable_image_promotion"
    assert (
        koyeb_release["services"]["api"]["repository"]
        == "ghcr.io/valdrics/valdrics-api"
    )
    assert (
        koyeb_release["services"]["api"]["image"]
        == "ghcr.io/valdrics/valdrics-api:2026.03.18"
    )
    assert (
        koyeb_release["services"]["api"]["image_digest"]
        == "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    assert (
        koyeb_release["services"]["api"]["promotion_ref"]
        == "ghcr.io/valdrics/valdrics-api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    assert (
        koyeb_release["services"]["dashboard"]["image"]
        == "ghcr.io/valdrics/valdrics-dashboard:2026.03.18"
    )
    assert (
        koyeb_release["services"]["dashboard"]["image_digest"]
        == "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    assert (
        koyeb_release["services"]["dashboard"]["promotion_ref"]
        == "ghcr.io/valdrics/valdrics-dashboard@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    assert helm_values["global"]["apiHostOverride"] == "api.runtime.example"
    assert helm_values["global"]["frontendHostOverride"] == "console.other-example.com"
    assert (
        helm_values["externalSecrets"]["remoteSecretKey"]
        == "/valdrics/prod/app-runtime"
    )
    assert helm_secret["DATABASE_URL"].startswith("postgresql+asyncpg://postgres:")
    assert (
        helm_secret["INTERNAL_JOB_SECRET"] == "ci-internal-job-secret-32-chars-min-000"
    )
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
            "SUPABASE_URL=https://REPLACE_WITH_SUPABASE_PROJECT.supabase.co",
            "SUPABASE_ANON_KEY=REPLACE_WITH_SUPABASE_ANON_KEY",
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
    assert report["ready_for_koyeb_release"] is False
    assert report["ready_for_helm"] is False
    assert "ORIGIN" in report["koyeb_dashboard_public_env_blockers"]
    assert "DATABASE_URL" in report["runtime_validation_blockers"]
    assert (
        "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN" in report["runtime_validation_blockers"]
    )
    assert "valdrics-groq-key-staging" in report["koyeb_secret_names"]
    assert "valdrics-aws-trust-principal-arn-staging" in report["koyeb_secret_names"]
    assert (
        "valdrics-forecaster-break-glass-enabled-staging"
        not in report["koyeb_secret_names"]
    )
    assert report["helm_external_secret_remote_key"] == "/valdrics/staging/app-runtime"
    assert api_manifest["name"] == "valdrics-api-staging"
    assert (
        api_manifest["definition"]["git"]["repository"]
        == "github.com/Valdrics/valdrics"
    )
    assert "PUBLIC_SUPABASE_ANON_KEY" in report["koyeb_dashboard_public_env_blockers"]
    assert "release_tag" in report["koyeb_release_value_blockers"]
    assert "services.api.image_digest" in report["koyeb_release_value_blockers"]
    assert "services.dashboard.image_digest" in report["koyeb_release_value_blockers"]
    assert "valdrics-internal-job-secret-staging" in report["koyeb_secret_names"]


def test_generate_managed_deployment_artifacts_flags_invalid_public_urls_as_blockers(
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
            "API_URL=http://api.runtime.example",
            "FRONTEND_URL=https://console.runtime.example",
            "LOG_LEVEL=INFO",
            "LLM_PROVIDER=groq",
            "GROQ_API_KEY=test-groq-key",
            "EXPOSE_API_DOCUMENTATION_PUBLICLY=false",
            "OTEL_LOGS_EXPORT_ENABLED=true",
            "SAAS_STRICT_INTEGRATIONS=true",
            "TRUST_PROXY_HEADERS=true",
            "CORS_ORIGINS='[\"https://console.runtime.example\"]'",
            "APP_RUNTIME_DATA_DIR=/tmp/valdrics",
            "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
            "REDIS_URL=redis://redis.example.com:6379/0",
            "SUPABASE_URL=https://example.supabase.co",
            "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=arn:aws:iam::123456789012:role/ValdricsControlPlane",
            "OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com:4317",
            "PAYSTACK_SECRET_KEY=sk_live_runtime_paystack_key",
            "PAYSTACK_PUBLIC_KEY=pk_live_runtime_paystack_key",
            "SENTRY_DSN=https://key@example.com/1",
            "TRUSTED_PROXY_CIDRS='[\"203.0.113.10/32\"]'",
        ],
    )

    report = generate_managed_deployment_artifacts(
        environment="production",
        runtime_env_file=runtime_env,
        output_dir=output_dir,
        release_tag="2026.03.19",
        api_image_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        dashboard_image_digest="sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )

    assert "API_URL" in report["runtime_validation_blockers"]
    assert report["ready_for_koyeb"] is False
    assert report["ready_for_koyeb_release"] is False
    assert report["ready_for_helm"] is False


@pytest.mark.parametrize(
    ("env_line", "expected_blocker"),
    [
        (
            "OTEL_EXPORTER_OTLP_ENDPOINT=otel.example.com:4317",
            "OTEL_EXPORTER_OTLP_ENDPOINT",
        ),
        ("SENTRY_DSN=not-a-url", "SENTRY_DSN"),
        ("TRUSTED_PROXY_CIDRS='[\"not-a-cidr\"]'", "TRUSTED_PROXY_CIDRS"),
        (
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=not-an-arn",
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN",
        ),
        ("ADMIN_API_KEY=too-short", "ADMIN_API_KEY"),
        ("INTERNAL_METRICS_AUTH_TOKEN=short-token", "INTERNAL_METRICS_AUTH_TOKEN"),
        ("PAYSTACK_SECRET_KEY=sk_test_runtime_paystack_key", "PAYSTACK_SECRET_KEY"),
        ("PAYSTACK_PUBLIC_KEY=pk_test_runtime_paystack_key", "PAYSTACK_PUBLIC_KEY"),
    ],
)
def test_generate_managed_deployment_artifacts_flags_invalid_runtime_values_as_blockers(
    tmp_path: Path,
    env_line: str,
    expected_blocker: str,
) -> None:
    runtime_env = tmp_path / "production.env"
    output_dir = tmp_path / "deploy" / "production"
    lines = [
        "ENVIRONMENT=production",
        "ENABLE_SCHEDULER=true",
        "WEB_CONCURRENCY=2",
        "API_URL=https://api.runtime.example",
        "FRONTEND_URL=https://console.runtime.example",
        "LOG_LEVEL=INFO",
        "LLM_PROVIDER=groq",
        "GROQ_API_KEY=test-groq-key",
        "EXPOSE_API_DOCUMENTATION_PUBLICLY=false",
        "OTEL_LOGS_EXPORT_ENABLED=true",
        "SAAS_STRICT_INTEGRATIONS=true",
        "TRUST_PROXY_HEADERS=true",
        "CORS_ORIGINS='[\"https://console.runtime.example\"]'",
        "APP_RUNTIME_DATA_DIR=/tmp/valdrics",
        "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
        "REDIS_URL=redis://redis.example.com:6379/0",
        "SUPABASE_URL=https://example.supabase.co",
        "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
        "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=arn:aws:iam::123456789012:role/ValdricsControlPlane",
        "OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com:4317",
        "PAYSTACK_SECRET_KEY=sk_live_runtime_paystack_key",
        "PAYSTACK_PUBLIC_KEY=pk_live_runtime_paystack_key",
        "SENTRY_DSN=https://key@example.com/1",
        "TRUSTED_PROXY_CIDRS='[\"203.0.113.10/32\"]'",
        "ADMIN_API_KEY=ci-admin-api-key-32-chars-min-0000000",
        "INTERNAL_METRICS_AUTH_TOKEN=ci-internal-metrics-token-32-chars-000",
    ]
    for index, line in enumerate(lines):
        if line.startswith(expected_blocker.split("[", 1)[0].split(".", 1)[0] + "="):
            lines[index] = env_line
            break
    _write_env(runtime_env, lines)

    report = generate_managed_deployment_artifacts(
        environment="production",
        runtime_env_file=runtime_env,
        output_dir=output_dir,
        release_tag="2026.03.19",
        api_image_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        dashboard_image_digest="sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    )

    assert expected_blocker in report["runtime_validation_blockers"]
    assert report["ready_for_koyeb"] is False
    assert report["ready_for_koyeb_release"] is False
    assert report["ready_for_helm"] is False


def test_generate_managed_deployment_artifacts_rejects_runtime_env_collision(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "deploy" / "production"
    runtime_env = output_dir / "deployment.report.json"
    _write_env(
        runtime_env,
        [
            "ENVIRONMENT=production",
            "ENABLE_SCHEDULER=true",
            "WEB_CONCURRENCY=2",
            "API_URL=https://api.runtime.example",
            "FRONTEND_URL=https://console.runtime.example",
            "LOG_LEVEL=INFO",
            "LLM_PROVIDER=openai",
            "OPENAI_API_KEY=sk-openai-live-key",
            "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
            "REDIS_URL=redis://redis.example.com:6379/0",
            "SUPABASE_URL=https://example.supabase.co",
            "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
            "TRUSTED_PROXY_CIDRS='[\"203.0.113.10/32\"]'",
        ],
    )

    with pytest.raises(
        ValueError,
        match="runtime_env_file must not overwrite generated deployment artifacts",
    ):
        generate_managed_deployment_artifacts(
            environment="production",
            runtime_env_file=runtime_env,
            output_dir=output_dir,
        )


def test_generate_managed_deployment_artifacts_rejects_invalid_image_digest(
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
            "FRONTEND_URL=https://console.runtime.example",
            "LOG_LEVEL=INFO",
            "LLM_PROVIDER=groq",
            "GROQ_API_KEY=test-groq-key",
            "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
            "REDIS_URL=redis://redis.example.com:6379/0",
            "SUPABASE_URL=https://example.supabase.co",
            "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
            "TRUSTED_PROXY_CIDRS='[\"203.0.113.10/32\"]'",
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=arn:aws:iam::123456789012:role/ValdricsControlPlane",
            "OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com:4317",
            "PAYSTACK_SECRET_KEY=sk_live_runtime_paystack_key",
            "PAYSTACK_PUBLIC_KEY=pk_live_runtime_paystack_key",
            "SENTRY_DSN=https://key@example.com/1",
        ],
    )

    with pytest.raises(
        ValueError, match="api_image_digest must be a sha256:<64-hex> digest"
    ):
        generate_managed_deployment_artifacts(
            environment="production",
            runtime_env_file=runtime_env,
            output_dir=output_dir,
            release_tag="2026.03.18",
            api_image_digest="sha256:not-a-real-digest",
            dashboard_image_digest="sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )


def test_generate_managed_deployment_artifacts_rejects_blank_registry(
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
            "FRONTEND_URL=https://console.runtime.example",
            "LOG_LEVEL=INFO",
            "LLM_PROVIDER=groq",
            "GROQ_API_KEY=test-groq-key",
            "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
            "REDIS_URL=redis://redis.example.com:6379/0",
            "SUPABASE_URL=https://example.supabase.co",
            "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
            "TRUSTED_PROXY_CIDRS='[\"203.0.113.10/32\"]'",
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=arn:aws:iam::123456789012:role/ValdricsControlPlane",
            "OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com:4317",
            "PAYSTACK_SECRET_KEY=sk_live_runtime_paystack_key",
            "PAYSTACK_PUBLIC_KEY=pk_live_runtime_paystack_key",
            "SENTRY_DSN=https://key@example.com/1",
        ],
    )

    with pytest.raises(
        ValueError,
        match="registry must be a non-empty container registry prefix",
    ):
        generate_managed_deployment_artifacts(
            environment="production",
            runtime_env_file=runtime_env,
            output_dir=output_dir,
            registry="   ",
        )


def test_generate_managed_deployment_artifacts_rejects_non_file_runtime_env_path(
    tmp_path: Path,
) -> None:
    runtime_env_dir = tmp_path / "runtime-env-dir"
    runtime_env_dir.mkdir()
    output_dir = tmp_path / "deploy" / "production"

    with pytest.raises(ValueError, match="runtime_env_file must be a file"):
        generate_managed_deployment_artifacts(
            environment="production",
            runtime_env_file=runtime_env_dir,
            output_dir=output_dir,
        )


def test_main_resolves_default_paths_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_generate_managed_deployment_artifacts(
        **kwargs: object,
    ) -> dict[str, object]:
        captured.update(kwargs)
        output_dir = kwargs["output_dir"]
        return {
            "environment": kwargs["environment"],
            "output_dir": output_dir.as_posix(),
            "runtime_validation_blockers": [],
            "ready_for_koyeb": False,
            "ready_for_koyeb_release": False,
            "ready_for_helm": False,
        }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        managed_deployment_generator,
        "generate_managed_deployment_artifacts",
        _fake_generate_managed_deployment_artifacts,
    )

    assert managed_deployment_generator.main(["--environment", "staging"]) == 0
    assert (
        captured["runtime_env_file"]
        == (
            managed_deployment_generator._repo_root() / ".runtime" / "staging.env"
        ).resolve()
    )
    assert (
        captured["output_dir"]
        == (
            managed_deployment_generator._repo_root()
            / managed_deployment_generator.DEFAULT_OUTPUT_ROOT
            / "staging"
        ).resolve()
    )


def test_main_resolves_explicit_relative_paths_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    captured: dict[str, object] = {}

    def _fake_generate_managed_deployment_artifacts(
        **kwargs: object,
    ) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "environment": kwargs["environment"],
            "output_dir": kwargs["output_dir"].as_posix(),  # type: ignore[index]
            "runtime_validation_blockers": [],
            "ready_for_koyeb": False,
            "ready_for_koyeb_release": False,
            "ready_for_helm": False,
        }

    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(managed_deployment_generator, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        managed_deployment_generator,
        "generate_managed_deployment_artifacts",
        _fake_generate_managed_deployment_artifacts,
    )

    assert (
        managed_deployment_generator.main(
            [
                "--environment",
                "staging",
                "--runtime-env-file",
                ".runtime/staging.env",
                "--output-dir",
                ".runtime/deploy/staging",
            ]
        )
        == 0
    )
    assert (
        captured["runtime_env_file"]
        == (repo_root / ".runtime" / "staging.env").resolve()
    )
    assert (
        captured["output_dir"]
        == (repo_root / ".runtime" / "deploy" / "staging").resolve()
    )


def test_main_rejects_relative_paths_that_escape_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(managed_deployment_generator, "_repo_root", lambda: repo_root)

    with pytest.raises(
        ValueError, match="runtime_env_file must stay within repo root when relative"
    ):
        managed_deployment_generator.main(
            [
                "--environment",
                "staging",
                "--runtime-env-file",
                "../escape/staging.env",
            ]
        )


def test_generate_managed_deployment_artifacts_rejects_file_output_dir(
    tmp_path: Path,
) -> None:
    runtime_env = tmp_path / "production.env"
    output_dir = tmp_path / "deploy-target"
    _write_env(
        runtime_env,
        [
            "ENVIRONMENT=production",
            "ENABLE_SCHEDULER=true",
            "WEB_CONCURRENCY=2",
            "API_URL=https://api.runtime.example",
            "FRONTEND_URL=https://console.runtime.example",
            "LOG_LEVEL=INFO",
            "LLM_PROVIDER=groq",
            "GROQ_API_KEY=test-groq-key",
            "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
            "REDIS_URL=redis://redis.example.com:6379/0",
            "SUPABASE_URL=https://example.supabase.co",
            "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
            "TRUSTED_PROXY_CIDRS='[\"203.0.113.10/32\"]'",
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=arn:aws:iam::123456789012:role/ValdricsControlPlane",
            "OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com:4317",
            "PAYSTACK_SECRET_KEY=sk_live_runtime_paystack_key",
            "PAYSTACK_PUBLIC_KEY=pk_live_runtime_paystack_key",
            "SENTRY_DSN=https://key@example.com/1",
        ],
    )
    output_dir.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="output_dir must be a directory path"):
        generate_managed_deployment_artifacts(
            environment="production",
            runtime_env_file=runtime_env,
            output_dir=output_dir,
        )


def test_generate_managed_deployment_artifacts_rejects_blocked_output_dir_parent(
    tmp_path: Path,
) -> None:
    runtime_env = tmp_path / "production.env"
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")
    _write_env(
        runtime_env,
        [
            "ENVIRONMENT=production",
            "ENABLE_SCHEDULER=true",
            "WEB_CONCURRENCY=2",
            "API_URL=https://api.runtime.example",
            "FRONTEND_URL=https://console.runtime.example",
            "LOG_LEVEL=INFO",
            "LLM_PROVIDER=groq",
            "GROQ_API_KEY=test-groq-key",
            "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
            "REDIS_URL=redis://redis.example.com:6379/0",
            "SUPABASE_URL=https://example.supabase.co",
            "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
            "TRUSTED_PROXY_CIDRS='[\"203.0.113.10/32\"]'",
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=arn:aws:iam::123456789012:role/ValdricsControlPlane",
            "OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com:4317",
            "PAYSTACK_SECRET_KEY=sk_live_runtime_paystack_key",
            "PAYSTACK_PUBLIC_KEY=pk_live_runtime_paystack_key",
            "SENTRY_DSN=https://key@example.com/1",
        ],
    )

    with pytest.raises(ValueError, match="output_dir parent must be a directory path"):
        generate_managed_deployment_artifacts(
            environment="production",
            runtime_env_file=runtime_env,
            output_dir=blocked_parent / "deploy" / "production",
        )


def test_generate_managed_deployment_artifacts_does_not_leave_outputs_when_report_build_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
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
            "FRONTEND_URL=https://console.runtime.example",
            "LOG_LEVEL=INFO",
            "LLM_PROVIDER=groq",
            "GROQ_API_KEY=test-groq-key",
            "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
            "REDIS_URL=redis://redis.example.com:6379/0",
            "SUPABASE_URL=https://example.supabase.co",
            "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
            "TRUSTED_PROXY_CIDRS='[\"203.0.113.10/32\"]'",
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=arn:aws:iam::123456789012:role/ValdricsControlPlane",
            "OTEL_EXPORTER_OTLP_ENDPOINT=https://otel.example.com:4317",
            "PAYSTACK_SECRET_KEY=sk_live_runtime_paystack_key",
            "PAYSTACK_PUBLIC_KEY=pk_live_runtime_paystack_key",
            "SENTRY_DSN=https://key@example.com/1",
        ],
    )
    original_json_dumps = managed_deployment_generator.json.dumps

    def _failing_json_dumps(payload: object, *args: object, **kwargs: object) -> str:
        if isinstance(payload, dict) and "artifacts" in payload:
            raise RuntimeError("deployment report build failed")
        return original_json_dumps(payload, *args, **kwargs)

    monkeypatch.setattr(managed_deployment_generator.json, "dumps", _failing_json_dumps)

    with pytest.raises(RuntimeError, match="deployment report build failed"):
        generate_managed_deployment_artifacts(
            environment="production",
            runtime_env_file=runtime_env,
            output_dir=output_dir,
            release_tag="2026.03.19",
            api_image_digest="sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
            dashboard_image_digest="sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        )

    for artifact_path in managed_deployment_generator._artifact_output_paths(
        output_dir
    ):
        assert not artifact_path.exists()
