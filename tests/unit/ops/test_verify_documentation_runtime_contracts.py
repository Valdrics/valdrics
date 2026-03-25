from __future__ import annotations

from pathlib import Path

import scripts.verify_documentation_runtime_contracts as documentation_runtime_contracts
from scripts.verify_documentation_runtime_contracts import (
    DocumentationContract,
    main,
    verify_contracts,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_verify_contracts_accepts_matching_docs(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs/architecture/overview.md",
        "boundary target\nHelm chart\nKoyeb-managed services\n",
    )
    _write(
        tmp_path / "docs/DEPLOYMENT.md",
        "Current supported production deployment profile\nKoyeb managed services with immutable image promotion\nFuture Scale Profile\n.github/workflows/publish-release-images.yml\ndigest-pinned `promotion_ref` values\nkoyeb-release.json\nkoyeb-dashboard-env.json\n",
    )
    _write(
        tmp_path / "docs/CAPACITY_PLAN.md",
        "current supported operating profile is Koyeb\nfuture scale path\nAWS RDS profile\nKoyeb-managed API, worker, and dashboard services\ndocs/architecture/tiering-2026.md\n",
    )
    _write(
        tmp_path / "docs/roadmap.md",
        "active planning document\nreports/roadmap/\nCurrent Focus\nbootstrap-only sqlite dev\nmanaged bundle verification\n",
    )
    _write(
        tmp_path / "docs/architecture/tiering-2026.md",
        "Permanent public proof lane\ndashboard/src/lib/pricing/publicPlans.ts\napp/shared/core/pricing.py\n",
    )
    _write(
        tmp_path / "docs/ROLLBACK_PLAN.md",
        "ENABLE_SCHEDULER=false\nbackup/restore\nKoyeb Rollback\nimmutable release artifacts\n",
    )
    _write(
        tmp_path / "docs/architecture/database_schema_overview.md",
        "One-step forward/rollback smoke\nbackup/restore is the primary rollback path\n",
    )
    _write(
        tmp_path / "docs/architecture/failover.md",
        "Cloudflare\nRDS\ndisaster-recovery-drill.yml\nregional-failover.yml\nscripts/run_regional_failover.py\nenable_multi_region_failover=true\nsecondary_db_endpoint\naws_role_to_assume\nGitHub OIDC\n/health\nsuccess=true\nregional_recovery_mode=automated_secondary_region_failover\n1200 seconds\nduration_seconds\nregional_recovery_mode=manual_restore_redeploy_reroute\nregional_recovery_rto_seconds=1200\nregional_recovery_rpo_contract=provider_backup_restore_external_to_repository\n",
    )
    _write(
        tmp_path / "docs/runbooks/disaster_recovery.md",
        "Current supported production: Koyeb-managed API, worker, and dashboard services\nAWS RDS\ndisaster-recovery-drill.yml\nregional-failover.yml\nscripts/run_regional_failover.py\nenable_multi_region_failover=true\nsecondary_db_endpoint\naws_role_to_assume\nGitHub OIDC\n/health\nsuccess=true\nregional_recovery_mode=automated_secondary_region_failover\n1200 seconds\nduration_seconds\nregional_recovery_mode=manual_restore_redeploy_reroute\nregional_recovery_rto_seconds=1200\nregional_recovery_rpo_contract=provider_backup_restore_external_to_repository\n",
    )
    _write(
        tmp_path / "docs/runbooks/incident_response.md",
        "Settings -> Notifications\nstrict SaaS mode\n",
    )
    _write(
        tmp_path / "docs/runbooks/production_env_checklist.md",
        "Python 3.12.x\n.python-version\nAPI_URL=https://api.example.com\nFRONTEND_URL=https://app.example.com\nSUPABASE_ANON_KEY=...\nSENTRY_DSN=https://...\nOTEL_EXPORTER_OTLP_ENDPOINT=https://collector:4317\nENFORCEMENT_APPROVAL_TOKEN_SECRET=...\nENFORCEMENT_EXPORT_SIGNING_SECRET=...\nINTERNAL_METRICS_AUTH_TOKEN=<32+ char secret>\nEXPOSE_API_DOCUMENTATION_PUBLICLY=false\ngenerate_managed_runtime_env.py\ngenerate_managed_migration_env.py\ngenerate_managed_deployment_artifacts.py\nverify_managed_deployment_bundle.py\npublish-release-images.yml\n--api-image-digest <sha256:...>\n--dashboard-image-digest <sha256:...>\nrun_public_frontend_quality_gate.py\ndeployment.report.json\nkoyeb-dashboard-env.json\nkoyeb-release.json\n--env-file .runtime/production.env\n--env-file .runtime/production.migrate.env\nset -a && source .runtime/production.migrate.env && uv run alembic upgrade head\n",
    )
    _write(
        tmp_path / "docs/runbooks/koyeb_release_promotion.md",
        "publish-release-images.yml\nghcr-release.env\npromotion_ref\nGHCR_NAMESPACE=valdrics\n",
    )
    _write(
        tmp_path / "docs/integrations/workflow_automation.md",
        "env channel routing (`SLACK_CHANNEL_ID`) is blocked\nself-host or break-glass-only paths\n",
    )
    _write(
        tmp_path / "docs/SOC2_CONTROLS.md",
        "CODEOWNERS\n`app/shared/core/logging.py`\n`docs/FULL_CODEBASE_AUDIT.md`\n",
    )
    _write(
        tmp_path / "docs/policies/data_retention.md",
        "Audit logs | Automated retention purge\nAUDIT_LOG_RETENTION_DAYS\nresource_type=audit_logs_retention\n",
    )
    _write(
        tmp_path / "docs/runbooks/enforcement_preprovision_integrations.md",
        "failurePolicy: Fail\n`failurePolicy: Fail` requires API HA\nKeep webhook timeout low (`<= 2s`)\n",
    )
    _write(
        tmp_path / "docs/runbooks/partition_maintenance.md",
        "internal scheduler\nX-Internal-Job-Secret\nadvisory lock\n",
    )
    _write(
        tmp_path / "docs/ops/cloudflare_go_live_checklist_2026-03-02.md",
        "historical preview/reference artifact\nnot part of the supported production deployment contract today\ndocs/DEPLOYMENT.md\n",
    )
    _write(
        tmp_path / "DEPLOYMENT.md",
        "Python 3.12.x\nuv sync --python 3.12\n/health/live\n/_internal/metrics\n--from-literal=DATABASE_URL=\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert errors == []


def test_verify_contracts_reports_missing_and_forbidden_phrases(tmp_path: Path) -> None:
    for contract in (
        DocumentationContract(
            path="docs/architecture/overview.md",
            required_phrases=("boundary target",),
            forbidden_phrases=("Zero external dependencies",),
        ),
        DocumentationContract(
            path="docs/DEPLOYMENT.md",
            required_phrases=("Supported production deployment profile",),
        ),
        DocumentationContract(
            path="docs/CAPACITY_PLAN.md",
            required_phrases=("AWS RDS profile",),
        ),
        DocumentationContract(
            path="docs/roadmap.md",
            required_phrases=("Current Focus",),
        ),
        DocumentationContract(
            path="docs/architecture/tiering-2026.md",
            required_phrases=("dashboard/src/lib/pricing/publicPlans.ts",),
        ),
        DocumentationContract(
            path="docs/ROLLBACK_PLAN.md",
            required_phrases=("ENABLE_SCHEDULER=false",),
        ),
        DocumentationContract(
            path="docs/architecture/database_schema_overview.md",
            required_phrases=("backup/restore is the primary rollback path",),
        ),
        DocumentationContract(
            path="docs/architecture/failover.md",
            required_phrases=("Cloudflare",),
        ),
        DocumentationContract(
            path="docs/runbooks/disaster_recovery.md",
            required_phrases=("AWS RDS",),
        ),
        DocumentationContract(
            path="docs/runbooks/incident_response.md",
            required_phrases=("Settings -> Notifications",),
            forbidden_phrases=("specified in `SLACK_CHANNEL_ID`",),
        ),
        DocumentationContract(
            path="docs/runbooks/production_env_checklist.md",
            required_phrases=(
                "Python 3.12.x",
                ".python-version",
                "OTEL_EXPORTER_OTLP_ENDPOINT=https://",
                "ENFORCEMENT_APPROVAL_TOKEN_SECRET=...",
                "ENFORCEMENT_EXPORT_SIGNING_SECRET=...",
                "generate_managed_migration_env.py",
                "generate_managed_deployment_artifacts.py",
                "verify_managed_deployment_bundle.py",
                "publish-release-images.yml",
                "--api-image-digest <sha256:...>",
                "--dashboard-image-digest <sha256:...>",
                "run_public_frontend_quality_gate.py",
            ),
        ),
        DocumentationContract(
            path="docs/runbooks/koyeb_release_promotion.md",
            required_phrases=(
                "publish-release-images.yml",
                "ghcr-release.env",
                "promotion_ref",
                "GHCR_NAMESPACE=valdrics",
            ),
        ),
        DocumentationContract(
            path="docs/integrations/workflow_automation.md",
            required_phrases=("self-host or break-glass-only paths",),
        ),
        DocumentationContract(
            path="docs/SOC2_CONTROLS.md",
            required_phrases=("CODEOWNERS",),
        ),
        DocumentationContract(
            path="docs/policies/data_retention.md",
            required_phrases=("AUDIT_LOG_RETENTION_DAYS",),
        ),
        DocumentationContract(
            path="docs/runbooks/enforcement_preprovision_integrations.md",
            required_phrases=("failurePolicy: Fail",),
        ),
        DocumentationContract(
            path="docs/runbooks/partition_maintenance.md",
            required_phrases=("internal scheduler",),
            forbidden_phrases=("pg_cron",),
        ),
        DocumentationContract(
            path="docs/ops/cloudflare_go_live_checklist_2026-03-02.md",
            required_phrases=("historical preview/reference artifact",),
        ),
        DocumentationContract(
            path="DEPLOYMENT.md",
            required_phrases=("Python 3.12.x", "/health/live"),
        ),
    ):
        _write(tmp_path / contract.path, "placeholder\n")

    _write(
        tmp_path / "docs/architecture/overview.md",
        "Zero external dependencies\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert "docs/architecture/overview.md: missing required phrase 'boundary target'" in errors
    assert (
        "docs/architecture/overview.md: forbidden phrase present 'Zero external dependencies'"
        in errors
    )


def test_verify_contracts_rejects_missing_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing-root"
    assert verify_contracts(root=missing_root) == [f"root not found: {missing_root}"]


def test_verify_contracts_rejects_non_directory_root(tmp_path: Path) -> None:
    root_file = tmp_path / "root.txt"
    root_file.write_text("not-a-directory\n", encoding="utf-8")
    assert verify_contracts(root=root_file) == [f"root must be a directory: {root_file}"]


def test_verify_contracts_rejects_directory_target(tmp_path: Path) -> None:
    target_dir = tmp_path / "docs" / "architecture" / "overview.md"
    target_dir.mkdir(parents=True, exist_ok=True)
    errors = verify_contracts(root=tmp_path)
    assert "docs/architecture/overview.md: target must be a file" in errors


def test_main_accepts_root_override(monkeypatch) -> None:
    seen: list[Path] = []

    def _fake_verify_contracts(*, root: Path) -> list[str]:
        seen.append(root)
        return []

    monkeypatch.setattr(documentation_runtime_contracts, "verify_contracts", _fake_verify_contracts)

    assert main(["--root", "docs"]) == 0
    assert seen == [documentation_runtime_contracts.DEFAULT_ROOT / "docs"]


def test_main_rejects_relative_root_escape(capsys) -> None:
    assert main(["--root", "../outside"]) == 2
    assert "must stay within repo root when relative" in capsys.readouterr().out
