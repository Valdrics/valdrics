# All Changes Categorization Register (2026-03-09)

Generated from live working tree using `git status --porcelain -uall`.

## Summary

- Total changed paths: 100
- Modified paths: 87
- New/untracked paths: 13
- Deleted paths: 0

## Track Rollup

| Track | Scope | Path Count | Tracking Issue |
|---|---|---:|---|
| Track AV | Backend runtime, governance, optimization, and pricing changes | 27 | #254 |
| Track AW | Frontend dashboard, pricing, billing, and status page changes | 29 | #255 |
| Track AX | Test coverage, CI workflows, and automation controls | 37 | #256 |
| Track AY | Documentation, deployment, and integration configuration | 7 | #257 |

## Full Inventory By Track

### Track AV - Backend runtime, governance, optimization, and pricing changes (27)

| Status | Path |
|---|---|
| `M` | `app/modules/enforcement/api/v1/actions.py` |
| `M` | `app/modules/enforcement/domain/action_errors.py` |
| `M` | `app/modules/governance/api/v1/audit_compliance.py` |
| `M` | `app/modules/governance/api/v1/settings/connections_azure_gcp.py` |
| `M` | `app/modules/governance/api/v1/settings/connections_helpers.py` |
| `M` | `app/modules/governance/api/v1/settings/connections_setup_snippets.py` |
| `M` | `app/modules/governance/domain/jobs/cur_ingestion.py` |
| `M` | `app/modules/governance/domain/security/compliance_pack_bundle.py` |
| `M` | `app/modules/optimization/adapters/aws/detector.py` |
| `M` | `app/modules/optimization/adapters/aws/plugins/analytics.py` |
| `M` | `app/modules/optimization/adapters/aws/plugins/compute.py` |
| `M` | `app/modules/optimization/adapters/aws/plugins/database.py` |
| `M` | `app/modules/optimization/adapters/aws/plugins/high_value.py` |
| `M` | `app/modules/optimization/adapters/aws/plugins/network.py` |
| `M` | `app/modules/optimization/adapters/aws/plugins/rightsizing.py` |
| `M` | `app/modules/optimization/adapters/aws/plugins/search.py` |
| `M` | `app/modules/optimization/adapters/aws/plugins/storage.py` |
| `M` | `app/modules/optimization/domain/zombie_scan_state.py` |
| `M` | `app/modules/reporting/domain/service.py` |
| `M` | `app/shared/connections/aws.py` |
| `M` | `app/shared/core/cloud_connection.py` |
| `M` | `app/shared/core/config_validation_runtime.py` |
| `M` | `app/shared/core/enforcement_http_boundary.py` |
| `M` | `app/shared/core/health_check_ops.py` |
| `M` | `app/shared/core/pricing_catalog.py` |
| `M` | `app/shared/core/pricing_defaults.py` |
| `??` | `app/modules/optimization/adapters/aws/plugins/pricing_evidence.py` |

### Track AW - Frontend dashboard, pricing, billing, and status page changes (29)

