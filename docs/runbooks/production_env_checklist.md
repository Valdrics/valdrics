# Production Environment Checklist (SaaS Mode)

Use this checklist before every production rollout.

## 0. Runtime toolchain contract

- Backend operator tooling and runtime validation are pinned to Python 3.12.x.
- The repository `.python-version` is the local source of truth for `uv` workflows.
- Do not promote or validate production with Python 3.13+ or older unsupported minors.

Preflight the interpreter before generating env files or running validation:

```bash
cat .python-version
uv run python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"
```

Expected result:

- `.python-version` prints `3.12`
- `uv run python ...` prints `3.12.x`

If either check drifts, fix the local/runtime interpreter first. Do not continue with
deployment validation on an unsupported Python runtime.

## 1. Ownership model (who sets what)

- Platform operator (you/Valdrics team) sets infrastructure env vars and deploys backend/frontend.
- Tenant users configure integrations in product UI under `/settings/notifications`.
- Tenant users do **not** set backend process env vars.

## 2. Required operator env vars

Set these in production runtime (Koyeb/Kubernetes/etc):

- `ENVIRONMENT=production`
- `API_URL=https://<your-api-domain>`
- `FRONTEND_URL=https://<your-frontend-domain>`
- `DATABASE_URL=...`
- `SUPABASE_ANON_KEY=...` for the dashboard public runtime/build contract
- `SUPABASE_JWT_SECRET=...`
- `ENFORCEMENT_APPROVAL_TOKEN_SECRET=...`
- `ENFORCEMENT_EXPORT_SIGNING_SECRET=...`
- `ENCRYPTION_KEY=...`
- `KDF_SALT=...`
- `CSRF_SECRET_KEY=...`
- `ADMIN_API_KEY=...`
- `LLM_PROVIDER=...`
- Provider key for selected LLM (`GROQ_API_KEY` or `OPENAI_API_KEY` or `CLAUDE_API_KEY` or `GOOGLE_API_KEY`)
- `PAYSTACK_SECRET_KEY=sk_live_...`
- `PAYSTACK_PUBLIC_KEY=pk_live_...`
- `CORS_ORIGINS=[\"https://<your-frontend-domain>\"]`
- `AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=arn:aws:iam::<valdrics-account-id>:role/<valdrics-control-plane-role>`
- `SAAS_STRICT_INTEGRATIONS=true`
- `SENTRY_DSN=https://...`
- `OTEL_EXPORTER_OTLP_ENDPOINT=https://<otel-collector>:4317`
- `OTEL_LOGS_EXPORT_ENABLED=true`
- `INTERNAL_METRICS_AUTH_TOKEN=<32+ char secret>` when the edge cannot fully isolate `/_internal/metrics`
- `EXPOSE_API_DOCUMENTATION_PUBLICLY=false`
- If `prophet` is not bundled, set all break-glass vars:
  - `FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK=true`
  - `FORECASTER_BREAK_GLASS_REASON=<incident/ticket reference>`
  - `FORECASTER_BREAK_GLASS_EXPIRES_AT=<ISO-8601 UTC future timestamp>`
- If an audited incident requires outbound TLS verification to be disabled temporarily, set all break-glass vars:
  - `ALLOW_INSECURE_OUTBOUND_TLS=true`
  - `OUTBOUND_TLS_BREAK_GLASS_REASON=<incident/ticket reference>`
  - `OUTBOUND_TLS_BREAK_GLASS_EXPIRES_AT=<ISO-8601 UTC future timestamp>`

Contract source of truth:

- Treat the generated reports as authoritative for exact key inventories and blocker sets.
- The grouped checklist above is operator guidance; the exact machine-readable contract is emitted by the managed generators and enforced by `scripts/verify_managed_deployment_bundle.py`.
- Runtime env authority: `.runtime/<environment>.report.json`
- Migration env authority: `.runtime/<environment>.migrate.report.json`
- Deployment env authority: `.runtime/deploy/<environment>/deployment.report.json`

Inspect the exact required keys from the generated reports instead of copying lists by hand:

```bash
jq '.required_operator_input_keys, .declared_but_not_runtime_required' .runtime/production.report.json
jq '.required_operator_input_keys' .runtime/production.migrate.report.json
jq '.koyeb_dashboard_public_env_keys, .terraform_remaining_inputs' .runtime/deploy/production/deployment.report.json
```

