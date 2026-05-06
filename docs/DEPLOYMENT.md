# Valdrics Deployment Guide

Last verified: **2026-04-16**

## Current supported production deployment profile

The current supported production deployment profile is:

`Google Cloud Run + Cloudflare Pages + Supabase`

This is the active operating model for both staging and production.

Current runtime note:

- the supported GCP profile delegates public API throttling to Cloudflare WAF rate limiting rules and keeps `RATELIMIT_ENABLED=false` inside the API runtime
- the public API path is `Cloudflare proxied hostname -> GCP external HTTPS load balancer -> Cloud Run`
- Cloud Armor allows only Cloudflare origin CIDRs to reach the API load balancer backend
- the API container binds `0.0.0.0:$PORT` and runs one Uvicorn process per Cloud Run instance
- scale is owned by Cloud Run request concurrency and instance counts, not a runtime `WEB_CONCURRENCY` knob

## Archived Future Scale Reference

Historical future-scale references may remain in explicitly archived or
reference-only material, but they are not part of the supported day-to-day
runtime profile.

## Shared Runtime Contract

All supported environments must satisfy these checks:

- `ENVIRONMENT=<staging|production>`
- explicit public URLs: `API_URL=https://...` and `FRONTEND_URL=https://...`
- `PLATFORM_RUNTIME_PROFILE=gcp`
- `OBSERVABILITY_BACKEND=gcp`
- `PUBLIC_API_RATE_LIMITING_BACKEND=cloudflare`
- `RATELIMIT_ENABLED=false`
- breaker state remains process-local inside each Cloud Run instance; there is no supported distributed breaker runtime toggle
- `API_URL` must be the Cloudflare-proxied custom hostname, not the raw `run.app` URL
- `GCP_CLOUD_RUN_SERVICE_NAME` must identify the Cloud Run API service used for internal Cloud Tasks delivery
- Cloud Run custom audiences must include `API_URL` so Cloud Tasks and Cloud Scheduler can authenticate directly to the internal `run.app` service URL while preserving the public API audience contract
- liveness probe: `/health/live`
- dependency health: `/health`
- internal metrics: `/_internal/metrics`
- immutable backend artifact promotion
- any forecasting or TLS break-glass expiry must remain within the configured max break-glass window

Machine-readable source of truth:

- `scripts/managed_deployment_contract.py`
- `.runtime/<environment>.report.json`
- `.runtime/<environment>.migrate.report.json`
- `.runtime/deploy/<environment>/deployment.report.json`
- `.runtime/deploy/<environment>/operator-handoff.md`
- `.runtime/deploy/managed-release-blockers.md` (release-level cross-environment summary rendered when both staging and production bundles are available)

GitHub release/deploy secret contract:

- Artifact publish requires `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_ARTIFACT_PUBLISHER_SERVICE_ACCOUNT`
- Environment deploy requires `GCP_WORKLOAD_IDENTITY_PROVIDER` and `GCP_DEPLOYER_SERVICE_ACCOUNT`
- Environment deploy also requires `CLOUDFLARE_API_TOKEN`, `SUPABASE_ACCESS_TOKEN`, `SUPABASE_DATABASE_PASSWORD`, and `RUNTIME_SECRET_ENV_JSON`
- `CLOUDFLARE_API_TOKEN` must include Zone `Bot Management:Edit`, DNS, Rulesets/WAF, and Pages permissions; Bot Fight Mode cannot be bypassed by WAF Skip rules, so release preflight and Terraform enforce `fight_mode=false` for API health probes

Use `.github/workflows/release-beta-app.yml` for normal beta/product releases
once infrastructure exists. It skips Terraform/state bootstrap and updates only
the Cloud Run app images, database migrations, and Cloudflare Pages deployment.
Reserve `.github/workflows/release-unified-platform.yml` for infrastructure or
production-promotion changes.

The runtime JSON inputs are not free-form. The active contract in
`scripts/managed_deployment_contract.py` and
`scripts/generate_managed_deployment_artifacts.py` blocks deployment until the
required runtime keys are present, including:

- non-secret runtime values such as `API_URL`, `FRONTEND_URL`, `GCP_PROJECT_ID`, `GCP_REGION`, `GCP_CLOUD_TASKS_QUEUE`, `GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL`, `GCP_CLOUD_RUN_SERVICE_NAME`, `GCP_CLOUD_RUN_BATCH_JOB_NAME`, `GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS`, and `TRUSTED_PROXY_CIDRS`
- secret runtime values such as `DATABASE_URL`, the `LLM_PROVIDER`-selected API key, `SUPABASE_JWT_SECRET`, `PAYSTACK_SECRET_KEY`, `PAYSTACK_PUBLIC_KEY`, `INTERNAL_METRICS_AUTH_TOKEN`, `CSRF_SECRET_KEY`, `ENCRYPTION_KEY`, `KDF_SALT`, `ENFORCEMENT_APPROVAL_TOKEN_SECRET`, and `ENFORCEMENT_EXPORT_SIGNING_SECRET`

The deploy workflow now enforces that secret-classified keys such as
`DATABASE_URL` stay in `RUNTIME_SECRET_ENV_JSON`, and plain-classified keys such
as `API_URL` stay in `RUNTIME_PLAIN_ENV_JSON`.

## Supported Release Surface

Repository evidence:

