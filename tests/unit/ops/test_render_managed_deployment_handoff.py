from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.render_managed_deployment_handoff as managed_handoff
from scripts.generate_managed_deployment_artifacts import (
    generate_managed_deployment_artifacts,
)
from scripts.generate_managed_migration_env import generate_managed_migration_env
from scripts.generate_managed_runtime_env import generate_managed_runtime_env
from scripts.render_managed_deployment_handoff import (
    main,
    render_managed_deployment_handoff,
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
    tmp_path: Path,
    *,
    environment: str,
    release_ready: bool,
) -> tuple[Path, Path, Path]:
    template = tmp_path / ".env.example"
    runtime_dir = tmp_path / ".runtime"
    runtime_env = runtime_dir / f"{environment}.env"
    runtime_report = runtime_dir / f"{environment}.report.json"
    migrate_env = runtime_dir / f"{environment}.migrate.env"
    migrate_report = runtime_dir / f"{environment}.migrate.report.json"
    deploy_dir = runtime_dir / "deploy" / environment
    deployment_report = deploy_dir / "deployment.report.json"
    _write(template, _runtime_template())

    runtime_kwargs = {
        "template_path": template,
        "output_path": runtime_env,
        "report_path": runtime_report,
        "environment": environment,
    }
    migration_kwargs = {
        "output_path": migrate_env,
        "report_path": migrate_report,
        "environment": environment,
    }
    deployment_kwargs = {
        "environment": environment,
        "runtime_env_file": runtime_env,
        "output_dir": deploy_dir,
    }
    if release_ready:
        runtime_kwargs.update(
            {
                "api_url": "https://api.runtime.example",
                "frontend_url": "https://app.runtime.example",
                "database_url": (
                    "postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres"
                ),
                "supabase_url": "https://example.supabase.co",
                "supabase_anon_key": "dashboard-anon-key",
                "supabase_jwt_secret": "x" * 40,
                "gcp_project_id": "valdrics-production",
                "gcp_region": "us-central1",
                "gcp_cloud_tasks_queue": "valdrics-managed-work",
                "gcp_cloud_tasks_invoker_service_account_email": (
                    "tasks@valdrics-production.iam.gserviceaccount.com"
                ),
                "gcp_cloud_run_service_name": "valdrics-api",
                "gcp_cloud_run_batch_job_name": "valdrics-batch",
                "gcp_internal_allowed_service_accounts": [
                    "tasks@valdrics-production.iam.gserviceaccount.com",
                    "scheduler@valdrics-production.iam.gserviceaccount.com",
                ],
                "llm_provider": "groq",
                "llm_api_key": "gsk_test_runtime_key",
                "paystack_secret_key": "sk_live_runtime_paystack_key",
                "paystack_public_key": "pk_live_runtime_paystack_key",
                "trusted_proxy_cidrs": ["203.0.113.10/32"],
            }
        )
        migration_kwargs.update(
            {
                "database_url": (
                    "postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres"
                ),
                "db_ssl_mode": "require",
            }
        )
        deployment_kwargs.update(
            {
                "release_tag": "2026.04.10",
                "api_promotion_ref": (
                    "us-central1-docker.pkg.dev/valdrics-prod/valdrics-runtime/"
                    "valdrics-api@sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
                ),
                "gcp_project_id": "valdrics-production",
                "gcp_region": "us-central1",
                "cloudflare_account_id": "cf-account-prod",
                "cloudflare_zone_id": "cf-zone-prod",
                "cloudflare_pages_project_name": "valdrics-dashboard",
                "cloudflare_pages_production_branch": "main",
                "supabase_organization_id": "supabase-org-prod",
                "supabase_project_name": "valdrics",
                "supabase_region": "us-east-1",
            }
        )

    generate_managed_runtime_env(**runtime_kwargs)
    generate_managed_migration_env(**migration_kwargs)
    generate_managed_deployment_artifacts(**deployment_kwargs)
    return runtime_report, migrate_report, deployment_report