## 2a. Generate the runtime scaffold first

Use the repo-managed generator to create staging or production env scaffolds with fresh
internal secrets:

```bash
uv run python scripts/generate_managed_runtime_env.py --environment staging
uv run python scripts/generate_managed_runtime_env.py --environment production
```

Default outputs:

- `.runtime/staging.env`
- `.runtime/staging.report.json`
- `.runtime/production.env`
- `.runtime/production.report.json`

The generated env files already include fresh internal secrets such as
`CSRF_SECRET_KEY`, `ENCRYPTION_KEY`, `ADMIN_API_KEY`,
`INTERNAL_JOB_SECRET`, `INTERNAL_METRICS_AUTH_TOKEN`,
`ENFORCEMENT_APPROVAL_TOKEN_SECRET`, and
`ENFORCEMENT_EXPORT_SIGNING_SECRET`.

They do **not** invent provider-owned live values. Expect explicit `REPLACE_WITH_...`
placeholders for operator-managed values such as:

- `DATABASE_URL`
- `SUPABASE_URL`
- `SUPABASE_JWT_SECRET`
- `REDIS_URL`
- `API_URL`
- `FRONTEND_URL`
- `TRUSTED_PROXY_CIDRS`
- `AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN`
- `PAYSTACK_SECRET_KEY`
- `PAYSTACK_PUBLIC_KEY`
- selected LLM provider API key
- `SENTRY_DSN`
- `OTEL_EXPORTER_OTLP_ENDPOINT`

Optional AWS onboarding override:

- `CLOUDFORMATION_TEMPLATE_URL=https://<public-template-host>/api/v1/public/templates/aws/valdrics-role.yaml`
  Leave empty to serve the release-owned template directly from `API_URL`.

Validate a completed file directly:

```bash
uv run python scripts/validate_runtime_env.py --environment production --env-file .runtime/production.env
```

The runtime report separates hard deployment blockers from broader declared
placeholders:

- `runtime_validation_blockers`: values that will fail the strict runtime validator.
- `declared_external_placeholders`: all still-placeholder external values in the file.
- `declared_but_not_runtime_required`: declared placeholders that do not currently gate startup.

## 2b. Generate the migration scaffold separately

Use the migration-specific scaffold for Alembic. This path is intentionally decoupled
from the full runtime contract so migrations only depend on database connectivity:

```bash
uv run python scripts/generate_managed_migration_env.py --environment staging
uv run python scripts/generate_managed_migration_env.py --environment production
```

Default outputs:

- `.runtime/staging.migrate.env`
- `.runtime/staging.migrate.report.json`
- `.runtime/production.migrate.env`
- `.runtime/production.migrate.report.json`

By default, the only migration blocker is `DATABASE_URL`. If you switch
`DB_SSL_MODE` to `verify-ca` or `verify-full`, `DB_SSL_CA_CERT_PATH` also becomes
mandatory.

Validate the migration env directly:

```bash
uv run python scripts/validate_migration_env.py --env-file .runtime/production.migrate.env
```

## 2c. Generate deployment artifacts from the runtime env

Once the runtime env is filled, publish immutable images first, then generate
deployment-ready artifacts for the current Koyeb production path and the future
Helm/EKS scale path.

### 2c.1 Publish immutable GHCR images first

Use the repository-managed GHCR release workflow:

- `.github/workflows/publish-release-images.yml`

Recommended GitHub repository or organization variable:

- `GHCR_NAMESPACE=valdrics`

Inputs:

- `release_tag=<immutable release tag>`
- optional `git_ref=<commit or tag to build>`
- optional `registry_namespace=<ghcr namespace override>`

Outputs:

- `release/ghcr-release.json`
- `release/ghcr-release.env`

The release artifact records the digest-pinned refs you must promote through
staging and production:

- `API_IMAGE_DIGEST=sha256:...`
- `DASHBOARD_IMAGE_DIGEST=sha256:...`
- `API_PROMOTION_REF=ghcr.io/.../valdrics-api@sha256:...`
- `DASHBOARD_PROMOTION_REF=ghcr.io/.../valdrics-dashboard@sha256:...`

