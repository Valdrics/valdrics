#!/usr/bin/env python3
"""Fail fast when checked-in runtime/architecture docs drift from repo reality."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from scripts.env_generation_common import repo_root_for, resolve_cli_path_from_root


@dataclass(frozen=True)
class DocumentationContract:
    path: str
    required_phrases: tuple[str, ...]
    forbidden_phrases: tuple[str, ...] = ()


DEFAULT_ROOT = repo_root_for(__file__)
DOCUMENTATION_CONTRACTS: tuple[DocumentationContract, ...] = (
    DocumentationContract(
        path="README.md",
        required_phrases=(
            "Valdrics",
            "Optimize Cloud Value, Not Just Cost",
            "Python 3.12",
            "Supported Managed Platform",
            "Archived Future-Scale Reference",
            "Local development only:",
        ),
        forbidden_phrases=(
            "11 zombie-detection plugins",
            "11 zombie detection plugins",
            "Unified Platform Migration Target",
            "Future Scale Path",
        ),
    ),
    DocumentationContract(
        path="docs/FULL_CODEBASE_AUDIT.md",
        required_phrases=(
            "time-bound snapshot",
            "first-party Python, TypeScript, and Svelte source",
            "live verification scripts remain the source of truth",
            "mixed secret model",
            "RLS enforcement plus documented exemptions",
        ),
        forbidden_phrases=(
            "Entire repository (every directory, every file type, all source code)",
            "5358 tests collected",
            "No TODO/FIXME/XXX/HACK in app",
            "No issues.",
        ),
    ),
    DocumentationContract(
        path="docs/architecture/overview.md",
        required_phrases=(
            "boundary target",
            "Google Cloud Run",
            "Cloudflare Pages",
            "Supabase",
            "Artifact Registry",
        ),
        forbidden_phrases=(
            "Zero external dependencies",
            "`k8s/`",
            "local cache infrastructure",
            "optional cache service",
        ),
    ),
    DocumentationContract(
        path="docs/DEPLOYMENT.md",
        required_phrases=(
            "Current supported production deployment profile",
            "Google Cloud Run + Cloudflare Pages + Supabase",
            ".github/workflows/release-unified-platform.yml",
            ".github/workflows/publish-artifact-registry-images.yml",
            ".github/workflows/deploy-unified-platform.yml",
            "verify_dashboard_runtime_contract.py",
            "render_managed_release_blocker_summary.py",
            "Artifact Registry",
            "artifact-registry-release.json",
            "cloudflare-pages-env.json",
            "unified-platform-manifest.json",
            "operator-handoff.md",
            "managed-release-blockers.md",
            "managed-release-blocker-summary-<release-tag>",
            "verify_codebase_audit_report.py",
            "Cloudflare WAF rate limiting rules",
            "GCP external HTTPS load balancer",
            "PUBLIC_API_RATE_LIMITING_BACKEND=cloudflare",
            "Cloud Run custom audiences",
        ),
        forbidden_phrases=(
            "Vercel",
            "Cloudflare Pages + Koyeb",
            "local cache infrastructure",
            "optional cache service",
            "Helm/Terraform material for future scale research",
            "OBSERVABILITY_BACKEND=otlp",
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "SENTRY_DSN",
        ),
    ),
    DocumentationContract(
        path="docs/CAPACITY_PLAN.md",
        required_phrases=(
            "current supported operating profile is the unified platform",
            "there is no parallel capacity track",
            "Google Cloud Run",
            "Cloud Tasks",
            "Cloud Run Jobs",
            "Cloudflare Pages",
            "Supabase",
        ),
        forbidden_phrases=("future scale path",),
    ),
    DocumentationContract(
        path="docs/ops/README.md",
        required_phrases=(
            "active operational material only",
            "Persistent operational contracts should use undated canonical paths.",
            "docs/ops/enforcement_release_gate_contract.json",
            "docs/ops/key-rotation-drill-2026-02-27.md",
        ),
    ),
    DocumentationContract(
        path="docs/ops/acceptance_evidence_capture.md",
        required_phrases=(
            "not the managed deployment release path",
            "docs/runbooks/unified_platform_release.md",
            "managed-deployment-bundle-<environment>-<release-tag>",
        ),
        forbidden_phrases=(
            "rollout/procurement sign-off",
            "production sign-off",
            "staging/prod sign-off",
        ),
    ),
    DocumentationContract(
        path="docs/ops/enforcement_release_gate_contract.json",
        required_phrases=(
            "post_closure_sanity",
            "required_snapshot_tokens",
            "forbidden_snapshot_tokens",
            "pkg015_launch_gate",
            "required_item_status",
            "required_runtime_gated_features",
        ),
    ),
    DocumentationContract(
        path="docs/product/external_feedback_validation.md",
        required_phrases=(
            "Status: Supporting evidence",
            "PLAN.md",
            "not the canonical shipping plan",
            "phase tracker",
            "ship-gate source of truth",
        ),
    ),
    DocumentationContract(
        path="docs/compliance/compliance_pack.md",
        required_phrases=(
            "supplemental evidence",
            "docs/runbooks/unified_platform_release.md",
            "managed-deployment-bundle-<environment>-<release-tag>",
        ),
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
        path="docs/runbooks/month_end_close.md",
        required_phrases=(
            "finance and audit review",
            "not a production cutover packet",
            "docs/runbooks/unified_platform_release.md",
            "supplemental finance evidence",
        ),
        forbidden_phrases=("finance/procurement sign-off",),
    ),
    DocumentationContract(
        path="docs/ROLLBACK_PLAN.md",
        required_phrases=(
            "backup/restore",
            "Cloud Run Rollback",
            "Artifact Registry",
            "Cloud Scheduler job",
            "Cloud Run custom audiences",
        ),
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
            "Supabase",
            "Google Cloud Run",
            "Artifact Registry",
            "/health",
            "/health/live",
            "regional_recovery_mode=manual_restore_redeploy_reroute",
        ),
        forbidden_phrases=(
            "Route 53",
            "aws_role_to_assume",
            "secondary_db_endpoint",
            "regional-failover",
            "regional_failover",
            "automated_secondary_region_failover",
            "FAILOVER_AWS_ROLE_TO_ASSUME",
            "secondary_db_instance_id",
        ),
    ),
    DocumentationContract(
        path="docs/runbooks/disaster_recovery.md",
        required_phrases=(
            "Google Cloud Run",
            "Cloud Run Jobs",
            "Cloudflare Pages",
            "Supabase",
            "Artifact Registry",
            ".github/workflows/deploy-unified-platform.yml",
            "/health",
            "/health/live",
            "regional_recovery_mode=manual_restore_redeploy_reroute",
        ),
        forbidden_phrases=(
            "aws_role_to_assume",
            "secondary_db_endpoint",
            "regional-failover",
            "regional_failover",
            "automated_secondary_region_failover",
            "FAILOVER_AWS_ROLE_TO_ASSUME",
            "secondary_db_instance_id",
        ),
    ),
    DocumentationContract(
        path="docs/runbooks/incident_response.md",
        required_phrases=(
            "Settings -> Notifications",
            "strict SaaS mode",
            "Cloudflare WAF rate limiting rules are healthy",
            "application-level throttling fallbacks are not tripping unexpectedly",
        ),
        forbidden_phrases=(
            "specified in `SLACK_CHANNEL_ID`",
            "optional cache backends are either healthy or falling back cleanly",
            "explicit break-glass shared cache backend",
        ),
    ),
    DocumentationContract(
        path="docs/runbooks/secret_rotation_emergency.md",
        required_phrases=(
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET",
            "PAYSTACK_SECRET_KEY",
            "Google Secret Manager or other provider-managed secret store",
        ),
        forbidden_phrases=("optional cache provider",),
    ),
    DocumentationContract(
        path="docs/runbooks/production_env_checklist.md",
        required_phrases=(
            "Python 3.12.x",
            ".python-version",
            "API_URL=https://",
            "FRONTEND_URL=https://",
            "PUBLIC_API_RATE_LIMITING_BACKEND=cloudflare",
            "RATELIMIT_ENABLED=false",
            "SUPABASE_ANON_KEY=...",
            "PLATFORM_RUNTIME_PROFILE=gcp",
            "OBSERVABILITY_BACKEND=gcp",
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET=...",
            "PAYSTACK_SECRET_KEY=sk_live_...",
            "INTERNAL_METRICS_AUTH_TOKEN=<32+ char secret>",
            "EXPOSE_API_DOCUMENTATION_PUBLICLY=false",
            "CLOUDFLARE_ZONE_ID",
            "generate_managed_runtime_env.py",
            "generate_managed_migration_env.py",
            "generate_managed_deployment_artifacts.py",
            "verify_managed_deployment_bundle.py",
            "verify_dashboard_runtime_contract.py",
            "render_managed_release_blocker_summary.py",
            "release-unified-platform.yml",
            "publish-artifact-registry-images.yml",
            "deploy-unified-platform.yml",
            "--api-promotion-ref <repo@sha256:...>",
            "--batch-promotion-ref <repo@sha256:...>",
            "run_public_frontend_quality_gate.py",
            "deployment.report.json",
            "cloudflare-pages-env.json",
            "artifact-registry-release.json",
            "unified-platform-manifest.json",
            "operator-handoff.md",
            "managed-release-blockers.md",
            "managed-release-blocker-summary-<release-tag>",
            "make render-managed-release-blockers",
            "Cloud Run custom audiences",
            "verify_codebase_audit_report.py",
            "--env-file .runtime/production.env",
            "--env-file .runtime/production.migrate.env",
            "reusable deploy workflow migration step succeeds from `.runtime/production.migrate.env`",
        ),
        forbidden_phrases=(
            "Optional but recommended: `SENTRY_DSN",
            "OBSERVABILITY_BACKEND=otlp",
            "OTEL_EXPORTER_OTLP_ENDPOINT",
            "SENTRY_DSN",
        ),
    ),
    DocumentationContract(
        path="docs/runbooks/unified_platform_release.md",
        required_phrases=(
            "Google Cloud Run",
            "Cloud Tasks",
            "Cloud Scheduler",
            "Cloud Run Jobs",
            "Artifact Registry",
            "Cloudflare Pages",
            "Supabase",
            "Cloudflare Pages/DNS/WAF",
            "GCP runtime + API load balancer",
            "release-unified-platform.yml",
            "publish-artifact-registry-images.yml",
            "deploy-unified-platform.yml",
            "managed-release-blocker-summary-<release-tag>",
            "promote_production=true",
            "REPLACE_WITH_REAL_STAGING_FRONTEND",
            "make render-managed-release-blockers NON_SECRET_BUNDLE=true",
            "supplemental procurement/audit artifacts only",
            "managed-deployment-bundle-<environment>-<release-tag>",
            "managed_cutover_operator_packet.md",
            "secret-classified keys such as `DATABASE_URL`",
        ),
    ),
    DocumentationContract(
        path="docs/runbooks/managed_cutover_operator_packet.md",
        required_phrases=(
            "RUNTIME_PLAIN_ENV_JSON",
            "RUNTIME_SECRET_ENV_JSON",
            "artifact-registry-release-<release-tag>",
            "managed-deployment-bundle-staging-<release-tag>",
            "managed-release-blocker-summary-<release-tag>",
            "Settings -> Environments",
            "Workload Identity Federation",
            "Workers & Pages",
            "Supabase",
            "\"DATABASE_URL\": \"postgresql://...\"",
        ),
        forbidden_phrases=(
            "\"DATABASE_URL\": \"postgres://...\"",
        ),
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
            "`docs/runbooks/disaster_recovery.md`",
            "`docs/ROLLBACK_PLAN.md`",
            "`docs/FULL_CODEBASE_AUDIT.md`",
        ),
        forbidden_phrases=(
            "Infrastructure: Helm chart",
            "`terraform/modules/db/main.tf`",
            "AWS RDS backup retention and HA posture",
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
            "Supabase-managed backups and point-in-time recovery",
            "Provider-managed retention outside repository automation",
        ),
        forbidden_phrases=(
            "AWS RDS backups (Terraform profile)",
            "`terraform/modules/db/main.tf`",
        ),
    ),
    DocumentationContract(
        path="docs/runbooks/enforcement_preprovision_integrations.md",
        required_phrases=(
            "failurePolicy: Fail",
            "`failurePolicy: Fail` requires API HA",
            "Archived self-managed Helm reference",
            "Keep webhook timeout low (`<= 2s`)",
        ),
        forbidden_phrases=("Helm deployment profile (recommended)",),
    ),
    DocumentationContract(
        path="docs/ops/benchmark_alignment_profiles.md",
        required_phrases=(
            "Kubernetes AdmissionReview guidance profile",
            "Archived self-managed Helm reference remains outside the supported deployment contract.",
            "tests/unit/enforcement/enforcement_api_cases_part01.py",
            "tests/unit/enforcement/enforcement_api_cases_part02.py",
            "test_enforcement_endpoint_wrappers_cover_preflight_and_k8s_review_branches",
        ),
        forbidden_phrases=(
            "Runtime/Helm contract in repository",
            "tests/unit/ops/",
        ),
    ),
    DocumentationContract(
        path="docs/runbooks/partition_maintenance.md",
        required_phrases=(
            "Cloud Scheduler",
            "Google-signed identity",
            "advisory lock",
        ),
        forbidden_phrases=("pg_cron", "no auth", "X-Internal-Job-Secret"),
    ),
)


def verify_contracts(*, root: Path) -> list[str]:
    if not root.exists():
        return [f"root not found: {root}"]
    if not root.is_dir():
        return [f"root must be a directory: {root}"]

    errors: list[str] = []
    for contract in DOCUMENTATION_CONTRACTS:
        target = root / contract.path
        if not target.exists():
            errors.append(f"missing file: {contract.path}")
            continue
        if not target.is_file():
            errors.append(f"{contract.path}: target must be a file")
            continue

        text = target.read_text(encoding="utf-8")
        for phrase in contract.required_phrases:
            if phrase not in text:
                errors.append(f"{contract.path}: missing required phrase {phrase!r}")
        for phrase in contract.forbidden_phrases:
            if phrase in text:
                errors.append(f"{contract.path}: forbidden phrase present {phrase!r}")
    return errors


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify runtime and architecture docs against checked-in contracts."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="Repository root to verify. Relative paths are resolved from the repo root.",
    )
    return parser


def _resolve_root(path: Path) -> Path:
    return resolve_cli_path_from_root(DEFAULT_ROOT, path, field_name="root")


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        root = _resolve_root(Path(str(args.root)))
    except ValueError as exc:
        print(str(exc))
        return 2

    errors = verify_contracts(root=root)
    if errors:
        print("Documentation runtime contract violations detected:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("Documentation runtime contract verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
