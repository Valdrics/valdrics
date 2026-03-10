# All Changes Categorization Register Follow-Up (2026-03-08)

Generated from live working tree using `git status --porcelain -uall`.

## Summary

- Total changed paths: 215
- Modified paths: 188
- New/untracked paths: 23
- Deleted paths: 4

## Track Rollup

| Track | Scope | Path Count | Tracking Issue |
|---|---|---:|---|
| Track AQ | Backend runtime, governance, enforcement, and data changes | 76 | #249 |
| Track AR | Frontend dashboard, pricing, proof, and marketing changes | 48 | #250 |
| Track AS | Test coverage, CI workflows, and automation controls | 58 | #251 |
| Track AT | Deployment, runbooks, infrastructure, and environment configuration | 33 | #252 |

## Full Inventory By Track

### Track AQ - Backend runtime, governance, enforcement, and data changes (76)

| Status | Path |
|---|---|
| `M` | `app/main.py` |
| `M` | `app/models/background_job.py` |
| `M` | `app/modules/billing/api/v1/billing_ops.py` |
| `M` | `app/modules/enforcement/api/v1/actions.py` |
| `M` | `app/modules/enforcement/domain/actions.py` |
| `M` | `app/modules/enforcement/domain/actions_terminal_ops.py` |
| `M` | `app/modules/enforcement/domain/approval_flow_ops.py` |
| `M` | `app/modules/enforcement/domain/approval_routing_ops.py` |
| `M` | `app/modules/enforcement/domain/approval_token_ops.py` |
| `M` | `app/modules/enforcement/domain/budget_credit_ops.py` |
| `M` | `app/modules/enforcement/domain/credit_ops.py` |
| `M` | `app/modules/enforcement/domain/export_bundle_ops.py` |
| `M` | `app/modules/enforcement/domain/policy_contract_ops.py` |
| `M` | `app/modules/enforcement/domain/reconciliation_flow_ops.py` |
| `M` | `app/modules/enforcement/domain/reconciliation_ops.py` |
| `M` | `app/modules/enforcement/domain/runtime_query_ops.py` |
| `M` | `app/modules/enforcement/domain/service.py` |
| `M` | `app/modules/enforcement/domain/service_approval_ops.py` |
| `M` | `app/modules/enforcement/domain/service_runtime_gate_lock_ops.py` |
| `M` | `app/modules/enforcement/domain/service_runtime_ops.py` |
| `M` | `app/modules/governance/api/oidc.py` |
| `M` | `app/modules/governance/api/v1/audit_access.py` |
| `M` | `app/modules/governance/api/v1/jobs.py` |
| `M` | `app/modules/governance/api/v1/public_marketing.py` |
| `M` | `app/modules/governance/api/v1/settings/identity_diagnostics_ops.py` |
| `M` | `app/modules/governance/domain/jobs/handlers/finops.py` |
| `M` | `app/modules/governance/domain/jobs/processor.py` |
| `M` | `app/modules/governance/domain/security/compliance_pack_support.py` |
| `M` | `app/modules/optimization/adapters/saas/plugins/api.py` |
| `M` | `app/modules/optimization/domain/actions/aws/base.py` |
| `M` | `app/modules/optimization/domain/actions/azure/base.py` |
| `M` | `app/modules/optimization/domain/actions/base.py` |
| `M` | `app/modules/optimization/domain/actions/gcp/base.py` |
| `M` | `app/modules/optimization/domain/actions/license/base.py` |
| `M` | `app/modules/optimization/domain/actions/saas/github.py` |
| `M` | `app/modules/optimization/domain/factory.py` |
| `M` | `app/modules/optimization/domain/plugin.py` |
| `M` | `app/modules/optimization/domain/ports.py` |
| `M` | `app/modules/optimization/domain/remediation.py` |
| `M` | `app/modules/optimization/domain/unified_discovery.py` |
| `M` | `app/modules/optimization/domain/zombie_scan_state.py` |
| `M` | `app/modules/reporting/domain/pricing/service.py` |
| `M` | `app/modules/reporting/domain/service.py` |
| `M` | `app/shared/adapters/aws_utils.py` |
| `M` | `app/shared/adapters/hybrid.py` |
| `M` | `app/shared/adapters/license.py` |
| `M` | `app/shared/adapters/platform.py` |
| `M` | `app/shared/adapters/saas.py` |
| `M` | `app/shared/connections/oidc.py` |
| `M` | `app/shared/core/celery_app.py` |
| `M` | `app/shared/core/cloud_pricing_data.py` |
| `M` | `app/shared/core/config.py` |
| `M` | `app/shared/core/config_validation_runtime.py` |
| `M` | `app/shared/core/cors_policy.py` |
| `M` | `app/shared/core/middleware.py` |
| `M` | `app/shared/core/ops_metrics.py` |
| `M` | `app/shared/core/ops_metrics_runtime.py` |
| `M` | `app/shared/core/pricing_defaults.py` |
| `M` | `app/shared/db/session.py` |
| `M` | `app/shared/llm/prompts.yaml` |
| `M` | `app/tasks/scheduler_background_job_retention_ops.py` |
| `M` | `app/tasks/scheduler_maintenance_ops.py` |
| `M` | `migrations/env.py` |
| `M` | `migrations/versions/a1b2c3d4e5f6_add_background_jobs_table.py` |
| `M` | `migrations/versions/g1h2i3j4k5l6_add_cost_aggregation_materialized_view.py` |
| `??` | `app/modules/enforcement/domain/action_errors.py` |
| `??` | `app/modules/optimization/domain/actions/recoverable_errors.py` |
| `??` | `app/modules/optimization/domain/unified_discovery_support.py` |
| `??` | `app/shared/core/adapter_resolver.py` |
| `??` | `app/shared/core/aws_credentials.py` |
| `??` | `app/shared/core/cloud_pricing_aws_sync.py` |
| `??` | `app/shared/core/enforcement_http_boundary.py` |
| `??` | `app/shared/core/ops_metrics_recorders.py` |
| `??` | `app/shared/core/outbound_tls.py` |
| `??` | `app/tasks/scheduler_audit_log_retention_ops.py` |
| `??` | `app/tasks/scheduler_retention_utils.py` |

