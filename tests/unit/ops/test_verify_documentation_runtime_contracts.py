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
        tmp_path / "PLAN.md",
        "Last reviewed: 2026-05-21\n"
        "2026.05.19-paystack-pending-8ef0b893\n"
        "26131799197\n"
        "docs/evidence/phase1-unified-release-closure.md\n"
        "no release-blocking engineering blocker remains\n"
        "PAYSTACK_ACTIVATION_PENDING=false\n",
    )
    _write(
        tmp_path / "README.md",
        "Valdrics\nOptimize Cloud Value, Not Just Cost\nPython 3.12\nSupported Managed Platform\nArchived Future-Scale Reference\nLocal development only:\n",
    )
    _write(
        tmp_path / "docs/FULL_CODEBASE_AUDIT.md",
        "time-bound snapshot\nfirst-party Python, TypeScript, and Svelte source\nlive verification scripts remain the source of truth\nmixed secret model\nRLS enforcement plus documented exemptions\n",
    )
    _write(
        tmp_path / "docs/architecture/overview.md",
        "boundary target\nGoogle Cloud Run\nCloudflare Pages\nSupabase\nArtifact Registry\n",
    )
    _write(
        tmp_path / "docs/DEPLOYMENT.md",
        "Current supported production deployment profile\nGoogle Cloud Run + Cloudflare Pages + Supabase\n.github/workflows/release-unified-platform.yml\n.github/workflows/publish-artifact-registry-images.yml\n.github/workflows/deploy-unified-platform.yml\nverify_codebase_audit_report.py\nverify_dashboard_runtime_contract.py\nverify_managed_release_readiness.py\nrender_managed_release_blocker_summary.py\nArtifact Registry\nartifact-registry-release.json\ncloudflare-pages-env.json\nunified-platform-manifest.json\ndeployment.report.json\noperator-handoff.md\nmanaged-release-blockers.md\nmanaged-release-blocker-summary-<release-tag>\nnon-secret deployment evidence bundle\nCloudflare WAF rate limiting rules\nGCP external HTTPS load balancer\nPUBLIC_API_RATE_LIMITING_BACKEND=cloudflare\nCloud Run custom audiences\nPAYSTACK_ACTIVATION_PENDING=true\n",
    )
    _write(
        tmp_path / "docs/CAPACITY_PLAN.md",
        "current supported operating profile is the unified platform\nthere is no parallel capacity track\nGoogle Cloud Run\nCloud Tasks\nCloud Run Jobs\nCloudflare Pages\nSupabase\n",
    )
    _write(
        tmp_path / "docs/ops/README.md",
        "active operational material only\n"
        "Persistent operational contracts should use undated canonical paths.\n"
        "docs/ops/enforcement_release_gate_contract.json\n"
        "docs/ops/key-rotation-drill-2026-02-27.md\n",
    )
    _write(
        tmp_path / "docs/ops/acceptance_evidence_capture.md",
        "not the managed deployment release path\n"
        "docs/runbooks/unified_platform_release.md\n"
        "managed-deployment-bundle-<environment>-<release-tag>\n",
    )
    _write(
        tmp_path / "docs/ops/enforcement_release_gate_contract.json",
        "{\n"
        '  "post_closure_sanity": {\n'
        '    "required_snapshot_tokens": ["CI-EVID-001"],\n'
        '    "forbidden_snapshot_tokens": ["legacy-helm-token"]\n'
        "  },\n"
        '  "pkg015_launch_gate": {\n'
        '    "required_item_status": {"PKG-015": "DONE"},\n'
        '    "required_runtime_gated_features": ["auto_remediation"]\n'
        "  }\n"
        "}\n",
    )
    _write(
        tmp_path / "docs/product/external_feedback_validation.md",
        "Status: Supporting evidence\nPLAN.md\nnot the canonical shipping plan\n"
        "phase tracker\nship-gate source of truth\n",
    )
    _write(
        tmp_path / "docs/compliance/compliance_pack.md",
        "supplemental evidence\ndocs/runbooks/unified_platform_release.md\n"
        "managed-deployment-bundle-<environment>-<release-tag>\n",
    )
    _write(
        tmp_path / "docs/architecture/tiering-2026.md",
        "Permanent public proof lane\ndashboard/src/lib/pricing/publicPlans.ts\napp/shared/core/pricing.py\n",
    )
    _write(
        tmp_path / "docs/runbooks/month_end_close.md",
        "finance and audit review\nnot a production cutover packet\n"
        "docs/runbooks/unified_platform_release.md\nsupplemental finance evidence\n",
    )
    _write(
        tmp_path / "docs/ROLLBACK_PLAN.md",
        "backup/restore\nCloud Run Rollback\nArtifact Registry\nCloud Scheduler job\nCloud Run custom audiences\n",
    )
    _write(
        tmp_path / "docs/architecture/database_schema_overview.md",
        "One-step forward/rollback smoke\nbackup/restore is the primary rollback path\n",
    )
    _write(
        tmp_path / "docs/architecture/failover.md",
        "Cloudflare\nSupabase\nGoogle Cloud Run\nArtifact Registry\n/health\n/health/live\nregional_recovery_mode=manual_restore_redeploy_reroute\n",
    )
    _write(
        tmp_path / "docs/runbooks/disaster_recovery.md",
        "Google Cloud Run\nCloud Run Jobs\nCloudflare Pages\nSupabase\nArtifact Registry\n.github/workflows/deploy-unified-platform.yml\n/health\n/health/live\nregional_recovery_mode=manual_restore_redeploy_reroute\n",
    )
    _write(
        tmp_path / "docs/runbooks/incident_response.md",
        "Settings -> Notifications\nstrict SaaS mode\nCloudflare WAF rate limiting rules are healthy\napplication-level throttling fallbacks are not tripping unexpectedly\n",
    )
    _write(
        tmp_path / "docs/runbooks/secret_rotation_emergency.md",
        "ENFORCEMENT_APPROVAL_TOKEN_SECRET\nPAYSTACK_SECRET_KEY=sk_live_...\nGoogle Secret Manager or other provider-managed secret store\n",
    )
    _write(
        tmp_path / "docs/runbooks/production_env_checklist.md",
        "Python 3.12.x\n.python-version\nAPI_URL=https://api.example.com\nFRONTEND_URL=https://app.example.com\nPUBLIC_API_RATE_LIMITING_BACKEND=cloudflare\nRATELIMIT_ENABLED=false\nSUPABASE_ANON_KEY=...\nPLATFORM_RUNTIME_PROFILE=gcp\nOBSERVABILITY_BACKEND=gcp\nENFORCEMENT_APPROVAL_TOKEN_SECRET=...\nPAYSTACK_SECRET_KEY=sk_live_...\nPAYSTACK_ACTIVATION_PENDING=true\nPAYSTACK_ACTIVATION_PENDING=false\nINTERNAL_METRICS_AUTH_TOKEN=<32+ char secret>\nEXPOSE_API_DOCUMENTATION_PUBLICLY=false\nCLOUDFLARE_ZONE_ID\ngenerate_managed_runtime_env.py\ngenerate_managed_migration_env.py\ngenerate_managed_deployment_artifacts.py\nverify_codebase_audit_report.py\nverify_managed_deployment_bundle.py\nverify_managed_release_readiness.py\nverify_dashboard_runtime_contract.py\nrender_managed_release_blocker_summary.py\nrelease-unified-platform.yml\npublish-artifact-registry-images.yml\ndeploy-unified-platform.yml\n--api-promotion-ref <repo@sha256:...>\n--batch-promotion-ref <repo@sha256:...>\nrun_public_frontend_quality_gate.py\nscripts/verify_managed_release_readiness.py\ndeployment.report.json\ncloudflare-pages-env.json\nartifact-registry-release.json\nunified-platform-manifest.json\noperator-handoff.md\nmanaged-release-blockers.md\nmanaged-release-blocker-summary-<release-tag>\nmake render-managed-release-blockers\nnon-secret deployment evidence bundle\nCloud Run custom audiences\n--env-file .runtime/production.env\n--env-file .runtime/production.migrate.env\nreusable deploy workflow migration step succeeds from `.runtime/production.migrate.env`\ndocs/evidence/phase1-unified-release-closure.md\n",
    )
    _write(
        tmp_path / "docs/runbooks/unified_platform_release.md",
        "Google Cloud Run\nCloud Tasks\nCloud Scheduler\nCloud Run Jobs\nArtifact Registry\nCloudflare Pages\nSupabase\nCloudflare Pages/DNS/WAF\nGCP runtime + API load balancer\nrelease-unified-platform.yml\npublish-artifact-registry-images.yml\ndeploy-unified-platform.yml\nmanaged-release-blocker-summary-<release-tag>\npromote_production=true\nREPLACE_WITH_REAL_STAGING_FRONTEND\nmake render-managed-release-blockers NON_SECRET_BUNDLE=true\nsupplemental procurement/audit artifacts only\nmanaged-deployment-bundle-<environment>-<release-tag>\nmanaged_cutover_operator_packet.md\nsecret-classified keys such as `DATABASE_URL`\nPAYSTACK_ACTIVATION_PENDING=true\nPAYSTACK_ACTIVATION_PENDING=false\ndocs/evidence/phase1-unified-release-closure.md\napi_promotion_ref\nbatch_promotion_ref\nverify_managed_release_readiness.py\n",
    )
    _write(
        tmp_path / "docs/runbooks/managed_cutover_operator_packet.md",
        "RUNTIME_PLAIN_ENV_JSON\nRUNTIME_SECRET_ENV_JSON\nartifact-registry-release-<release-tag>\n"
        "managed-deployment-bundle-staging-<release-tag>\n"
        "managed-release-blocker-summary-<release-tag>\n"
        "Settings -> Environments\nWorkload Identity Federation\nWorkers & Pages\nSupabase\n"
        '"DATABASE_URL": "postgresql://..."\n'
        '"PAYSTACK_ACTIVATION_PENDING": "true"\n'
        "docs/evidence/phase1-unified-release-closure.md\n",
    )
    _write(
        tmp_path / "docs/evidence/phase1-unified-release-closure.md",
        "Phase 1 Unified Release Closure Evidence\n"
        "26131799197\n"
        "https://github.com/Arvenqor/valdrics/actions/runs/26131799197\n"
        "8ef0b893c2ac7d7d87798d8efee94f70044a7fa0\n"
        "2026.05.19-paystack-pending-8ef0b893\n"
        "artifact-registry-release-2026.05.19-paystack-pending-8ef0b893\n"
        "managed-deployment-bundle-staging-2026.05.19-paystack-pending-8ef0b893\n"
        "managed-deployment-bundle-production-2026.05.19-paystack-pending-8ef0b893\n"
        "managed-release-blocker-summary-2026.05.19-paystack-pending-8ef0b893\n"
        "PAYSTACK_ACTIVATION_PENDING=true\n"
        "PAYSTACK_ACTIVATION_PENDING=false\n"
        "Operator artifact review: complete for release run `26131799197`\n"
        "Real-tenant production-use confirmation: pending manual sign-off\n",
    )
    _write(
        tmp_path / "docs/integrations/workflow_automation.md",
        "env channel routing (`SLACK_CHANNEL_ID`) is blocked\nself-host or break-glass-only paths\n",
    )
    _write(
        tmp_path / "docs/SOC2_CONTROLS.md",
        "CODEOWNERS\n`app/shared/core/logging.py`\n`docs/runbooks/disaster_recovery.md`\n`docs/ROLLBACK_PLAN.md`\n`docs/FULL_CODEBASE_AUDIT.md`\n",
    )
    _write(
        tmp_path / "docs/policies/data_retention.md",
        "Audit logs | Automated retention purge\nAUDIT_LOG_RETENTION_DAYS\nresource_type=audit_logs_retention\nSupabase-managed backups and point-in-time recovery\nProvider-managed retention outside repository automation\n",
    )
    _write(
        tmp_path / "docs/runbooks/enforcement_preprovision_integrations.md",
        "failurePolicy: Fail\n`failurePolicy: Fail` requires API HA\nArchived self-managed Helm reference\nKeep webhook timeout low (`<= 2s`)\n",
    )
    _write(
        tmp_path / "docs/ops/benchmark_alignment_profiles.md",
        "Kubernetes AdmissionReview guidance profile\n"
        "Archived self-managed Helm reference remains outside the supported deployment contract.\n"
        "tests/unit/enforcement/enforcement_api_cases_part01.py\n"
        "tests/unit/enforcement/enforcement_api_cases_part02.py\n"
        "test_enforcement_endpoint_wrappers_cover_preflight_and_k8s_review_branches\n",
    )
    _write(
        tmp_path / "docs/runbooks/partition_maintenance.md",
        "Cloud Scheduler\nGoogle-signed identity\nadvisory lock\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert errors == []


def test_verify_contracts_reports_missing_and_forbidden_phrases(tmp_path: Path) -> None:
    for contract in (
        DocumentationContract(
            path="README.md",
            required_phrases=("Valdrics",),
            forbidden_phrases=("11 zombie-detection plugins",),
        ),
        DocumentationContract(
            path="docs/FULL_CODEBASE_AUDIT.md",
            required_phrases=("time-bound snapshot",),
            forbidden_phrases=("5358 tests collected",),
        ),
        DocumentationContract(
            path="docs/architecture/overview.md",
            required_phrases=("boundary target",),
            forbidden_phrases=("Zero external dependencies",),
        ),
        DocumentationContract(
            path="docs/DEPLOYMENT.md",
            required_phrases=("Current supported production deployment profile",),
            forbidden_phrases=("Helm/Terraform material for future scale research",),
        ),
        DocumentationContract(
            path="docs/CAPACITY_PLAN.md",
            required_phrases=("Google Cloud Run",),
            forbidden_phrases=("future scale path",),
        ),
        DocumentationContract(
            path="docs/ops/README.md",
            required_phrases=(
                "active operational material only",
                "docs/ops/enforcement_release_gate_contract.json",
            ),
        ),
        DocumentationContract(
            path="docs/ops/acceptance_evidence_capture.md",
            required_phrases=(
                "not the managed deployment release path",
                "managed-deployment-bundle-<environment>-<release-tag>",
            ),
            forbidden_phrases=("production sign-off",),
        ),
        DocumentationContract(
            path="docs/ops/enforcement_release_gate_contract.json",
            required_phrases=("post_closure_sanity", "required_runtime_gated_features"),
        ),
        DocumentationContract(
            path="docs/product/external_feedback_validation.md",
            required_phrases=("Status: Supporting evidence", "phase tracker"),
        ),
        DocumentationContract(
            path="docs/compliance/compliance_pack.md",
            required_phrases=(
                "supplemental evidence",
                "managed-deployment-bundle-<environment>-<release-tag>",
            ),
        ),
        DocumentationContract(
            path="docs/architecture/tiering-2026.md",
            required_phrases=("dashboard/src/lib/pricing/publicPlans.ts",),
        ),
        DocumentationContract(
            path="docs/runbooks/month_end_close.md",
            required_phrases=("not a production cutover packet",),
            forbidden_phrases=("finance/procurement sign-off",),
        ),
        DocumentationContract(
            path="docs/ROLLBACK_PLAN.md",
            required_phrases=("Cloud Scheduler job", "Cloud Run custom audiences"),
        ),
        DocumentationContract(
            path="docs/architecture/database_schema_overview.md",
            required_phrases=("backup/restore is the primary rollback path",),
        ),
        DocumentationContract(
            path="docs/architecture/failover.md",
            required_phrases=("Cloudflare",),
            forbidden_phrases=("aws_role_to_assume",),
        ),
        DocumentationContract(
            path="docs/runbooks/disaster_recovery.md",
            required_phrases=("Supabase",),
            forbidden_phrases=("secondary_db_endpoint",),
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
                "release-unified-platform.yml",
                "publish-artifact-registry-images.yml",
                "--api-promotion-ref <repo@sha256:...>",
                "cloudflare-pages-env.json",
            ),
        ),
        DocumentationContract(
            path="docs/runbooks/unified_platform_release.md",
            required_phrases=(
                "release-unified-platform.yml",
                "supplemental procurement/audit artifacts only",
            ),
        ),
        DocumentationContract(
            path="docs/runbooks/managed_cutover_operator_packet.md",
            required_phrases=(
                "RUNTIME_PLAIN_ENV_JSON",
                "managed-release-blocker-summary-<release-tag>",
            ),
        ),
        DocumentationContract(
            path="docs/integrations/workflow_automation.md",
            required_phrases=("self-host or break-glass-only paths",),
        ),
        DocumentationContract(
            path="docs/SOC2_CONTROLS.md",
            required_phrases=("CODEOWNERS",),
            forbidden_phrases=("Infrastructure: Helm chart",),
        ),
        DocumentationContract(
            path="docs/policies/data_retention.md",
            required_phrases=("AUDIT_LOG_RETENTION_DAYS",),
            forbidden_phrases=("AWS RDS backups (Terraform profile)",),
        ),
        DocumentationContract(
            path="docs/runbooks/enforcement_preprovision_integrations.md",
            required_phrases=("Archived self-managed Helm reference",),
            forbidden_phrases=("Helm deployment profile (recommended)",),
        ),
        DocumentationContract(
            path="docs/ops/benchmark_alignment_profiles.md",
            required_phrases=("Kubernetes AdmissionReview guidance profile",),
            forbidden_phrases=("tests/unit/ops/",),
        ),
        DocumentationContract(
            path="docs/runbooks/partition_maintenance.md",
            required_phrases=("Cloud Scheduler",),
            forbidden_phrases=("pg_cron", "X-Internal-Job-Secret"),
        ),
    ):
        _write(tmp_path / contract.path, "placeholder\n")

    _write(tmp_path / "README.md", "11 zombie-detection plugins\n")
    _write(tmp_path / "docs/FULL_CODEBASE_AUDIT.md", "5358 tests collected\n")
    _write(tmp_path / "docs/architecture/overview.md", "Zero external dependencies\n")

    errors = verify_contracts(root=tmp_path)
    assert "README.md: missing required phrase 'Valdrics'" in errors
    assert "README.md: forbidden phrase present '11 zombie-detection plugins'" in errors
    assert (
        "docs/FULL_CODEBASE_AUDIT.md: missing required phrase 'time-bound snapshot'"
        in errors
    )
    assert (
        "docs/FULL_CODEBASE_AUDIT.md: forbidden phrase present '5358 tests collected'"
        in errors
    )
    assert (
        "docs/architecture/overview.md: missing required phrase 'boundary target'"
        in errors
    )
    assert (
        "docs/architecture/overview.md: forbidden phrase present 'Zero external dependencies'"
        in errors
    )


