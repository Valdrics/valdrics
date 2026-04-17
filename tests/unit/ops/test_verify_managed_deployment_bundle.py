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
from scripts.verify_managed_deployment_bundle import (
    main,
    verify_managed_deployment_bundle,
)


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
            "SUPABASE_URL=",
            "SUPABASE_ANON_KEY=",
            "SUPABASE_JWT_SECRET=",
            "CSRF_SECRET_KEY=",
            "ENCRYPTION_KEY=",
            "KDF_SALT=",
            "ADMIN_API_KEY=",
            "INTERNAL_METRICS_AUTH_TOKEN=",
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET=",
            "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
            "LLM_PROVIDER=groq",
            "GROQ_API_KEY=",
            "PAYSTACK_SECRET_KEY=",
            "PAYSTACK_PUBLIC_KEY=",
            "TRUSTED_PROXY_CIDRS=[]",
            "",
        ]
    )


def _build_bundle(
    tmp_path: Path, *, environment: str = "production"
) -> tuple[Path, Path, Path]:
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
        supabase_url="https://example.supabase.co",
        supabase_anon_key="dashboard-anon-key",
        supabase_jwt_secret="x" * 40,
        llm_provider="groq",
        llm_api_key="gsk_test_runtime_key",
        paystack_secret_key="sk_live_runtime_paystack_key",
        paystack_public_key="pk_live_runtime_paystack_key",
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
        release_tag="2026.04.10",
        api_promotion_ref=(
            "us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime/"
            "valdrics-api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        ),
        gcp_project_id="valdrics-prod",
        gcp_region="us-central1",
        cloudflare_account_id="cf-account-prod",
        cloudflare_zone_id="cf-zone-prod",
        cloudflare_pages_project_name="valdrics-dashboard",
        cloudflare_pages_production_branch="main",
        supabase_organization_id="supabase-org-prod",
        supabase_project_name="valdrics",
        supabase_region="us-east-1",
    )
    return runtime_report, migrate_report, deployment_report