def test_render_managed_deployment_handoff_renders_blocked_bundle_summary(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(
        tmp_path,
        environment="staging",
        release_ready=False,
    )
    output_path = tmp_path / ".runtime" / "deploy" / "staging" / "operator-handoff.md"

    rendered_path = render_managed_deployment_handoff(
        environment="staging",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
        output_path=output_path,
    )

    content = rendered_path.read_text(encoding="utf-8")
    assert "Managed Deployment Handoff: staging" in content
    assert "Runtime env validation: BLOCKED" in content
    assert "Current supported profile (`Google Cloud Run + Cloudflare Pages + Supabase`): BLOCKED" in content
    assert "Artifact Registry promotion contract: BLOCKED" in content
    assert "Terraform infrastructure contract: BLOCKED" in content
    assert "verify_managed_release_readiness.py" in content
    assert "verify_codebase_audit_report.py" in content
    assert "verify_dashboard_runtime_contract.py" in content
    assert "technology-value-admission-receipt.json" in content
    assert "render_managed_release_blocker_summary.py" in content
    assert "after both staging and production bundles are available" in content
    assert "--non-secret-deployment-bundle" in content
    assert "procurement/audit artifacts only" in content
    assert "capture_acceptance_evidence.py" in content
    assert "audit/compliance-pack" in content
    assert "run_public_frontend_quality_gate.py" in content
    assert "release-unified-platform.yml" in content
    assert "publish-artifact-registry-images.yml" in content
    assert "deploy-unified-platform.yml" in content
    assert "unified_platform_release.md" in content
    assert "`API_URL`" in content
    assert "`DATABASE_URL`" in content
    assert "`PUBLIC_API_URL`" in content
    assert "`release_tag`" in content
    assert "`gcp_project_id`" in content
    assert "`SUPABASE_URL`" in content


def test_render_managed_deployment_handoff_marks_unified_release_ready(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(
        tmp_path,
        environment="production",
        release_ready=True,
    )
    output_path = tmp_path / ".runtime" / "deploy" / "production" / "operator-handoff.md"

    render_managed_deployment_handoff(
        environment="production",
        runtime_report_path=runtime_report,
        migration_report_path=migrate_report,
        deployment_report_path=deployment_report,
        output_path=output_path,
    )

    content = output_path.read_text(encoding="utf-8")
    assert "Runtime env validation: READY" in content
    assert "Migration env validation: READY" in content
    assert "Current supported profile (`Google Cloud Run + Cloudflare Pages + Supabase`): READY" in content
    assert "Unified runtime deploy contract: READY" in content
    assert "Artifact Registry promotion contract: READY" in content
    assert "Terraform infrastructure contract: READY" in content
    assert "Technology Value admission receipt" in content
    assert (
        "verify_codebase_audit_report.py --report .runtime/production.audit.report.json"
        in content
    )
    assert (
        "refresh_codebase_audit_report.py --report .runtime/production.audit.report.json"
        in content
    )


def test_render_managed_deployment_handoff_rejects_incoherent_bundle(
    tmp_path: Path,
) -> None:
    runtime_report, migrate_report, deployment_report = _build_bundle(
        tmp_path,
        environment="production",
        release_ready=True,
    )
    payload = json.loads(deployment_report.read_text(encoding="utf-8"))
    payload["runtime_validation_blockers"] = ["DATABASE_URL"]
    deployment_report.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="cannot render managed deployment handoff"):
        render_managed_deployment_handoff(
            environment="production",
            runtime_report_path=runtime_report,
            migration_report_path=migrate_report,
            deployment_report_path=deployment_report,
            output_path=tmp_path / "handoff.md",
        )


def test_main_resolves_default_paths_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    runtime_report, migrate_report, deployment_report = _build_bundle(
        repo_root,
        environment="staging",
        release_ready=False,
    )

    monkeypatch.setattr(managed_handoff, "_repo_root", lambda: repo_root)
    monkeypatch.chdir(tmp_path)

    assert main(["--environment", "staging"]) == 0
    output_path = repo_root / ".runtime" / "deploy" / "staging" / "operator-handoff.md"
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert f"Runtime report: `{runtime_report}`" in content
    assert f"Migration report: `{migrate_report}`" in content
    assert f"Deployment report: `{deployment_report}`" in content
