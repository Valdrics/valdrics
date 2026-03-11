# All Changes Categorization Register (2026-03-11 Follow-Up)

Generated from the live branch delta on `fix/main-actions-2026-03-11` against `origin/main`, plus the current uncommitted worktree state.

## Summary

- Total changed paths in branch scope: 71
- Existing committed PR paths already on `#274`: 24
- Additional local modified/untracked paths: 49
- Active merge vehicle: PR `#274` (`fix: restore main GitHub Actions reliability`)

## Track Rollup

| Track | Scope | Path Count | Tracking Issue |
|---|---|---:|---|
| Track AG - CI, Deployment, and Supply-Chain Hardening | GitHub Actions repair, DAST/SBOM/security scan hardening, container/runtime contract alignment, deployment docs, and release verification evidence. | 20 | `#276` |
| Track AH - Runtime Security and Configuration Contracts | Runtime env validation, proxy/rate-limit/middleware hardening, DB/session and scheduler safety, remediation circuit-breaker behavior, and supporting regression tests. | 22 | `#277` |
| Track AI - Billing, LLM, and Encrypted Data Safeguards | Billing/LLM API behavior, ORM encryption coverage, pricing/runtime safety, and related validation tests. | 9 | `#278` |
| Track AJ - Public Web Navigation and Website Source of Truth | Landing/about/public-route UX, sitemap and route-protection behavior, public nav wiring, and website evidence documentation. | 20 | `#275` |

## Notes

- This follow-up batch reuses the existing open PR `#274` rather than creating a second overlapping merge path.
- The branch already contains the earlier CI restoration commits; this document covers that committed scope plus the current local frontend/runtime follow-up changes.
- `dashboard/src/routes/auth/login/+page.svelte` remains in the CI/deployment track because it was changed to remove DAST-time SSR failures in ephemeral environments.

## Full Inventory By Track

### Track AG - CI, Deployment, and Supply-Chain Hardening (20)

Tracking issue: `#276`

| Status | Path |
|---|---|
| `M` | `.github/workflows/ci.yml` |
| `M` | `.github/workflows/sbom.yml` |
| `M` | `.github/workflows/security-scan.yml` |
| `M` | `DEPLOYMENT.md` |
| `M` | `Dockerfile` |
| `M` | `dashboard/src/routes/auth/login/+page.svelte` |
| `M` | `docker-compose.yml` |
| `M` | `docs/DEPLOYMENT.md` |
| `M` | `koyeb-worker.yaml` |
| `??` | `scripts/docker-entrypoint.sh` |
| `M` | `scripts/generate_managed_deployment_artifacts.py` |
| `M` | `scripts/run_public_frontend_quality_gate.py` |
| `M` | `scripts/verify_supply_chain_attestations.py` |
| `??` | `tests/unit/ops/test_env_tracking_contract.py` |
| `M` | `tests/unit/ops/test_generate_managed_deployment_artifacts.py` |
| `M` | `tests/unit/ops/test_production_deployment_contracts.py` |
| `M` | `tests/unit/ops/test_validate_migration_env.py` |
| `M` | `tests/unit/ops/test_validate_runtime_env.py` |
| `M` | `tests/unit/supply_chain/test_supply_chain_provenance_workflow.py` |
| `M` | `tests/unit/supply_chain/test_verify_supply_chain_attestations.py` |

### Track AH - Runtime Security and Configuration Contracts (22)

Tracking issue: `#277`

| Status | Path |
|---|---|
| `??` | `app/shared/core/bools.py` |
| `M` | `app/shared/core/config.py` |
| `M` | `app/shared/core/config_validation.py` |
| `M` | `app/shared/core/config_validation_observability.py` |
| `A` | `app/shared/core/config_validation_placeholders.py` |
| `M` | `app/shared/core/config_validation_runtime.py` |
| `M` | `app/shared/core/cors_policy.py` |
| `M` | `app/shared/core/error_governance.py` |
| `M` | `app/shared/core/middleware.py` |
| `M` | `app/shared/core/migration_settings.py` |
| `M` | `app/shared/core/proxy_headers.py` |
| `M` | `app/shared/core/rate_limit.py` |
| `M` | `app/shared/db/session.py` |
| `M` | `app/shared/remediation/autonomous.py` |
| `M` | `app/shared/remediation/circuit_breaker.py` |
| `M` | `app/tasks/scheduler_tasks.py` |
| `M` | `tests/core/test_circuit_breaker.py` |
| `M` | `tests/unit/core/test_config_branch_paths.py` |
| `M` | `tests/unit/core/test_middleware.py` |
| `M` | `tests/unit/core/test_migration_settings.py` |
| `M` | `tests/unit/core/test_rate_limit_branch_paths_2.py` |
| `M` | `tests/unit/db/test_session_branch_paths_2.py` |

### Track AI - Billing, LLM, and Encrypted Data Safeguards (9)

Tracking issue: `#278`

| Status | Path |
|---|---|
| `M` | `app/models/__init__.py` |
| `M` | `app/models/_encryption.py` |
| `M` | `app/modules/billing/api/v1/billing.py` |
| `M` | `app/modules/governance/api/v1/settings/llm.py` |
| `M` | `app/shared/llm/budget_manager.py` |
| `M` | `app/shared/llm/factory.py` |
| `M` | `app/shared/llm/pricing_data.py` |
| `??` | `tests/security/test_orm_encryption_key_resolution.py` |
| `M` | `tests/unit/api/v1/test_billing.py` |

### Track AJ - Public Web Navigation and Website Source of Truth (20)

Tracking issue: `#275`

| Status | Path |
|---|---|
| `M` | `dashboard/src/hooks.server.test.ts` |
| `M` | `dashboard/src/hooks.server.ts` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/LandingHero.trust.details.css` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroView.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroView.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/landing/LandingTrustSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts` |
| `M` | `dashboard/src/lib/landing/publicNav.test.ts` |
| `M` | `dashboard/src/lib/landing/publicNav.ts` |
| `M` | `dashboard/src/lib/routeProtection.test.ts` |
| `M` | `dashboard/src/lib/routeProtection.ts` |
| `??` | `dashboard/src/routes/about/+page.svelte` |
| `??` | `dashboard/src/routes/about/about-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/resources/resources-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/sitemap.xml/+server.ts` |
| `M` | `dashboard/src/routes/sitemap.xml/sitemap.server.test.ts` |
| `??` | `docs/ops/website_review_source_of_truth_2026-03-11.md` |
| `??` | `docs/ops/all_changes_categorization_2026-03-11_followup.md` |
