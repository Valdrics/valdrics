# Unified Platform Release Runbook

This runbook defines the target operating model for the unified platform:

- backend runtime on Google Cloud Run
- async work on Cloud Tasks
- scheduled work on Cloud Scheduler
- long-running work on Cloud Run Jobs
- backend images in Artifact Registry
- frontend deploys on Cloudflare Pages
- database, auth, and storage on Supabase

## 1. Run the single release pipeline

Use:

- `.github/workflows/release-unified-platform.yml`
- `docs/runbooks/managed_cutover_operator_packet.md`

Required workflow inputs:

- `release_tag`
- optional `git_ref`
- `promote_production`

Required repository/environment variables:

- `ARTIFACT_REGISTRY_PROJECT_ID`
- `ARTIFACT_REGISTRY_REGION`
- `ARTIFACT_REGISTRY_REPOSITORY`
- `TERRAFORM_STATE_BUCKET`

The release pipeline validates the release contract, applies the Terraform
Artifact Registry foundation, publishes one digest-pinned backend image, deploys
staging first, and promotes production only when `promote_production=true`.
Production receives the same `api_promotion_ref` and `batch_promotion_ref` that
passed staging.

Implementation detail:

- `.github/workflows/publish-artifact-registry-images.yml` is reusable and records
  `release/artifact-registry-release.json` plus `release/artifact-registry-release.env`
- `.github/workflows/release-unified-platform.yml` applies
  `terraform/artifact-registry/` before publishing, so the first image push uses
  a Terraform-owned Docker repository instead of a console-created repository
- `.github/workflows/deploy-unified-platform.yml` is reusable and applies one
  environment at a time with the digest-pinned `api_promotion_ref`, explicit
  `batch_promotion_ref`, and the immutable `release_tag`
- `.github/workflows/deploy-unified-platform.yml` refreshes the codebase audit
  report and runs `scripts/verify_managed_release_readiness.py` after the deploy
  smoke check
- `.github/workflows/release-unified-platform.yml` renders and uploads
  `managed-release-blocker-summary-<release-tag>` only when
  `promote_production=true`, because that summary requires both staging and
  production non-secret bundles

## 2. Prepare the GitHub environment contract

For each environment (`staging`, `production`) define:

- repository/environment variables for non-secret platform control-plane values
- repository/environment secrets for provider credentials plus the runtime secret payload

At minimum the deployment workflow expects:

- `vars.GCP_PROJECT_ID`
- `vars.GCP_REGION`
- `vars.CLOUDFLARE_ACCOUNT_ID`
- `vars.CLOUDFLARE_ZONE_ID`
- `vars.CLOUDFLARE_PAGES_PROJECT_NAME`
- `vars.CLOUDFLARE_PAGES_PRODUCTION_BRANCH`
- `vars.SUPABASE_ORGANIZATION_ID`
- `vars.SUPABASE_PROJECT_NAME`
- `vars.SUPABASE_REGION`
- `vars.TERRAFORM_STATE_BUCKET`
- `vars.RUNTIME_PLAIN_ENV_JSON`
- `secrets.GCP_WORKLOAD_IDENTITY_PROVIDER`
- `secrets.GCP_DEPLOYER_SERVICE_ACCOUNT`
- `secrets.CLOUDFLARE_API_TOKEN` with Zone `Bot Management:Edit`, DNS, Rulesets/WAF, and Pages permissions for the target zone/account
- `secrets.SUPABASE_ACCESS_TOKEN`
- `secrets.SUPABASE_DATABASE_PASSWORD`
- `secrets.RUNTIME_SECRET_ENV_JSON`

Cloudflare Bot Fight Mode must be disabled for API health checks. WAF Skip rules
cannot bypass Bot Fight Mode, so the release preflight checks Bot Management API
access before the slower Terraform/image/deploy stages.

The release pipeline also requires:

- `secrets.GCP_WORKLOAD_IDENTITY_PROVIDER`
- `secrets.GCP_ARTIFACT_PUBLISHER_SERVICE_ACCOUNT`

The GitHub Workload Identity principal must be granted
`roles/iam.workloadIdentityUser` on each service account it impersonates. Grant
the repository principal to both the deployer and artifact publisher service
accounts:

