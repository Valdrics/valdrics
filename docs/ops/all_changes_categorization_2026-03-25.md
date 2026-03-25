# All Changes Categorization (2026-03-25)

Snapshot:
- Captured at: `2026-03-25T00:00:00Z`
- Base commit: `d135f31bf0105253b343e340a105a5a8e1cd1d2b`
- Pending paths: `201`
- Branch at snapshot: `main`

## Track CN: Dashboard Frontend Surfaces, Charts, Routes, and Style System
Scope:
- Consolidate dashboard application shells, route views, chart adapters, content models, and style-system changes in one frontend review lane.
- Keep the related Svelte component tests, route tests, and frontend runtime wiring together with the UI they exercise.
- Treat this as the dashboard and public-frontend implementation slice of the batch.

Paths:
- `dashboard/src/app.base.css`
- `dashboard/src/app.components-layout.css`
- `dashboard/src/app.css`
- `dashboard/src/app.design.css`
- `dashboard/src/app.shared-utilities.css`
- `dashboard/src/app.theme.css`
- `dashboard/src/app.utilities.css`
- `dashboard/src/app.variables.css`
- `dashboard/src/authenticated.app.css`
- `dashboard/src/lib/api.ts`
- `dashboard/src/lib/chartjs.ts`
- `dashboard/src/lib/chartjsRuntime.test.ts`
- `dashboard/src/lib/chartjsRuntime.ts`
- `dashboard/src/lib/components/CommandPalette.svelte`
- `dashboard/src/lib/components/FindingsTable.svelte`
- `dashboard/src/lib/components/LandingHero.metrics-demo.css`
- `dashboard/src/lib/components/LandingHero.motion.surface.shell.css`
- `dashboard/src/lib/components/LandingHero.svelte`
- `dashboard/src/lib/components/LandingHero.svelte.test.ts`
- `dashboard/src/lib/components/PieChart.svelte`
- `dashboard/src/lib/components/PieChart.svelte.test.ts`
- `dashboard/src/lib/components/ROAChart.svelte`
- `dashboard/src/lib/components/ROAChart.svelte.test.ts`
- `dashboard/src/lib/components/SavingsHero.svelte`
- `dashboard/src/lib/components/landing/LandingHeroView.public.css`
- `dashboard/src/lib/components/landing/LandingHeroView.svelte`
- `dashboard/src/lib/components/landing/LandingHeroView.svelte.test.ts`
- `dashboard/src/lib/components/landing/LandingSignalMapCard.svelte`
- `dashboard/src/lib/content/publicContent.docs.ts`
- `dashboard/src/lib/content/publicContent.insights.ts`
- `dashboard/src/lib/content/publicContent.proof.ts`
- `dashboard/src/lib/content/publicContent.resources.ts`
- `dashboard/src/lib/content/publicContent.test.ts`
- `dashboard/src/lib/content/publicContent.ts`
- `dashboard/src/lib/content/publicContent.types.ts`
- `dashboard/src/lib/content/publicContent.validation.ts`
- `dashboard/src/lib/landing/landingSignalSnapshots.test.ts`
- `dashboard/src/lib/landing/landingSignalSnapshots.ts`
- `dashboard/src/lib/landing/realtimeSignalMap.ts`
- `dashboard/src/lib/landing/signalRotation.ts`
- `dashboard/src/lib/landing/signalTrace.ts`
- `dashboard/src/lib/stores/jobs.svelte.ts`
- `dashboard/src/lib/supabase.browser.ts`
- `dashboard/src/lib/supabase.ts`
- `dashboard/src/public.app.css`
- `dashboard/src/routes/+layout.svelte`
- `dashboard/src/routes/admin/health/HealthDashboardPanel.svelte`
- `dashboard/src/routes/audit/+page.svelte`
- `dashboard/src/routes/audit/audit.app.css`
- `dashboard/src/routes/auth/login/+page.svelte`
- `dashboard/src/routes/auth/login/login-page.svelte.test.ts`
- `dashboard/src/routes/billing/+page.svelte`
- `dashboard/src/routes/billing/billing.app.css`
- `dashboard/src/routes/connections/+page.svelte`
- `dashboard/src/routes/connections/ConnectionsOrgDiscoverySection.svelte`
- `dashboard/src/routes/connections/ConnectionsPageViewBody.svelte`
- `dashboard/src/routes/connections/ConnectionsPageViewContent.css`
- `dashboard/src/routes/connections/ConnectionsPageViewContent.svelte`
- `dashboard/src/routes/connections/ConnectionsPlatformHybridCards.svelte`
- `dashboard/src/routes/connections/ConnectionsPublicCloudCards.svelte`
- `dashboard/src/routes/connections/ConnectionsSaasLicenseCards.svelte`
- `dashboard/src/routes/connections/connections.app.css`
- `dashboard/src/routes/dashboard/+page.svelte`
- `dashboard/src/routes/dashboard/dashboard.app.css`
- `dashboard/src/routes/greenops/+page.svelte`
- `dashboard/src/routes/greenops/greenops-bento.css`
- `dashboard/src/routes/greenops/greenops.app.css`
- `dashboard/src/routes/layout-public-menu.svelte.test.ts`
- `dashboard/src/routes/layout/AppAuthenticatedShell.svelte`
- `dashboard/src/routes/layout/AppAuthenticatedShell.svelte.test.ts`
- `dashboard/src/routes/layout/PublicSiteShell.svelte`
- `dashboard/src/routes/leaderboards/+page.svelte`
- `dashboard/src/routes/leaderboards/leaderboards.app.css`
- `dashboard/src/routes/llm/+page.svelte`
- `dashboard/src/routes/llm/llm.app.css`
- `dashboard/src/routes/onboarding/+page.svelte`
- `dashboard/src/routes/onboarding/OnboardingPageViewBody.svelte`
- `dashboard/src/routes/onboarding/OnboardingStepConfigurationSection.svelte`
- `dashboard/src/routes/onboarding/OnboardingVerifySuccessSection.svelte`
- `dashboard/src/routes/onboarding/onboarding-page.svelte.test.ts`
- `dashboard/src/routes/onboarding/onboarding.app.css`
- `dashboard/src/routes/ops/+page.svelte`
- `dashboard/src/routes/ops/OpsAcceptanceKpiSection.svelte`
- `dashboard/src/routes/ops/OpsCloseWorkflowSection.svelte`
- `dashboard/src/routes/ops/OpsIntegrationAcceptanceSection.svelte`
- `dashboard/src/routes/ops/OpsOperationalHealthSection.svelte`
- `dashboard/src/routes/ops/OpsPageViewContent.svelte`
- `dashboard/src/routes/ops/ops.app.css`
- `dashboard/src/routes/savings/+page.svelte`
- `dashboard/src/routes/savings/savings.app.css`
- `dashboard/src/routes/settings/+page.svelte`
- `dashboard/src/routes/settings/SettingsPageViewBody.svelte`
- `dashboard/src/routes/settings/settings.app.css`
- `dashboard/static/public-site-shell.css`
- `dashboard/vite.config.ts`

