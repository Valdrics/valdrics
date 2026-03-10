# Workstream Categorization: Follow-up Batch (2026-03-02)

This document categorizes the full follow-up local delta after PR `#217`.

## Inventory Source
- `docs/ops/evidence/all_changes_inventory_followup_2026-03-02.txt`
- Total changed paths: `16`
  - Modified: `12`
  - Added: `4`
  - Deleted: `0`

## Track P: Landing UX/accessibility polish + public discoverability
- Issue: https://github.com/Valdrics/valdrics/issues/218
- Scope:
  - Landing hero/trust/CTA polish
  - Reduced-motion helper + tests
  - Public route protection/nav additions
  - Blog route and sitemap coverage
- Files:
  - `dashboard/src/lib/components/LandingHero.svelte`
  - `dashboard/src/lib/components/LandingHero.svelte.test.ts`
  - `dashboard/src/lib/components/landing/LandingRoiPlannerCta.svelte`
  - `dashboard/src/lib/components/landing/LandingTrustSection.svelte`
  - `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts`
  - `dashboard/src/lib/landing/heroContent.ts`
  - `dashboard/src/lib/landing/publicNav.ts`
  - `dashboard/src/lib/landing/reducedMotion.ts`
  - `dashboard/src/lib/landing/reducedMotion.test.ts`
  - `dashboard/src/lib/routeProtection.ts`
  - `dashboard/src/lib/routeProtection.test.ts`
  - `dashboard/src/routes/sitemap.xml/+server.ts`
  - `dashboard/src/routes/sitemap.xml/sitemap.server.test.ts`
  - `dashboard/src/routes/blog/+page.server.ts`
  - `dashboard/src/routes/blog/blog-page.server.test.ts`

## Track Q: Ops landing audit closure evidence sync
- Issue: https://github.com/Valdrics/valdrics/issues/219
- Scope:
  - Audit closure document update
  - Snapshot evidence inventory for this follow-up batch
- Files:
  - `docs/ops/landing_page_audit_closure_2026-03-02.md`
  - `docs/ops/evidence/all_changes_inventory_followup_2026-03-02.txt`

## Merge intent
- One PR for this entire follow-up batch, linked to both track issues.
