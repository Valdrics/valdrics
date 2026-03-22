# All Changes Categorization (2026-03-22)

Snapshot:
- Captured at: `2026-03-22T00:00:00Z`
- Base commit: `d9faf99f4064d5c3317dc7b3b1511c0b64f5f059`
- Pending paths: `103`
- Branch at snapshot: `main`

## Track CC: Frontend Landing Composition, Runtime, and Visual System
Scope:
- Consolidate landing hero composition, runtime behavior, calculator logic, and visual system changes in one frontend implementation lane.
- Keep component-level tests and browser runtime helpers with the exact landing modules they exercise.
- Treat this as the core landing implementation track separate from route wiring and public content pages.

Paths:
- `dashboard/src/lib/components/LandingHero.hero-copy.primary.layout.css`
- `dashboard/src/lib/components/LandingHero.metrics-demo.css`
- `dashboard/src/lib/components/LandingHero.motion.surface.shell.css`
- `dashboard/src/lib/components/LandingHero.motion.surface.story.css`
- `dashboard/src/lib/components/LandingHero.roi-plans.free.css`
- `dashboard/src/lib/components/LandingHero.roi-plans.simulator.css`
- `dashboard/src/lib/components/LandingHero.signal-preview.approval-chain.css`
- `dashboard/src/lib/components/LandingHero.signal-preview.shell.css`
- `dashboard/src/lib/components/LandingHero.svelte`
- `dashboard/src/lib/components/LandingHero.svelte.test.ts`
- `dashboard/src/lib/components/LandingHero.trust.details.css`
- `dashboard/src/lib/components/LandingHero.trust.plan-rollout.css`
- `dashboard/src/lib/components/landing/LandingCurrencyToggle.svelte`
- `dashboard/src/lib/components/landing/LandingHeroCopy.svelte`
- `dashboard/src/lib/components/landing/LandingHeroView.public.css`
- `dashboard/src/lib/components/landing/LandingHeroView.svelte`
- `dashboard/src/lib/components/landing/LandingHeroView.svelte.test.ts`
- `dashboard/src/lib/components/landing/LandingHumanProofStrip.svelte`
- `dashboard/src/lib/components/landing/LandingOutcomeBand.svelte`
- `dashboard/src/lib/components/landing/LandingPlansSection.svelte`
- `dashboard/src/lib/components/landing/LandingProductSection.svelte`
- `dashboard/src/lib/components/landing/LandingRoiCalculator.svelte`
- `dashboard/src/lib/components/landing/LandingRoiPlannerCta.svelte`
- `dashboard/src/lib/components/landing/LandingRoiSimulator.svelte`
- `dashboard/src/lib/components/landing/LandingSignalMapCard.svelte`
- `dashboard/src/lib/components/landing/LandingTrustSection.svelte`
- `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts`
- `dashboard/src/lib/landing/currencyPreference.test.ts`
- `dashboard/src/lib/landing/currencyPreference.ts`
- `dashboard/src/lib/landing/heroContent.core.ts`
- `dashboard/src/lib/landing/landingHeroBrowserRuntime.ts`
- `dashboard/src/lib/landing/landingHeroRuntime.ts`
- `dashboard/src/lib/landing/publicNav.ts`
- `dashboard/src/lib/landing/roiCalculator.test.ts`
- `dashboard/src/lib/landing/roiCalculator.ts`
- `dashboard/src/lib/public/publicTheme.test.ts`
- `dashboard/src/lib/public/publicTheme.ts`

Notes:
- This track is the primary landing-build surface for the batch.

## Track CD: Public Routes, Marketing Content, and Browser Coverage
Scope:
- Batch public route pages, public marketing content, marketing API wiring, and browser or visual coverage together.
- Keep the public shell, navigation layout, article components, and e2e coverage in the same review lane.
- Separate route and content behavior from backend notification and reporting work.

