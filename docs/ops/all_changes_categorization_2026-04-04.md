# All Changes Categorization (2026-04-04)

## Scope

- Worktree snapshot date: `2026-04-04`
- Base branch at snapshot: `main`
- Base commit at snapshot: `d9f455859fb88f17b1c5c9ba253dc5f4d8c0624d`
- Total changed paths categorized: `132`
- Categorization rule: every changed path in the dirty worktree is assigned to exactly one execution track.

## Track Register

### Track CY (#353)

- Title: Backend governance, runtime config, health, and rate-limit hardening
- Paths: `40`
- Scope summary: Governance settings, job surfaces, runtime configuration decomposition, health endpoints, middleware, tenant modeling, and rate-limiting behavior together with backend regression coverage.
- Assigned paths:
  - `app/main.py`
  - `app/models/tenant.py`
  - `app/modules/governance/api/v1/health_dashboard.py`
  - `app/modules/governance/api/v1/jobs.py`
  - `app/modules/governance/api/v1/settings/account.py`
  - `app/modules/governance/api/v1/settings/activeops.py`
  - `app/modules/governance/api/v1/settings/carbon.py`
  - `app/modules/governance/api/v1/settings/identity.py`
  - `app/modules/governance/api/v1/settings/identity_settings_ops.py`
  - `app/modules/governance/api/v1/settings/llm.py`
  - `app/modules/governance/api/v1/settings/notifications.py`
  - `app/shared/core/config.py`
  - `app/shared/core/config_sections_core.py`
  - `app/shared/core/config_sections_governance.py`
  - `app/shared/core/config_sections_integrations.py`
  - `app/shared/core/config_sections_security.py`
  - `app/shared/core/config_validation.py`
  - `app/shared/core/health.py`
  - `app/shared/core/middleware.py`
  - `app/shared/core/rate_limit.py`
  - `tests/core/test_circuit_breaker.py`
  - `tests/unit/api/v1/test_health_dashboard_branches.py`
  - `tests/unit/api/v1/test_health_dashboard_endpoints.py`
  - `tests/unit/core/test_config_extras.py`
  - `tests/unit/core/test_config_validation.py`
  - `tests/unit/core/test_health_deep.py`
  - `tests/unit/core/test_health_service.py`
  - `tests/unit/core/test_middleware_audit.py`
  - `tests/unit/core/test_rate_limit.py`
  - `tests/unit/core/test_rate_limit_branch_paths_2.py`
  - `tests/unit/core/test_rate_limit_expanded.py`
  - `tests/unit/db/test_session_branch_paths_2.py`
  - `tests/unit/governance/settings/test_account_settings.py`
  - `tests/unit/governance/settings/test_activeops.py`
  - `tests/unit/governance/settings/test_carbon.py`
  - `tests/unit/governance/settings/test_identity_settings_additional_branches.py`
  - `tests/unit/governance/settings/test_llm_settings.py`
  - `tests/unit/governance/settings/test_notifications_core_slack.py`
  - `tests/unit/governance/settings/test_notifications_diagnostics_workflow.py`
  - `tests/unit/governance/test_jobs_api.py`

### Track CZ (#354)

- Title: Dashboard marketing, pricing, settings, and ops shell surfaces
- Paths: `37`
- Scope summary: Public marketing shell changes, pricing route/server restructuring, settings and ops UI decomposition, dashboard runtime/package updates, and related visual snapshot churn.
- Assigned paths:
  - `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-hero-desktop-linux.png`
  - `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-hero-mobile-linux.png`
  - `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-hook-desktop-linux.png`
  - `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-hook-mobile-linux.png`
  - `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-trust-desktop-linux.png`
  - `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-trust-mobile-linux.png`
  - `dashboard/e2e/public-marketing.spec.ts`
  - `dashboard/package.json`
  - `dashboard/pnpm-lock.yaml`
  - `dashboard/server.node.mjs`
  - `dashboard/src/lib/components/EnforcementSettingsCardView.svelte`
  - `dashboard/src/lib/components/IdentitySettingsCardContent.svelte`
  - `dashboard/src/lib/components/LandingHero.svelte`
  - `dashboard/src/lib/components/identity/identitySettingsRuntime.ts`
  - `dashboard/src/lib/components/landing/LandingHeroBelowFold.svelte`
  - `dashboard/src/lib/components/landing/LandingRoiSimulator.svelte`
  - `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts`
  - `dashboard/src/lib/landing/landingHeroScenario.ts`
  - `dashboard/src/lib/landing/landingScenarioMetrics.ts`
  - `dashboard/src/lib/landing/publicNav.ts`
  - `dashboard/src/routes/layout/PublicSiteFooter.svelte`
  - `dashboard/src/routes/ops/OpsOperationalHealthSection.svelte`
  - `dashboard/src/routes/ops/opsOperationalCoreActions.ts`
  - `dashboard/src/routes/ops/opsOperationalReliabilityActions.ts`
  - `dashboard/src/routes/ops/opsOperationalUnitActions.ts`
  - `dashboard/src/routes/pricing/+page.server.ts`
  - `dashboard/src/routes/pricing/+page.ts`
  - `dashboard/src/routes/pricing/pricing.load.test.ts`
  - `dashboard/src/routes/settings/SettingsDeferredSection.svelte`
  - `dashboard/src/routes/settings/SettingsNotificationControlsController.svelte`
  - `dashboard/src/routes/settings/SettingsPageViewBody.svelte`
  - `dashboard/src/routes/settings/SettingsPageViewContent.svelte`
  - `dashboard/src/routes/settings/SettingsWorkflowAutomationCard.svelte`
  - `dashboard/src/routes/settings/SettingsWorkflowProviderFields.svelte`
  - `dashboard/src/routes/settings/settings.app.css`
  - `dashboard/src/routes/settings/settingsNotificationRuntime.ts`
  - `dashboard/static/public-site-shell.css`