| Status | Path |
|---|---|
| `M` | `dashboard/src/lib/components/IdentitySettingsCard.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/IdentitySettingsCardContent.svelte` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/LandingHero.trust.css` |
| `M` | `dashboard/src/lib/components/identity/identitySettingsHelpers.ts` |
| `M` | `dashboard/src/lib/components/landing/LandingPlansSection.svelte` |
| `M` | `dashboard/src/lib/landing/heroContent.extended.ts` |
| `M` | `dashboard/src/routes/billing/+page.svelte` |
| `M` | `dashboard/src/routes/enterprise/+page.svelte` |
| `M` | `dashboard/src/routes/greenops/+page.svelte` |
| `M` | `dashboard/src/routes/greenops/+page.ts` |
| `M` | `dashboard/src/routes/pricing/+page.svelte` |
| `M` | `dashboard/src/routes/pricing/+page.ts` |
| `M` | `dashboard/src/routes/pricing/plans.ts` |
| `M` | `dashboard/src/routes/pricing/pricing-page.css` |
| `M` | `dashboard/src/routes/pricing/pricing-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/status/+page.svelte` |
| `M` | `dashboard/src/routes/status/status-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/talk-to-sales/+page.svelte` |
| `??` | `dashboard/src/lib/pricing/publicPlans.ts` |
| `??` | `dashboard/src/routes/billing/+page.ts` |
| `??` | `dashboard/src/routes/billing/billing.load.test.ts` |
| `??` | `dashboard/src/routes/billing/billingPage.test.ts` |
| `??` | `dashboard/src/routes/billing/billingPage.ts` |
| `??` | `dashboard/src/routes/greenops/greenopsApiPaths.test.ts` |
| `??` | `dashboard/src/routes/greenops/greenopsApiPaths.ts` |
| `??` | `dashboard/src/routes/status/+page.server.ts` |
| `??` | `dashboard/src/routes/status/status.server.test.ts` |
| `??` | `dashboard/src/routes/status/statusPage.ts` |

### Track AX - Test coverage, CI workflows, and automation controls (37)

| Status | Path |
|---|---|
| `M` | `.github/workflows/ci.yml` |
| `M` | `.github/workflows/disaster-recovery-drill.yml` |
| `M` | `.github/workflows/performance-gate.yml` |
| `M` | `.github/workflows/regional-failover.yml` |
| `M` | `scripts/run_regional_failover.py` |
| `M` | `scripts/verify_api_auth_coverage.py` |
| `M` | `scripts/verify_documentation_runtime_contracts.py` |
| `M` | `tests/billing/test_tier_guard.py` |
| `M` | `tests/unit/core/test_cloud_connection.py` |
| `M` | `tests/unit/core/test_cloud_connection_audit.py` |
| `M` | `tests/unit/core/test_config_branch_paths.py` |
| `M` | `tests/unit/core/test_config_validation.py` |
| `M` | `tests/unit/core/test_health_deep.py` |
| `M` | `tests/unit/core/test_health_service.py` |
| `M` | `tests/unit/governance/api/test_public.py` |
| `M` | `tests/unit/governance/api/test_public_branch_paths.py` |
| `M` | `tests/unit/governance/jobs/test_cur_ingestion.py` |
| `M` | `tests/unit/governance/jobs/test_cur_ingestion_branch_paths.py` |
| `M` | `tests/unit/governance/settings/test_connections_branches.py` |
| `M` | `tests/unit/governance/settings/test_identity_settings.py` |
| `M` | `tests/unit/governance/settings/test_identity_settings_additional_branches.py` |
| `M` | `tests/unit/governance/settings/test_identity_settings_direct_branches.py` |
| `M` | `tests/unit/governance/settings/test_identity_settings_high_impact_branches.py` |
| `M` | `tests/unit/governance/test_connections_api_aws.py` |
| `M` | `tests/unit/modules/optimization/adapters/aws/plugins/test_aws_plugins_analytics_containers_database.py` |
| `M` | `tests/unit/modules/optimization/adapters/aws/plugins/test_aws_plugins_deep.py` |
| `M` | `tests/unit/modules/optimization/adapters/aws/plugins/test_search_branch_paths.py` |
| `M` | `tests/unit/modules/reporting/test_reporting_service_ingestion.py` |
| `M` | `tests/unit/modules/reporting/test_reporting_service_post_ingest.py` |
| `M` | `tests/unit/ops/test_documentation_runtime_contracts.py` |
| `M` | `tests/unit/ops/test_production_deployment_contracts.py` |
| `M` | `tests/unit/ops/test_run_regional_failover.py` |
| `M` | `tests/unit/ops/test_verify_documentation_runtime_contracts.py` |
| `M` | `tests/unit/optimization/test_zombie_scan_state.py` |
| `M` | `tests/unit/services/zombies/aws_provider/test_aws_detector.py` |
| `??` | `scripts/configure_github_oidc_aws_credentials.py` |
| `??` | `tests/unit/ops/test_configure_github_oidc_aws_credentials.py` |

### Track AY - Documentation, deployment, and integration configuration (7)

| Status | Path |
|---|---|
| `M` | `docs/architecture/failover.md` |
| `M` | `docs/integrations/idp_reference_configs.md` |
| `M` | `docs/integrations/sso.md` |
| `M` | `docs/pricing_model.md` |
| `M` | `docs/runbooks/disaster_recovery.md` |
| `M` | `koyeb-worker.yaml` |
| `M` | `koyeb.yaml` |
