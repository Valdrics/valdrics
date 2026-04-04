# Full Codebase Audit — Active Snapshot

**Snapshot date:** 2026-04-02  
**Status:** Active governance artifact  
**Scope:** This document is a **time-bound snapshot** of the repository on the date above. It covers **first-party Python, TypeScript, and Svelte source**, active runtime/deployment configuration, and targeted pattern sweeps. It is not a claim that every vendored, generated, archived, or binary-adjacent artifact was manually re-read line by line on this date.

This file remains intentionally checked in because downstream controls and compliance mappings reference it, but **live verification scripts remain the source of truth** for current hygiene and runtime assertions.

## Snapshot Summary

- Current source inventory at snapshot time:
  - `app/`: 599 Python files
  - `tests/`: 831 Python files
  - `dashboard/src/`: 425 TypeScript/JavaScript/Svelte files
  - `scripts/`: 151 Python files
  - `migrations/versions/`: 116 Python files
- Pattern sweeps on 2026-04-02 found `13` `TODO/FIXME/HACK` matches across `4` files in the active source roots. App-side hits were limited to vendored static assets under `app/static`, not first-party runtime modules.
- Historical exact counts such as prior `pytest --collect-only` totals are intentionally not repeated as durable facts here because they drift rapidly and are better verified in CI or by targeted repo scripts.

## Security Corrections

### Secret handling uses a mixed secret model

The repository does not support a blanket "zero secrets stored" claim. The current posture is a **mixed secret model**:

- AWS onboarding uses STS assume-role and avoids long-lived AWS access keys in the application database.
- Azure and GCP connections support workload identity where available, but can also persist encrypted `client_secret` or encrypted `service_account_json` values when secret-based auth is required.
- Tenant-scoped integration tokens and API keys are also stored encrypted at rest where the feature requires persistent credentials.
- Encryption at rest is implemented through both SQLAlchemy encrypted column types and Fernet/MultiFernet-backed helpers, so the repo should not describe the mechanism as a single-library-only implementation.

### Tenant isolation uses RLS enforcement plus documented exemptions

The database posture is **RLS enforcement plus documented exemptions**, not "RLS across all tables":

- Postgres session setup and query listeners fail closed for tenant-scoped access paths.
- A narrow list of global/system tables is intentionally exempt from RLS enforcement.
- Audits and scripts should distinguish between "required tenant-scoped tables are protected" and "every table in the database uses RLS."

### Raw SQL in migrations is not a request-path injection finding

Alembic revisions include raw SQL for schema, partitioning, and RLS operations. In the current codebase this is migration-time DDL/DML, not user-input SQL executed on the request path. The real concern is operational clarity and migration safety, not an active runtime SQL injection report by itself.

## Local Development And Compose Hardening

- Local sqlite development uses generated `.env.dev`.
- Local docker compose development uses generated `.env.compose.dev`.
- Checked-in templates now leave local compose secrets blank rather than embedding shared fallback passwords.
- The supported compose workflow uses `docker compose` with an explicit env file instead of relying on legacy `docker-compose` examples plus checked-in defaults.

## Current Recommendations

1. Keep audit conclusions time-bound and tie them back to executable verification where possible.
2. Prefer workload identity and STS-based access for cloud providers when the provider supports it; otherwise keep stored credentials encrypted, narrow in scope, and rotation-friendly.
3. Keep the RLS exemption list documented and intentionally small, with tests and scripts verifying that only approved global/system tables bypass enforcement.
4. Keep local-only runtime files generated and git-ignored so development convenience does not leak into checked-in defaults.

## Source Of Truth

This snapshot is useful context, but active verification should come from the repository's runtime and hygiene checks, including documentation contracts, placeholder guards, module-size budgets, and targeted test suites. When this document and executable verification disagree, the executable verification wins and this file must be updated.
