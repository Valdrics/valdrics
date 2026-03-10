# Production Environment Checklist (SaaS Mode)

Use this checklist before every production rollout.

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
- `PAYSTACK_SECRET_KEY`
- `PAYSTACK_PUBLIC_KEY`
- selected LLM provider API key
- `SENTRY_DSN`
- `OTEL_EXPORTER_OTLP_ENDPOINT`

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

Once the runtime env is filled, generate deployment-ready artifacts for both the
reference managed-platform path and the supported Helm/EKS production path:

```bash
uv run python scripts/generate_managed_deployment_artifacts.py --environment staging --runtime-env-file .runtime/staging.env
uv run python scripts/generate_managed_deployment_artifacts.py --environment production --runtime-env-file .runtime/production.env
```

Default outputs:

- `.runtime/deploy/<environment>/koyeb-api.yaml`
- `.runtime/deploy/<environment>/koyeb-worker.yaml`
- `.runtime/deploy/<environment>/koyeb-secrets.json`
- `.runtime/deploy/<environment>/helm-values.yaml`
- `.runtime/deploy/<environment>/aws-runtime-secret.json`
- `.runtime/deploy/<environment>/terraform.runtime.auto.tfvars.json`
- `.runtime/deploy/<environment>/deployment.report.json`

The deployment report separates:

- `runtime_validation_blockers`: app-runtime values still blocking startup
- `koyeb_secret_value_blockers`: placeholder/empty values still blocking the generated Koyeb bundle
- `helm_runtime_secret_value_blockers`: placeholder/empty values still blocking the Helm/EKS secret payload
- `terraform_remaining_inputs`: infrastructure values still required outside the runtime env, such as `external_id` and `valdrics_account_id`

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

1. Generate or refresh both `.runtime/production.env` and `.runtime/production.migrate.env`.
2. Validate the migration env: `uv run python scripts/validate_migration_env.py --env-file .runtime/production.migrate.env`
3. Run migrations with the migration env:
   `set -a && source .runtime/production.migrate.env && uv run alembic upgrade head`
4. Validate the full runtime env:
   `uv run python scripts/validate_runtime_env.py --environment production --env-file .runtime/production.env`
5. Apply the full runtime env and restart the app.
6. Deploy frontend.
7. Validate health and notification paths.

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

## 7. Change management rule

Whenever config behavior changes:

1. Update this file.
2. Update `.env.example`.
3. Update `docs/integrations/workflow_automation.md`.
4. Add/adjust tests for config validation where applicable.
