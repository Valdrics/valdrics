# All Changes Categorization (2026-04-01)

Snapshot:
- Captured at: `2026-04-01T00:00:00Z`
- Base commit: `b21f2ebdb5447f3b5d47b29f60616e657b9c29e1`
- Pending paths: `148`
- Branch at snapshot: `main`

## Track CU: Backend Runtime, Billing, Scheduler, Safety, and Core Regression Coverage
Scope:
- Group backend runtime, billing, scheduler, optimization, circuit-breaker, retry, rate-limit, session, and safety-service changes together.
- Keep the aligned integration, security, core, DB, governance, LLM, notifications, optimization, remediation, services, shared DB, and task regression suites in the same backend review lane.
- Treat this as the backend runtime and correctness slice of the batch.

Paths:
- `app/main.py`
- `app/modules/billing/domain/billing/paystack_client_impl.py`
- `app/modules/governance/domain/scheduler/orchestrator.py`
- `app/modules/governance/domain/scheduler/processors.py`
- `app/modules/notifications/domain/slack.py`
- `app/modules/optimization/domain/actions/aws/rds.py`
- `app/modules/optimization/domain/remediation_execute.py`
- `app/shared/core/celery_app.py`
- `app/shared/core/circuit_breaker.py`
- `app/shared/core/currency.py`
- `app/shared/core/performance_benchmarking.py`
- `app/shared/core/performance_testing.py`
- `app/shared/core/pricing_cache.py`
- `app/shared/core/rate_limit.py`
- `app/shared/core/retry.py`
- `app/shared/core/safety_service.py`
- `app/shared/core/timeout.py`
- `app/shared/db/session.py`
- `app/shared/llm/circuit_breaker.py`
- `app/shared/llm/hybrid_scheduler.py`
- `app/shared/remediation/circuit_breaker.py`
- `app/tasks/scheduler_sweep_ops.py`
- `app/tasks/scheduler_sweep_runtime.py`
- `app/tasks/scheduler_tasks.py`
- `tests/integration/test_edge_cases.py`
- `tests/security/test_rls_security.py`
- `tests/unit/core/test_circuit_breaker_core.py`
- `tests/unit/core/test_circuit_breaker_distributed.py`
- `tests/unit/core/test_currency.py`
- `tests/unit/core/test_currency_deep.py`
- `tests/unit/core/test_db_session_deep.py`
- `tests/unit/core/test_main.py`
- `tests/unit/core/test_performance_testing.py`
- `tests/unit/core/test_pricing_cache.py`
- `tests/unit/core/test_rate_limit_expanded.py`
- `tests/unit/core/test_retry_utils.py`
- `tests/unit/core/test_safety_service_audit.py`
- `tests/unit/core/test_session_audit.py`
- `tests/unit/core/test_timeout_utils.py`
- `tests/unit/db/test_session_deep.py`
- `tests/unit/db/test_session_exhaustive.py`
- `tests/unit/governance/scheduler/test_orchestrator_branches.py`
- `tests/unit/llm/test_circuit_breaker.py`
- `tests/unit/llm/test_hybrid_scheduler_exhaustive.py`
- `tests/unit/notifications/domain/test_slack_service.py`
- `tests/unit/optimization/test_remediation_branch_coverage.py`
- `tests/unit/remediation/test_circuit_breaker_deep.py`
- `tests/unit/services/billing/test_currency_service.py`
- `tests/unit/services/billing/test_paystack_billing.py`
- `tests/unit/services/scheduler/test_scheduler_processors.py`
- `tests/unit/services/zombies/test_remediation_service.py`
- `tests/unit/shared/db/test_session_coverage.py`
- `tests/unit/tasks/test_scheduler_funnel_ops.py`
- `tests/unit/tasks/test_scheduler_sweep_runtime.py`
- `tests/unit/tasks/test_scheduler_tasks_branch_paths_2.py`
- `tests/unit/tasks/test_scheduler_tasks_reliability.py`

Notes:
- This track contains all `app/` changes and the aligned backend test coverage excluding script-focused tests.