def test_verify_contracts_rejects_local_cache_wording_in_managed_deployment_docs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        documentation_runtime_contracts,
        "DOCUMENTATION_CONTRACTS",
        (
            DocumentationContract(
                path="docs/DEPLOYMENT.md",
                required_phrases=("Current supported production deployment profile",),
                forbidden_phrases=("local cache infrastructure",),
            ),
        ),
    )
    _write(
        tmp_path / "docs/DEPLOYMENT.md",
        "Current supported production deployment profile\nlocal cache infrastructure\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert (
        "docs/DEPLOYMENT.md: forbidden phrase present 'local cache infrastructure'"
        in errors
    )


def test_verify_contracts_rejects_broad_cache_wording_in_incident_runbook(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        documentation_runtime_contracts,
        "DOCUMENTATION_CONTRACTS",
        (
            DocumentationContract(
                path="docs/runbooks/incident_response.md",
                required_phrases=("strict SaaS mode",),
                forbidden_phrases=(
                    "optional cache backends are either healthy or falling back cleanly",
                ),
            ),
        ),
    )
    _write(
        tmp_path / "docs/runbooks/incident_response.md",
        "strict SaaS mode\n"
        "optional cache backends are either healthy or falling back cleanly\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert (
        "docs/runbooks/incident_response.md: forbidden phrase present 'optional cache backends are either healthy or falling back cleanly'"
        in errors
    )