Do not rebuild a second image for production after staging signoff.

You can source `release/ghcr-release.env` directly before running `make deploy`.

### 2c.2 Generate digest-pinned deployment artifacts

```bash
uv run python scripts/generate_managed_deployment_artifacts.py --environment staging --runtime-env-file .runtime/staging.env --release-tag <release-tag> --api-image-digest <sha256:...> --dashboard-image-digest <sha256:...>
uv run python scripts/generate_managed_deployment_artifacts.py --environment production --runtime-env-file .runtime/production.env --release-tag <release-tag> --api-image-digest <sha256:...> --dashboard-image-digest <sha256:...>
```

Default outputs:

- `.runtime/deploy/<environment>/koyeb-api.yaml`
- `.runtime/deploy/<environment>/koyeb-worker.yaml`
- `.runtime/deploy/<environment>/koyeb-dashboard-env.json`
- `.runtime/deploy/<environment>/koyeb-release.json`
- `.runtime/deploy/<environment>/koyeb-secrets.json`
- `.runtime/deploy/<environment>/helm-values.yaml`
- `.runtime/deploy/<environment>/aws-runtime-secret.json`
- `.runtime/deploy/<environment>/terraform.runtime.auto.tfvars.json`
- `.runtime/deploy/<environment>/deployment.report.json`

Public dashboard contract notes:

- The dashboard service now has a first-class public-marketing/runtime contract. Treat these as required Koyeb dashboard public env values whenever the public site is promoted:
  - `PUBLIC_API_URL`
  - `PUBLIC_SUPABASE_URL`
  - `PUBLIC_SUPABASE_ANON_KEY`
- The generated deployment bundle records these under `koyeb_dashboard_public_env_keys` and `koyeb_dashboard_public_env_blockers`.
- The generated output directory must include both:
  - `.runtime/deploy/<environment>/koyeb-dashboard-env.json`
  - `.runtime/deploy/<environment>/koyeb-release.json`
- If either file is missing, regenerate the deployment artifacts before promotion. Do not hand-edit the deployment report.

The deployment report separates:

- `runtime_validation_blockers`: app-runtime values still blocking startup
- `koyeb_secret_value_blockers`: placeholder/empty values still blocking the generated Koyeb bundle
- `koyeb_dashboard_public_env_blockers`: missing/placeholder dashboard public env values still blocking the Koyeb dashboard service contract
- `koyeb_release_value_blockers`: placeholder release tag or image digest values still blocking immutable Koyeb promotion
- `helm_runtime_secret_value_blockers`: placeholder/empty values still blocking the Helm/EKS secret payload
- `terraform_remaining_inputs`: infrastructure values still required outside the runtime env, such as `external_id` and `valdrics_account_id`

## 2d. Verify the managed bundle before promotion

Once the runtime env, migration env, and deployment artifacts exist, verify the
bundle as one coherent operator handoff:

```bash
uv run python scripts/verify_managed_deployment_bundle.py --environment production
```

This check fails if any of the following drift:

- runtime blockers vs `.runtime/production.report.json`
- migration blockers vs `.runtime/production.migrate.report.json`
- deployment blockers/readiness vs `.runtime/deploy/production/deployment.report.json`
- generated artifact paths or secret payload indexes
- dashboard public env artifact presence (`koyeb-dashboard-env.json`) and immutable release metadata (`koyeb-release.json`)

Promotion should not proceed when the bundle verifier fails.

## 2e. Render the operator handoff from verified reports

Once the bundle verifies cleanly, render the single operator-facing handoff file:

```bash
uv run python scripts/render_managed_deployment_handoff.py --environment production
```

Default output:

- `.runtime/deploy/<environment>/operator-handoff.md`

Contract notes:

- This file is derived from the verified runtime, migration, and deployment reports.
- It is a human-friendly handoff for promotion review; the JSON reports remain the source of truth.
- Regenerate it after any runtime env, migration env, or deployment artifact change.

## 3. Strict SaaS integration rules

When `SAAS_STRICT_INTEGRATIONS=true`:

- Allowed:
  - `SLACK_BOT_TOKEN` (shared bot token used with tenant channel settings)