## Track CV: Dashboard Landing, Content, Settings, and Public Route Surfaces
Scope:
- Consolidate landing hero, public content, docs or insights or proof or resources routes, settings surfaces, enforcement or identity cards, and dashboard UI sections together.
- Keep the Svelte component tests, route tests, and page-server motion coverage with the exact dashboard and public surfaces they exercise.
- Treat this as the frontend product-surface slice of the batch.

Paths:
- `dashboard/src/lib/components/EnforcementSettingsAdvancedSection.svelte`
- `dashboard/src/lib/components/EnforcementSettingsCard.svelte`
- `dashboard/src/lib/components/EnforcementSettingsCard.svelte.test.ts`
- `dashboard/src/lib/components/EnforcementSettingsCardView.svelte`
- `dashboard/src/lib/components/FindingsTable.svelte`
- `dashboard/src/lib/components/FindingsTable.svelte.test.ts`
- `dashboard/src/lib/components/FindingsTableDetailBody.svelte`
- `dashboard/src/lib/components/IdentitySettingsCard.svelte`
- `dashboard/src/lib/components/IdentitySettingsCard.svelte.test.ts`
- `dashboard/src/lib/components/IdentitySettingsCardContent.svelte`
- `dashboard/src/lib/components/LandingHero.svelte`
- `dashboard/src/lib/components/LandingHero.svelte.test.ts`
- `dashboard/src/lib/components/identity/IdentityDiagnosticsSection.svelte`
- `dashboard/src/lib/components/identity/IdentityScimSection.svelte`
- `dashboard/src/lib/components/landing/LandingCurrencyToggle.svelte`
- `dashboard/src/lib/components/landing/LandingHeroBelowFold.svelte`
- `dashboard/src/lib/components/landing/LandingHeroRoiPlaceholder.svelte`
- `dashboard/src/lib/components/landing/LandingHeroTrustSections.svelte`
- `dashboard/src/lib/components/landing/LandingHeroView.svelte`
- `dashboard/src/lib/components/landing/LandingHeroView.svelte.test.ts`
- `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts`
- `dashboard/src/lib/components/public/PublicContentArticlePage.svelte`
- `dashboard/src/lib/components/public/PublicContentArticlePage.svelte.test.ts`
- `dashboard/src/lib/components/public/PublicPageMeta.svelte`
- `dashboard/src/lib/landing/currencyDisplay.ts`
- `dashboard/src/lib/landing/currencyPreference.test.ts`
- `dashboard/src/lib/landing/currencyPreference.ts`
- `dashboard/src/lib/landing/geoCurrency.ts`
- `dashboard/src/lib/landing/landingCurrencyPolicy.ts`
- `dashboard/src/lib/landing/landingHeroScenario.ts`
- `dashboard/src/lib/landing/landingRoiDefaults.ts`
- `dashboard/src/lib/landing/roiCalculator.ts`
- `dashboard/src/public.app.css`
- `dashboard/src/routes/+page.server.ts`
- `dashboard/src/routes/+page.svelte`
- `dashboard/src/routes/api/geo/currency/+server.ts`
- `dashboard/src/routes/docs/+page.server.ts`
- `dashboard/src/routes/docs/+page.svelte`
- `dashboard/src/routes/docs/[slug]/+page.server.ts`
- `dashboard/src/routes/docs/[slug]/+page.svelte`
- `dashboard/src/routes/docs/[slug]/+page.ts`
- `dashboard/src/routes/docs/docs-page.svelte.test.ts`
- `dashboard/src/routes/insights/+page.server.ts`
- `dashboard/src/routes/insights/+page.svelte`
- `dashboard/src/routes/insights/[slug]/+page.server.ts`
- `dashboard/src/routes/insights/[slug]/+page.svelte`
- `dashboard/src/routes/insights/[slug]/+page.ts`
- `dashboard/src/routes/insights/insights-page.svelte.test.ts`
- `dashboard/src/routes/layout-public-menu.svelte.test.ts`
- `dashboard/src/routes/layout/PublicMobileMenuDialog.svelte`
- `dashboard/src/routes/layout/PublicSiteFooter.svelte`
- `dashboard/src/routes/layout/PublicSiteShell.svelte`
- `dashboard/src/routes/onboarding/OnboardingPageView.svelte`
- `dashboard/src/routes/onboarding/OnboardingPageViewContent.svelte`
- `dashboard/src/routes/onboarding/onboarding-page.svelte.test.ts`
- `dashboard/src/routes/ops/OpsOperationalHealthSection.svelte`
- `dashboard/src/routes/ops/ops-page.core.svelte.test.ts`
- `dashboard/src/routes/page.server.motion.test.ts`
- `dashboard/src/routes/proof/+page.server.ts`
- `dashboard/src/routes/proof/+page.svelte`
- `dashboard/src/routes/proof/[slug]/+page.server.ts`
- `dashboard/src/routes/proof/[slug]/+page.svelte`
- `dashboard/src/routes/proof/[slug]/+page.ts`
- `dashboard/src/routes/proof/proof-page.svelte.test.ts`
- `dashboard/src/routes/resources/+page.server.ts`
- `dashboard/src/routes/resources/+page.svelte`
- `dashboard/src/routes/resources/[slug]/+page.server.ts`
- `dashboard/src/routes/resources/[slug]/+page.svelte`
- `dashboard/src/routes/resources/[slug]/+page.ts`
- `dashboard/src/routes/resources/resources-page.svelte.test.ts`
- `dashboard/src/routes/roi-planner/+page.server.ts`
- `dashboard/src/routes/roi-planner/+page.svelte`
- `dashboard/src/routes/roi-planner/page.server.test.ts`
- `dashboard/src/routes/roi-planner/roi-planner-page.svelte.test.ts`
- `dashboard/src/routes/settings/SettingsDeferredSection.svelte`
- `dashboard/src/routes/settings/SettingsNotificationControls.svelte`
- `dashboard/src/routes/settings/SettingsPageViewBody.svelte`
- `dashboard/src/routes/settings/SettingsPageViewContent.svelte`
- `dashboard/src/routes/settings/settings-page.advanced.svelte.test.ts`
- `dashboard/src/routes/settings/settings-page.core.svelte.test.ts`
- `dashboard/src/routes/settings/settings.app.css`