def test_verify_contracts_rejects_otlp_observability_in_managed_production_docs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        documentation_runtime_contracts,
        "DOCUMENTATION_CONTRACTS",
        (
            DocumentationContract(
                path="docs/runbooks/production_env_checklist.md",
                required_phrases=("OBSERVABILITY_BACKEND=gcp",),
                forbidden_phrases=("OBSERVABILITY_BACKEND=otlp",),
            ),
        ),
    )
    _write(
        tmp_path / "docs/runbooks/production_env_checklist.md",
        "OBSERVABILITY_BACKEND=gcp\nOBSERVABILITY_BACKEND=otlp\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert (
        "docs/runbooks/production_env_checklist.md: forbidden phrase present 'OBSERVABILITY_BACKEND=otlp'"
        in errors
    )


def test_verify_contracts_rejects_legacy_regional_failover_wording(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        documentation_runtime_contracts,
        "DOCUMENTATION_CONTRACTS",
        (
            DocumentationContract(
                path="docs/architecture/failover.md",
                required_phrases=(
                    "regional_recovery_mode=manual_restore_redeploy_reroute",
                ),
                forbidden_phrases=(
                    "regional-failover",
                    "automated_secondary_region_failover",
                ),
            ),
        ),
    )
    _write(
        tmp_path / "docs/architecture/failover.md",
        "regional_recovery_mode=manual_restore_redeploy_reroute\n"
        "regional-failover\n"
        "automated_secondary_region_failover\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert (
        "docs/architecture/failover.md: forbidden phrase present 'regional-failover'"
        in errors
    )
    assert (
        "docs/architecture/failover.md: forbidden phrase present 'automated_secondary_region_failover'"
        in errors
    )