```text
principalSet://iam.googleapis.com/projects/<project-number>/locations/global/workloadIdentityPools/github-actions/attribute.repository/<github-owner>/<github-repo>
```

For this repository, staging uses:

```text
principalSet://iam.googleapis.com/projects/772936428016/locations/global/workloadIdentityPools/github-actions/attribute.repository/Arvenqor/valdrics
```

The deployer service account also needs project-level permissions for the
Terraform-managed platform resources. At minimum, grant roles that include:

- `iam.serviceAccounts.create`
- `iam.serviceAccounts.get`
- `iam.serviceAccounts.getIamPolicy`
- `iam.serviceAccounts.setIamPolicy`
- `resourcemanager.projects.getIamPolicy`
- `resourcemanager.projects.setIamPolicy`

Typical first-bootstrap grants are `roles/iam.serviceAccountAdmin`,
`roles/resourcemanager.projectIamAdmin`, `roles/iam.serviceAccountUser`, plus
the service-specific admin roles for Cloud Run, Cloud Tasks, Cloud Scheduler,
Secret Manager, Compute, Service Usage, Artifact Registry, and Terraform state
storage. The release workflow preflights the service-account and project-IAM
permissions before image publishing so missing bootstrap grants fail early.

`RUNTIME_PLAIN_ENV_JSON` is not an arbitrary blob. It must satisfy the managed
runtime contract consumed by `scripts/generate_managed_deployment_artifacts.py`
and `scripts/managed_deployment_contract.py`, including keys such as:

- `API_URL`
- `FRONTEND_URL`
- `GCP_PROJECT_ID`
- `GCP_REGION`
- `GCP_CLOUD_TASKS_QUEUE`
- `GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL`
- `GCP_CLOUD_RUN_SERVICE_NAME`
- `GCP_CLOUD_RUN_BATCH_JOB_NAME`
- `GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS`
- `TRUSTED_PROXY_CIDRS`

`RUNTIME_SECRET_ENV_JSON` must also provide the selected LLM provider secret
and the core runtime secrets required by the same contract, including:

- `DATABASE_URL`
- the `LLM_PROVIDER`-selected API key (`OPENAI_API_KEY`, `GROQ_API_KEY`, `CLAUDE_API_KEY`, or `GOOGLE_API_KEY`)
- `SUPABASE_JWT_SECRET`
- `PAYSTACK_SECRET_KEY`
- `PAYSTACK_PUBLIC_KEY`
- `INTERNAL_METRICS_AUTH_TOKEN`
- `CSRF_SECRET_KEY`
- `ENCRYPTION_KEY`
- `KDF_SALT`
- `ENFORCEMENT_APPROVAL_TOKEN_SECRET`
- `ENFORCEMENT_EXPORT_SIGNING_SECRET`

`RUNTIME_PLAIN_ENV_JSON` and `RUNTIME_SECRET_ENV_JSON` must be JSON objects with
string values. The reusable deploy workflow rejects secret-classified keys such as `DATABASE_URL`
if they appear in `RUNTIME_PLAIN_ENV_JSON`, and rejects plain-classified keys such as `API_URL`
if they appear in `RUNTIME_SECRET_ENV_JSON`. After that validation it materializes
`.runtime/<environment>.env` from the two inputs, derives
`.runtime/<environment>.migrate.env` from the materialized `DATABASE_URL`, then
generates and verifies the managed deployment bundle before Terraform or
Alembic run.

The generated migration env defaults to `DB_SSL_MODE=require`, which requires
TLS but does not verify the database certificate chain. Use `verify-ca` or
`verify-full` plus `DB_SSL_CA_CERT_PATH` only when you have a pinned Supabase CA
bundle available to the runner.

## 2a. Bootstrap Terraform state

Set `TERRAFORM_STATE_BUCKET` to the globally unique GCS bucket name that should
hold the environment Terraform state. The release workflow applies
`terraform/state-backend/` first and will create the bucket or import an existing
bucket into the bootstrap state before continuing.

The deployer service account needs API enablement and state-bucket permissions
before this can succeed, including `roles/serviceusage.serviceUsageAdmin` and
`roles/storage.admin` on the target project during bootstrap.