Notes:
- This track contains all `dashboard/` path changes in the batch.

## Track CW: Operational Tooling, Frontend Hygiene, SCIM Smoke, and Exchange-Rate Utilities
Scope:
- Batch frontend-hygiene verification, API load testing, RLS optimization, SCIM smoke scripts, and exchange-rate utility changes together.
- Keep the direct script-focused regression suites with the tooling they validate.
- Treat this as the operational tooling and verification slice of the batch.

Paths:
- `scripts/check_frontend_hygiene.py`
- `scripts/load_test_api.py`
- `scripts/run_rls_optimization.py`
- `scripts/smoke_test_scim_helpers.py`
- `scripts/smoke_test_scim_idp.py`
- `scripts/update_exchange_rates.py`
- `tests/unit/core/test_load_test_api_script.py`
- `tests/unit/core/test_smoke_test_scim_helpers.py`
- `tests/unit/ops/test_check_frontend_hygiene.py`
- `tests/unit/ops/test_legacy_db_maintenance_scripts.py`
- `tests/unit/ops/test_smoke_test_scim_idp.py`

Notes:
- This track contains the script changes and their direct script-oriented tests.

## Batching Decision
Decision:
- Merge as one consolidated PR to `main`.

Reasoning:
- The batch is one active runtime and frontend follow-up spanning backend scheduler and safety work, public-content and settings surfaces, and operational tooling updates together.
- The issue split preserves review accountability without fragmenting the delivery batch across overlapping runtime, frontend, and tooling surfaces.
- No clearly unwanted tracked docs or artifacts were found in this batch; ignored `__pycache__` files were cleaned outside the tracked diff.