def test_verify_contracts_rejects_helm_scope_in_soc2_controls(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        documentation_runtime_contracts,
        "DOCUMENTATION_CONTRACTS",
        (
            DocumentationContract(
                path="docs/SOC2_CONTROLS.md",
                required_phrases=("CODEOWNERS",),
                forbidden_phrases=("Infrastructure: Helm chart",),
            ),
        ),
    )
    _write(
        tmp_path / "docs/SOC2_CONTROLS.md",
        "CODEOWNERS\nInfrastructure: Helm chart\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert (
        "docs/SOC2_CONTROLS.md: forbidden phrase present 'Infrastructure: Helm chart'"
        in errors
    )


def test_verify_contracts_rejects_aws_rds_retention_wording_in_supported_policy(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        documentation_runtime_contracts,
        "DOCUMENTATION_CONTRACTS",
        (
            DocumentationContract(
                path="docs/policies/data_retention.md",
                required_phrases=("AUDIT_LOG_RETENTION_DAYS",),
                forbidden_phrases=("AWS RDS backups (Terraform profile)",),
            ),
        ),
    )
    _write(
        tmp_path / "docs/policies/data_retention.md",
        "AUDIT_LOG_RETENTION_DAYS\nAWS RDS backups (Terraform profile)\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert (
        "docs/policies/data_retention.md: forbidden phrase present 'AWS RDS backups (Terraform profile)'"
        in errors
    )


