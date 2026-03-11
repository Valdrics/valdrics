# All Changes Categorization Register (2026-03-11)

Generated from live `git status --porcelain --untracked-files=all` on branch `fix/gh-actions-2026-03-10`.

## Summary

- Total changed paths: 86
- Modified paths: 66
- New/untracked paths: 15
- Deleted paths: 5
- Renamed paths: 0
- Active merge vehicle: PR `#269` (`fix: repair workflow parsing and security gate failures`)

## Track Rollup

| Track | Scope | Path Count | Tracking Issue |
|---|---|---:|---|
| Track AC - Licensing and Commercial Policy | BUSL/BSL licensing terms, commercial policy pages, public legal messaging, and related product-policy docs. | 12 | #270 |
| Track AD - Public Frontend and Funnel | Landing/enterprise/public-route UX, CTA attribution flow, preview support, Playwright coverage, and visual snapshots. | 44 | #271 |
| Track AE - Runtime Config and Managed Validation Gates | Runtime/config logging branch-path hardening plus managed deployment, public frontend, and documentation contract verification gates. | 15 | #272 |
| Track AF - Docs Archive Hygiene and Historical Moves | Move superseded dated ops docs into archive space and enforce archive hygiene rules against active-tree drift. | 15 | #273 |

## Notes

- This batch keeps the existing open PR `#269` as the consolidation and merge path instead of opening a second overlapping PR.
- The archived ops docs are moved, not discarded; the new archive hygiene gate is part of this batch.
- Public frontend changes include updated Playwright snapshots under `dashboard/e2e/landing-visual.spec.ts-snapshots/`.

## Full Inventory By Track

### Track AC - Licensing and Commercial Policy (12)

Tracking issue: `#270`

| Status | Path |
|---|---|
| `M` | `COMMERCIAL_LICENSE.md` |
| `M` | `CONTRIBUTING.md` |
| `M` | `LICENSE` |
| `M` | `README.md` |
| `M` | `TRADEMARK_POLICY.md` |
| `M` | `docs/CAPACITY_PLAN.md` |
| `M` | `docs/architecture/tiering-2026.md` |
| `M` | `docs/licensing.md` |
| `M` | `docs/open_core_boundary.md` |
| `M` | `docs/roadmap.md` |
| `M` | `docs/runbooks/production_env_checklist.md` |
| `M` | `docs/runbooks/webhook_job_reliability_drill.md` |

### Track AD - Public Frontend and Funnel (44)

Tracking issue: `#271`