Notes:
- This track contains all `dashboard/` path changes in the March 25 batch.

## Track CO: Backend Runtime, Compliance, Billing, LLM, and Core Regression Coverage
Scope:
- Group backend runtime entrypoints, billing webhook retry behavior, enforcement locking, compliance support, optimization discovery, and LLM client changes together.
- Keep the related core, governance, enforcement, reporting, optimization, and LLM regression suites in the same backend review lane.
- Treat this as the backend and core-runtime slice of the batch.

Paths:
- `app/main.py`
- `app/modules/billing/domain/billing/webhook_retry.py`
- `app/modules/enforcement/domain/service_runtime_gate_lock_ops.py`
- `app/modules/governance/domain/security/compliance_pack_support.py`
- `app/modules/optimization/adapters/aws/region_discovery.py`
- `app/shared/core/celery_app.py`
- `app/shared/core/config.py`
- `app/shared/core/performance_testing.py`
- `app/shared/llm/llm_client.py`
- `tests/conftest.py`
- `tests/core/test_middleware.py`
- `tests/integration/test_edge_cases.py`
- `tests/unit/core/test_celery_app_exhaustive.py`
- `tests/unit/core/test_config_branch_paths.py`
- `tests/unit/core/test_main.py`
- `tests/unit/core/test_performance_testing.py`
- `tests/unit/core/test_rate_limit.py`
- `tests/unit/enforcement/enforcement_service_helper_cases_part03.py`
- `tests/unit/governance/connections_api_fixtures.py`
- `tests/unit/governance/test_compliance_pack_support.py`
- `tests/unit/governance/test_connections_api_azure.py`
- `tests/unit/governance/test_connections_api_cloud_plus.py`
- `tests/unit/governance/test_connections_api_gcp.py`
- `tests/unit/llm/test_analyzer.py`
- `tests/unit/llm/test_analyzer_branch_edges.py`
- `tests/unit/llm/test_analyzer_exhaustive.py`
- `tests/unit/modules/reporting/test_webhook_retry.py`
- `tests/unit/optimization/test_region_discovery_error_paths.py`
- `tests/unit/test_main_coverage.py`

Notes:
- This track contains the `app/` changes plus non-ops backend regression coverage.

## Track CP: Ops Automation, Diagnostics, Repo Hygiene, and Script Verification
Scope:
- Batch operational bootstrap, diagnostics, maintenance, validation, and evidence scripts together with their direct regression suites.
- Include the tracked cleanup of the unwanted backup file in the same hygiene and automation lane.
- Treat this as the operational tooling and repo-cleanup slice of the batch.

