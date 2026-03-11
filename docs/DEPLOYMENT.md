# Valdrics Deployment Guide

Last verified: **2026-03-07**

## Supported Production Deployment Profile

The repository-backed production deployment profile is:

Supported production deployment profile: `Helm + Terraform (AWS/EKS)`.

1. `Helm + Terraform (AWS/EKS)`

Do not mix preview/reference manifests into the production operational contract.

## Shared Runtime Contract

All production profiles should satisfy these checks:

- `ENVIRONMENT=production`
- explicit public URLs: `API_URL=https://...` and `FRONTEND_URL=https://...`
- `ENABLE_SCHEDULER=true` unless intentionally disabled for incident control
- liveness probe: `/health/live`
- dependency health/readiness: `/health`
- internal-only metrics: `/_internal/metrics`
- immutable image or deployment versioning
- any forecasting break-glass expiry must remain within the configured max break-glass window

## Profile A: Helm + Terraform (AWS/EKS)

Repository evidence:

- Helm chart: `helm/valdrics/`
- Infrastructure modules: `terraform/`

Expected posture:

- API replicas >= 2
- ExternalSecrets enabled for production values
- AWS RDS Multi-AZ and automated backups
- ElastiCache Multi-AZ replication group

Core operator steps:

1. Provision infrastructure with Terraform.
2. Publish an immutable application image.
3. Deploy with Helm values that preserve the production defaults.
4. Validate `/health/live`, `/health`, and cluster-internal `/_internal/metrics`.

## Reference Managed-Platform Manifests

Repository evidence:

- Dashboard adapter/config: `dashboard/svelte.config.js`
- Backend API manifest: `koyeb.yaml`
- Backend worker manifest: `koyeb-worker.yaml`

These manifests remain checked in as a managed-platform reference and preview
surface. They are not a supported production profile because the checked-in
Koyeb definitions are branch-driven and do not, by themselves, satisfy the
repository requirement for immutable release artifacts.

Reference operator steps:

1. Deploy the dashboard to Cloudflare Pages.
2. Deploy the API to Koyeb using the checked-in `Dockerfile`.
3. Deploy the Celery worker to Koyeb using `koyeb-worker.yaml`; the worker starts with the image-bundled `celery` entrypoint rather than `uv run`.
4. Configure runtime secrets through the platform secret store, including `SENTRY_DSN`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `TRUSTED_PROXY_CIDRS`, `INTERNAL_METRICS_AUTH_TOKEN`, and `INTERNAL_JOB_SECRET`.
5. Validate dashboard-to-API connectivity, worker connectivity to Redis, and API health endpoints.

Promote this path to production only if external release automation enforces
immutable artifacts and a separate DR/rollback contract.

## Verification Checklist

- `/health/live` returns `200`
- `/health` reflects dependency state accurately
- `/_internal/metrics` is reachable only by internal scrapers or callers presenting `INTERNAL_METRICS_AUTH_TOKEN`
- workers and scheduler start only when expected
- rollback path is documented for the chosen profile

## Related Runbooks

- `docs/ROLLBACK_PLAN.md`
- `docs/runbooks/disaster_recovery.md`
- `docs/runbooks/tenant_data_lifecycle.md`
