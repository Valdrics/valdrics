# All Changes Categorization (2026-03-18)

Snapshot:
- Captured at: `2026-03-18T00:00:00Z`
- Base commit: `c89a4e9b2386e3c7f032a5fbd4452f043fadee5d`
- Pending paths: `105`
- Branch at snapshot: `chore/all-changes-categorization-2026-03-18`

## Track BM: Optimization, Remediation, Savings Proof, and Findings Pipeline
Scope:
- Group backend changes for optimization findings, remediation workflows, zombie handling, realized savings, and savings proof generation.
- Keep the related enforcement runtime/export hooks and migration for optimization request binding in the same control path review lane.
- Carry the matching optimization, savings, zombie, and remediation regression suites together.

Paths:
- `app/models/optimization.py`
- `app/models/realized_savings.py`
- `app/models/remediation.py`
- `app/modules/enforcement/domain/export_bundle_ops.py`
- `app/modules/enforcement/domain/service_runtime_ops.py`
- `app/modules/optimization/api/v1/zombies.py`
- `app/modules/optimization/domain/remediation.py`
- `app/modules/optimization/domain/remediation_credentials.py`
- `app/modules/optimization/domain/remediation_execute.py`
- `app/modules/optimization/domain/remediation_iac.py`
- `app/modules/optimization/domain/remediation_workflow.py`
- `app/modules/optimization/domain/service.py`
- `app/modules/reporting/api/v1/savings.py`
- `app/modules/reporting/domain/realized_savings.py`
- `app/modules/reporting/domain/savings_proof.py`
- `app/modules/reporting/domain/savings_proof_drilldown_ops.py`
- `app/shared/llm/zombie_analyzer.py`
- `tests/api/test_endpoints_zombies_plan_policy.py`
- `tests/api/test_endpoints_zombies_scan_requests.py`
- `tests/governance/test_detector.py`
- `tests/integration/optimization/test_remediation_lifecycle.py`
- `tests/unit/api/v1/test_savings_branch_paths.py`
- `tests/unit/enforcement/test_export_bundle_ops_regressions.py`
- `tests/unit/modules/optimization/domain/test_remediation_credentials.py`
- `tests/unit/optimization/test_remediation_branch_coverage.py`
- `tests/unit/optimization/test_remediation_region_resolution.py`
- `tests/unit/optimization/test_remediation_service_audit.py`
- `tests/unit/optimization/test_zombie_service_audit.py`
- `tests/unit/reporting/test_realized_savings_service_branches.py`
- `tests/unit/reporting/test_savings_api_branches.py`
- `tests/unit/reporting/test_savings_proof_api.py`
- `tests/unit/services/llm/test_zombie_analyzer_logic.py`
- `tests/unit/services/zombies/test_remediation_service.py`
- `tests/unit/zombies/test_zombies_api_branches.py`
- `app/modules/optimization/domain/findings.py`
- `migrations/versions/v8w9x0y1z2a_add_optimization_findings_and_request_binding.py`

Notes:
- This is the main product-runtime backend slice for cost-actioning and savings proof behavior.

## Track BN: Frontend Public Experience, Ops UX, and Savings Interfaces
Scope:
- Batch the public shell, landing, legal, status, sitemap, robots, and progressive enhancement updates together.
- Keep the savings and remediation UI components with their route-level and end-to-end tests.
- Treat the operator-facing dashboard refinements as one frontend review lane.

Paths:
- `dashboard/e2e/public-marketing.spec.ts`
- `dashboard/src/app.utilities.css`
- `dashboard/src/lib/components/FindingsTable.svelte`
- `dashboard/src/lib/components/FindingsTable.svelte.test.ts`
- `dashboard/src/lib/components/RemediationModal.svelte`
- `dashboard/src/lib/components/ZombieTable.svelte`
- `dashboard/src/routes/+layout.svelte`
- `dashboard/src/routes/+page.svelte`
- `dashboard/src/routes/layout/PublicSiteShell.svelte`
- `dashboard/src/routes/ops/OpsBacklogSection.svelte`
- `dashboard/src/routes/ops/OpsPageViewContent.svelte`
- `dashboard/src/routes/ops/ops-page.remediation.svelte.test.ts`
- `dashboard/src/routes/ops/ops-page.test.setup.ts`
- `dashboard/src/routes/ops/opsTypes.ts`
- `dashboard/src/routes/privacy/+page.svelte`
- `dashboard/src/routes/privacy/privacy-page.svelte.test.ts`
- `dashboard/src/routes/savings/+page.svelte`
- `dashboard/src/routes/savings/SavingsPageViewContent.svelte`
- `dashboard/src/routes/savings/savings-page.svelte.test.ts`
- `dashboard/src/routes/savings/savingsTypes.ts`
- `dashboard/src/routes/sitemap.xml/+server.ts`
- `dashboard/src/routes/sitemap.xml/sitemap.server.test.ts`
- `dashboard/src/routes/status/+page.svelte`
- `dashboard/src/routes/status/status-page.svelte.test.ts`
- `dashboard/src/routes/terms/+page.svelte`
- `dashboard/src/routes/terms/terms-page.svelte.test.ts`
- `dashboard/e2e/public-progressive-enhancement.spec.ts`
- `dashboard/src/lib/components/RemediationModal.svelte.test.ts`
- `dashboard/src/lib/components/ZombieTable.svelte.test.ts`
- `dashboard/src/routes/robots.txt/robots.server.test.ts`