For local operator bootstrap or repair, run:

```bash
terraform -chdir=terraform/state-backend init
terraform -chdir=terraform/state-backend apply \
  -var="gcp_project_id=<project-id>" \
  -var="gcp_region=<region>" \
  -var="state_bucket_name=<globally-unique-state-bucket>" \
  -var='terraform_state_principals=["serviceAccount:<github-deployer-service-account>"]'
```

The release workflow uses `TERRAFORM_STATE_BUCKET` for both
`terraform/artifact-registry/` and the main `terraform/` runtime state after the
state bucket foundation succeeds.

## 3. Apply infrastructure and deploy the app

Reusable implementation:

- `.github/workflows/deploy-unified-platform.yml`

Required workflow inputs:

- `environment`
- `release_tag`
- `api_promotion_ref`
- `batch_promotion_ref`
- optional `git_ref`

Before image publishing, the release workflow runs a managed-platform preflight
against the target environment. The preflight enables required Google APIs early
validates deployer IAM permissions for Terraform service-account and project
IAM management, and validates that `SUPABASE_URL` points at an existing Supabase
project in the configured organization. This catches GCP bootstrap and
org/token/project binding issues before the expensive Docker build and publish
path.

The deploy workflow performs:

1. Google Cloud authentication with Workload Identity Federation
2. Materialize `.runtime/<environment>.env`, `.runtime/<environment>.migrate.env`, and `.runtime/deploy/<environment>/...`
3. Verify the managed deployment bundle
4. Upload the non-secret deployment evidence bundle as an artifact for operator auditability. Keep `.runtime/<environment>.env`, `.runtime/<environment>.migrate.env`, `secret-manager-runtime-secrets.json`, and `terraform.runtime.auto.tfvars.json` on the deploy runner only.
5. Import the existing Supabase project ref derived from `SUPABASE_URL` into Terraform state when it is not already tracked
6. Terraform apply for GCP runtime + API load balancer, Cloudflare Pages/DNS/WAF, and Supabase project/settings
7. Alembic migration from `.runtime/<environment>.migrate.env`
8. Dashboard build from `.runtime/deploy/<environment>/cloudflare-pages-env.json`
9. Cloudflare Pages direct upload deploy
10. API liveness smoke check
11. Refresh the codebase audit report and run the managed release readiness verifier against the uploaded non-secret bundle

## 3a. Staging cutover operator sequence

Use this sequence to close the remaining environment-side staging gate with the
same immutable artifact contract the release workflow enforces.

Local preflight commands:

```bash
uv run python scripts/generate_managed_runtime_env.py --environment staging
uv run python scripts/generate_managed_migration_env.py --environment staging
uv run python scripts/validate_runtime_env.py --environment staging --env-file .runtime/staging.env
uv run python scripts/validate_migration_env.py --env-file .runtime/staging.migrate.env
uv run python scripts/generate_managed_deployment_artifacts.py --environment staging --runtime-env-file .runtime/staging.env --release-tag <release-tag> --api-promotion-ref <repo@sha256:...> --batch-promotion-ref <repo@sha256:...>
uv run python scripts/verify_managed_deployment_bundle.py --environment staging
uv run python scripts/render_managed_deployment_handoff.py --environment staging
uv run python scripts/verify_dashboard_runtime_contract.py --build
```

Release dispatch:

- Trigger `.github/workflows/release-unified-platform.yml` with `release_tag=<release-tag>`, optional `git_ref=<git-ref-or-sha>`, and `promote_production=false` for staging-only validation.
- Keep `release/artifact-registry-release.json` and `release/artifact-registry-release.env` as the immutable promotion evidence produced by the publish workflow.
- Download `managed-deployment-bundle-staging-<release-tag>` into the repo root if you need to rerun operator checks on a clean machine, so the artifact restores the expected `.runtime/...` paths.

Staging evidence and validation gates:

