# Production Environment Checklist (Unified Platform)

Use this checklist before every production rollout.

## 0. Runtime toolchain contract

- Backend operator tooling and runtime validation are pinned to Python 3.12.x.
- The repository `.python-version` is the local source of truth for `uv` workflows.

Preflight:

```bash
cat .python-version
uv run python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
```

## 1. Ownership model

- Platform operator sets infrastructure values and deploys backend/frontend.
- Tenant users configure integrations in product UI under `/settings/notifications`.
- Tenant users do not set backend process env vars.
- The supported Cloud Run profile uses one API process per container and scales via Cloud Run concurrency and instance settings.

## 2. Required operator inputs

Set these in the runtime, deployment, and promotion contract:

- `ENVIRONMENT=production`
- `API_URL=https://<your-api-domain>`
- `FRONTEND_URL=https://<your-frontend-domain>`
- `PLATFORM_RUNTIME_PROFILE=gcp`
- `OBSERVABILITY_BACKEND=gcp`
- `PUBLIC_API_RATE_LIMITING_BACKEND=cloudflare`
- `RATELIMIT_ENABLED=false`
- `SUPABASE_ANON_KEY=...`
- `SUPABASE_JWT_SECRET=...`
- `ENFORCEMENT_APPROVAL_TOKEN_SECRET=...`
- `ENFORCEMENT_EXPORT_SIGNING_SECRET=...`
- `INTERNAL_METRICS_AUTH_TOKEN=<32+ char secret>`
- `EXPOSE_API_DOCUMENTATION_PUBLICLY=false`
- selected LLM provider key
- `PAYSTACK_SECRET_KEY=sk_live_...`
- `PAYSTACK_PUBLIC_KEY=pk_live_...`

Required promotion refs for the reusable deploy workflow:

- `api_promotion_ref=repo@sha256:...`
- `batch_promotion_ref=repo@sha256:...`

Use the generated reports as the authoritative key-level contract:

```bash
jq '.required_operator_input_keys, .declared_but_not_runtime_required' .runtime/production.report.json
jq '.required_operator_input_keys' .runtime/production.migrate.report.json
jq '.cloudflare_pages_public_env_keys, .terraform_remaining_inputs' .runtime/deploy/production/deployment.report.json
```

## 2a. Generate the runtime scaffold

```bash
uv run python scripts/generate_managed_runtime_env.py --environment staging
uv run python scripts/generate_managed_runtime_env.py --environment production
uv run python scripts/validate_runtime_env.py --environment production --env-file .runtime/production.env
```

Key runtime outputs:

- `.runtime/production.env`
- `.runtime/production.report.json`

## 2b. Generate the migration scaffold

```bash
uv run python scripts/generate_managed_migration_env.py --environment staging
uv run python scripts/generate_managed_migration_env.py --environment production
uv run python scripts/validate_migration_env.py --env-file .runtime/production.migrate.env
```

Key migration outputs:

- `.runtime/production.migrate.env`
- `.runtime/production.migrate.report.json`

## 2c. Run the release pipeline

Use the repository-managed release workflow:

- `.github/workflows/release-unified-platform.yml`

The release workflow validates the release contract, calls the reusable Artifact
Registry workflow, deploys staging, and promotes production with the same digest
only when `promote_production=true`.

Reusable implementation details:

- `.github/workflows/publish-artifact-registry-images.yml`
- `.github/workflows/deploy-unified-platform.yml`

Outputs:

- `release/artifact-registry-release.json`
- `release/artifact-registry-release.env`
- `managed-deployment-bundle-<environment>-<release-tag>` non-secret evidence bundle uploaded by the reusable deploy workflow
- `managed-release-blocker-summary-<release-tag>` uploaded by `release-unified-platform.yml` only when `promote_production=true`

Required promotion input format:

- `--api-promotion-ref <repo@sha256:...>`
- `--batch-promotion-ref <repo@sha256:...>`

## 2d. Generate and verify deployment artifacts

Normal release path:

- `.github/workflows/deploy-unified-platform.yml` materializes `.runtime/production.env`
- `.github/workflows/deploy-unified-platform.yml` materializes `.runtime/production.migrate.env`
- `.github/workflows/deploy-unified-platform.yml` generates `.runtime/deploy/production/*`
- `.github/workflows/deploy-unified-platform.yml` runs `scripts/verify_managed_deployment_bundle.py` before Terraform apply
- `.github/workflows/deploy-unified-platform.yml` renders `.runtime/deploy/production/operator-handoff.md`
- `.github/workflows/deploy-unified-platform.yml` refreshes the codebase audit report and runs `scripts/verify_managed_release_readiness.py` after the deploy smoke check

