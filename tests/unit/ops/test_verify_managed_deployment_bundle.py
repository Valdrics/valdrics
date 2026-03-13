from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_managed_deployment_artifacts import (
    generate_managed_deployment_artifacts,
)
from scripts.generate_managed_migration_env import generate_managed_migration_env
from scripts.generate_managed_runtime_env import generate_managed_runtime_env
from scripts.verify_managed_deployment_bundle import verify_managed_deployment_bundle


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _runtime_template() -> str:
    return "\n".join(
        [
            "API_URL=",
            "FRONTEND_URL=",
            "CORS_ORIGINS=[]",
            "DATABASE_URL=",
            "REDIS_URL=",
            "SUPABASE_URL=",
            "SUPABASE_JWT_SECRET=",
            "CSRF_SECRET_KEY=",
            "ENCRYPTION_KEY=",
            "KDF_SALT=",
            "ADMIN_API_KEY=",
            "INTERNAL_JOB_SECRET=",
            "INTERNAL_METRICS_AUTH_TOKEN=",
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET=",
            "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
            "LLM_PROVIDER=groq",
            "GROQ_API_KEY=",
            "PAYSTACK_SECRET_KEY=",
            "PAYSTACK_PUBLIC_KEY=",
            "SENTRY_DSN=",
            "OTEL_EXPORTER_OTLP_ENDPOINT=",
            "TRUSTED_PROXY_CIDRS=[]",
            "",
        ]
    )


def _build_bundle(tmp_path: Path, *, environment: str = "production") -> tuple[Path, Path, Path]:
    template = tmp_path / ".env.example"
    runtime_env = tmp_path / f"{environment}.env"
    runtime_report = tmp_path / f"{environment}.report.json"
    migrate_env = tmp_path / f"{environment}.migrate.env"
    migrate_report = tmp_path / f"{environment}.migrate.report.json"
    deploy_dir = tmp_path / "deploy" / environment
    deployment_report = deploy_dir / "deployment.report.json"
    _write(template, _runtime_template())

    generate_managed_runtime_env(
        template_path=template,
        output_path=runtime_env,
        report_path=runtime_report,
        environment=environment,
        api_url="https://api.runtime.example",
        frontend_url="https://app.runtime.example",
        database_url="postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
        redis_url="redis://redis.example.com:6379/0",
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret="x" * 40,
        aws_assume_role_trust_principal_arn=(
            "arn:aws:iam::123456789012:role/ValdricsControlPlane"
        ),
        llm_provider="groq",
        llm_api_key="gsk_test_runtime_key",
        paystack_secret_key="sk_live_runtime_paystack_key",
        paystack_public_key="pk_live_runtime_paystack_key",
        sentry_dsn="https://key@example.com/1",
        otel_endpoint="https://otel.example.com:4317",
        trusted_proxy_cidrs=["203.0.113.10/32"],
    )
    generate_managed_migration_env(
        output_path=migrate_env,
        report_path=migrate_report,
        environment=environment,
        database_url="postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
        db_ssl_mode="require",
    )
    generate_managed_deployment_artifacts(
        environment=environment,
        runtime_env_file=runtime_env,
        output_dir=deploy_dir,
    )
    return runtime_report, migrate_report, deployment_report


def test_verify_managed_deployment_bundle_accepts_coherent_bundle(tmp_path: Path) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert errors == []


def test_verify_managed_deployment_bundle_detects_runtime_blocker_drift(tmp_path: Path) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["runtime_validation_blockers"] = ["DATABASE_URL"]
    deployment_report.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any("deployment report runtime blockers drift from runtime env" in error for error in errors)


def test_verify_managed_deployment_bundle_detects_missing_artifact_and_report_env_mismatch(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    runtime_payload = json.loads(runtime_report.read_text(encoding="utf-8"))
    runtime_payload["environment"] = "staging"
    runtime_report.write_text(json.dumps(runtime_payload, indent=2, sort_keys=True), encoding="utf-8")
    (deployment_report.parent / "koyeb-worker.yaml").unlink()

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any("runtime report environment mismatch" in error for error in errors)
    assert any("deployment artifact missing on disk" in error for error in errors)
