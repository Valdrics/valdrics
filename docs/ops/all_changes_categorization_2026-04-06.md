# All Changes Categorization (2026-04-06)

## Scope

- Worktree snapshot date: `2026-04-06`
- Base branch at snapshot: `main`
- Base commit at snapshot: `ab4347f890a5b3bedb377316b1c64bc458a0460c`
- Total changed paths categorized: `22`
- Categorization rule: every changed path in the dirty worktree is assigned to exactly one execution track.

## Track Register

### Track DF (`#362`)

- Title: landing hero, cookie consent, and exit-intent frontend surfaces
- Paths: `6`
- Scope summary: Landing hero styling, cookie-consent and exit-intent experience updates, and the paired lead-exit regression coverage.
- Assigned paths:
  - `dashboard/src/lib/components/LandingHero.css`
  - `dashboard/src/lib/components/LandingHero.footer.css`
  - `dashboard/src/lib/components/landing/LandingCookieConsent.svelte`
  - `dashboard/src/lib/components/landing/LandingExitIntentPrompt.svelte`
  - `dashboard/src/lib/components/landing/LandingHeroView.svelte`
  - `dashboard/src/lib/components/landing/landing_decomposition.lead_exit.svelte.test.ts`

### Track DG (`#363`)

- Title: managed deployment runtime contracts, handoff docs, and local artifact hygiene
- Paths: `12`
- Scope summary: Managed runtime environment generation, deployment handoff and release-readiness verification, deployment docs/runbooks, and local artifact hygiene via repo ignore rules.
- Assigned paths:
  - `.gitignore`
  - `docs/DEPLOYMENT.md`
  - `docs/runbooks/koyeb_release_promotion.md`
  - `docs/runbooks/production_env_checklist.md`
  - `scripts/generate_managed_runtime_env.py`
  - `scripts/render_managed_deployment_handoff.py`
  - `scripts/verify_documentation_runtime_contracts.py`
  - `scripts/verify_managed_release_readiness.py`
  - `tests/unit/ops/test_generate_managed_runtime_env.py`
  - `tests/unit/ops/test_render_managed_deployment_handoff.py`
  - `tests/unit/ops/test_verify_documentation_runtime_contracts.py`
  - `tests/unit/ops/test_verify_managed_release_readiness.py`

### Track DH (`#364`)

- Title: codebase audit report refresh and verification automation
- Paths: `4`
- Scope summary: Audit report refresh tooling, the verification script updates, and matching operational tests.
- Assigned paths:
  - `scripts/refresh_codebase_audit_report.py`
  - `scripts/verify_codebase_audit_report.py`
  - `tests/unit/ops/test_refresh_codebase_audit_report.py`
  - `tests/unit/ops/test_verify_codebase_audit_report.py`

## Cleanup Pass

- The untracked root-level `.codex` artifact is environment-owned and mounted read-only in this workspace.
- Instead of force-removing that mount, `.gitignore` now excludes `.codex` so it no longer pollutes batch status.
- No additional clearly unwanted tracked docs, backup files, reject files, or tracked log artifacts were identified in this repo snapshot.
