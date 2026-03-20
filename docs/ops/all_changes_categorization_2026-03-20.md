# All Changes Categorization (2026-03-20)

Snapshot:
- Captured at: `2026-03-20T00:00:00Z`
- Base commit: `96bc2602f7717e5c460ea8435198b69141846fad`
- Pending paths: `46`
- Branch at snapshot: `main`

## Track BY: Frontend Landing Refresh, Public Shell, and Accessibility Coverage
Scope:
- Consolidate the landing hero refresh, public navigation shell, and first-fold copy changes in one frontend review lane.
- Keep the public accessibility browser coverage with the exact UI surfaces it exercises.
- Treat this as the browser-facing marketing shell track for the batch.

Paths:
- `dashboard/e2e/public-a11y.spec.ts`
- `dashboard/src/lib/components/LandingHero.hero-copy.primary.layout.css`
- `dashboard/src/lib/components/LandingHero.hero-copy.primary.support.css`
- `dashboard/src/lib/components/LandingHero.svelte.test.ts`
- `dashboard/src/lib/components/landing/LandingHeroCopy.svelte`
- `dashboard/src/lib/landing/heroContent.core.ts`
- `dashboard/src/routes/layout/PublicSiteShell.svelte`
- `dashboard/src/routes/layout/layoutPublicNav.css`

Notes:
- This is the same landing slice already opened in PR `#322`, so that PR will be reused as the merge vehicle for the full batch.

## Track BZ: Backend Jobs, Performance, SQLite Datetime, and LLM Runtime
Scope:
- Group governance jobs API behavior, performance testing utilities, SQLite datetime handling, session behavior, and LLM analyzer changes together.
- Keep direct backend regression suites and shared test harness updates in the same runtime review lane.
- Separate backend request-path and persistence behavior from artifact-generation automation.

Paths:
- `app/modules/governance/api/v1/jobs.py`
- `app/shared/core/performance_testing.py`
- `app/shared/db/session.py`
- `app/shared/db/sqlite_datetime.py`
- `app/shared/llm/analyzer.py`
- `tests/conftest.py`
- `tests/unit/core/test_performance_testing.py`
- `tests/unit/db/test_sqlite_datetime.py`
- `tests/unit/governance/test_jobs_api.py`
- `tests/unit/governance/test_jobs_api_direct.py`

Notes:
- This track captures backend runtime correctness and local SQLite compatibility work.

## Track CA: Evidence Generators, Finance Artifacts, and Operational Proof Packs
Scope:
- Consolidate enforcement, finance committee, pricing, telemetry, and key-rotation evidence generation changes in one operational evidence lane.
- Keep the paired verification and runtime-evidence tests with the scripts that emit those artifacts.
- Treat this as artifact-quality and evidence-integrity work, not request-path product behavior.

Paths:
- `scripts/generate_enforcement_failure_injection_evidence.py`
- `scripts/generate_enforcement_stress_evidence.py`
- `scripts/generate_finance_committee_packet.py`
- `scripts/generate_finance_committee_packet_assumptions.py`
- `scripts/generate_finance_telemetry_snapshot.py`
- `scripts/generate_key_rotation_drill_evidence.py`
- `scripts/generate_pkg_fin_policy_decisions.py`
- `scripts/generate_pricing_benchmark_register.py`
- `scripts/generate_valdrics_disposition_register.py`
- `tests/unit/ops/test_generate_enforcement_failure_injection_evidence.py`
- `tests/unit/ops/test_generate_finance_committee_packet.py`
- `tests/unit/ops/test_generate_finance_committee_packet_assumptions.py`
- `tests/unit/ops/test_generate_key_rotation_drill_evidence.py`
- `tests/unit/ops/test_generate_pkg_fin_policy_decisions.py`
- `tests/unit/ops/test_runtime_evidence_generators.py`
- `tests/unit/supply_chain/test_generate_enforcement_stress_evidence.py`

Notes:
- This track is evidence-pack and artifact-generation focused.

## Track CB: Managed Deployment, Local Bootstrap, Feature Matrix, and Provenance Automation
Scope:
- Batch local env generation, managed deployment artifacts, migration/runtime env generation, provenance manifest work, and feature enforceability automation together.
- Keep the associated ops and supply-chain verification suites in the same release-engineering lane.
- Separate deployment automation and provenance concerns from frontend and backend product behavior.

Paths:
- `scripts/generate_feature_enforceability_matrix.py`
- `scripts/generate_local_dev_env.py`
- `scripts/generate_managed_deployment_artifacts.py`
- `scripts/generate_managed_migration_env.py`
- `scripts/generate_managed_runtime_env.py`
- `scripts/generate_provenance_manifest.py`
- `tests/unit/ops/test_generate_local_dev_env.py`
- `tests/unit/ops/test_generate_managed_deployment_artifacts.py`
- `tests/unit/ops/test_generate_managed_migration_env.py`
- `tests/unit/ops/test_generate_managed_runtime_env.py`
- `tests/unit/supply_chain/test_feature_enforceability_matrix.py`
- `tests/unit/supply_chain/test_supply_chain_provenance.py`

Notes:
- This track is release-engineering and automation focused.

## Batching Decision
Decision:
- Merge as one consolidated PR by updating existing PR `#322`.

Reasoning:
- PR `#322` already carries the landing refresh subset of this batch, so opening another overlapping PR would create duplicate review surfaces and merge risk.
- The remaining backend runtime and automation changes are part of the same active worktree snapshot and can be closed together while preserving review accountability through the issue split.
- Reusing the existing PR reduces branch churn and leaves one merge path for the full March 20 batch.
