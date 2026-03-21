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
- generated Koyeb artifacts:
  - `.runtime/deploy/<environment>/koyeb-api.yaml`
  - `.runtime/deploy/<environment>/koyeb-worker.yaml`
  - `.runtime/deploy/<environment>/koyeb-dashboard-env.json`
  - `.runtime/deploy/<environment>/koyeb-release.json`

Expected posture:

- separate Koyeb apps or service groups for `staging` and `production`
- separate database, Redis, and secret stores per environment
- API and worker release from the same immutable GHCR image digest
- dashboard release from a separate immutable GHCR image digest
- GHCR is the supported current registry; Docker Hub is not part of the release contract
- Koyeb deploys from immutable digest refs, not Git branch tracking
- production promotion reuses the exact tested release image digests from staging
- dashboard public configuration remains runtime-driven through `koyeb-dashboard-env.json`, so the same dashboard image can be promoted between environments

Core operator steps:

1. Generate or refresh the runtime and migration bundles.
2. Publish immutable API and dashboard images with `.github/workflows/publish-release-images.yml`.
3. Capture the published `sha256:...` digests from `ghcr-release.json` / `ghcr-release.env`.
4. Generate the deployment bundle with `--release-tag`, `--api-image-digest`, and `--dashboard-image-digest`.
5. Apply migrations with the environment-specific migration env.
6. Deploy API, worker, and dashboard in Koyeb using the digest-pinned `promotion_ref` values in `koyeb-release.json`.
7. Apply dashboard public env from `koyeb-dashboard-env.json`.
8. Validate `/health/live`, `/health`, worker connectivity, dashboard-to-API connectivity, and `/_internal/metrics`.

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

## Legacy Checked-In Manifests

- `koyeb.yaml`
- `koyeb-worker.yaml`

These remain checked in as compatibility helpers for local/manual evaluation, but
the authoritative Koyeb production handoff is the generated managed bundle under
`.runtime/deploy/<environment>/`.

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
