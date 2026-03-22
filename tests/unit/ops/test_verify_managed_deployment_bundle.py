from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.verify_managed_deployment_bundle as managed_bundle_verifier
from scripts.generate_managed_deployment_artifacts import (
    generate_managed_deployment_artifacts,
)
from scripts.generate_managed_migration_env import generate_managed_migration_env
from scripts.generate_managed_runtime_env import generate_managed_runtime_env
from scripts.verify_managed_deployment_bundle import main, verify_managed_deployment_bundle


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
            "SUPABASE_ANON_KEY=",
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
        supabase_anon_key="dashboard-anon-key",
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


def test_verify_managed_deployment_bundle_rejects_artifact_path_outside_output_dir(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    outside_artifact = tmp_path / "outside-worker.yaml"
    outside_artifact.write_text("kind: service\n", encoding="utf-8")

    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["artifacts"]["koyeb_worker_manifest"] = str(outside_artifact)
    deployment_report.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any("deployment artifact path must stay within deployment output_dir" in error for error in errors)


def test_verify_managed_deployment_bundle_rejects_tfvars_path_outside_output_dir(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    outside_tfvars = tmp_path / "outside.tfvars.json"
    outside_tfvars.write_text("{}", encoding="utf-8")

    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["terraform_runtime_tfvars_path"] = str(outside_tfvars)
    deployment_report.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any("terraform runtime tfvars must stay within deployment output_dir" in error for error in errors)


def test_verify_managed_deployment_bundle_rejects_duplicate_artifact_paths(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)

    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["artifacts"]["koyeb_worker_manifest"] = payload["artifacts"]["koyeb_api_manifest"]
    deployment_report.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any("deployment artifact paths must be distinct" in error for error in errors)


def test_verify_managed_deployment_bundle_rejects_unexpected_artifact_filename(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    output_dir = deployment_report.parent
    renamed = output_dir / "renamed-worker.yaml"
    original = output_dir / "koyeb-worker.yaml"
    original.rename(renamed)

    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["artifacts"]["koyeb_worker_manifest"] = str(renamed)
    deployment_report.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any("deployment artifact path has unexpected filename" in error for error in errors)


def test_main_resolves_default_report_paths_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    captured: dict[str, Path] = {}

    def _capture(
        *,
        environment: str,
        runtime_report_path: Path,
        migration_report_path: Path,
        deployment_report_path: Path,
    ) -> list[str]:
        captured["runtime"] = runtime_report_path
        captured["migration"] = migration_report_path
        captured["deployment"] = deployment_report_path
        return []

    monkeypatch.setattr(managed_bundle_verifier, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(managed_bundle_verifier, "verify_managed_deployment_bundle", _capture)
    monkeypatch.chdir(tmp_path)

    assert main(["--environment", "staging"]) == 0
    assert captured["runtime"] == repo_root / ".runtime" / "staging.report.json"
    assert captured["migration"] == repo_root / ".runtime" / "staging.migrate.report.json"
    assert captured["deployment"] == (
        repo_root / ".runtime" / "deploy" / "staging" / "deployment.report.json"
    )


def test_main_rejects_relative_report_repo_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(managed_bundle_verifier, "_repo_root", lambda: repo_root)

    assert (
        main(
            [
                "--environment",
                "staging",
                "--runtime-report",
                "../escape.report.json",
            ]
        )
        == 2
    )


def test_main_rejects_directory_report_path(tmp_path: Path) -> None:
    report_dir = tmp_path / "report-dir"
    report_dir.mkdir()

    assert (
        main(
            [
                "--environment",
                "staging",
                "--runtime-report",
                str(report_dir),
            ]
        )
        == 2
    )
