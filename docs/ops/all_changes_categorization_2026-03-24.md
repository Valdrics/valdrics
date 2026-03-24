# All Changes Categorization (2026-03-24)

Snapshot:
- Captured at: `2026-03-24T00:00:00Z`
- Base commit: `1e95d99760090ba0784c0bb2c532c13a6d8fa21f`
- Pending paths: `28`
- Branch at snapshot: `main`

## Track CJ: Dashboard Hero Capture Automation, Fixture, and Generated Asset
Scope:
- Consolidate dashboard hero capture automation, the dedicated capture route, fixture wiring, and generated still asset changes in one review lane.
- Keep the capture script migration and capture-only route surfaces together so the artifact flow stays auditable.
- Treat this as the image-capture and fixture-generation slice of the batch.

Paths:
- `dashboard/scripts/capture-dashboard-hero-still.mjs`
- `dashboard/scripts/capture-dashboard-hero-still.ts`
- `dashboard/src/routes/__capture/dashboard-hero/+page.server.ts`
- `dashboard/src/routes/__capture/dashboard-hero/+page.svelte`
- `dashboard/src/routes/dashboard/dashboardHeroCaptureFixture.ts`
- `dashboard/static/landing-dashboard-still.jpg`

Notes:
- This track is focused on dashboard-hero still capture workflow changes.

## Track CK: Public Shell Styling and Landing Hero View Surfaces
Scope:
- Batch public shell styling, landing hero view changes, and related landing-view tests together.
- Keep shared public layout CSS and the public-site shell in the same review lane as the landing view they present.
- Treat this as the public visual-shell slice of the batch.

Paths:
- `dashboard/src/app.components-layout.css`
- `dashboard/src/app.utilities.css`
- `dashboard/src/lib/components/LandingHero.svelte.test.ts`
- `dashboard/src/lib/components/landing/LandingHeroView.public.css`
- `dashboard/src/lib/components/landing/LandingHeroView.svelte`
- `dashboard/src/lib/components/landing/LandingHeroView.svelte.test.ts`
- `dashboard/src/lib/components/public/PublicMarketingPage.layout.css`
- `dashboard/src/routes/layout/PublicSiteShell.svelte`
- `dashboard/src/routes/layout/layoutPublicNav.css`
- `dashboard/static/public-site-shell.css`

Notes:
- This track is the public visual presentation layer for the follow-up batch.

## Track CL: Authenticated Shell Guarding and Route Protection Contracts
Scope:
- Group route protection logic, authenticated shell updates, and shell-specific styling together.
- Keep the route protection tests with the runtime contract they validate.
- Treat this as the authenticated-shell control and contract slice of the batch.

Paths:
- `dashboard/src/lib/routeProtection.test.ts`
- `dashboard/src/lib/routeProtection.ts`
- `dashboard/src/routes/layout/AppAuthenticatedShell.svelte`
- `dashboard/static/authenticated-shell.css`

Notes:
- This track captures authenticated-shell behavior and guarding changes.

## Track CM: Ops Capture and SCIM Smoke Automation
Scope:
- Group the operational capture, bootstrap, and SCIM smoke-test scripts together with their direct regression suites.
- Keep script-level validation in one automation lane separate from dashboard-shell rendering changes.
- Treat this as the supporting ops automation slice of the batch.

Paths:
- `scripts/bootstrap_performance_tenant.py`
- `scripts/capture_carbon_assurance_evidence.py`
- `scripts/smoke_test_scim_helpers.py`
- `scripts/smoke_test_scim_idp.py`
- `tests/unit/core/test_smoke_test_scim_helpers.py`
- `tests/unit/ops/test_bootstrap_performance_tenant.py`
- `tests/unit/ops/test_capture_carbon_assurance_evidence.py`
- `tests/unit/ops/test_smoke_test_scim_idp.py`

Notes:
- This track captures the supporting operational automation that landed with the shell follow-up batch.

## Batching Decision
Decision:
- Merge as one consolidated PR to `main`.

Reasoning:
- The batch is one focused dashboard-shell follow-up spanning capture automation, landing-view presentation, authenticated-shell guarding, and supporting ops automation.
- Splitting it further would create overlapping PRs across the same shell and capture surfaces.
- The issue split preserves accountability without fragmenting a small, tightly related batch.