- Must be unset/empty in production:
  - `SLACK_CHANNEL_ID`
  - `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY`
  - `GITHUB_ACTIONS_OWNER`, `GITHUB_ACTIONS_REPO`, `GITHUB_ACTIONS_WORKFLOW_ID`, `GITHUB_ACTIONS_TOKEN`, `GITHUB_ACTIONS_ENABLED`
  - `GITLAB_CI_PROJECT_ID`, `GITLAB_CI_TRIGGER_TOKEN`, `GITLAB_CI_ENABLED`
  - `GENERIC_CI_WEBHOOK_URL`, `GENERIC_CI_WEBHOOK_BEARER_TOKEN`, `GENERIC_CI_WEBHOOK_ENABLED`

If disallowed vars are set in production, startup fails by design.

## 4. Tenant onboarding requirements

Each tenant should configure (UI):

- Slack channel override (if Slack alerts enabled)
- Jira settings (if Jira enabled)
- Workflow automation target(s): GitHub/GitLab/webhook

All tokens/secrets are stored in tenant notification settings.

## 5. Deployment sequence

1. Generate or refresh `.runtime/production.env` and `.runtime/production.migrate.env`.
2. Publish immutable images with `.github/workflows/publish-release-images.yml`.
3. Generate `.runtime/deploy/production/deployment.report.json` with `--release-tag`, `--api-image-digest`, and `--dashboard-image-digest`.
4. Verify the bundle: `uv run python scripts/verify_managed_deployment_bundle.py --environment production`
5. Render the operator handoff: `uv run python scripts/render_managed_deployment_handoff.py --environment production`
6. Validate the migration env: `uv run python scripts/validate_migration_env.py --env-file .runtime/production.migrate.env`
7. Run migrations with the migration env:
   `set -a && source .runtime/production.migrate.env && uv run alembic upgrade head`
8. Validate the full runtime env:
   `uv run python scripts/validate_runtime_env.py --environment production --env-file .runtime/production.env`
9. Apply the generated Koyeb secrets and dashboard public env.
10. Promote API, worker, and dashboard using the digest-pinned `promotion_ref` values recorded in `.runtime/deploy/production/koyeb-release.json`.
11. Validate health and notification paths.

## 6. Smoke tests after deploy

- `GET /health` returns healthy.
- `GET /health/live` returns `200`.
- `GET /docs`, `GET /redoc`, and `GET /openapi.json` are blocked from the public deployment surface.
- `GET /_internal/metrics` is blocked from the unauthenticated public surface and accessible only to internal scrapers or callers presenting `INTERNAL_METRICS_AUTH_TOKEN`.
- Internal Alertmanager routing is live for:
  - `LandingSignupToConnectionCritical`
  - `LandingConnectionToFirstValueCritical`
  - `LandingSignupToConnectionWatch`
  - `LandingConnectionToFirstValueWatch`
  - `LandingFunnelHealthMetricsStale`
- From UI/API, run:
  - `POST /api/v1/settings/notifications/test-jira`
  - `POST /api/v1/settings/notifications/test-workflow`
- Capture and persist audit-grade acceptance evidence:
  - `POST /api/v1/settings/notifications/acceptance-evidence/capture`
  - `GET /api/v1/settings/notifications/acceptance-evidence`
- Export the tenant compliance pack ZIP (owner-only, Pro+):
  - `GET /api/v1/audit/compliance-pack?include_focus_export=true&include_savings_proof=true&include_realized_savings=true&include_close_package=true`
- Trigger one policy event (`block` or `escalate`) and confirm downstream notifications.

## 6a. Public release gate before final promotion

Run the public browser quality gate against the release candidate or staging surface:

```bash
uv run python scripts/run_public_frontend_quality_gate.py --dashboard-url https://REPLACE_WITH_FRONTEND_DOMAIN --skip-webserver
```

This gate runs the public smoke, accessibility, performance, and visual suites
as one operator command.

## 7. Change management rule

Whenever config behavior changes:

1. Update this file.
2. Update `.env.example`.
3. Update `docs/integrations/workflow_automation.md`.
4. Add/adjust tests for config validation where applicable.
5. Re-run `scripts/verify_managed_deployment_bundle.py` for the affected environment.
