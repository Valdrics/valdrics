# Valdrics Deployment Guide

Last verified: **2026-03-18**

## Current Supported Production Deployment Profile

The current supported production deployment profile is:
Current supported production deployment profile means the Koyeb-managed release path below.

`Koyeb managed services with immutable image promotion`

This is the active operating model for both staging and production.

## Future Scale Profile

The repository retains a future scale profile:

`Helm + Terraform (AWS/EKS)`

That path remains in-repo for later scale-up work, but it is not the current
day-to-day operating default.

## Shared Runtime Contract

All deployment profiles must satisfy these checks:

- `ENVIRONMENT=production`
- explicit public URLs: `API_URL=https://...` and `FRONTEND_URL=https://...`
- `ENABLE_SCHEDULER=true` unless intentionally disabled for incident control
- liveness probe: `/health/live`
- dependency health/readiness: `/health`
- internal-only metrics: `/_internal/metrics`
- immutable image or deployment versioning
- any forecasting break-glass expiry must remain within the configured max break-glass window

Machine-readable source of truth:

- `scripts/managed_deployment_contract.py` defines the shared deployment/runtime key contract.
- `.runtime/<environment>.report.json` is the authoritative runtime env blocker inventory.
- `.runtime/<environment>.migrate.report.json` is the authoritative migration env blocker inventory.
- `.runtime/deploy/<environment>/deployment.report.json` is the authoritative deployment artifact blocker inventory.
- `.runtime/deploy/<environment>/operator-handoff.md` is the derived human handoff rendered from those verified reports.
- `.runtime/deploy/managed-release-blockers.md` is the derived cross-environment blocker rollup rendered from the verified staging and production bundles.
- `docs/runbooks/production_env_checklist.md` is the operator runbook; the generated reports remain the canonical key-level contract.

## Profile A: Koyeb Managed Services

Repository evidence:

- runtime and deploy bundle generators:
  - `scripts/generate_managed_runtime_env.py`
  - `scripts/generate_managed_migration_env.py`
  - `scripts/generate_managed_deployment_artifacts.py`
  - `scripts/verify_managed_deployment_bundle.py`
- immutable image publish workflow:
  - `.github/workflows/publish-release-images.yml`
- dashboard runtime verifier:
  - `scripts/verify_dashboard_runtime_contract.py`
- generated Koyeb artifacts:
  - `.runtime/deploy/<environment>/koyeb-api.yaml`
  - `.runtime/deploy/<environment>/koyeb-worker.yaml`
  - `.runtime/deploy/<environment>/koyeb-dashboard-env.json`
  - `.runtime/deploy/<environment>/koyeb-release.json`
  - `.runtime/deploy/<environment>/operator-handoff.md`

Expected posture:

- separate Koyeb apps or service groups for `staging` and `production`
- separate database, Redis, and secret stores per environment
- API and worker release from the same immutable GHCR image digest
- dashboard release from a separate immutable GHCR image digest
- GHCR is the supported current registry; Docker Hub is not part of the release contract
- Koyeb deploys from immutable digest refs, not Git branch tracking
- production promotion reuses the exact tested release image digests from staging
- dashboard public configuration remains runtime-driven through `koyeb-dashboard-env.json`, so the same dashboard image can be promoted between environments
- the dashboard image is built from `Dockerfile.dashboard`, which packages the SvelteKit build output and serves it through `dashboard/server.node.mjs` for the managed Node runtime

Core operator steps:

1. Generate or refresh the runtime and migration bundles.
2. Publish immutable API and dashboard images with `.github/workflows/publish-release-images.yml`.
3. Capture the published `sha256:...` digests from `ghcr-release.json` / `ghcr-release.env`.
4. Run the consolidated readiness gate:
   `uv run python scripts/verify_managed_release_readiness.py --environment <staging|production> --dashboard-url https://REPLACE_WITH_FRONTEND_DOMAIN --skip-webserver`
   If you are reusing a local `vite preview` instance instead of a deployed domain, add
   `--reuse-built-dashboard-runtime` so the gate verifies the existing build instead of
   rebuilding underneath the live preview server.
   If the managed runtime env already contains a live `FRONTEND_URL`, the wrapper can
   derive the dashboard URL automatically and `--dashboard-url` becomes optional.
   This wrapper now verifies the checked-in codebase audit report as well, so the
   release gate fails if `.runtime/staging.audit.report.json` drifts from live repo facts.
   The underlying audit command is `uv run python scripts/verify_codebase_audit_report.py --report .runtime/staging.audit.report.json`.
   If that audit artifact drifts after real repo changes, refresh it with
   `uv run python scripts/refresh_codebase_audit_report.py --report .runtime/staging.audit.report.json`
   and commit the updated snapshot before promotion.
5. Render the cross-environment blocker rollup:
   `uv run python scripts/render_managed_release_blocker_summary.py`
6. Generate the deployment bundle with `--release-tag`, `--api-image-digest`, and `--dashboard-image-digest`.
7. Apply migrations with the environment-specific migration env.
8. Deploy API, worker, and dashboard in Koyeb using the digest-pinned `promotion_ref` values in `koyeb-release.json`.
9. Apply dashboard public env from `koyeb-dashboard-env.json`.
10. Validate `/health/live`, `/health`, worker connectivity, dashboard-to-API connectivity, and `/_internal/metrics`.

## Profile B: Helm + Terraform (AWS/EKS) Future Scale

Repository evidence:

- Helm chart: `helm/valdrics/`
- Infrastructure modules: `terraform/`

Expected posture when activated:

- API replicas >= 2
- ExternalSecrets enabled for production values
- AWS RDS Multi-AZ and automated backups
- ElastiCache Multi-AZ replication group

Future-scale operator steps:

1. Provision infrastructure with Terraform.
2. Publish immutable application images.
3. Deploy with Helm values that preserve the production defaults.
4. Validate `/health/live`, `/health`, and cluster-internal `/_internal/metrics`.

## Verification Checklist

- `/health/live` returns `200`
- `/health` reflects dependency state accurately
- `/_internal/metrics` is reachable only by internal scrapers or callers presenting `INTERNAL_METRICS_AUTH_TOKEN`
- workers and scheduler start only when expected
- rollback path is documented for the chosen profile

## Related Runbooks

- `docs/runbooks/production_env_checklist.md`
- `docs/runbooks/koyeb_release_promotion.md`
- `docs/ROLLBACK_PLAN.md`
- `docs/runbooks/disaster_recovery.md`
- `docs/runbooks/tenant_data_lifecycle.md`
