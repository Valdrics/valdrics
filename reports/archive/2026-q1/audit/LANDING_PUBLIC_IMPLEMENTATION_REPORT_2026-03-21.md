# Landing/Public Remediation Implementation Report

Date: 2026-03-21

## Status

- Implementation status: complete for the landing/public remediation plan.
- Public validation status: complete.
- Authenticated browser validation status: complete.
- Managed deployment bundle verification status: passing for both staging and production.
- Promotion readiness: not yet ready because operator/runtime placeholders and release metadata blockers still exist.

## Plan Matrix

| Plan area | Implemented in | Validation |
| --- | --- | --- |
| Market positioning and company trust | `docs/product/launch-market-positioning.md`, `dashboard/src/lib/content/publicCompany.ts`, `dashboard/src/routes/about/+page.svelte`, `dashboard/src/lib/landing/publicNav.ts` | `dashboard/src/routes/about/about-page.svelte.test.ts`, `dashboard/e2e/public-marketing.spec.ts`, `dashboard/e2e/public-a11y.spec.ts` |
| Landing IA simplification and shorter narrative | `dashboard/src/lib/components/landing/LandingHeroView.svelte`, `dashboard/src/lib/components/landing/LandingOutcomeBand.svelte`, `dashboard/src/lib/components/landing/LandingProductSection.svelte`, `dashboard/src/lib/components/landing/LandingHumanProofStrip.svelte` | `dashboard/src/lib/components/landing/LandingHeroView.svelte.test.ts`, `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts`, `dashboard/e2e/landing-layout-audit.spec.ts`, `dashboard/e2e/public-marketing.spec.ts` |
| First-fold/hero upgrade | `dashboard/src/lib/components/LandingHero.svelte`, `dashboard/src/lib/components/landing/LandingHeroCopy.svelte`, `dashboard/src/lib/landing/heroContent.core.ts`, `dashboard/src/lib/components/LandingHero.hero-copy.primary.layout.css`, `dashboard/src/lib/components/LandingHero.hero-copy.primary.support.css` | `dashboard/src/lib/components/LandingHero.svelte.test.ts`, `dashboard/e2e/landing.test.ts`, `dashboard/e2e/public-a11y.spec.ts` |
| Currency policy and ROI behavior | `dashboard/src/lib/landing/currencyPreference.ts`, `dashboard/src/lib/components/landing/LandingRoiSimulator.svelte`, `dashboard/src/lib/components/landing/LandingRoiCalculator.svelte`, `dashboard/src/lib/components/landing/LandingRoiPlannerCta.svelte`, `dashboard/src/routes/roi-planner/+page.svelte`, `dashboard/src/lib/landing/landingHeroBrowserRuntime.ts`, `dashboard/src/lib/landing/landingHeroRuntime.ts` | `dashboard/src/lib/landing/currencyPreference.test.ts`, `dashboard/src/lib/components/LandingHero.svelte.test.ts`, `dashboard/e2e/public-marketing.spec.ts` |
| CSP cleanup and no-inline-style posture | `dashboard/src/lib/components/landing/LandingHeroCopy.svelte`, `dashboard/src/lib/components/landing/LandingSignalMapCard.svelte`, `dashboard/src/lib/components/landing/LandingRoiSimulator.svelte`, `dashboard/src/lib/components/landing/LandingRoiPlannerCta.svelte`, `dashboard/src/routes/auth/login/+page.svelte`, `dashboard/svelte.config.js` | `dashboard/src/routes/auth/login/login-page.svelte.test.ts`, `dashboard/e2e/public-marketing.spec.ts`, `dashboard/e2e/public-a11y.spec.ts` |
| Product proof simplification | `dashboard/src/lib/components/landing/LandingSignalMapCard.svelte`, `dashboard/src/lib/components/LandingHero.signal-preview.approval-chain.css`, `dashboard/src/lib/components/LandingHero.signal-preview.shell.css`, `dashboard/src/lib/components/LandingHero.motion.surface.story.css` | `dashboard/src/lib/components/landing/landing_decomposition.svelte.test.ts`, `dashboard/e2e/landing-layout-audit.spec.ts` |
| Landing pricing teaser and dark-theme continuity | `dashboard/src/lib/components/landing/LandingPlansSection.svelte`, `dashboard/src/lib/components/LandingHero.roi-plans.simulator.css`, `dashboard/src/lib/components/LandingHero.roi-plans.free.css` | `dashboard/e2e/public-marketing.spec.ts`, `dashboard/e2e/public-a11y.spec.ts` |
| Trust/proof/residency/human signal | `dashboard/src/lib/components/landing/LandingTrustSection.svelte`, `dashboard/src/lib/content/publicContent.proof.ts`, `dashboard/src/lib/content/publicContent.docs.ts`, `dashboard/src/lib/content/publicContent.insights.ts`, `dashboard/src/lib/components/landing/LandingHumanProofStrip.svelte` | `dashboard/src/lib/content/publicContent.test.ts`, `dashboard/e2e/public-marketing.spec.ts`, `dashboard/e2e/public-a11y.spec.ts` |
| Procurement/legal/privacy diligence path | `dashboard/src/routes/enterprise/+page.svelte`, `dashboard/src/routes/privacy/+page.svelte`, `dashboard/src/routes/terms/+page.svelte` | `dashboard/src/routes/enterprise/enterprise-page.svelte.test.ts`, `dashboard/src/routes/privacy/privacy-page.svelte.test.ts`, `dashboard/src/routes/terms/terms-page.svelte.test.ts` |
| Talk-to-sales buyer region capture | `dashboard/src/routes/talk-to-sales/+page.svelte`, `dashboard/src/routes/talk-to-sales/talk-to-sales-page-content.ts`, `dashboard/src/routes/api/marketing/talk-to-sales/+server.ts`, `app/modules/governance/api/v1/public_marketing.py`, `app/models/public_sales_inquiry.py`, `migrations/versions/w9x0y1z2a3b_add_public_sales_inquiry_buyer_region.py` | `dashboard/src/routes/talk-to-sales/talk-to-sales-page.svelte.test.ts`, `dashboard/src/routes/api/marketing/talk-to-sales/talk-to-sales.server.test.ts`, `tests/unit/governance/api/test_public.py`, `tests/unit/notifications/domain/test_email_service.py` |
| Mobile control-foundations layout fix | `dashboard/src/lib/components/LandingHero.trust.details.css`, `dashboard/src/lib/components/LandingHero.trust.plan-rollout.css` | `dashboard/e2e/landing-layout-audit.spec.ts`, `dashboard/e2e/public-a11y.spec.ts` |
| Authenticated shell/network clean-up discovered during rollout | `app/shared/core/dependencies.py`, `app/modules/reporting/api/v1/costs_http_routes_core.py`, `app/modules/reporting/api/v1/costs_core_endpoints.py`, `app/modules/reporting/api/v1/costs.py` | `tests/unit/core/test_dependencies.py`, `tests/unit/api/v1/test_costs_endpoints_core.py`, `dashboard/e2e/authenticated-shell.spec.ts`, `dashboard/e2e/critical-paths.spec.ts` |