### Track AR - Frontend dashboard, pricing, proof, and marketing changes (48)

| Status | Path |
|---|---|
| `M` | `dashboard/e2e/landing-visual.spec.ts` |
| `M` | `dashboard/e2e/public-marketing.spec.ts` |
| `M` | `dashboard/src/lib/components/LandingHero.footer.css` |
| `M` | `dashboard/src/lib/components/LandingHero.hero-copy.primary.css` |
| `M` | `dashboard/src/lib/components/LandingHero.metrics-demo.css` |
| `M` | `dashboard/src/lib/components/LandingHero.motion.surface.css` |
| `M` | `dashboard/src/lib/components/LandingHero.roi-plans.css` |
| `M` | `dashboard/src/lib/components/LandingHero.signal-preview.css` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/LandingHero.trust.css` |
| `M` | `dashboard/src/lib/components/landing/LandingCapabilitiesSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingCloudHookSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroCopy.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroView.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingPlansSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingRoiSimulator.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingTrustSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/landing_components.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts` |
| `M` | `dashboard/src/lib/landing/heroContent.core.ts` |
| `M` | `dashboard/src/lib/landing/publicNav.test.ts` |
| `M` | `dashboard/src/lib/landing/publicNav.ts` |
| `M` | `dashboard/src/lib/routeProtection.test.ts` |
| `M` | `dashboard/src/lib/routeProtection.ts` |
| `M` | `dashboard/src/routes/api/edge/[...path]/+server.ts` |
| `M` | `dashboard/src/routes/api/edge/[...path]/edge-proxy.test.ts` |
| `M` | `dashboard/src/routes/api/marketing/subscribe/subscribe.server.test.ts` |
| `M` | `dashboard/src/routes/docs/+page.svelte` |
| `M` | `dashboard/src/routes/docs/docs-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/insights/+page.svelte` |
| `M` | `dashboard/src/routes/layout-public-menu.svelte.test.ts` |
| `M` | `dashboard/src/routes/pricing/+page.svelte` |
| `M` | `dashboard/src/routes/pricing/plans.ts` |
| `D` | `dashboard/src/routes/pricing/pricing-page.base.css` |
| `D` | `dashboard/src/routes/pricing/pricing-page.cards.css` |
| `M` | `dashboard/src/routes/pricing/pricing-page.css` |
| `D` | `dashboard/src/routes/pricing/pricing-page.enterprise.css` |
| `D` | `dashboard/src/routes/pricing/pricing-page.motion.css` |
| `M` | `dashboard/src/routes/pricing/pricing-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/proof/+page.svelte` |
| `M` | `dashboard/src/routes/proof/proof-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/resources/+page.svelte` |
| `M` | `dashboard/src/routes/talk-to-sales/+page.svelte` |
| `M` | `dashboard/src/routes/talk-to-sales/talk-to-sales-page.svelte.test.ts` |
| `??` | `dashboard/src/lib/components/landing/LandingHeroView.svelte.test.ts` |
| `??` | `dashboard/src/lib/components/public/PublicMarketingPage.css` |
| `??` | `dashboard/src/lib/components/public/PublicMarketingPage.svelte` |

### Track AS - Test coverage, CI workflows, and automation controls (58)

| Status | Path |
|---|---|
| `M` | `.github/workflows/ci.yml` |
| `M` | `.github/workflows/cla.yml` |
| `M` | `.github/workflows/disaster-recovery-drill.yml` |
| `M` | `.github/workflows/performance-gate.yml` |
| `M` | `.github/workflows/sbom.yml` |
| `M` | `.github/workflows/security-scan.yml` |
| `M` | `scripts/generate_local_dev_env.py` |
| `M` | `scripts/run_disaster_recovery_drill.py` |
| `M` | `scripts/validate_runtime_env.py` |
| `M` | `scripts/verify_documentation_runtime_contracts.py` |
| `M` | `tests/conftest.py` |
| `M` | `tests/unit/api/v1/test_billing.py` |
| `M` | `tests/unit/core/test_cloud_pricing_data.py` |
| `M` | `tests/unit/core/test_config_branch_paths.py` |
| `M` | `tests/unit/core/test_config_validation.py` |
| `M` | `tests/unit/core/test_cors_policy.py` |
| `M` | `tests/unit/core/test_main.py` |
| `M` | `tests/unit/core/test_middleware.py` |
| `M` | `tests/unit/core/test_ops_metrics.py` |
| `M` | `tests/unit/db/test_session_branch_paths_2.py` |
| `M` | `tests/unit/db/test_session_exhaustive.py` |
| `M` | `tests/unit/enforcement/enforcement_service_cases_common.py` |
| `M` | `tests/unit/enforcement/enforcement_service_cases_part03.py` |
| `M` | `tests/unit/enforcement/enforcement_service_cases_part04.py` |
| `M` | `tests/unit/enforcement/enforcement_service_cases_part08.py` |
| `M` | `tests/unit/enforcement/enforcement_service_helper_cases_common.py` |
| `M` | `tests/unit/enforcement/enforcement_service_helper_cases_part03.py` |
| `M` | `tests/unit/enforcement/enforcement_service_helper_cases_part04.py` |
| `M` | `tests/unit/enforcement/enforcement_service_helper_cases_part06.py` |
| `M` | `tests/unit/enforcement/test_enforcement_actions_service.py` |
| `M` | `tests/unit/governance/api/test_oidc.py` |
| `M` | `tests/unit/governance/api/test_public.py` |
| `M` | `tests/unit/governance/jobs/test_finops_handler_branches.py` |
| `M` | `tests/unit/governance/settings/test_identity_settings_direct_branches.py` |
| `M` | `tests/unit/modules/reporting/test_pricing_service.py` |
| `M` | `tests/unit/ops/test_documentation_runtime_contracts.py` |
| `M` | `tests/unit/ops/test_enforcement_webhook_helm_contract.py` |
| `M` | `tests/unit/ops/test_generate_local_dev_env.py` |
| `M` | `tests/unit/ops/test_production_deployment_contracts.py` |
| `M` | `tests/unit/ops/test_run_disaster_recovery_drill.py` |
| `M` | `tests/unit/ops/test_terraform_ha_contracts.py` |
| `M` | `tests/unit/ops/test_verify_documentation_runtime_contracts.py` |
| `M` | `tests/unit/optimization/test_unified_discovery.py` |
| `M` | `tests/unit/reporting/test_billing_api.py` |
| `M` | `tests/unit/services/jobs/test_job_handlers.py` |
| `M` | `tests/unit/services/zombies/test_base.py` |
| `M` | `tests/unit/services/zombies/test_factory.py` |
| `M` | `tests/unit/shared/connections/test_oidc_service.py` |
| `M` | `tests/unit/supply_chain/test_supply_chain_provenance_workflow.py` |
| `M` | `tests/unit/tasks/test_scheduler_tasks_sweeps.py` |
| `??` | `.github/workflows/regional-failover.yml` |
| `??` | `scripts/run_regional_failover.py` |
| `??` | `tests/unit/core/test_aws_credentials.py` |
| `??` | `tests/unit/governance/test_compliance_pack_support.py` |
| `??` | `tests/unit/ops/test_run_regional_failover.py` |
| `??` | `tests/unit/ops/test_validate_runtime_env.py` |
| `??` | `tests/unit/optimization/test_zombie_scan_state.py` |
| `??` | `tests/unit/tasks/test_scheduler_audit_log_retention_ops.py` |

### Track AT - Deployment, runbooks, infrastructure, and environment configuration (33)

| Status | Path |
|---|---|
| `M` | `.env.example` |
| `M` | `DEPLOYMENT.md` |
| `M` | `docs/CAPACITY_PLAN.md` |
| `M` | `docs/DEPLOYMENT.md` |
| `M` | `docs/ROLLBACK_PLAN.md` |
| `M` | `docs/architecture/failover.md` |
| `M` | `docs/architecture/overview.md` |
| `M` | `docs/ops/cloudflare_go_live_checklist_2026-03-02.md` |
| `M` | `docs/policies/data_retention.md` |
| `M` | `docs/runbooks/disaster_recovery.md` |
| `M` | `docs/runbooks/enforcement_incident_response.md` |
| `M` | `docs/runbooks/enforcement_preprovision_integrations.md` |
| `M` | `docs/runbooks/partition_maintenance.md` |
| `M` | `docs/runbooks/production_env_checklist.md` |
| `M` | `docs/runbooks/secret_rotation_emergency.md` |
| `M` | `helm/valdrics/templates/_helpers.tpl` |
| `M` | `helm/valdrics/templates/deployment.yaml` |
| `M` | `helm/valdrics/templates/worker-deployment.yaml` |
| `M` | `helm/valdrics/values.yaml` |
| `M` | `koyeb-worker.yaml` |
| `M` | `koyeb.yaml` |
| `M` | `terraform/main.tf` |
| `M` | `terraform/modules/db/main.tf` |
| `M` | `terraform/modules/db/outputs.tf` |
| `M` | `terraform/modules/db/variables.tf` |
| `M` | `terraform/modules/eks/main.tf` |
| `M` | `terraform/modules/eks/variables.tf` |
| `M` | `terraform/modules/network/main.tf` |
| `M` | `terraform/modules/network/variables.tf` |
| `M` | `terraform/outputs.tf` |
| `M` | `terraform/providers.tf` |
| `M` | `terraform/variables.tf` |
| `??` | `.vscode/settings.json` |