def test_verify_managed_deployment_bundle_accepts_coherent_bundle(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert errors == []


def test_verify_managed_deployment_bundle_detects_runtime_blocker_drift(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["runtime_validation_blockers"] = ["DATABASE_URL"]
    deployment_report.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any(
        "deployment report runtime blockers drift from runtime env" in error
        for error in errors
    )


def test_verify_managed_deployment_bundle_detects_terraform_report_drift(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["terraform_remaining_inputs"] = ["gcp_project_id"]
    payload["terraform_value_blockers"] = ["gcp_project_id"]
    deployment_report.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any(
        "deployment report terraform_remaining_inputs drift from generated Terraform tfvars"
        in error
        for error in errors
    )
    assert any(
        "deployment report terraform_value_blockers drift from generated Terraform tfvars"
        in error
        for error in errors
    )


def test_verify_managed_deployment_bundle_detects_missing_artifact_and_report_env_mismatch(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    runtime_payload = json.loads(runtime_report.read_text(encoding="utf-8"))
    runtime_payload["environment"] = "staging"
    runtime_report.write_text(
        json.dumps(runtime_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    (deployment_report.parent / "secret-manager-runtime-secrets.json").unlink()

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any("runtime report environment mismatch" in error for error in errors)
    assert any("deployment artifact missing on disk" in error for error in errors)


def test_verify_managed_deployment_bundle_accepts_non_secret_release_artifact_bundle(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    runtime_payload = json.loads(runtime_report.read_text(encoding="utf-8"))
    migration_payload = json.loads(migrate_report.read_text(encoding="utf-8"))
    runtime_payload["runtime_validation_blockers"] = []
    runtime_payload["declared_external_placeholders"] = []
    runtime_payload["unresolved_external_keys"] = []
    runtime_payload["required_operator_input_keys"] = []
    runtime_payload["validation_ready"] = True
    runtime_report.write_text(
        json.dumps(runtime_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    deployment_payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    deployment_payload["runtime_validation_blockers"] = []
    deployment_payload["secret_manager_secret_value_blockers"] = []
    deployment_payload["terraform_remaining_inputs"] = []
    deployment_payload["terraform_value_blockers"] = []
    deployment_payload["ready_for_unified_platform"] = True
    deployment_payload["ready_for_release_promotion"] = True
    deployment_payload["ready_for_terraform"] = True
    deployment_report.write_text(
        json.dumps(deployment_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    operator_handoff = deployment_report.parent / "operator-handoff.md"
    operator_handoff.write_text("# handoff\n", encoding="utf-8")
    (deployment_report.parent / "secret-manager-runtime-secrets.json").unlink()
    (deployment_report.parent / "terraform.runtime.auto.tfvars.json").unlink()
    Path(runtime_payload["output_path"]).unlink()
    Path(migration_payload["output_path"]).unlink()

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
        allow_non_secret_artifact_bundle=True,
    )

    assert errors == []


def test_verify_managed_deployment_bundle_rejects_missing_operator_handoff_in_non_secret_bundle(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    runtime_payload = json.loads(runtime_report.read_text(encoding="utf-8"))
    migration_payload = json.loads(migrate_report.read_text(encoding="utf-8"))
    runtime_payload["runtime_validation_blockers"] = []
    runtime_payload["declared_external_placeholders"] = []
    runtime_payload["unresolved_external_keys"] = []
    runtime_payload["required_operator_input_keys"] = []
    runtime_payload["validation_ready"] = True
    runtime_report.write_text(
        json.dumps(runtime_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    deployment_payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    deployment_payload["runtime_validation_blockers"] = []
    deployment_payload["secret_manager_secret_value_blockers"] = []
    deployment_payload["terraform_remaining_inputs"] = []
    deployment_payload["terraform_value_blockers"] = []
    deployment_payload["ready_for_unified_platform"] = True
    deployment_payload["ready_for_release_promotion"] = True
    deployment_payload["ready_for_terraform"] = True
    deployment_report.write_text(
        json.dumps(deployment_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    (deployment_report.parent / "secret-manager-runtime-secrets.json").unlink()
    (deployment_report.parent / "terraform.runtime.auto.tfvars.json").unlink()
    Path(runtime_payload["output_path"]).unlink()
    Path(migration_payload["output_path"]).unlink()

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
        allow_non_secret_artifact_bundle=True,
    )

    assert any("operator-handoff.md" in error for error in errors)


def test_verify_managed_deployment_bundle_rejects_artifact_path_outside_output_dir(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    outside_artifact = tmp_path / "outside-release.json"
    outside_artifact.write_text("{}", encoding="utf-8")

    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["artifacts"]["artifact_registry_release_metadata"] = str(outside_artifact)
    deployment_report.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any(
        "deployment artifact path must stay within deployment output_dir" in error
        for error in errors
    )


def test_verify_managed_deployment_bundle_rejects_tfvars_path_outside_output_dir(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    outside_tfvars = tmp_path / "outside.tfvars.json"
    outside_tfvars.write_text("{}", encoding="utf-8")

    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["terraform_runtime_tfvars_path"] = str(outside_tfvars)
    deployment_report.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any(
        "terraform runtime tfvars must stay within deployment output_dir" in error
        for error in errors
    )


def test_verify_managed_deployment_bundle_rejects_duplicate_artifact_paths(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)

    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["artifacts"]["artifact_registry_release_metadata"] = payload["artifacts"][
        "unified_platform_manifest"
    ]
    deployment_report.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any(
        "deployment artifact paths must be distinct" in error for error in errors
    )


def test_verify_managed_deployment_bundle_rejects_unexpected_artifact_filename(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(tmp_path)
    output_dir = deployment_report.parent
    renamed = output_dir / "renamed-release.json"
    original = output_dir / "artifact-registry-release.json"
    original.rename(renamed)

    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["artifacts"]["artifact_registry_release_metadata"] = str(renamed)
    deployment_report.write_text(
        json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8"
    )

    errors = verify_managed_deployment_bundle(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
    )

    assert any(
        "deployment artifact path has unexpected filename" in error for error in errors
    )


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
    monkeypatch.setattr(
        managed_bundle_verifier, "verify_managed_deployment_bundle", _capture
    )
    monkeypatch.chdir(tmp_path)

    assert main(["--environment", "staging"]) == 0
    assert captured["runtime"] == repo_root / ".runtime" / "staging.report.json"
    assert (
        captured["migration"] == repo_root / ".runtime" / "staging.migrate.report.json"
    )
    assert (
        captured["deployment"]
        == repo_root / ".runtime" / "deploy" / "staging" / "deployment.report.json"
    )
