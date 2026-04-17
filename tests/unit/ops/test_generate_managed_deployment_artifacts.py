from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_managed_deployment_artifacts import (
    generate_managed_deployment_artifacts,
)


def _write_env(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _base_runtime_lines() -> list[str]:
    return [
        "ENVIRONMENT=production",
        "API_URL=https://api.runtime.example",
        "FRONTEND_URL=https://console.runtime.example",
        "LOG_LEVEL=INFO",
        "PLATFORM_RUNTIME_PROFILE=gcp",
        "OBSERVABILITY_BACKEND=gcp",
        "PUBLIC_API_RATE_LIMITING_BACKEND=cloudflare",
        "RATELIMIT_ENABLED=false",
        "LLM_PROVIDER=openai",
        "OPENAI_API_KEY=sk-openai-live-key",
        "EXPOSE_API_DOCUMENTATION_PUBLICLY=false",
        "SAAS_STRICT_INTEGRATIONS=true",
        "TRUST_PROXY_HEADERS=true",
        "CORS_ORIGINS='[\"https://console.runtime.example\"]'",
        "APP_RUNTIME_DATA_DIR=/tmp/valdrics",
        "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
        "GCP_PROJECT_ID=valdrics-prod",
        "GCP_REGION=us-central1",
        "GCP_CLOUD_TASKS_QUEUE=valdrics-managed-work",
        "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL=tasks-invoker@valdrics-prod.iam.gserviceaccount.com",
        "GCP_CLOUD_RUN_SERVICE_NAME=valdrics-api",
        "GCP_CLOUD_RUN_BATCH_JOB_NAME=valdrics-batch",
        'GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS=\'["tasks-invoker@valdrics-prod.iam.gserviceaccount.com","scheduler-invoker@valdrics-prod.iam.gserviceaccount.com"]\'',
        "SUPABASE_URL=https://example.supabase.co",
        "SUPABASE_ANON_KEY=ci-public-supabase-anon-key",
        "SUPABASE_JWT_SECRET=ci-supabase-jwt-secret-32-chars-0000",
        "PAYSTACK_SECRET_KEY=sk_live_runtime_paystack_key",
        "PAYSTACK_PUBLIC_KEY=pk_live_runtime_paystack_key",
        "TRUSTED_PROXY_CIDRS='[\"203.0.113.10/32\"]'",
        "ENCRYPTION_KEY=ci-encryption-key-32-chars-min-00000000",
        "KDF_SALT=MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
        "CSRF_SECRET_KEY=ci-csrf-secret-key-32-chars-min-000000",
        "ADMIN_API_KEY=ci-admin-api-key-32-chars-min-0000000",
        "INTERNAL_METRICS_AUTH_TOKEN=ci-internal-metrics-token-32-chars-000",
        "ENFORCEMENT_APPROVAL_TOKEN_SECRET=ci-enforcement-approval-token-secret-32-chars",
        "ENFORCEMENT_EXPORT_SIGNING_SECRET=ci-enforcement-export-signing-secret-32-char",
    ]


def _resolved_terraform_inputs() -> dict[str, str]:
    return {
        "gcp_project_id": "valdrics-prod",
        "gcp_region": "us-central1",
        "cloudflare_account_id": "cf-account-prod",
        "cloudflare_zone_id": "cf-zone-prod",
        "cloudflare_pages_project_name": "valdrics-dashboard",
        "cloudflare_pages_production_branch": "main",
        "supabase_organization_id": "supabase-org-prod",
        "supabase_project_name": "valdrics",
        "supabase_region": "us-east-1",
    }


def test_generate_managed_deployment_artifacts_outputs_unified_platform_bundle(
    tmp_path: Path,
) -> None:
    runtime_env = tmp_path / "production.env"
    output_dir = tmp_path / "deploy" / "production"
    _write_env(runtime_env, _base_runtime_lines())

    report = generate_managed_deployment_artifacts(
        environment="production",
        runtime_env_file=runtime_env,
        output_dir=output_dir,
        release_tag="2026.04.10",
        api_promotion_ref=(
            "us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime/"
            "valdrics-api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        ),
        batch_promotion_ref=(
            "us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime/"
            "valdrics-api@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
        ),
        **_resolved_terraform_inputs(),
    )

    manifest = json.loads(
        (output_dir / "unified-platform-manifest.json").read_text(encoding="utf-8")
    )
    secret_payload = json.loads(
        (output_dir / "secret-manager-runtime-secrets.json").read_text(encoding="utf-8")
    )
    cloudflare_env = json.loads(
        (output_dir / "cloudflare-pages-env.json").read_text(encoding="utf-8")
    )
    release_payload = json.loads(
        (output_dir / "artifact-registry-release.json").read_text(encoding="utf-8")
    )
    terraform_tfvars = json.loads(
        (output_dir / "terraform.runtime.auto.tfvars.json").read_text(encoding="utf-8")
    )
    operator_handoff = output_dir / "operator-handoff.md"

    assert report["ready_for_unified_platform"] is True
    assert report["ready_for_release_promotion"] is True
    assert report["ready_for_terraform"] is True
    assert report["runtime_validation_blockers"] == []
    assert report["artifact_registry_release_value_blockers"] == []
    assert report["cloudflare_pages_public_env_blockers"] == []
    assert report["secret_manager_secret_value_blockers"] == []
    assert report["terraform_remaining_inputs"] == []
    assert report["terraform_value_blockers"] == []

    assert manifest["strategy"] == "unified_platform_managed_release"
    assert manifest["backend"]["runtime"] == "google_cloud_run"
    assert manifest["backend"]["batch_job_name"] == "valdrics-batch"
    assert manifest["backend"]["scheduler_owner"] == "cloud_scheduler"
    assert manifest["backend"]["runtime_plain_env"]["PLATFORM_RUNTIME_PROFILE"] == "gcp"
    assert manifest["backend"]["runtime_plain_env"]["OBSERVABILITY_BACKEND"] == "gcp"
    assert (
        manifest["backend"]["runtime_plain_env"]["PUBLIC_API_RATE_LIMITING_BACKEND"]
        == "cloudflare"
    )
    assert manifest["backend"]["runtime_plain_env"]["RATELIMIT_ENABLED"] == "false"
    assert "WEB_CONCURRENCY" not in manifest["backend"]["runtime_plain_env"]

    assert secret_payload["DATABASE_URL"].startswith("postgresql+asyncpg://postgres:")
    assert secret_payload["OPENAI_API_KEY"] == "sk-openai-live-key"
    assert "INTERNAL_JOB_SECRET" not in secret_payload
    assert "WEB_CONCURRENCY" not in secret_payload
    assert "SUPABASE_URL" not in secret_payload
    assert "SUPABASE_ANON_KEY" not in secret_payload
    assert "SENTRY_DSN" not in secret_payload
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in secret_payload
    assert "GCP_CLOUD_RUN_SERVICE_NAME" not in secret_payload
    assert "GCP_INTERNAL_BASE_URL" not in secret_payload

    assert cloudflare_env["PUBLIC_API_URL"] == "https://api.runtime.example/api/v1"
    assert cloudflare_env["PUBLIC_SUPABASE_URL"] == "https://example.supabase.co"
    assert cloudflare_env["PUBLIC_SUPABASE_ANON_KEY"] == "ci-public-supabase-anon-key"

    assert release_payload["strategy"] == "immutable_artifact_registry_promotion"
    assert release_payload["services"]["api"]["runtime"] == "google_cloud_run"
    assert release_payload["services"]["batch"]["runtime"] == "google_cloud_run_jobs"
    assert release_payload["services"]["api"]["promotion_ref"].endswith(
        "@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    )
    assert release_payload["services"]["batch"]["promotion_ref"].endswith(
        "@sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )

    assert terraform_tfvars["environment"] == "production"
    assert (
        terraform_tfvars["api_image"]
        == release_payload["services"]["api"]["promotion_ref"]
    )
    assert (
        terraform_tfvars["batch_job_image"]
        == release_payload["services"]["batch"]["promotion_ref"]
    )
    assert (
        terraform_tfvars["runtime_secret_env"]["OPENAI_API_KEY"] == "sk-openai-live-key"
    )
    assert terraform_tfvars["gcp_project_id"] == "valdrics-prod"
    assert terraform_tfvars["cloudflare_zone_id"] == "cf-zone-prod"
    assert terraform_tfvars["supabase_project_name"] == "valdrics"
    assert (
        report["artifacts"]["operator_handoff_markdown"]
        == operator_handoff.as_posix()
    )
    assert not operator_handoff.exists()


def test_generate_managed_deployment_artifacts_reports_placeholder_blockers_for_staging(
    tmp_path: Path,
) -> None:
    runtime_env = tmp_path / "staging.env"
    output_dir = tmp_path / "deploy" / "staging"
    _write_env(
        runtime_env,
        [
            "ENVIRONMENT=staging",
            "API_URL=https://REPLACE_WITH_API_DOMAIN",
            "FRONTEND_URL=https://REPLACE_WITH_FRONTEND_DOMAIN",
            "LOG_LEVEL=INFO",
            "PLATFORM_RUNTIME_PROFILE=gcp",
            "OBSERVABILITY_BACKEND=gcp",
            "PUBLIC_API_RATE_LIMITING_BACKEND=cloudflare",
            "RATELIMIT_ENABLED=false",
            "LLM_PROVIDER=groq",
            "GROQ_API_KEY=REPLACE_WITH_GROQ_API_KEY",
            "DATABASE_URL=postgresql+asyncpg://REPLACE_WITH_DB_USER:REPLACE_WITH_DB_PASSWORD@REPLACE_WITH_DB_HOST:5432/postgres",
            "GCP_PROJECT_ID=REPLACE_WITH_GCP_PROJECT_ID",
            "GCP_REGION=REPLACE_WITH_GCP_REGION",
            "GCP_CLOUD_TASKS_QUEUE=valdrics-managed-work",
            "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL=REPLACE_WITH_GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL",
            "GCP_CLOUD_RUN_SERVICE_NAME=valdrics-api",
            "GCP_CLOUD_RUN_BATCH_JOB_NAME=valdrics-batch",
            'GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS=\'["REPLACE_WITH_GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL","REPLACE_WITH_GCP_CLOUD_SCHEDULER_INVOKER_SERVICE_ACCOUNT_EMAIL"]\'',
            "SUPABASE_URL=https://REPLACE_WITH_SUPABASE_PROJECT.supabase.co",
            "SUPABASE_ANON_KEY=REPLACE_WITH_SUPABASE_ANON_KEY",
            "SUPABASE_JWT_SECRET=REPLACE_WITH_SUPABASE_JWT_SECRET_MINIMUM_32_CHARS_VALUE",
            "PAYSTACK_SECRET_KEY=sk_live_REPLACE_WITH_PAYSTACK_SECRET_KEY",
            "PAYSTACK_PUBLIC_KEY=pk_live_REPLACE_WITH_PAYSTACK_PUBLIC_KEY",
            "TRUSTED_PROXY_CIDRS='[\"REPLACE_WITH_TRUSTED_PROXY_CIDR\"]'",
            "ENCRYPTION_KEY=ci-encryption-key-32-chars-min-00000000",
            "KDF_SALT=MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=",
            "CSRF_SECRET_KEY=ci-csrf-secret-key-32-chars-min-000000",
            "ADMIN_API_KEY=ci-admin-api-key-32-chars-min-0000000",
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

    assert report["ready_for_unified_platform"] is False
    assert report["ready_for_release_promotion"] is False
    assert "DATABASE_URL" in report["runtime_validation_blockers"]
    assert "GCP_PROJECT_ID" in report["runtime_validation_blockers"]
    assert "PUBLIC_SUPABASE_ANON_KEY" in report["cloudflare_pages_public_env_blockers"]
    assert "release_tag" in report["artifact_registry_release_value_blockers"]
    assert (
        "services.api.promotion_ref"
        in report["artifact_registry_release_value_blockers"]
    )
    assert (
        "services.batch.promotion_ref"
        in report["artifact_registry_release_value_blockers"]
    )
    assert "OPENAI_API_KEY" not in report["secret_manager_secret_keys"]
    assert "GROQ_API_KEY" in report["secret_manager_secret_keys"]
    assert "gcp_project_id" in report["terraform_remaining_inputs"]
    assert "cloudflare_zone_id" in report["terraform_remaining_inputs"]
    assert "gcp_project_id" in report["terraform_value_blockers"]
    assert "runtime_plain_env.API_URL" in report["terraform_value_blockers"]


def test_generate_managed_deployment_artifacts_strips_legacy_internal_job_secret(
    tmp_path: Path,
) -> None:
    runtime_env = tmp_path / "production.env"
    output_dir = tmp_path / "deploy" / "production"
    _write_env(
        runtime_env,
        _base_runtime_lines() + ["INTERNAL_JOB_SECRET=legacy-shared-secret"],
    )

    report = generate_managed_deployment_artifacts(
        environment="production",
        runtime_env_file=runtime_env,
        output_dir=output_dir,
    )
    secret_payload = json.loads(
        (output_dir / "secret-manager-runtime-secrets.json").read_text(encoding="utf-8")
    )

    assert "INTERNAL_JOB_SECRET" not in secret_payload
    assert "INTERNAL_JOB_SECRET" not in report["secret_manager_secret_keys"]


def test_generate_managed_deployment_artifacts_prunes_unmanaged_bundle_outputs(
    tmp_path: Path,
) -> None:
    runtime_env = tmp_path / "production.env"
    output_dir = tmp_path / "deploy" / "production"
    _write_env(runtime_env, _base_runtime_lines())
    output_dir.mkdir(parents=True, exist_ok=True)
    for stale_name in (
        "aws-runtime-secret.json",
        "helm-values.yaml",
        "koyeb-api.yaml",
        "koyeb-dashboard-env.json",
        "koyeb-release.json",
        "koyeb-secrets.json",
        "koyeb-worker.yaml",
        "random-operator-note.txt",
    ):
        (output_dir / stale_name).write_text("legacy\n", encoding="utf-8")
    preserved_handoff = output_dir / "operator-handoff.md"
    preserved_handoff.write_text("keep me\n", encoding="utf-8")

    generate_managed_deployment_artifacts(
        environment="production",
        runtime_env_file=runtime_env,
        output_dir=output_dir,
        **_resolved_terraform_inputs(),
    )

    for stale_name in (
        "aws-runtime-secret.json",
        "helm-values.yaml",
        "koyeb-api.yaml",
        "koyeb-dashboard-env.json",
        "koyeb-release.json",
        "koyeb-secrets.json",
        "koyeb-worker.yaml",
        "random-operator-note.txt",
    ):
        assert not (output_dir / stale_name).exists()
    assert preserved_handoff.exists()


@pytest.mark.parametrize(
    ("env_line", "expected_blocker"),
    [
        ("API_URL=http://api.runtime.example", "API_URL"),
        ("TRUSTED_PROXY_CIDRS='[\"not-a-cidr\"]'", "TRUSTED_PROXY_CIDRS"),
        ("ADMIN_API_KEY=too-short", "ADMIN_API_KEY"),
        ("INTERNAL_METRICS_AUTH_TOKEN=short-token", "INTERNAL_METRICS_AUTH_TOKEN"),
        ("PAYSTACK_SECRET_KEY=not-a-paystack-key", "PAYSTACK_SECRET_KEY"),
        ("PAYSTACK_PUBLIC_KEY=not-a-paystack-key", "PAYSTACK_PUBLIC_KEY"),
    ],
)
def test_generate_managed_deployment_artifacts_flags_invalid_runtime_values_as_blockers(
    tmp_path: Path,
    env_line: str,
    expected_blocker: str,
) -> None:
    runtime_env = tmp_path / "production.env"
    output_dir = tmp_path / "deploy" / "production"
    lines = _base_runtime_lines()
    key_prefix = expected_blocker.split("[", 1)[0].split(".", 1)[0] + "="
    for index, line in enumerate(lines):
        if line.startswith(key_prefix):
            lines[index] = env_line
            break
    _write_env(runtime_env, lines)

    report = generate_managed_deployment_artifacts(
        environment="production",
        runtime_env_file=runtime_env,
        output_dir=output_dir,
        release_tag="2026.04.10",
        api_promotion_ref=(
            "us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime/"
            "valdrics-api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        ),
    )

    assert expected_blocker in report["runtime_validation_blockers"]
    assert report["ready_for_unified_platform"] is False


def test_generate_managed_deployment_artifacts_rejects_runtime_env_collision(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "deploy" / "production"
    runtime_env = output_dir / "deployment.report.json"
    _write_env(runtime_env, _base_runtime_lines())

    with pytest.raises(
        ValueError,
        match="runtime_env_file must not overwrite generated deployment artifacts",
    ):
        generate_managed_deployment_artifacts(
            environment="production",
            runtime_env_file=runtime_env,
            output_dir=output_dir,
        )


def test_generate_managed_deployment_artifacts_flags_invalid_promotion_refs(
    tmp_path: Path,
) -> None:
    runtime_env = tmp_path / "production.env"
    output_dir = tmp_path / "deploy" / "production"
    _write_env(runtime_env, _base_runtime_lines())

    report = generate_managed_deployment_artifacts(
        environment="production",
        runtime_env_file=runtime_env,
        output_dir=output_dir,
        release_tag="2026.04.10",
        api_promotion_ref="us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime/valdrics-api:not-digest-pinned",
    )

    assert report["artifact_registry_release_value_blockers"] == []
    assert report["ready_for_release_promotion"] is False
