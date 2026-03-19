# All Changes Categorization (2026-03-19 Follow-Up)

Snapshot:
- Captured at: `2026-03-19T00:00:00Z`
- Base commit: `d5b6f18f17ce7a9daf341dd051bccf70f4c612ce`
- Pending paths: `99`
- Branch at snapshot: `chore/all-changes-categorization-2026-03-19-followup`

## Track BU: Frontend Shell, Landing, Audit, Ops, and Browser Coverage
Scope:
- Consolidate landing hero, audit page, ops page, settings page, and authenticated shell changes in one frontend review lane.
- Keep Playwright support, browser tests, route-load behavior, and shared frontend helpers together with the UI they exercise.
- Carry dashboard entitlements, persona, and command-palette changes in the same browser-surface track.

Paths:
- `dashboard/e2e/critical-paths.spec.ts`
- `dashboard/e2e/landing-layout-audit.spec.ts`
- `dashboard/e2e/landing.test.ts`
- `dashboard/e2e/public-marketing.spec.ts`
- `dashboard/e2e/support/e2eAuth.ts`
- `dashboard/src/app.html`
- `dashboard/src/hooks.server.test.ts`
- `dashboard/src/hooks.server.ts`
- `dashboard/src/lib/components/CommandPalette.svelte`
- `dashboard/src/lib/components/LandingHero.hero-copy.primary.layout.css`
- `dashboard/src/lib/components/LandingHero.hero-copy.primary.support.css`
- `dashboard/src/lib/components/LandingHero.motion.signal.css`
- `dashboard/src/lib/components/LandingHero.motion.surface.shell.css`
- `dashboard/src/lib/components/LandingHero.svelte`
- `dashboard/src/lib/components/LandingHero.svelte.test.ts`
- `dashboard/src/lib/components/landing/LandingHeroCopy.svelte`
- `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts`
- `dashboard/src/lib/landing/heroContent.core.ts`
- `dashboard/src/lib/persona.test.ts`
- `dashboard/src/lib/persona.ts`
- `dashboard/src/lib/testing/playwrightE2EAuth.test.ts`
- `dashboard/src/lib/testing/playwrightE2EAuth.ts`
- `dashboard/src/routes/+layout.server.ts`
- `dashboard/src/routes/+layout.svelte`
- `dashboard/src/routes/admin/health/+page.svelte`
- `dashboard/src/routes/audit/+page.svelte`
- `dashboard/src/routes/audit/AuditPageViewContent.svelte`
- `dashboard/src/routes/layout.server.load.test.ts`
- `dashboard/src/routes/layout/AppAuthenticatedShell.svelte`
- `dashboard/src/routes/ops/OpsOperationalHealthSection.svelte`
- `dashboard/src/routes/ops/ops-page.core.svelte.test.ts`
- `dashboard/src/routes/ops/ops-page.test.setup.ts`
- `dashboard/src/routes/ops/opsOperationalCoreActions.ts`
- `dashboard/src/routes/settings/SettingsPageViewContent.svelte`
- `dashboard/src/routes/settings/settings-page.core.svelte.test.ts`
- `dashboard/tests/e2e/dashboard_sniper.test.ts`
- `dashboard/tests/e2e/scenarios.test.ts`
- `dashboard/src/lib/entitlements.test.ts`
- `dashboard/src/lib/entitlements.ts`
- `dashboard/src/routes/audit/audit-page.svelte.test.ts`

Notes:
- This track is intentionally browser-heavy and spans public and authenticated dashboard surfaces.

## Track BV: Backend Governance, Reporting, Health, and Remediation Runtime
Scope:
- Group backend SCIM, profile settings, carbon and reconciliation routes, remediation helpers, and runtime health changes together.
- Keep the related backend regression suites for governance settings, reporting, jobs, zombies, and health behavior in the same review lane.
- Separate service-runtime behavior from docs or deployment automation so code-path risk is easier to review.

Paths:
- `app/modules/governance/api/v1/scim_group_route_ops.py`
- `app/modules/governance/api/v1/scim_user_route_ops.py`
- `app/modules/governance/api/v1/settings/profile.py`
- `app/modules/optimization/domain/remediation_execute_helpers.py`
- `app/modules/reporting/api/v1/carbon.py`
- `app/modules/reporting/api/v1/costs_reconciliation_routes.py`
- `app/shared/core/health.py`
- `tests/unit/api/v1/test_carbon.py`
- `tests/unit/core/test_health_extra.py`
- `tests/unit/governance/settings/test_identity_settings_high_impact_branches.py`
- `tests/unit/governance/settings/test_profile_settings.py`
- `tests/unit/modules/optimization/adapters/azure/conftest.py`
- `tests/unit/modules/optimization/adapters/azure/test_azure_next_gen.py`
- `tests/unit/services/jobs/test_job_handlers.py`
- `tests/unit/services/zombies/test_zombie_service_cloud_plus.py`
- `tests/unit/zombies/test_tier_gating_phase8.py`

