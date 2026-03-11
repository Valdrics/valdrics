#!/usr/bin/env python3
"""Fail fast when checked-in runtime/architecture docs drift from repo reality."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class DocumentationContract:
    path: str
    required_phrases: tuple[str, ...]
    forbidden_phrases: tuple[str, ...] = ()


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTATION_CONTRACTS: tuple[DocumentationContract, ...] = (
    DocumentationContract(
        path="docs/architecture/overview.md",
        required_phrases=(
            "boundary target",
            "Helm chart",
            "reference managed-platform surface",
        ),
        forbidden_phrases=("Zero external dependencies", "`k8s/`"),
    ),
    DocumentationContract(
        path="docs/DEPLOYMENT.md",
        required_phrases=(
            "Supported production deployment profile",
            "Helm + Terraform (AWS/EKS)",
            "Reference Managed-Platform Manifests",
            "koyeb-worker.yaml",
        ),
        forbidden_phrases=("Vercel", "two supported deployment profiles"),
    ),
    DocumentationContract(
        path="docs/CAPACITY_PLAN.md",
        required_phrases=(
            "sole supported production scale path",
            "managed-platform preview/reference surface",
            "AWS RDS profile",
            "koyeb-worker.yaml",
            "docs/architecture/tiering-2026.md",
        ),
    ),
    DocumentationContract(
        path="docs/roadmap.md",
        required_phrases=(
            "active planning document",
            "reports/roadmap/",
            "Current Focus",
            "bootstrap-only sqlite dev",
            "managed bundle verification",
        ),
        forbidden_phrases=("Latest Sprint Shipped", "Sprint Status (Current)"),
    ),
    DocumentationContract(
        path="docs/architecture/tiering-2026.md",
        required_phrases=(
            "Permanent public proof lane",
            "dashboard/src/lib/pricing/publicPlans.ts",
            "app/shared/core/pricing.py",
        ),
    ),
    DocumentationContract(
        path="docs/ROLLBACK_PLAN.md",
        required_phrases=("ENABLE_SCHEDULER=false", "backup/restore"),
        forbidden_phrases=("Koyeb/Vercel", "alembic downgrade [VERSION_ID]"),
    ),
    DocumentationContract(
        path="docs/architecture/database_schema_overview.md",
        required_phrases=(
            "One-step forward/rollback smoke",
            "backup/restore is the primary rollback path",
        ),
    ),
    DocumentationContract(
        path="docs/architecture/failover.md",
        required_phrases=(
            "Cloudflare",
            "RDS",
            "disaster-recovery-drill.yml",
            "regional-failover.yml",
            "scripts/run_regional_failover.py",
            "enable_multi_region_failover=true",
            "secondary_db_endpoint",
            "aws_role_to_assume",
            "GitHub OIDC",
            "/health",
            "success=true",
            "regional_recovery_mode=automated_secondary_region_failover",
            "1200 seconds",
            "duration_seconds",
            "regional_recovery_mode=manual_restore_redeploy_reroute",
            "regional_recovery_rto_seconds=1200",
            "regional_recovery_rpo_contract=provider_backup_restore_external_to_repository",
        ),
        forbidden_phrases=("Route 53",),
    ),
    DocumentationContract(
        path="docs/runbooks/disaster_recovery.md",
        required_phrases=(
            "AWS RDS",
            "Cloudflare",
            "disaster-recovery-drill.yml",
            "regional-failover.yml",
            "scripts/run_regional_failover.py",
            "enable_multi_region_failover=true",
            "secondary_db_endpoint",
            "aws_role_to_assume",
            "GitHub OIDC",
            "/health",
            "success=true",
            "regional_recovery_mode=automated_secondary_region_failover",
            "koyeb-worker.yaml",
            "1200 seconds",
            "duration_seconds",
            "regional_recovery_mode=manual_restore_redeploy_reroute",
            "regional_recovery_rto_seconds=1200",
            "regional_recovery_rpo_contract=provider_backup_restore_external_to_repository",
        ),
        forbidden_phrases=("Supabase",),
    ),
    DocumentationContract(
        path="docs/runbooks/incident_response.md",
        required_phrases=(
            "Settings -> Notifications",
            "strict SaaS mode",
        ),
        forbidden_phrases=("specified in `SLACK_CHANNEL_ID`",),
    ),
    DocumentationContract(
        path="docs/runbooks/production_env_checklist.md",
        required_phrases=(
            "API_URL=https://",
            "FRONTEND_URL=https://",
            "SENTRY_DSN=https://",
            "OTEL_EXPORTER_OTLP_ENDPOINT=https://",
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET=...",
            "ENFORCEMENT_EXPORT_SIGNING_SECRET=...",
            "INTERNAL_METRICS_AUTH_TOKEN=<32+ char secret>",
            "EXPOSE_API_DOCUMENTATION_PUBLICLY=false",
            "generate_managed_runtime_env.py",
            "generate_managed_migration_env.py",
            "generate_managed_deployment_artifacts.py",
            "verify_managed_deployment_bundle.py",
            "run_public_frontend_quality_gate.py",
            "deployment.report.json",
            "--env-file .runtime/production.env",
            "--env-file .runtime/production.migrate.env",
            "set -a && source .runtime/production.migrate.env && uv run alembic upgrade head",
        ),
        forbidden_phrases=("Optional but recommended: `SENTRY_DSN",),
    ),
    DocumentationContract(
        path="docs/integrations/workflow_automation.md",
        required_phrases=(
            "env channel routing (`SLACK_CHANNEL_ID`) is blocked",
            "self-host or break-glass-only paths",
        ),
    ),
    DocumentationContract(
        path="docs/SOC2_CONTROLS.md",
        required_phrases=(
            "CODEOWNERS",
            "`app/shared/core/logging.py`",
            "`docs/FULL_CODEBASE_AUDIT.md`",
        ),
        forbidden_phrases=(
            "`app/core/logging.py`",
            "`docs/DR_RUNBOOK.md`",
            "`technical_due_diligence.md`",
        ),
    ),
    DocumentationContract(
        path="docs/policies/data_retention.md",
        required_phrases=(
            "Audit logs | Automated retention purge",
            "AUDIT_LOG_RETENTION_DAYS",
            "resource_type=audit_logs_retention",
        ),
    ),
    DocumentationContract(
        path="docs/runbooks/enforcement_preprovision_integrations.md",
        required_phrases=(
            "failurePolicy: Fail",
            "`failurePolicy: Fail` requires API HA",
            "Keep webhook timeout low (`<= 2s`)",
        ),
    ),
    DocumentationContract(
        path="docs/runbooks/partition_maintenance.md",
        required_phrases=(
            "internal scheduler",
            "X-Internal-Job-Secret",
            "advisory lock",
        ),
        forbidden_phrases=("pg_cron", "no auth"),
    ),
    DocumentationContract(
        path="docs/ops/cloudflare_go_live_checklist_2026-03-02.md",
        required_phrases=(
            "historical preview/reference artifact",
            "not part of the supported production deployment contract today",
            "docs/DEPLOYMENT.md",
        ),
    ),
    DocumentationContract(
        path="DEPLOYMENT.md",
        required_phrases=(
            "/health/live",
            "/_internal/metrics",
            "--from-literal=DATABASE_URL=",
        ),
    ),
)


def verify_contracts(*, root: Path) -> list[str]:
    errors: list[str] = []
    for contract in DOCUMENTATION_CONTRACTS:
        target = root / contract.path
        if not target.exists():
            errors.append(f"missing file: {contract.path}")
            continue

        text = target.read_text(encoding="utf-8")
        for phrase in contract.required_phrases:
            if phrase not in text:
                errors.append(f"{contract.path}: missing required phrase {phrase!r}")
        for phrase in contract.forbidden_phrases:
            if phrase in text:
                errors.append(f"{contract.path}: forbidden phrase present {phrase!r}")
    return errors


def main() -> int:
    errors = verify_contracts(root=DEFAULT_ROOT)
    if errors:
        print("Documentation runtime contract violations detected:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Documentation runtime contract verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