## Validation Summary

Public/browser validation already completed before this report:

- `pnpm -C dashboard lint`
- `pnpm -C dashboard check`
- `pnpm -C dashboard build`
- `pnpm -C dashboard check:bundle`
- `pnpm -C dashboard exec playwright test e2e/public-marketing.spec.ts e2e/public-a11y.spec.ts --workers=1`
- `pnpm -C dashboard exec playwright test e2e/landing.test.ts e2e/landing-layout-audit.spec.ts --workers=1`

Authenticated and backend validation completed in the final follow-up:

- `uv run pytest tests/unit/core/test_dependencies.py tests/unit/api/v1/test_costs_endpoints_core.py -q`
- `uv run ruff check app/shared/core/dependencies.py app/modules/reporting/api/v1/costs_http_routes_core.py app/modules/reporting/api/v1/costs_core_endpoints.py app/modules/reporting/api/v1/costs.py tests/unit/core/test_dependencies.py tests/unit/api/v1/test_costs_endpoints_core.py`
- `pnpm -C dashboard exec playwright test e2e/critical-paths.spec.ts --grep "dashboard loads with key metrics" --workers=1`
- `pnpm -C dashboard exec playwright test e2e/authenticated-shell.spec.ts e2e/critical-paths.spec.ts tests/e2e/scenarios.test.ts tests/e2e/dashboard_sniper.test.ts --workers=1`