Paths:
- `data/emissions.csv.bak`
- `scripts/bootstrap_local_sqlite_schema.py`
- `scripts/capture_acceptance_bootstrap.py`
- `scripts/check_frontend_api_contracts.py`
- `scripts/check_partitions.py`
- `scripts/create_partitions.py`
- `scripts/database_wipe.py`
- `scripts/db_diagnostics.py`
- `scripts/deactivate_aws.py`
- `scripts/delete_cloudfront.py`
- `scripts/dev_bearer_token.py`
- `scripts/emergency_disconnect.py`
- `scripts/emergency_token.py`
- `scripts/enterprise_tdd_gate_coverage.py`
- `scripts/finance_committee_packet_common.py`
- `scripts/finance_committee_packet_engine.py`
- `scripts/fix_scan_signature.py`
- `scripts/force_wipe_app.py`
- `scripts/generate_enforcement_stress_evidence.py`
- `scripts/generate_finance_telemetry_snapshot.py`
- `scripts/in_process_runtime_env.py`
- `scripts/list_partitions.py`
- `scripts/list_tables.py`
- `scripts/list_zombies.py`
- `scripts/manage_partitions.py`
- `scripts/run_archival_setup.py`
- `scripts/run_dashboard_playwright_backend.py`
- `scripts/run_rls_optimization.py`
- `scripts/security/check_local_env_for_live_secrets.py`
- `scripts/seed_dev_data.py`
- `scripts/seed_pricing_plans.py`
- `scripts/simple_token.py`
- `scripts/smoke_test_local_sqlite_bootstrap.py`
- `scripts/test_tenant_import.py`
- `scripts/truncate_cost_records.py`
- `scripts/update_exchange_rates.py`
- `scripts/update_llm_pricing.py`
- `scripts/validate_migration_env.py`
- `scripts/validate_runtime_env.py`
- `scripts/verify_all_plugins.py`
- `scripts/verify_api_auth_coverage.py`
- `scripts/verify_audit_report_resolved.py`
- `scripts/verify_container_image_pinning.py`
- `scripts/verify_dependency_locking.py`
- `scripts/verify_documentation_runtime_contracts.py`
- `scripts/verify_pending_approval_flow.py`
- `scripts/verify_plugins.py`
- `scripts/verify_remediation.py`
- `tests/shared/asgi_client.py`
- `tests/unit/ops/test_bootstrap_local_sqlite_schema_script.py`
- `tests/unit/ops/test_capture_acceptance_bootstrap.py`
- `tests/unit/ops/test_check_local_env_for_live_secrets.py`
- `tests/unit/ops/test_db_diagnostics.py`
- `tests/unit/ops/test_delete_cloudfront.py`
- `tests/unit/ops/test_destructive_script_validations.py`
- `tests/unit/ops/test_emergency_token_guardrails.py`
- `tests/unit/ops/test_finance_committee_packet_common.py`
- `tests/unit/ops/test_fix_scan_signature.py`
- `tests/unit/ops/test_in_process_runtime_env.py`
- `tests/unit/ops/test_legacy_db_maintenance_scripts.py`
- `tests/unit/ops/test_legacy_script_hardening.py`
- `tests/unit/ops/test_partition_and_rls_scripts.py`
- `tests/unit/ops/test_run_dashboard_playwright_backend.py`
- `tests/unit/ops/test_runtime_evidence_generators.py`
- `tests/unit/ops/test_smoke_test_local_sqlite_bootstrap.py`
- `tests/unit/ops/test_update_llm_pricing.py`
- `tests/unit/ops/test_validate_migration_env.py`
- `tests/unit/ops/test_validate_runtime_env.py`
- `tests/unit/ops/test_verify_api_auth_coverage.py`
- `tests/unit/ops/test_verify_audit_report_resolved.py`
- `tests/unit/ops/test_verify_container_image_pinning.py`
- `tests/unit/ops/test_verify_dependency_locking.py`
- `tests/unit/ops/test_verify_documentation_runtime_contracts.py`
- `tests/unit/ops/test_verify_plugins.py`
- `tests/unit/scripts/test_check_frontend_api_contracts.py`
- `tests/unit/supply_chain/test_enterprise_tdd_gate_runner.py`
- `tests/unit/supply_chain/test_generate_enforcement_stress_evidence.py`

Notes:
- This track contains script changes, script-focused tests, shared test utilities, and tracked cleanup.

## Batching Decision
Decision:
- Merge as one consolidated PR to `main`.

Reasoning:
- The batch is one active worktree snapshot spanning dashboard frontend work, backend support paths, and operational automation that are being advanced together.
- The issue split preserves review accountability without fragmenting the delivery batch across overlapping product and tooling surfaces.
- Repo cleanup is included only where the file is clearly unwanted and tracked, namely `data/emissions.csv.bak`; ignored local junk was cleaned outside the tracked batch.