- `managed-deployment-bundle-staging-<release-tag>` must contain `.runtime/deploy/staging/operator-handoff.md`, `.runtime/staging.report.json`, `.runtime/staging.migrate.report.json`, and `.runtime/deploy/staging/deployment.report.json`.
- Run `uv run python scripts/verify_managed_release_readiness.py --environment staging --runtime-report .runtime/staging.report.json --migration-report .runtime/staging.migrate.report.json --deployment-report .runtime/deploy/staging/deployment.report.json --non-secret-deployment-bundle --dashboard-url https://REPLACE_WITH_REAL_STAGING_FRONTEND --skip-webserver` against the downloaded non-secret bundle when performing clean-runner review. If the bundle already contains a live `FRONTEND_URL`, the dashboard URL may be omitted.
- Confirm the live staging environment passes `/health/live`, background task dispatch, Cloud Scheduler execution, Cloud Run Job execution, dashboard/public browser checks, and rollback rehearsal before production promotion.
- Do not promote production until the staging evidence packet is complete and release operations signs off on the live cutover facts.

## 4. Terraform source of truth

Terraform is split by lifecycle:

- `terraform/state-backend/` bootstraps the GCS bucket used for Terraform state.
  This foundation is created first and is intentionally protected from normal
  runtime teardown.
- `terraform/artifact-registry/` owns the Artifact Registry Docker repository
  used by the publish workflow.
- `terraform/` owns the environment runtime stack and consumes the digest-pinned
  image refs produced by the publish workflow.

The runtime stack owns:

- Secret Manager secrets
- Cloud Run API service
- GCP external HTTPS load balancer for the public API
- Cloud Armor origin guard for Cloudflare-only API load balancer ingress
- Cloud Run public invocation via `invoker_iam_disabled`, not an `allUsers`
  IAM binding, so projects with domain restricted sharing org policy can deploy
- Cloud Run batch job
- Cloud Tasks queue
- Cloud Scheduler jobs
- Cloudflare API DNS record, strict origin TLS posture, and WAF rate limiting rules
- Pages project shell in Cloudflare
- Supabase project and managed settings

Terraform enables required Google APIs before creating runtime resources. Fresh
projects still require deployer permission to enable services, and the Compute
Engine API can take a few minutes to propagate before load balancer resources
accept creates. Cloudflare rate limiting defaults to 50 requests per 10 seconds
with a 10-second mitigation timeout because this zone is only entitled to the
10-second `http_ratelimit` window and mitigation timeout.
Supabase projects are expected to exist before release. Terraform imports the
project ref derived from `SUPABASE_URL` before planning, so an empty existing
project is sufficient; Alembic owns table creation during the migration step.

Terraform inputs are environment-specific and should be supplied through
the generated `.runtime/deploy/<environment>/terraform.runtime.auto.tfvars.json`
plus provider credentials that remain in GitHub environment secrets. The tfvars
file is a deploy-runner-local input, not part of the uploaded non-secret
artifact bundle.

## 5. Release rules

- Do not rebuild a second backend image for production.
- Promote the same `api_promotion_ref` that passed staging.
- Promote the same `batch_promotion_ref` that passed staging.
- Prefer `.github/workflows/release-unified-platform.yml` for operator-triggered
  releases; direct reusable workflow dispatch is for incident repair only.
- Keep Cloud Run scheduler ownership external. Do not re-enable the in-process scheduler in the API.
- Keep internal task and scheduler endpoints authenticated with Google-signed identity tokens.
- Treat this runbook as the only supported release path for staging and production.
- `scripts/capture_acceptance_evidence.py` and `GET /api/v1/audit/compliance-pack`
  are supplemental procurement/audit artifacts only. They do not replace the
  environment-specific `managed-deployment-bundle-<environment>-<release-tag>`
  or `scripts/verify_managed_release_readiness.py`.

## 6. Post-release checks

After each deploy confirm:

- `${API_URL}/health/live` returns `200`
- Cloud Scheduler jobs show successful recent executions
- Cloud Tasks queue dispatches successfully
- Cloud Run Job executions are launching and emitting logs
- Cloudflare Pages serves the new frontend deployment
- `scripts/verify_managed_release_readiness.py` completes successfully for the deployed bundle
- Supabase auth site URL matches the public frontend URL
- When production promotion is part of the same run, `managed-release-blocker-summary-<release-tag>` is uploaded and matches the downloaded staging and production non-secret bundles. For manual review outside that path, use `make render-managed-release-blockers NON_SECRET_BUNDLE=true`.