### Track DA (#355)

- Title: Managed deployment, local env generation, release readiness, and repo contracts
- Paths: `31`
- Scope summary: Managed deployment and local environment tooling, release-readiness verification, CI and repo contract updates, and deployment/runtime documentation with targeted operational tests.
- Assigned paths:
  - `.env.example`
  - `.github/workflows/ci.yml`
  - `.gitignore`
  - `Makefile`
  - `docker-compose.yml`
  - `docs/DEPLOYMENT.md`
  - `docs/runbooks/koyeb_release_promotion.md`
  - `docs/runbooks/production_env_checklist.md`
  - `scripts/generate_local_compose_env.py`
  - `scripts/generate_local_dev_env.py`
  - `scripts/generate_managed_deployment_artifacts.py`
  - `scripts/generate_managed_runtime_env.py`
  - `scripts/local_env_generation_shared.py`
  - `scripts/managed_deployment_contract.py`
  - `scripts/render_managed_deployment_handoff.py`
  - `scripts/render_managed_release_blocker_summary.py`
  - `scripts/verify_dashboard_runtime_contract.py`
  - `scripts/verify_documentation_runtime_contracts.py`
  - `scripts/verify_managed_release_readiness.py`
  - `tests/unit/ops/test_documentation_runtime_contracts.py`
  - `tests/unit/ops/test_generate_local_compose_env.py`
  - `tests/unit/ops/test_generate_managed_deployment_artifacts.py`
  - `tests/unit/ops/test_generate_managed_runtime_env.py`
  - `tests/unit/ops/test_local_dev_runtime_contracts.py`
  - `tests/unit/ops/test_managed_deployment_contract.py`
  - `tests/unit/ops/test_production_deployment_contracts.py`
  - `tests/unit/ops/test_render_managed_deployment_handoff.py`
  - `tests/unit/ops/test_render_managed_release_blocker_summary.py`
  - `tests/unit/ops/test_verify_dashboard_runtime_contract.py`
  - `tests/unit/ops/test_verify_documentation_runtime_contracts.py`
  - `tests/unit/ops/test_verify_managed_release_readiness.py`

### Track DB (#356)

- Title: Audit evidence, finance telemetry, seeding, remediation verification, and operational proof packs
- Paths: `24`
- Scope summary: Finance telemetry, disposition register and audit evidence updates, seeding helpers, remediation verification, and the supporting operational proof-pack tests.
- Assigned paths:
  - `README.md`
  - `docs/FULL_CODEBASE_AUDIT.md`
  - `docs/ops/evidence/exception_governance_baseline.json`
  - `docs/ops/evidence/pkg_fin_operational_readiness_2026-03-01.json`
  - `docs/ops/evidence/python_module_size_preferred_baseline.json`
  - `docs/ops/evidence/valdrics_disposition_register_2026-02-28.json`
  - `docs/ops/evidence/valdrics_disposition_register_TEMPLATE.json`
  - `scripts/collect_finance_telemetry_snapshot.py`
  - `scripts/generate_valdrics_disposition_register.py`
  - `scripts/seed_dev_data.py`
  - `scripts/seed_pricing_plans.py`
  - `scripts/test_tenant_import.py`
  - `scripts/verify_codebase_audit_report.py`
  - `scripts/verify_exception_governance.py`
  - `scripts/verify_pkg_fin_operational_readiness.py`
  - `scripts/verify_remediation.py`
  - `tests/unit/enforcement/test_key_rotation_drill_selectors.py`
  - `tests/unit/ops/test_generate_enforcement_failure_injection_evidence.py`
  - `tests/unit/ops/test_legacy_db_maintenance_scripts.py`
  - `tests/unit/ops/test_runtime_evidence_generators.py`
  - `tests/unit/ops/test_valdrics_disposition_register_pack.py`
  - `tests/unit/ops/test_verify_codebase_audit_report.py`
  - `tests/unit/ops/test_verify_exception_governance.py`
  - `tests/unit/ops/test_verify_pkg_fin_operational_readiness.py`

## Cleanup Pass

- Ignored local `__pycache__` directories were removed before packaging this batch.
- No additional clearly unwanted tracked `*.bak`, `*.orig`, `*.rej`, `*.pyc`, or tracked log artifacts were identified in the repo snapshot used for this register.
- Historical operational docs under `docs/ops/` were retained because they are tracked audit history, not disposable junk.