| Status | Path |
|---|---|
| `M` | `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-hero-desktop-linux.png` |
| `M` | `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-hero-mobile-linux.png` |
| `M` | `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-hook-desktop-linux.png` |
| `M` | `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-hook-mobile-linux.png` |
| `M` | `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-trust-desktop-linux.png` |
| `M` | `dashboard/e2e/landing-visual.spec.ts-snapshots/landing-trust-mobile-linux.png` |
| `M` | `dashboard/e2e/public-a11y.spec.ts` |
| `M` | `dashboard/e2e/public-marketing.spec.ts` |
| `M` | `dashboard/package.json` |
| `M` | `dashboard/playwright.config.ts` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte` |
| `M` | `dashboard/src/lib/components/LandingHero.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/landing/LandingCapabilitiesSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingCloudHookSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroView.svelte` |
| `M` | `dashboard/src/lib/components/landing/LandingHeroView.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/landing/LandingPlansSection.svelte` |
| `M` | `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts` |
| `M` | `dashboard/src/lib/components/public/PublicContentArticlePage.svelte` |
| `M` | `dashboard/src/lib/components/public/PublicContentArticlePage.svelte.test.ts` |
| `M` | `dashboard/src/lib/content/publicContent.docs.ts` |
| `M` | `dashboard/src/lib/content/publicContent.insights.ts` |
| `M` | `dashboard/src/lib/content/publicContent.proof.ts` |
| `M` | `dashboard/src/lib/content/publicContent.resources.ts` |
| `M` | `dashboard/src/lib/landing/landingExperiment.test.ts` |
| `M` | `dashboard/src/lib/landing/landingExperiment.ts` |
| `M` | `dashboard/src/lib/landing/landingHeroActions.ts` |
| `M` | `dashboard/src/lib/landing/landingHeroLinks.ts` |
| `M` | `dashboard/src/lib/landing/publicNav.test.ts` |
| `M` | `dashboard/src/lib/landing/publicNav.ts` |
| `M` | `dashboard/src/routes/enterprise/+page.svelte` |
| `M` | `dashboard/src/routes/enterprise/enterprise-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/insights/+page.svelte` |
| `M` | `dashboard/src/routes/insights/insights-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/layout-public-menu.svelte.test.ts` |
| `M` | `dashboard/src/routes/pricing/+page.svelte` |
| `M` | `dashboard/src/routes/pricing/pricing-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/proof/+page.svelte` |
| `M` | `dashboard/src/routes/proof/proof-page.svelte.test.ts` |
| `M` | `dashboard/src/routes/resources/+page.svelte` |
| `M` | `dashboard/src/routes/resources/resources-page.svelte.test.ts` |
| `??` | `dashboard/scripts/sync-preview-static-assets.mjs` |
| `??` | `dashboard/src/lib/public/publicBuyingMotion.test.ts` |
| `??` | `dashboard/src/lib/public/publicBuyingMotion.ts` |

### Track AE - Runtime Config and Managed Validation Gates (15)

Tracking issue: `#272`

| Status | Path |
|---|---|
| `M` | `Makefile` |
| `M` | `app/shared/core/config.py` |
| `M` | `app/shared/core/config_validation.py` |
| `M` | `app/shared/core/runtime_dependencies.py` |
| `M` | `app/shared/db/connect_args.py` |
| `M` | `scripts/verify_documentation_runtime_contracts.py` |
| `M` | `tests/unit/core/test_config_branch_paths.py` |
| `M` | `tests/unit/core/test_runtime_dependencies.py` |
| `M` | `tests/unit/db/test_session_branch_paths_2.py` |
| `M` | `tests/unit/ops/test_documentation_runtime_contracts.py` |
| `M` | `tests/unit/ops/test_verify_documentation_runtime_contracts.py` |
| `??` | `scripts/run_public_frontend_quality_gate.py` |
| `??` | `scripts/verify_managed_deployment_bundle.py` |
| `??` | `tests/unit/ops/test_run_public_frontend_quality_gate.py` |
| `??` | `tests/unit/ops/test_verify_managed_deployment_bundle.py` |

### Track AF - Docs Archive Hygiene and Historical Moves (15)

Tracking issue: `#273`

| Status | Path |
|---|---|
| `M` | `docs/archive/README.md` |
| `M` | `docs/ops/README.md` |
| `D` | `docs/ops/all_changes_categorization_2026-03-04.md` |
| `D` | `docs/ops/all_changes_categorization_2026-03-10.md` |
| `D` | `docs/ops/deep_debt_remediation_2026-03-06.md` |
| `D` | `docs/ops/fresh_audit_remediation_2026-03-05.md` |
| `D` | `docs/ops/parallel_backend_hardening_2026-03-05.md` |
| `??` | `docs/archive/ops/2026-q1/all_changes_categorization_2026-03-04.md` |
| `??` | `docs/archive/ops/2026-q1/all_changes_categorization_2026-03-10.md` |
| `??` | `docs/archive/ops/2026-q1/deep_debt_remediation_2026-03-06.md` |
| `??` | `docs/archive/ops/2026-q1/fresh_audit_remediation_2026-03-05.md` |
| `??` | `docs/archive/ops/2026-q1/parallel_backend_hardening_2026-03-05.md` |
| `??` | `docs/ops/all_changes_categorization_2026-03-11.md` |
| `??` | `scripts/verify_docs_archive_hygiene.py` |
| `??` | `tests/unit/ops/test_verify_docs_archive_hygiene.py` |