def test_verify_contracts_rejects_recommended_helm_wording_in_enforcement_runbook(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        documentation_runtime_contracts,
        "DOCUMENTATION_CONTRACTS",
        (
            DocumentationContract(
                path="docs/runbooks/enforcement_preprovision_integrations.md",
                required_phrases=("Archived self-managed Helm reference",),
                forbidden_phrases=("Helm deployment profile (recommended)",),
            ),
        ),
    )
    _write(
        tmp_path / "docs/runbooks/enforcement_preprovision_integrations.md",
        "Archived self-managed Helm reference\nHelm deployment profile (recommended)\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert (
        "docs/runbooks/enforcement_preprovision_integrations.md: forbidden phrase present 'Helm deployment profile (recommended)'"
        in errors
    )


def test_verify_contracts_rejects_stale_helm_test_reference_in_benchmark_profile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        documentation_runtime_contracts,
        "DOCUMENTATION_CONTRACTS",
        (
            DocumentationContract(
                path="docs/ops/benchmark_alignment_profiles.md",
                required_phrases=("Kubernetes AdmissionReview guidance profile",),
                forbidden_phrases=("tests/unit/ops/",),
            ),
        ),
    )
    _write(
        tmp_path / "docs/ops/benchmark_alignment_profiles.md",
        "Kubernetes AdmissionReview guidance profile\n"
        "tests/unit/ops/legacy_contract_test.py\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert (
        "docs/ops/benchmark_alignment_profiles.md: forbidden phrase present 'tests/unit/ops/'"
        in errors
    )