Procurement-surface validation completed in the final audit pass:

- `pnpm -C dashboard check`
- `pnpm -C dashboard exec vitest --run src/routes/enterprise/enterprise-page.svelte.test.ts src/routes/privacy/privacy-page.svelte.test.ts src/routes/terms/terms-page.svelte.test.ts`

## Deployment Readiness Verification

Managed bundle verification now passes for both environments:

- `uv run python scripts/verify_managed_deployment_bundle.py --environment staging`
- `uv run python scripts/verify_managed_deployment_bundle.py --environment production`

The verification failure originally found in production was not a runtime code defect. It was stale generated metadata:

- `.runtime/production.report.json` was out of sync with `.runtime/production.env`
- `.runtime/deploy/production/deployment.report.json` predated the current `koyeb-dashboard-env.json` and `koyeb-release.json` artifact contract

Those generated files were refreshed without changing operator-entered env values:

- `.runtime/production.report.json`
- `.runtime/deploy/production/deployment.report.json`
- `.runtime/deploy/production/koyeb-dashboard-env.json`
- `.runtime/deploy/production/koyeb-release.json`

Deployment artifact inspection after that refresh confirmed that the repository still contains scaffold values, not promotable live values:

- `.runtime/deploy/staging/koyeb-release.json`
- `.runtime/deploy/production/koyeb-release.json`
- `.runtime/deploy/staging/koyeb-dashboard-env.json`
- `.runtime/deploy/production/koyeb-dashboard-env.json`
- `.runtime/deploy/staging/koyeb-secrets.json`
- `.runtime/deploy/production/koyeb-secrets.json`
- `.runtime/staging.env`
- `.runtime/production.env`

No immutable image tag/digest source of truth exists in the repository beyond scaffold defaults and unit-test fixtures. Promotion remains blocked on operator-provided release metadata and secrets.

## Current Deployment Blockers

### Staging

- Runtime blockers: `API_URL`, `AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN`, `DATABASE_URL`, `FRONTEND_URL`, `GROQ_API_KEY`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `PAYSTACK_PUBLIC_KEY`, `PAYSTACK_SECRET_KEY`, `REDIS_URL`, `SENTRY_DSN`, `SUPABASE_JWT_SECRET`, `TRUSTED_PROXY_CIDRS`
- Dashboard public env blockers: `PUBLIC_API_URL`, `PUBLIC_SUPABASE_ANON_KEY`, `PUBLIC_SUPABASE_URL`
- Release blockers: `release_tag`, API/dashboard/worker image refs and digests
- Terraform remaining inputs: `external_id`, `valdrics_account_id`

### Production

- Runtime blockers: `API_URL`, `AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN`, `DATABASE_URL`, `FRONTEND_URL`, `GROQ_API_KEY`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `PAYSTACK_PUBLIC_KEY`, `PAYSTACK_SECRET_KEY`, `REDIS_URL`, `SENTRY_DSN`, `SUPABASE_JWT_SECRET`, `TRUSTED_PROXY_CIDRS`
- Dashboard public env blockers: `PUBLIC_API_URL`, `PUBLIC_SUPABASE_ANON_KEY`, `PUBLIC_SUPABASE_URL`
- Release blockers: `release_tag`, API/dashboard/worker image refs and digests
- Terraform remaining inputs: `external_id`, `valdrics_account_id`, `secret_rotation_lambda_arn`

## Operational Notes

- The new landing/public/company/trust surfaces do not require new runtime application env keys beyond the existing dashboard public contract.
- Enterprise procurement review is now materially clearer on the public site:
  - `enterprise` exposes a buyer review lane linking proof, privacy, terms, and status.
  - `privacy` now explains the enterprise DPA/residency review path instead of implying a universal public answer.
  - `terms` now exposes legal contact and an explicit enterprise contracting/procurement path.
- The public marketing stack is blocked operationally until the dashboard service receives:
  - `PUBLIC_API_URL`
  - `PUBLIC_SUPABASE_URL`
  - `PUBLIC_SUPABASE_ANON_KEY`
- The talk-to-sales schema changed. Promotion must keep Alembic current so `migrations/versions/w9x0y1z2a3b_add_public_sales_inquiry_buyer_region.py` is applied before relying on `buyer_region` writes in production.