Notes:
- This track is intentionally frontend-heavy and spans public pages plus authenticated ops and savings screens.

## Track BO: Runtime Platform, Security, and API Contract Hardening
Scope:
- Group app bootstrap, health, DB session, CI workflow, and security-sensitive API contract changes together.
- Keep the associated endpoint, privilege, health, and main import coverage in the same platform review lane.
- Separate runtime/platform hardening from feature and ops-script work so the risk profile is easier to review.

Paths:
- `.github/workflows/ci.yml`
- `app/main.py`
- `app/shared/core/health.py`
- `app/shared/db/session.py`
- `migrations/env.py`
- `tests/api/test_api_endpoints.py`
- `tests/api/test_endpoints_security_auth.py`
- `tests/api/test_endpoints_validation_jobs.py`
- `tests/conftest.py`
- `tests/security/test_privilege_escalation.py`
- `tests/unit/core/test_health_deep.py`
- `tests/unit/db/test_session_branch_paths_2.py`
- `tests/unit/test_main_coverage.py`

Notes:
- This track is the platform/runtime contract slice of the batch.

## Track BP: Operational Evidence, Provenance, Finance Guardrails, and Runbooks
Scope:
- Consolidate evidence-generation, provenance, finance committee, key rotation, and disposition verification tooling updates.
- Keep the runbook and ops documentation refresh in the same operational evidence review lane.
- Carry the matching ops and supply-chain verification tests together.

Paths:
- `docs/ops/key-rotation-drill-2026-02-27.md`
- `scripts/finance_committee_packet_assumptions_engine.py`
- `scripts/finance_committee_packet_common.py`
- `scripts/generate_enforcement_failure_injection_evidence.py`
- `scripts/generate_feature_enforceability_matrix.py`
- `scripts/generate_key_rotation_drill_evidence.py`
- `scripts/generate_local_dev_env.py`
- `scripts/generate_pkg_fin_policy_decisions.py`
- `scripts/generate_provenance_manifest.py`
- `scripts/verify_finance_guardrails_evidence.py`
- `scripts/verify_key_rotation_drill_evidence.py`
- `scripts/verify_valdrics_disposition_freshness.py`
- `tests/governance/test_audit_phase_1.py`
- `tests/unit/ops/test_generate_enforcement_failure_injection_evidence.py`
- `tests/unit/ops/test_generate_finance_committee_packet_assumptions.py`
- `tests/unit/ops/test_generate_local_dev_env.py`
- `tests/unit/ops/test_key_rotation_drill_evidence_pack.py`
- `tests/unit/ops/test_runtime_evidence_generators.py`
- `tests/unit/ops/test_verify_finance_guardrails_evidence.py`
- `tests/unit/ops/test_verify_key_rotation_drill_evidence.py`
- `tests/unit/ops/test_verify_repo_root_hygiene.py`
- `tests/unit/ops/test_verify_valdrics_disposition_freshness.py`
- `tests/unit/supply_chain/test_feature_enforceability_matrix.py`
- `tests/unit/supply_chain/test_supply_chain_provenance.py`
- `docs/runbooks/aws_first_operator_flow.md`
- `tests/unit/ops/test_generate_key_rotation_drill_evidence.py`

Notes:
- This track is operational and release-gate oriented rather than end-user feature work.

## Batching Decision
Decision:
- Merge as one consolidated PR.

Reasoning:
- The frontend, backend, runtime, and ops evidence changes are broad, but they are part of one active worktree snapshot and are now tracked through separate review lanes.
- Splitting this snapshot further would add PR overhead while still crossing the same remediation, savings, platform, and verification contracts.
- The issue split preserves accountability without fragmenting the actual delivery batch.
