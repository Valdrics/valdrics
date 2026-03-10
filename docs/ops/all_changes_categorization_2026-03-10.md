# All Changes Categorization Register (2026-03-10)

Generated from the live working tree using `git status --porcelain -uall`.

## Summary

- Total changed paths: 274
- Modified paths: 178
- New / untracked paths: 77
- Deleted paths: 19

## Track Rollup

| Track | Scope | Path Count | Tracking Issue |
|---|---|---:|---|
| Track BE | Backend services, governance, billing, shared runtime, and migrations | 72 | #264 |
| Track BF | Frontend dashboard, landing funnel, onboarding, billing, and admin product surfaces | 71 | #265 |
| Track BG | Verification, test coverage, runtime automation, deployment configuration, and release gates | 74 | #266 |
| Track BH | Documentation, archive migration, repo guidance, and ops evidence updates | 57 | #267 |

## Categorization Notes

- Archive migration appears in `git status` as delete-plus-add pairs because the working tree has not recorded them as git renames.
- Root-level deployment and repo-control files are grouped with verification/runtime or docs based on operational ownership.

## Full Inventory By Track

### Track BE - Backend services, governance, billing, shared runtime, and migrations (72)

Tracking issue: #264

| Status | Path |
|---|---|
| `M` | `app/main.py` |
| `M` | `app/models/__init__.py` |
| `M` | `app/models/pricing.py` |
| `??` | `app/models/tenant_growth_funnel_snapshot.py` |
| `M` | `app/modules/billing/domain/billing/dunning_service.py` |
| `M` | `app/modules/billing/domain/billing/paystack_client_impl.py` |
| `M` | `app/modules/billing/domain/billing/paystack_service_impl.py` |
| `M` | `app/modules/billing/domain/billing/paystack_service_runtime_ops.py` |
| `M` | `app/modules/billing/domain/billing/paystack_webhook_impl.py` |
| `M` | `app/modules/billing/domain/billing/webhook_retry.py` |
| `M` | `app/modules/governance/api/v1/admin.py` |
| `M` | `app/modules/governance/api/v1/health_dashboard.py` |
| `M` | `app/modules/governance/api/v1/health_dashboard_models.py` |
| `M` | `app/modules/governance/api/v1/jobs.py` |
| `??` | `app/modules/governance/api/v1/landing_funnel_health_ops.py` |
| `M` | `app/modules/governance/api/v1/settings/activeops.py` |
| `M` | `app/modules/governance/api/v1/settings/carbon.py` |
| `M` | `app/modules/governance/api/v1/settings/connections_azure_gcp.py` |
| `M` | `app/modules/governance/api/v1/settings/connections_cloud_plus.py` |
| `M` | `app/modules/governance/api/v1/settings/connections_setup_aws_discovery.py` |
| `M` | `app/modules/governance/api/v1/settings/identity_settings_ops.py` |
| `M` | `app/modules/governance/api/v1/settings/llm.py` |
| `M` | `app/modules/governance/api/v1/settings/notification_diagnostics_ops.py` |
| `M` | `app/modules/governance/api/v1/settings/notification_settings_ops.py` |
| `M` | `app/modules/governance/api/v1/settings/notifications.py` |
| `M` | `app/modules/governance/api/v1/settings/notifications_acceptance_ops.py` |
| `M` | `app/modules/governance/api/v1/settings/onboard.py` |
| `M` | `app/modules/governance/api/v1/settings/safety.py` |
| `??` | `app/modules/governance/domain/jobs/errors.py` |
| `M` | `app/modules/governance/domain/jobs/handlers/acceptance_integration_ops.py` |
| `M` | `app/modules/governance/domain/jobs/handlers/base.py` |
| `M` | `app/modules/governance/domain/jobs/handlers/billing.py` |
| `M` | `app/modules/governance/domain/jobs/handlers/dunning.py` |
| `M` | `app/modules/governance/domain/jobs/processor.py` |
| `M` | `app/modules/governance/domain/scheduler/orchestrator.py` |
| `M` | `app/modules/governance/domain/security/audit_log.py` |
| `M` | `app/modules/optimization/domain/remediation_execute_helpers.py` |
| `M` | `app/modules/reporting/api/v1/usage.py` |
| `M` | `app/modules/reporting/domain/anomaly_detection.py` |
| `M` | `app/modules/reporting/domain/budget_alerts.py` |
| `??` | `app/modules/reporting/domain/tenant_growth_funnel.py` |
| `M` | `app/shared/core/cloud_connection.py` |
| `M` | `app/shared/core/config.py` |
| `M` | `app/shared/core/config_validation.py` |
| `M` | `app/shared/core/health_check_ops.py` |
| `M` | `app/shared/core/logging.py` |
| `??` | `app/shared/core/migration_settings.py` |
| `M` | `app/shared/core/notifications.py` |
| `M` | `app/shared/core/ops_metrics.py` |
| `M` | `app/shared/core/pricing_catalog.py` |
| `M` | `app/shared/core/pricing_types.py` |
| `??` | `app/shared/db/connect_args.py` |
| `??` | `app/shared/db/local_sqlite_bootstrap.py` |
| `??` | `app/shared/db/migration_context.py` |
| `M` | `app/shared/db/session.py` |
| `M` | `app/shared/db/session_context_ops.py` |
| `M` | `app/shared/llm/budget_execution.py` |
| `M` | `app/shared/llm/budget_execution_runtime_ops.py` |
| `M` | `app/shared/llm/budget_fair_use.py` |
| `M` | `app/shared/llm/budget_fair_use_abuse.py` |
| `M` | `app/shared/llm/budget_fair_use_limits.py` |
| `M` | `app/shared/llm/budget_manager.py` |
| `M` | `app/tasks/scheduler_audit_log_retention_ops.py` |
| `M` | `app/tasks/scheduler_background_job_retention_ops.py` |
| `??` | `app/tasks/scheduler_funnel_ops.py` |
| `M` | `app/tasks/scheduler_maintenance_ops.py` |
| `M` | `app/tasks/scheduler_sweep_ops.py` |
| `M` | `app/tasks/scheduler_tasks.py` |
| `M` | `migrations/env.py` |
| `??` | `migrations/versions/q2r3s4t5u6v7_add_unique_charge_reference_constraint.py` |
| `??` | `migrations/versions/r3s4t5u6v7w8_add_tenant_growth_funnel_snapshots.py` |
| `??` | `migrations/versions/s4t5u6v7w8x_add_system_audit_logs.py` |

