# All Changes Categorization (2026-03-13 Follow-up)

Branch snapshot date: 2026-03-13  
Base branch for this batch: `origin/main` @ `b6976f857abfe96c8d174813db1d0b5a75bdc206`

## Summary

- Total changed paths in this batch: `44`
- Scope: runtime/bootstrap contracts, governance public/docs surface, carbon scheduler reliability, and operational evidence/safety scripts.
- Note: the earlier CLA migration from PR `#289` is already in `origin/main`; it is not a new delta in this follow-up batch.

## Track BA: Runtime Contracts, Deployment Inputs, and Documentation Surface (`#290`)

Intent: tighten runtime path/config wiring, managed deployment artifact generation, deployment contract coverage, and contributor/runtime docs alignment.

Paths:
- `CONTRIBUTING.md`
- `app/main.py`
- `app/shared/core/config.py`
- `app/shared/core/docs_assets.py`
- `app/shared/core/migration_settings.py`
- `app/shared/core/runtime_paths.py`
- `helm/valdrics/Chart.yaml`
- `koyeb.yaml`
- `koyeb-worker.yaml`
- `scripts/generate_managed_deployment_artifacts.py`
- `scripts/in_process_runtime_env.py`
- `tests/unit/core/test_main.py`
- `tests/unit/core/test_runtime_paths.py`
- `tests/unit/ops/test_generate_managed_deployment_artifacts.py`
- `tests/unit/ops/test_production_deployment_contracts.py`
- `tests/unit/supply_chain/test_supply_chain_provenance_workflow.py`
- `tests/unit/test_main_coverage.py`

## Track BB: Governance Public Endpoints, Docs Route Protection, and Customer-Comment Admin Paths (`#291`)

Intent: align public/governance surfaces with docs delivery, dashboard route protection, and admin customer-comment handling.

Paths:
- `app/modules/governance/api/v1/public.py`
- `app/static/redoc.standalone.js`
- `dashboard/src/hooks.server.test.ts`
- `dashboard/src/lib/routeProtection.ts`
- `dashboard/src/lib/routeProtection.test.ts`
- `dashboard/src/routes/api/admin/customer-comments/+server.ts`
- `dashboard/src/routes/api/admin/customer-comments/customer-comments-admin.server.test.ts`
- `dashboard/src/routes/docs/+page.svelte`
- `dashboard/src/routes/docs/docs-page.svelte.test.ts`
- `tests/unit/governance/api/test_public.py`

## Track BC: Carbon Budgeting, Scheduler Orchestration, and Cost Handler Reliability (`#292`)

Intent: harden carbon alert scheduling/orchestration, job handler behavior, and the API/test coverage around those flows.

Paths:
- `app/modules/governance/domain/jobs/handlers/costs.py`
- `app/modules/governance/domain/scheduler/orchestrator.py`
- `app/modules/reporting/api/v1/carbon.py`
- `app/modules/reporting/domain/carbon_scheduler.py`
- `tests/unit/api/v1/test_carbon.py`
- `tests/unit/governance/domain/jobs/handlers/test_cost_handlers.py`
- `tests/unit/governance/scheduler/test_orchestrator.py`
- `tests/unit/modules/reporting/test_carbon_scheduler_comprehensive.py`

## Track BD: Cloud Safety, Acceptance Bootstrap, and Operational Evidence Scripts (`#293`)

Intent: improve operator tooling, AWS deactivation/safety handling, webhook reliability drill evidence, and related helper scripts.

Paths:
- `app/shared/connections/aws.py`
- `scripts/capture_acceptance_bootstrap.py`
- `scripts/deactivate_aws.py`
- `scripts/emergency_disconnect.py`
- `scripts/generate_enforcement_stress_evidence.py`
- `scripts/generate_key_rotation_drill_evidence.py`
- `scripts/run_webhook_job_reliability_drill.py`
- `scripts/safety_guardrails.py`
- `scripts/simple_token.py`
- `scripts/verify_key_rotation_drill_evidence.py`

## Path Inventory

| Status | Path |
|---|---|
| `M` | `CONTRIBUTING.md` |
| `M` | `app/main.py` |
| `M` | `app/modules/governance/api/v1/public.py` |
| `M` | `app/modules/governance/domain/jobs/handlers/costs.py` |
| `M` | `app/modules/governance/domain/scheduler/orchestrator.py` |
| `M` | `app/modules/reporting/api/v1/carbon.py` |
| `M` | `app/modules/reporting/domain/carbon_scheduler.py` |
| `M` | `app/shared/connections/aws.py` |
| `M` | `app/shared/core/config.py` |
| `M` | `app/shared/core/docs_assets.py` |
| `M` | `app/shared/core/migration_settings.py` |
| `??` | `app/shared/core/runtime_paths.py` |
| `??` | `app/static/redoc.standalone.js` |
| `M` | `dashboard/src/hooks.server.test.ts` |
| `M` | `dashboard/src/lib/routeProtection.test.ts` |
| `M` | `dashboard/src/lib/routeProtection.ts` |
| `M` | `dashboard/src/routes/api/admin/customer-comments/+server.ts` |
| `M` | `dashboard/src/routes/api/admin/customer-comments/customer-comments-admin.server.test.ts` |
| `M` | `dashboard/src/routes/docs/+page.svelte` |
| `M` | `dashboard/src/routes/docs/docs-page.svelte.test.ts` |
| `M` | `helm/valdrics/Chart.yaml` |
| `M` | `koyeb-worker.yaml` |
| `M` | `koyeb.yaml` |
| `M` | `scripts/capture_acceptance_bootstrap.py` |
| `M` | `scripts/deactivate_aws.py` |
| `D` | `scripts/emergency_disconnect.py` |
| `M` | `scripts/generate_enforcement_stress_evidence.py` |
| `M` | `scripts/generate_key_rotation_drill_evidence.py` |
| `M` | `scripts/generate_managed_deployment_artifacts.py` |
| `??` | `scripts/in_process_runtime_env.py` |
| `M` | `scripts/run_webhook_job_reliability_drill.py` |
| `M` | `scripts/safety_guardrails.py` |
| `M` | `scripts/simple_token.py` |
| `M` | `scripts/verify_key_rotation_drill_evidence.py` |
| `M` | `tests/unit/api/v1/test_carbon.py` |
| `M` | `tests/unit/core/test_main.py` |
| `??` | `tests/unit/core/test_runtime_paths.py` |
| `M` | `tests/unit/governance/api/test_public.py` |
| `M` | `tests/unit/governance/domain/jobs/handlers/test_cost_handlers.py` |
| `M` | `tests/unit/governance/scheduler/test_orchestrator.py` |
| `M` | `tests/unit/modules/reporting/test_carbon_scheduler_comprehensive.py` |
| `M` | `tests/unit/ops/test_generate_managed_deployment_artifacts.py` |
| `M` | `tests/unit/ops/test_production_deployment_contracts.py` |
| `M` | `tests/unit/supply_chain/test_supply_chain_provenance_workflow.py` |
| `M` | `tests/unit/test_main_coverage.py` |