Notes:
- This track is the backend runtime and API behavior slice of the follow-up batch.

## Track BW: Evidence Templates, Finance Artifacts, and Operational Proof Packs
Scope:
- Consolidate evidence templates, finance committee packet generation, enforcement failure or stress artifacts, and policy decision packs together.
- Keep the related verification and runtime-evidence tests with the artifact generators they exercise.
- Maintain one operational evidence review lane for finance, enforcement, pricing benchmark, and disposition outputs.

Paths:
- `docs/ops/evidence/enforcement_failure_injection_TEMPLATE.json`
- `docs/ops/evidence/enforcement_stress_artifact_TEMPLATE.json`
- `docs/ops/evidence/exception_governance_baseline.json`
- `docs/ops/evidence/finance_guardrails_TEMPLATE.json`
- `docs/ops/evidence/pkg_fin_policy_decisions_TEMPLATE.json`
- `docs/ops/evidence/pricing_benchmark_register_TEMPLATE.json`
- `docs/ops/evidence/valdrics_disposition_register_TEMPLATE.json`
- `scripts/finance_committee_packet_common.py`
- `scripts/generate_enforcement_failure_injection_evidence.py`
- `scripts/generate_enforcement_stress_evidence.py`
- `scripts/generate_finance_committee_packet.py`
- `scripts/generate_finance_committee_packet_assumptions.py`
- `scripts/generate_finance_telemetry_snapshot.py`
- `scripts/generate_key_rotation_drill_evidence.py`
- `scripts/generate_pkg_fin_policy_decisions.py`
- `scripts/generate_pricing_benchmark_register.py`
- `scripts/generate_valdrics_disposition_register.py`
- `scripts/pkg_fin_policy_decisions_parsers.py`
- `scripts/verify_finance_telemetry_snapshot.py`
- `tests/unit/ops/test_generate_enforcement_failure_injection_evidence.py`
- `tests/unit/ops/test_generate_finance_committee_packet.py`
- `tests/unit/ops/test_generate_finance_committee_packet_assumptions.py`
- `tests/unit/ops/test_generate_key_rotation_drill_evidence.py`
- `tests/unit/ops/test_generate_pkg_fin_policy_decisions.py`
- `tests/unit/ops/test_runtime_evidence_generators.py`
- `tests/unit/ops/test_verify_finance_telemetry_snapshot.py`
- `tests/unit/ops/test_verify_pkg_fin_policy_decisions.py`
- `tests/unit/supply_chain/test_generate_enforcement_stress_evidence.py`

Notes:
- This track is artifact and evidence oriented rather than request-path oriented.

## Track BX: CI, Managed Deployment, Local Bootstrap, and Provenance Automation
Scope:
- Batch CI workflow adjustments, managed deployment generators, local env/bootstrap helpers, provenance manifest generation, and release template checks together.
- Keep feature enforceability, managed environment, and provenance verification suites in the same automation review lane.
- Separate deployment and supply-chain automation from frontend and backend product behavior.

Paths:
- `.github/workflows/ci.yml`
- `scripts/generate_feature_enforceability_matrix.py`
- `scripts/generate_local_dev_env.py`
- `scripts/generate_managed_deployment_artifacts.py`
- `scripts/generate_managed_migration_env.py`
- `scripts/generate_managed_runtime_env.py`
- `scripts/generate_provenance_manifest.py`
- `scripts/smoke_test_local_sqlite_bootstrap.py`
- `tests/unit/ops/test_generate_local_dev_env.py`
- `tests/unit/ops/test_generate_managed_deployment_artifacts.py`
- `tests/unit/ops/test_generate_managed_migration_env.py`
- `tests/unit/ops/test_generate_managed_runtime_env.py`
- `tests/unit/ops/test_release_artifact_templates_pack.py`
- `tests/unit/supply_chain/test_feature_enforceability_matrix.py`
- `tests/unit/supply_chain/test_supply_chain_provenance.py`

Notes:
- This track is release-engineering and automation focused.

## Batching Decision
Decision:
- Merge as one consolidated PR.

Reasoning:
- The snapshot is still one active worktree batch even though it spans frontend shell follow-up, backend route changes, evidence artifacts, and deployment automation.
- Splitting it further would add extra PR overhead while still crossing the same landing, health, SCIM, carbon, and artifact generation contracts.
- The issue split preserves accountability and review lanes without fragmenting the delivery batch.