### Track BF - Frontend dashboard, landing funnel, onboarding, billing, and admin product surfaces (71)

Tracking issue: #265

| Status | Path |
|---|---|
| `??` | `dashboard/src/lib/components/LandingHero.cloud-hook.css` |
| `M` | `dashboard/src/lib/components/LandingHero.css` |
| `M` | `dashboard/src/lib/components/LandingHero.hero-copy.primary.layout.css` |
| `M` | `dashboard/src/lib/components/LandingHero.hero-copy.primary.support.css` |
| `M` | `dashboard/src/lib/components/LandingHero.metrics-demo.css` |
| `M` | `dashboard/src/lib/components/LandingHero.motion.surface.shell.css` |
| `M` | `dashboard/src/lib/components/LandingHero.motion.surface.story.css` |
| `M` | `dashboard/src/lib/components/LandingHero.roi-plans.css` |
| `??` | `dashboard/src/lib/components/LandingHero.roi-plans.free.css` |
| `M` | `dashboard/src/lib/components/LandingHero.roi-plans.outcomes.css` |
| `??` | `dashboard/src/lib/components/LandingHero.section-copy.css` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/LandingHero.trust.coverage.css` |
| `M` | `dashboard/src/lib/components/LandingHero.trust.plan-rollout.css` |
| `M` | `dashboard/src/lib/components/landing/LandingCapabilitiesSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingCloudHookSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingExitIntentPrompt.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroCopy.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroView.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroView.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/landing/LandingPlansSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingTrustSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/landing_decomposition.lead_exit.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts` |
| `??` | `dashboard/src/lib/funnel/productFunnelTelemetry.test.ts` |
| `??` | `dashboard/src/lib/funnel/productFunnelTelemetry.ts` |
| `M` | `dashboard/src/lib/landing/heroContent.core.ts` |
| `M` | `dashboard/src/lib/landing/heroContent.extended.ts` |
| `M` | `dashboard/src/lib/landing/landingFunnel.test.ts` |
| `M` | `dashboard/src/lib/landing/landingFunnel.ts` |
| `??` | `dashboard/src/lib/landing/landingHeroActions.ts` |
| `??` | `dashboard/src/lib/landing/landingHeroBrowserRuntime.ts` |
| `??` | `dashboard/src/lib/landing/landingHeroConfig.ts` |
| `??` | `dashboard/src/lib/landing/landingHeroRuntime.ts` |
| `??` | `dashboard/src/lib/landing/landingHeroScenario.ts` |
| `??` | `dashboard/src/lib/landing/landingHeroTelemetryBridge.ts` |
| `M` | `dashboard/src/lib/landing/publicNav.ts` |
| `M` | `dashboard/src/lib/pricing/publicPlans.ts` |
| `M` | `dashboard/src/routes/+page.svelte` |
| `M` | `dashboard/src/routes/admin/health/+page.svelte` |
| `M` | `dashboard/src/routes/admin/health/HealthDashboardPanel.svelte` |
| `??` | `dashboard/src/routes/admin/health/HealthDashboardPanel.svelte.test.ts` |
| `M` | `dashboard/src/routes/admin/health/healthTypes.ts` |
| `M` | `dashboard/src/routes/admin/landing-campaigns/+page.svelte` |
| `??` | `dashboard/src/routes/admin/landing-campaigns/landing-campaigns-page.svelte.test.ts` |
| `??` | `dashboard/src/routes/admin/landing-campaigns/landingCampaignAnalytics.ts` |
| `M` | `dashboard/src/routes/billing/+page.svelte` |
| `M` | `dashboard/src/routes/billing/billing-page.css` |
| `M` | `dashboard/src/routes/billing/billing-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/billing/billingPage.ts` |
| `??` | `dashboard/src/routes/homeDashboardContent.ts` |
| `M` | `dashboard/src/routes/layout/PublicSiteShell.svelte` |
| `M` | `dashboard/src/routes/layout/layoutPublicNav.css` |
| `M` | `dashboard/src/routes/onboarding/OnboardingPageViewContent.svelte` |
| `M` | `dashboard/src/routes/onboarding/OnboardingVerifySuccessSection.svelte` |
| `M` | `dashboard/src/routes/onboarding/onboarding-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/onboarding/onboardingApi.ts` |
| `??` | `dashboard/src/routes/onboarding/onboardingDiscoveryActions.ts` |
| `??` | `dashboard/src/routes/onboarding/onboardingUiActions.ts` |
| `M` | `dashboard/src/routes/pricing/+page.svelte` |
| `M` | `dashboard/src/routes/pricing/pricing-page.css` |
| `M` | `dashboard/src/routes/pricing/pricing-page.svelte.test.ts` |
| `??` | `dashboard/src/routes/pricing/pricingPageContent.ts` |
| `M` | `dashboard/src/routes/resources/valdrics-enterprise-one-pager.md/+server.ts` |
| `M` | `dashboard/src/routes/resources/valdrics-enterprise-one-pager.md/one-pager.server.test.ts` |
| `M` | `dashboard/src/routes/settings/SettingsNotificationControls.svelte` |
| `M` | `dashboard/src/routes/settings/settings-page.advanced.svelte.test.ts` |
| `M` | `dashboard/src/routes/settings/settings-page.core.svelte.test.ts` |
| `M` | `dashboard/src/routes/status/+page.server.ts` |
| `M` | `dashboard/src/routes/status/status.server.test.ts` |

### Track BG - Verification, test coverage, runtime automation, deployment configuration, and release gates (74)

Tracking issue: #266

| Status | Path |
|---|---|
| `M` | `Makefile` |
| `M` | `grafana/dashboards/finops-overview.json` |
| `M` | `helm/valdrics/templates/_helpers.tpl` |
| `M` | `helm/valdrics/values.yaml` |
| `M` | `koyeb.yaml` |
| `M` | `prod.env.template` |
| `M` | `prometheus/alerts.yml` |
| `M` | `scripts/audit_report_controls_core.py` |
| `??` | `scripts/bootstrap_local_sqlite_schema.py` |
| `M` | `scripts/enterprise_tdd_gate_config.py` |
| `??` | `scripts/env_generation_common.py` |
| `M` | `scripts/generate_local_dev_env.py` |
| `??` | `scripts/generate_managed_deployment_artifacts.py` |
| `??` | `scripts/generate_managed_migration_env.py` |
| `??` | `scripts/generate_managed_runtime_env.py` |
| `??` | `scripts/run_webhook_job_reliability_drill.py` |
| `??` | `scripts/smoke_test_local_sqlite_bootstrap.py` |
| `??` | `scripts/validate_migration_env.py` |
| `M` | `scripts/validate_runtime_env.py` |
| `M` | `scripts/verify_documentation_runtime_contracts.py` |
| `M` | `scripts/verify_repo_root_hygiene.py` |
| `M` | `tests/billing/test_tier_guard.py` |
| `M` | `tests/conftest.py` |
| `M` | `tests/unit/api/v1/test_health_dashboard_endpoints.py` |
| `??` | `tests/unit/api/v1/test_usage_funnel_endpoint.py` |
| `M` | `tests/unit/core/test_config_validation.py` |
| `M` | `tests/unit/core/test_env_contract_templates.py` |
| `M` | `tests/unit/core/test_logging_audit.py` |
| `??` | `tests/unit/core/test_migration_settings.py` |
| `M` | `tests/unit/core/test_notifications_coverage.py` |
| `M` | `tests/unit/core/test_ops_metrics.py` |
| `??` | `tests/unit/db/test_local_sqlite_bootstrap.py` |
| `??` | `tests/unit/db/test_migration_context.py` |
| `M` | `tests/unit/db/test_session_branch_paths_2.py` |
| `M` | `tests/unit/governance/domain/jobs/handlers/test_base_handler.py` |
| `M` | `tests/unit/governance/jobs/test_job_processor.py` |
| `M` | `tests/unit/governance/scheduler/test_orchestrator.py` |
| `M` | `tests/unit/governance/scheduler/test_orchestrator_branches.py` |
| `M` | `tests/unit/governance/settings/test_identity_settings_direct_branches.py` |
| `M` | `tests/unit/governance/settings/test_identity_settings_high_impact_branches.py` |
| `M` | `tests/unit/governance/settings/test_notification_entitlement_ops.py` |
| `M` | `tests/unit/governance/settings/test_notifications_diagnostics_workflow.py` |
| `M` | `tests/unit/governance/settings/test_notifications_teams_jira.py` |
| `M` | `tests/unit/governance/settings/test_onboard_branch_paths.py` |
| `M` | `tests/unit/governance/test_admin_api.py` |
| `??` | `tests/unit/governance/test_jobs_api_direct.py` |
| `M` | `tests/unit/modules/reporting/test_budget_alerts_deep.py` |
| `??` | `tests/unit/modules/reporting/test_tenant_growth_funnel.py` |
| `M` | `tests/unit/modules/reporting/test_webhook_retry.py` |
| `M` | `tests/unit/ops/test_documentation_runtime_contracts.py` |
| `M` | `tests/unit/ops/test_generate_local_dev_env.py` |
| `??` | `tests/unit/ops/test_generate_managed_deployment_artifacts.py` |
| `??` | `tests/unit/ops/test_generate_managed_migration_env.py` |
| `??` | `tests/unit/ops/test_generate_managed_runtime_env.py` |
| `??` | `tests/unit/ops/test_local_dev_runtime_contracts.py` |
| `M` | `tests/unit/ops/test_observability_metric_contracts.py` |
| `M` | `tests/unit/ops/test_production_deployment_contracts.py` |
| `??` | `tests/unit/ops/test_smoke_test_local_sqlite_bootstrap.py` |
| `??` | `tests/unit/ops/test_validate_migration_env.py` |
| `M` | `tests/unit/ops/test_validate_runtime_env.py` |
| `M` | `tests/unit/ops/test_verify_documentation_runtime_contracts.py` |
| `M` | `tests/unit/ops/test_verify_repo_root_hygiene.py` |
| `??` | `tests/unit/ops/test_webhook_job_reliability_drill_pack.py` |
| `M` | `tests/unit/optimization/test_remediation_policy.py` |
| `M` | `tests/unit/services/billing/test_dunning_service.py` |
| `M` | `tests/unit/services/billing/test_paystack_billing.py` |
| `M` | `tests/unit/services/billing/test_paystack_billing_branches.py` |
| `M` | `tests/unit/services/jobs/test_acceptance_suite_capture_handler_branches.py` |
| `M` | `tests/unit/supply_chain/test_verify_supply_chain_attestations.py` |
| `M` | `tests/unit/tasks/test_scheduler_audit_log_retention_ops.py` |
| `M` | `tests/unit/tasks/test_scheduler_background_job_retention_ops.py` |
| `??` | `tests/unit/tasks/test_scheduler_funnel_ops.py` |
| `M` | `tests/unit/tasks/test_scheduler_tasks_sweeps.py` |
| `M` | `tests/unit/test_main_coverage.py` |

### Track BH - Documentation, archive migration, repo guidance, and ops evidence updates (57)

Tracking issue: #267

| Status | Path |
|---|---|
| `M` | `.gitignore` |
| `M` | `DEPLOYMENT.md` |
| `M` | `README.md` |
| `M` | `docs/CAPACITY_PLAN.md` |
| `M` | `docs/DEPLOYMENT.md` |
| `M` | `docs/FULL_CODEBASE_AUDIT.md` |
| `D` | `docs/LOGIC_AND_PERFORMANCE_AUDIT.md` |
| `D` | `docs/ZOMBIE_DETECTION_REFERENCE.md` |
| `M` | `docs/architecture/database_schema_overview.md` |
| `??` | `docs/archive/README.md` |
| `??` | `docs/archive/ops/2026-q1/all_changes_categorization_2026-03-05.md` |
| `??` | `docs/archive/ops/2026-q1/all_changes_categorization_2026-03-06.md` |
| `??` | `docs/archive/ops/2026-q1/all_changes_categorization_2026-03-07.md` |
| `??` | `docs/archive/ops/2026-q1/all_changes_categorization_2026-03-08.md` |
| `??` | `docs/archive/ops/2026-q1/all_changes_categorization_2026-03-08_followup.md` |
| `??` | `docs/archive/ops/2026-q1/all_changes_categorization_2026-03-09.md` |
| `??` | `docs/archive/ops/2026-q1/all_changes_categorization_2026-03-09_followup.md` |
| `??` | `docs/archive/ops/2026-q1/competitive_positioning_matrix_2026-03-09.md` |
| `??` | `docs/archive/ops/2026-q1/gtm_positioning_one_pager_2026-03-09.md` |
| `??` | `docs/archive/ops/2026-q1/landing_growth_pack_2026-02-28.md` |
| `??` | `docs/archive/ops/2026-q1/landing_post_closure_sanity_2026-02-28.md` |
| `??` | `docs/archive/ops/2026-q1/landing_release_package_2026-02-28.md` |
| `??` | `docs/archive/ops/2026-q1/sidebar_latency_audit_2026-02-13.md` |
| `??` | `docs/archive/ops/2026-q1/workstream_categorization_2026-03-01.md` |
| `??` | `docs/archive/ops/2026-q1/workstream_categorization_2026-03-02.md` |
| `??` | `docs/archive/ops/2026-q1/workstream_categorization_followup2_2026-03-02.md` |
| `??` | `docs/archive/ops/2026-q1/workstream_categorization_followup_2026-03-02.md` |
| `??` | `docs/archive/ops/2026-q1/zero_budget_launch_cloudflare_fact_check_2026-02-17.md` |
| `??` | `docs/archive/reference/2026-q1/ZOMBIE_DETECTION_REFERENCE.md` |
| `??` | `docs/archive/reviews/2026-q1/LOGIC_AND_PERFORMANCE_AUDIT.md` |
| `??` | `docs/archive/runbooks/2026-q1/incident_response_plan.md` |
| `D` | `docs/incident_response_plan.md` |
| `M` | `docs/integrations/workflow_automation.md` |
| `??` | `docs/ops/README.md` |
| `D` | `docs/ops/all_changes_categorization_2026-03-05.md` |
| `D` | `docs/ops/all_changes_categorization_2026-03-06.md` |
| `D` | `docs/ops/all_changes_categorization_2026-03-07.md` |
| `D` | `docs/ops/all_changes_categorization_2026-03-08.md` |
| `D` | `docs/ops/all_changes_categorization_2026-03-08_followup.md` |
| `D` | `docs/ops/all_changes_categorization_2026-03-09.md` |
| `D` | `docs/ops/all_changes_categorization_2026-03-09_followup.md` |
| `M` | `docs/ops/evidence/python_module_size_preferred_baseline.json` |
| `M` | `docs/ops/feature_enforceability_matrix_2026-02-27.json` |
| `??` | `docs/ops/landing_funnel_alerting_2026-03-10.md` |
| `D` | `docs/ops/landing_growth_pack_2026-02-28.md` |
| `D` | `docs/ops/landing_post_closure_sanity_2026-02-28.md` |
| `D` | `docs/ops/landing_release_package_2026-02-28.md` |
| `D` | `docs/ops/sidebar_latency_audit_2026-02-13.md` |
| `D` | `docs/ops/workstream_categorization_2026-03-01.md` |
| `D` | `docs/ops/workstream_categorization_2026-03-02.md` |
| `D` | `docs/ops/workstream_categorization_followup2_2026-03-02.md` |
| `D` | `docs/ops/workstream_categorization_followup_2026-03-02.md` |
| `D` | `docs/ops/zero_budget_launch_cloudflare_fact_check_2026-02-17.md` |
| `M` | `docs/pricing_model.md` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/runbooks/production_env_checklist.md` |
| `??` | `docs/runbooks/webhook_job_reliability_drill.md` |