Paths:
- `dashboard/e2e/critical-paths.spec.ts`
- `dashboard/e2e/landing-layout-audit.spec.ts`
- `dashboard/e2e/landing-visual.spec.ts`
- `dashboard/e2e/landing.test.ts`
- `dashboard/e2e/public-a11y.spec.ts`
- `dashboard/e2e/public-marketing.spec.ts`
- `dashboard/src/lib/components/public/PublicContentArticlePage.svelte`
- `dashboard/src/lib/components/public/PublicMarketingPage.article.css`
- `dashboard/src/lib/components/public/PublicMarketingPage.layout.css`
- `dashboard/src/lib/components/public/PublicMarketingPage.svelte`
- `dashboard/src/lib/components/public/PublicPageMeta.svelte`
- `dashboard/src/lib/content/publicCompany.ts`
- `dashboard/src/lib/content/publicContent.docs.ts`
- `dashboard/src/lib/content/publicContent.insights.ts`
- `dashboard/src/lib/content/publicContent.proof.ts`
- `dashboard/src/lib/content/publicContent.test.ts`
- `dashboard/src/routes/+layout.svelte`
- `dashboard/src/routes/about/+page.svelte`
- `dashboard/src/routes/about/about-page.svelte.test.ts`
- `dashboard/src/routes/api/marketing/talk-to-sales/+server.ts`
- `dashboard/src/routes/api/marketing/talk-to-sales/talk-to-sales.server.test.ts`
- `dashboard/src/routes/auth/login/+page.svelte`
- `dashboard/src/routes/auth/login/login-page.svelte.test.ts`
- `dashboard/src/routes/docs/+page.svelte`
- `dashboard/src/routes/docs/docs-page.svelte.test.ts`
- `dashboard/src/routes/enterprise/+page.svelte`
- `dashboard/src/routes/enterprise/enterprise-page.svelte.test.ts`
- `dashboard/src/routes/layout-public-menu.svelte.test.ts`
- `dashboard/src/routes/layout/PublicSiteShell.svelte`
- `dashboard/src/routes/layout/layoutPublicNav.css`
- `dashboard/src/routes/pricing/+page.svelte`
- `dashboard/src/routes/pricing/pricing-page.css`
- `dashboard/src/routes/pricing/pricing-page.svelte.test.ts`
- `dashboard/src/routes/privacy/+page.svelte`
- `dashboard/src/routes/privacy/privacy-page.svelte.test.ts`
- `dashboard/src/routes/proof/+page.svelte`
- `dashboard/src/routes/proof/proof-page.svelte.test.ts`
- `dashboard/src/routes/resources/+page.svelte`
- `dashboard/src/routes/resources/resources-page.svelte.test.ts`
- `dashboard/src/routes/roi-planner/+page.svelte`
- `dashboard/src/routes/talk-to-sales/+page.svelte`
- `dashboard/src/routes/talk-to-sales/talk-to-sales-page-content.ts`
- `dashboard/src/routes/talk-to-sales/talk-to-sales-page.svelte.test.ts`
- `dashboard/src/routes/terms/+page.svelte`
- `dashboard/src/routes/terms/terms-page.svelte.test.ts`
- `dashboard/svelte.config.js`
- `dashboard/tests/e2e/dashboard_sniper.test.ts`
- `dashboard/tests/e2e/scenarios.test.ts`

Notes:
- This track is the route-level and browser-coverage slice of the public web experience.

## Track CE: Backend Public Marketing, Reporting, Notifications, and Data Contracts
Scope:
- Group public marketing API behavior, notification delivery, reporting cost routes, and shared dependency updates together.
- Keep schema, migration, model, and backend regression tests in the same runtime review lane.
- Treat this as the backend implementation slice supporting the public and reporting surfaces.

Paths:
- `app/models/public_sales_inquiry.py`
- `app/modules/governance/api/v1/public_marketing.py`
- `app/modules/governance/domain/jobs/handlers/notifications.py`
- `app/modules/notifications/domain/email_service.py`
- `app/modules/reporting/api/v1/costs.py`
- `app/modules/reporting/api/v1/costs_core_endpoints.py`
- `app/modules/reporting/api/v1/costs_http_routes_core.py`
- `app/shared/core/dependencies.py`
- `migrations/versions/w9x0y1z2a3b_add_public_sales_inquiry_buyer_region.py`
- `tests/unit/api/v1/test_costs_endpoints_core.py`
- `tests/unit/core/test_dependencies.py`
- `tests/unit/core/test_load_test_api_script.py`
- `tests/unit/governance/api/test_public.py`
- `tests/unit/llm/test_analyzer_branch_edges.py`
- `tests/unit/notifications/domain/test_email_service.py`

Notes:
- This track captures backend runtime, persistence, and API contract changes for the batch.

## Track CF: Public Positioning, Architecture, and Audit Collateral
Scope:
- Consolidate product-positioning, architecture-decision, and audit collateral changes in one documentation lane.
- Keep public-market narrative and recorded implementation evidence together for review clarity.
- Separate supporting documentation from the code-path changes it describes.

Paths:
- `docs/architecture/ADR-0005-paystack-over-stripe.md`
- `docs/product/launch-market-positioning.md`
- `reports/audit/LANDING_PUBLIC_IMPLEMENTATION_REPORT_2026-03-21.md`

Notes:
- This track is the documentation and collateral slice of the batch.

## Batching Decision
Decision:
- Merge as one consolidated PR.

Reasoning:
- The batch is one active worktree snapshot spanning public web experience, backend support paths, and documentation collateral for the same launch surface.
- The issue split preserves accountability and review lanes without fragmenting the delivery batch into overlapping PRs.
- Keeping the batch together avoids branch churn across tightly related landing, marketing API, notification, and pricing-surface changes.
