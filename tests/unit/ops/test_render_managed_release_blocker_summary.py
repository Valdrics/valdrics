from __future__ import annotations

from pathlib import Path

import pytest

import scripts.render_managed_release_blocker_summary as blocker_summary
from scripts.generate_managed_deployment_artifacts import (
    generate_managed_deployment_artifacts,
)
from scripts.generate_managed_migration_env import generate_managed_migration_env
from scripts.generate_managed_runtime_env import generate_managed_runtime_env
from scripts.render_managed_release_blocker_summary import (
    main,
    render_managed_release_blocker_summary,
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
            "REDIS_URL=",
            "SUPABASE_URL=",
            "SUPABASE_ANON_KEY=",
            "SUPABASE_JWT_SECRET=",
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=",
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


def _build_bundle(tmp_path: Path, *, environment: str) -> tuple[Path, Path, Path]:
    template = tmp_path / ".env.example"
    runtime_dir = tmp_path / ".runtime"
    runtime_env = runtime_dir / f"{environment}.env"
    runtime_report = runtime_dir / f"{environment}.report.json"
    migrate_env = runtime_dir / f"{environment}.migrate.env"
    migrate_report = runtime_dir / f"{environment}.migrate.report.json"
    deploy_dir = runtime_dir / "deploy" / environment
    deployment_report = deploy_dir / "deployment.report.json"
    _write(template, _runtime_template())

    generate_managed_runtime_env(
        template_path=template,
        output_path=runtime_env,
        report_path=runtime_report,
        environment=environment,
    )
    generate_managed_migration_env(
        output_path=migrate_env,
        report_path=migrate_report,
        environment=environment,
    )
    generate_managed_deployment_artifacts(
        environment=environment,
        runtime_env_file=runtime_env,
        output_dir=deploy_dir,
    )
    return runtime_report, migrate_report, deployment_report


def test_render_managed_release_blocker_summary_renders_shared_and_env_specific_gaps(
    tmp_path: Path,
) -> None:
    staging_runtime, staging_migration, staging_deployment = _build_bundle(
        tmp_path, environment="staging"
    )
    production_runtime, production_migration, production_deployment = _build_bundle(
        tmp_path, environment="production"
    )
    output_path = tmp_path / ".runtime" / "deploy" / "managed-release-blockers.md"

    rendered_path = render_managed_release_blocker_summary(
        root=tmp_path,
        staging_runtime_report_path=staging_runtime,
        staging_migration_report_path=staging_migration,
        staging_deployment_report_path=staging_deployment,
        production_runtime_report_path=production_runtime,
        production_migration_report_path=production_migration,
        production_deployment_report_path=production_deployment,
        output_path=output_path,
    )

    content = rendered_path.read_text(encoding="utf-8")
    assert "Managed Release Blocker Summary" in content
    assert "## Shared Blockers" in content
    assert "## Staging-Only Blockers" in content
    assert "## Production-Only Blockers" in content
    assert "`AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN`" in content
    assert "`valdrics-aws-trust-principal-arn`" in content
    assert "`secret_rotation_lambda_arn`" in content
    assert "Comparison normalizes staging secret names" in content


def test_render_managed_release_blocker_summary_rejects_incoherent_bundle(
    tmp_path: Path,
) -> None:
    staging_runtime, staging_migration, staging_deployment = _build_bundle(
        tmp_path, environment="staging"
    )
    production_runtime, production_migration, production_deployment = _build_bundle(
        tmp_path, environment="production"
    )
    staging_payload = blocker_summary._load_json(staging_deployment)
    staging_payload["runtime_validation_blockers"] = ["DATABASE_URL"]
    staging_deployment.write_text(
        blocker_summary.json.dumps(staging_payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError, match="cannot render blocker summary for staging bundle"
    ):
        render_managed_release_blocker_summary(
            root=tmp_path,
            staging_runtime_report_path=staging_runtime,
            staging_migration_report_path=staging_migration,
            staging_deployment_report_path=staging_deployment,
            production_runtime_report_path=production_runtime,
            production_migration_report_path=production_migration,
            production_deployment_report_path=production_deployment,
            output_path=tmp_path / "summary.md",
        )


def test_main_resolves_default_paths_from_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = tmp_path / "repo"
    _build_bundle(repo_root, environment="staging")
    _build_bundle(repo_root, environment="production")

    monkeypatch.setattr(blocker_summary, "_repo_root", lambda: repo_root)
    monkeypatch.chdir(tmp_path)

    assert main([]) == 0
    output_path = repo_root / ".runtime" / "deploy" / "managed-release-blockers.md"
    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "### staging" in content
    assert "### production" in content