def test_verify_contracts_rejects_live_deployment_doc_research_wording(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        documentation_runtime_contracts,
        "DOCUMENTATION_CONTRACTS",
        (
            DocumentationContract(
                path="docs/DEPLOYMENT.md",
                required_phrases=("Current supported production deployment profile",),
                forbidden_phrases=(
                    "Helm/Terraform material for future scale research",
                ),
            ),
        ),
    )
    _write(
        tmp_path / "docs/DEPLOYMENT.md",
        "Current supported production deployment profile\n"
        "Helm/Terraform material for future scale research\n",
    )

    errors = verify_contracts(root=tmp_path)
    assert (
        "docs/DEPLOYMENT.md: forbidden phrase present 'Helm/Terraform material for future scale research'"
        in errors
    )


def test_verify_contracts_rejects_missing_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing-root"
    assert verify_contracts(root=missing_root) == [f"root not found: {missing_root}"]


def test_verify_contracts_rejects_non_directory_root(tmp_path: Path) -> None:
    root_file = tmp_path / "root.txt"
    root_file.write_text("not-a-directory\n", encoding="utf-8")
    assert verify_contracts(root=root_file) == [
        f"root must be a directory: {root_file}"
    ]


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

    monkeypatch.setattr(
        documentation_runtime_contracts, "verify_contracts", _fake_verify_contracts
    )

    assert main(["--root", "docs"]) == 0
    assert seen == [documentation_runtime_contracts.DEFAULT_ROOT / "docs"]


def test_main_rejects_relative_root_escape(capsys) -> None:
    assert main(["--root", "../outside"]) == 2
    assert "must stay within repo root when relative" in capsys.readouterr().out