Operator preflight or incident-repair path:

```bash
uv run python scripts/generate_managed_deployment_artifacts.py --environment production --runtime-env-file .runtime/production.env --release-tag <release-tag> --api-promotion-ref <repo@sha256:...> --batch-promotion-ref <repo@sha256:...>
uv run python scripts/verify_dashboard_runtime_contract.py --build
uv run python scripts/verify_managed_deployment_bundle.py --environment production
uv run python scripts/render_managed_deployment_handoff.py --environment production
```

When both staging and production bundles are present locally, render the
cross-environment blocker rollup with `scripts/render_managed_release_blocker_summary.py` via:

```bash
make render-managed-release-blockers
```

Default deploy-workspace outputs:

- `.runtime/deploy/<environment>/unified-platform-manifest.json`
- `.runtime/deploy/<environment>/secret-manager-runtime-secrets.json`
- `.runtime/deploy/<environment>/cloudflare-pages-env.json`
- `.runtime/deploy/<environment>/artifact-registry-release.json`
- `.runtime/deploy/<environment>/terraform.runtime.auto.tfvars.json`
- `.runtime/deploy/<environment>/deployment.report.json`
- `.runtime/deploy/<environment>/operator-handoff.md`
- `.runtime/deploy/managed-release-blockers.md`

Uploaded non-secret deployment evidence bundle:

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

Uploaded cross-environment release review artifact:

- `.runtime/deploy/managed-release-blockers.md`
- generated from downloaded non-secret staging and production bundles
- download both per-environment bundles into the repo root before rendering manually so the expected `.runtime/...` paths are restored
- uploaded automatically only when `.github/workflows/release-unified-platform.yml` runs with `promote_production=true`

## 2e. Apply infrastructure and deploy

Use the unified release workflow for normal operations:

- `.github/workflows/release-unified-platform.yml`

Direct reusable deployment workflow dispatch is reserved for incident repair:

- `.github/workflows/deploy-unified-platform.yml`

This path:

- materializes the managed runtime env from `RUNTIME_PLAIN_ENV_JSON` and `RUNTIME_SECRET_ENV_JSON`
- generates the managed migration env and deployment bundle
- verifies the managed deployment bundle
- uploads the non-secret deployment evidence bundle for clean-runner release verification
- applies Terraform from `.runtime/deploy/<environment>/terraform.runtime.auto.tfvars.json`
- runs Alembic from `.runtime/<environment>.migrate.env`
- deploys the dashboard from `.runtime/deploy/<environment>/cloudflare-pages-env.json`

Infrastructure values still required outside the runtime env:

- `CLOUDFLARE_ZONE_ID`
- `CLOUDFLARE_ACCOUNT_ID`
- `API_URL` must resolve through a Cloudflare-proxied DNS record owned by Terraform
- Cloud Armor must be attached to the API backend service and allow only Cloudflare origin CIDRs.

## 3. Production validation sequence

1. Refresh `.runtime/production.env` and `.runtime/production.migrate.env`.
2. Run the release workflow once for staging.
3. Confirm the publish job produced `artifact-registry-release.json` and `artifact-registry-release.env`.
4. Confirm the deploy job uploaded `managed-deployment-bundle-production-<release-tag>`.
5. Verify the dashboard runtime contract.
6. Verify the managed deployment bundle.
7. Render the operator handoff and, when both staging and production bundles are available locally, refresh the cross-environment blocker rollup with `make render-managed-release-blockers NON_SECRET_BUNDLE=true`.
8. Confirm the reusable deploy workflow migration step succeeds from `.runtime/production.migrate.env`.
9. Deploy through `.github/workflows/release-unified-platform.yml`.
10. Validate `/health/live`, then confirm the reusable deploy workflow refreshes the codebase audit report and runs `scripts/verify_managed_release_readiness.py --non-secret-deployment-bundle` against the uploaded non-secret bundle.
11. When the same release run also promoted production, confirm `managed-release-blocker-summary-<release-tag>` was uploaded and matches the downloaded staging and production bundles.

## 4. Notes

- `API_URL` must not point at the raw `run.app` origin in staging or production.
- `GCP_CLOUD_RUN_SERVICE_NAME` must identify the Cloud Run API service so Cloud Tasks can resolve the direct `run.app` URL instead of traversing Cloudflare.
- Cloud Run custom audiences must include `API_URL` so Google-signed internal calls can target the direct `run.app` service URL.
- `run_public_frontend_quality_gate.py` remains part of release validation.
- `verify_codebase_audit_report.py` remains part of release validation.