- runtime and deployment generators:
  - `scripts/generate_managed_runtime_env.py`
  - `scripts/generate_managed_migration_env.py`
  - `scripts/generate_managed_deployment_artifacts.py`
  - `scripts/verify_managed_deployment_bundle.py`
  - `scripts/verify_codebase_audit_report.py`
- single operator release workflow:
  - `.github/workflows/release-unified-platform.yml`
- reusable immutable backend artifact workflow:
  - `.github/workflows/publish-artifact-registry-images.yml`
- reusable unified deployment workflow:
  - `.github/workflows/deploy-unified-platform.yml`
- dashboard runtime verifier:
  - `scripts/verify_dashboard_runtime_contract.py`
- release readiness verifier:
  - `scripts/verify_managed_release_readiness.py`
- generated deploy-workspace artifacts:
  - `.runtime/deploy/<environment>/unified-platform-manifest.json`
  - `.runtime/deploy/<environment>/secret-manager-runtime-secrets.json`
  - `.runtime/deploy/<environment>/cloudflare-pages-env.json`
  - `.runtime/deploy/<environment>/artifact-registry-release.json`
  - `.runtime/deploy/<environment>/terraform.runtime.auto.tfvars.json`
  - `.runtime/deploy/<environment>/deployment.report.json`
  - `.runtime/deploy/<environment>/operator-handoff.md`
- uploaded non-secret deployment evidence bundle:
  - `.runtime/<environment>.report.json`
  - `.runtime/<environment>.migrate.report.json`
  - `.runtime/deploy/<environment>/unified-platform-manifest.json`
  - `.runtime/deploy/<environment>/cloudflare-pages-env.json`
  - `.runtime/deploy/<environment>/artifact-registry-release.json`
  - `.runtime/deploy/<environment>/deployment.report.json`
  - `.runtime/deploy/<environment>/operator-handoff.md`
  - excludes `.runtime/<environment>.env`, `.runtime/<environment>.migrate.env`,
    `secret-manager-runtime-secrets.json`, and
    `terraform.runtime.auto.tfvars.json`
- uploaded cross-environment release review artifact:
  - `.runtime/deploy/managed-release-blockers.md`
  - `managed-release-blocker-summary-<release-tag>`
  - uploaded by `.github/workflows/release-unified-platform.yml` only when both staging and production bundles are present in the same promotion run

Expected posture:

- backend API runs on Google Cloud Run
- public API ingress is terminated at a Google external HTTPS load balancer
- Cloudflare owns the public API DNS record, origin TLS mode, and WAF rate limiting rules
- Cloud Armor blocks direct origin access that does not come from Cloudflare origin CIDRs
- request-adjacent async work runs through Cloud Tasks
- scheduled triggers are owned by Cloud Scheduler
- long-running jobs execute on Cloud Run Jobs
- frontend deploys to Cloudflare Pages
- database, auth, and storage run on Supabase
- backend artifacts are promoted from Artifact Registry using digest-pinned refs
- production promotion reuses the same tested backend artifact that passed staging

## Core Operator Flow

1. Generate or refresh the runtime and migration bundles.
2. Run `.github/workflows/release-unified-platform.yml` for staging first.
3. Publish one immutable backend artifact and keep the digest-pinned `artifact-registry-release.json` / `artifact-registry-release.env` as release evidence.
4. Let `.github/workflows/deploy-unified-platform.yml` materialize `.runtime/<environment>.env`, `.runtime/<environment>.migrate.env`, and `.runtime/deploy/<environment>/...` from the GitHub environment contract plus the promoted digest refs.
5. Let the reusable deploy workflow run `scripts/generate_managed_deployment_artifacts.py`, `scripts/verify_managed_deployment_bundle.py`, and `scripts/render_managed_deployment_handoff.py` before any Terraform apply.
6. Upload the non-secret managed deployment evidence bundle from the deploy workflow as the operator audit artifact for the environment, including `operator-handoff.md`. Keep the secret-bearing runtime env, Secret Manager payload, and Terraform tfvars on the deploy runner only.
7. Let the deploy workflow refresh the codebase audit report and run `scripts/verify_managed_release_readiness.py` after the API smoke check.
8. Verify the dashboard runtime contract with `scripts/verify_dashboard_runtime_contract.py`.
9. Let `.github/workflows/release-unified-platform.yml` render `.runtime/deploy/managed-release-blockers.md` after both staging and production non-secret bundles have passed readiness when `promote_production=true`. For preflight or incident-repair review, render the same file manually with `scripts/render_managed_release_blocker_summary.py` via `make render-managed-release-blockers NON_SECRET_BUNDLE=true` after downloading both bundles into the repo root.
10. Let the release workflow apply infrastructure and run Alembic from the generated `.runtime/<environment>.migrate.env`.
11. Deploy the dashboard from the generated `cloudflare-pages-env.json`.
12. Validate `/health/live`, then confirm the release readiness verifier completed successfully against the deployed non-secret bundle.

## Verification Checklist

- `/health/live` returns `200`
- `scripts/verify_managed_release_readiness.py` completes successfully for the deployed bundle
- rollback path is documented for the unified profile
- release promotion uses digest-pinned Artifact Registry refs only

## Related Runbooks

- `docs/runbooks/unified_platform_release.md`
- `docs/runbooks/managed_cutover_operator_packet.md`
- `docs/runbooks/production_env_checklist.md`
- `docs/ROLLBACK_PLAN.md`
- `docs/runbooks/disaster_recovery.md`
- `docs/runbooks/tenant_data_lifecycle.md`
