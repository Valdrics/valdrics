# Managed Cutover Operator Packet

Use this packet when you are preparing the live `staging` and `production`
cutover for the supported managed platform:

- backend on Google Cloud Run
- async work on Cloud Tasks
- scheduled work on Cloud Scheduler
- long-running work on Cloud Run Jobs
- frontend on Cloudflare Pages
- database, auth, and storage on Supabase

This packet is for the environment-side work that must be completed manually by
an operator with access to the real provider accounts and GitHub repository
settings.

## 1. What you will do manually

You are responsible for:

- creating or verifying the GitHub repository/environment contract
- collecting the real provider-side IDs, URLs, service accounts, and secrets
- dispatching the managed release workflow for staging
- validating the uploaded staging evidence packet
- promoting the exact same digest-pinned artifact to production
- collecting the final production evidence packet and blocker summary

The repository already defines the workflow and artifact contract. Your job is
to supply the real hosted values and run the promotion.

Canonical release path:

- `docs/runbooks/unified_platform_release.md`
- `.github/workflows/release-unified-platform.yml`
- `.github/workflows/deploy-unified-platform.yml`
- `.github/workflows/publish-artifact-registry-images.yml`

## 2. One-time platform prerequisites

### GitHub

Create or verify:

- repository variables for Artifact Registry publishing
- `staging` environment
- `production` environment
- environment protection rules and required reviewers where your release process
  needs them
- environment variables and environment secrets for both `staging` and
  `production`

Where to get it:

- GitHub repository `Settings -> Environments`
- GitHub docs: https://docs.github.com/en/actions/reference/environments

#### GitHub environment protection profiles

Use one of these profiles when configuring `staging` and `production`.

##### Recommended team-operated profile

Use this when at least one other human can review production deployments.

`staging`:

- `Required reviewers`: unchecked unless you want staging approvals
- `Prevent self-review`: unchecked unless `Required reviewers` is enabled
- `Wait timer`: unchecked
- `Allow administrators to bypass configured protection rules`: checked
- `Custom deployment protection rules`: unchecked unless you already operate one
- `Deployment branches and tags`: `Selected branches and tags`
- Allowed branch rule: `main`

`production`:

- `Required reviewers`: checked
- `Prevent self-review`: checked
- `Wait timer`: unchecked unless your release policy explicitly requires one
- `Allow administrators to bypass configured protection rules`: unchecked
- `Custom deployment protection rules`: unchecked unless you already operate one
- `Deployment branches and tags`: `Selected branches and tags`
- Allowed branch rule: `main`

##### Single-operator production profile

Use this when you are the only operator on the project today.

This is operationally workable, but it is a reduced-control model compared with
the team-operated production profile above.

`staging`:

- `Required reviewers`: unchecked
- `Prevent self-review`: unchecked or not applicable
- `Wait timer`: unchecked
- `Allow administrators to bypass configured protection rules`: checked
- `Custom deployment protection rules`: unchecked
- `Deployment branches and tags`: `Selected branches and tags`
- Allowed branch rule: `main`

`production`:

- `Required reviewers`: unchecked
- `Prevent self-review`: unchecked or not applicable
- `Wait timer`: if GitHub shows the option and you want a deliberate pause, set
  a short timer such as `10` minutes; otherwise leave it unchecked
- `Allow administrators to bypass configured protection rules`: unchecked if you
  enabled a wait timer; otherwise this setting is effectively irrelevant because
  no reviewer-based protection rule is active
- `Custom deployment protection rules`: unchecked
- `Deployment branches and tags`: `Selected branches and tags`
- Allowed branch rule: `main`

Compensating controls for the single-operator production profile:

- keep production deployments manual through
  `.github/workflows/release-unified-platform.yml`
- require staging to pass first with `promote_production=false`
- promote the same immutable digest-pinned artifact to production
- download and review `managed-deployment-bundle-staging-<release-tag>` before
  promoting production
- keep the final `managed-release-blocker-summary-<release-tag>` artifact
- protect the `main` branch separately in GitHub branch protection settings
- treat this profile as transitional; move to required human review when another
  trusted operator is available

### Google Cloud

Create or verify:

- target GCP project for `staging`
- target GCP project for `production`
- Terraform state bucket for each environment
- Terraform-managed Artifact Registry repository used by the publish workflow
- enabled Google APIs, or deployer permissions to enable them during Terraform
  apply, including `cloudresourcemanager.googleapis.com` for IAM preflights and
  `compute.googleapis.com` for the public API load balancer
- Workload Identity Federation provider for GitHub Actions
- deployer service account for environment deployment
- artifact publisher service account for image publishing
- `roles/iam.workloadIdentityUser` on both service accounts for the repository
  principal:
  `principalSet://iam.googleapis.com/projects/<project-number>/locations/global/workloadIdentityPools/github-actions/attribute.repository/<github-owner>/<github-repo>`
- deployer project-level permissions required by Terraform, including
  `iam.serviceAccounts.create`, service-account IAM policy management, and
  project IAM policy management
- permission grants required by Terraform state bootstrap, API enablement,
  Cloud Run, Cloud Tasks, Cloud Scheduler, Cloud Run Jobs, Secret Manager,
  Artifact Registry, and load balancer management
- Cloud Run public access should use disabled Invoker IAM checks
  (`invoker_iam_disabled`) instead of an `allUsers` IAM binding when the project
  is under domain restricted sharing organization policy

Where to get it:

- Google Cloud Console `IAM & Admin -> Workload Identity Federation`
- Google Cloud Console `IAM & Admin -> Service Accounts`
- Google Cloud Console `Artifact Registry -> Repositories`
- Auth action reference:
  https://github.com/google-github-actions/auth

### Cloudflare

Create or verify:

- Cloudflare account that owns the deployment
- zone for the public domains
- Pages project for the dashboard
- API token with the minimum permissions needed by Terraform and Pages deploys
- proxied API hostname and frontend hostname in the target zone
- rate-limiting entitlement for the configured window. The Terraform default is
  50 requests per 10 seconds with a 10-second mitigation timeout because this
  zone only allows a 10-second `http_ratelimit` period and mitigation timeout;
  use an environment tfvars override only after the zone entitlement supports
  different values.

Where to get it:

- Cloudflare dashboard `Workers & Pages`
- Cloudflare dashboard `Account Home`
- Cloudflare dashboard `My Profile -> API Tokens` or `Manage Account -> API Tokens`
- Find IDs:
  https://developers.cloudflare.com/fundamentals/account/find-account-and-zone-ids/
- Create token:
  https://developers.cloudflare.com/fundamentals/api/get-started/create-token/

### Supabase

Create or verify:

- target organization
- target project
- project URL in `SUPABASE_URL`, because the release workflow derives the
  project ref from that URL and imports the existing project into Terraform
  state before plan
- empty tables are acceptable for a new staging or production project; Alembic
  owns schema/table creation after Terraform finishes
- project region
- personal access token for Management API and Terraform
- project database password
- project URL
- project API key for the frontend runtime
- Postgres connection string for the backend runtime and migrations

Where to get it:

- Supabase dashboard `Account -> Access Tokens`
- Supabase dashboard project `Connect`
- Supabase dashboard project `Settings -> API Keys`
- Supabase dashboard project `Database`
- PAT and management API:
  https://supabase.com/docs/reference/api/introduction
- API URL and keys:
  https://supabase.com/docs/guides/api/api-keys
- Connection strings:
  https://supabase.com/docs/guides/database/connecting-to-postgres

## 3. GitHub repository variables

These are repository-level variables used by
`.github/workflows/release-unified-platform.yml`.

| Key | What it is | Where to get it |
| --- | --- | --- |
| `ARTIFACT_REGISTRY_PROJECT_ID` | GCP project that owns Artifact Registry | Google Cloud project selector / Artifact Registry |
| `ARTIFACT_REGISTRY_REGION` | Artifact Registry region, for example `us-central1` | Artifact Registry repository location |
| `ARTIFACT_REGISTRY_REPOSITORY` | Artifact Registry Docker repository ID | Google Cloud `Artifact Registry -> Repositories` |

## 4. GitHub environment variables

Set the following for both `staging` and `production` environments.

| Key | What it is | Where to get it |
| --- | --- | --- |
| `GCP_PROJECT_ID` | GCP project for the target environment | Google Cloud project selector |
| `GCP_REGION` | Region for Cloud Run and related resources | Google Cloud architecture choice / existing project deployment region |
| `API_URL` | Public HTTPS API hostname | Cloudflare DNS record that fronts the GCP HTTPS load balancer |
| `FRONTEND_URL` | Public HTTPS dashboard hostname | Cloudflare Pages custom domain |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare account identifier | Cloudflare dashboard `Workers & Pages` or `Account Home` |
| `CLOUDFLARE_ZONE_ID` | Zone identifier for the public domain | Cloudflare dashboard `Account Home -> Overview -> API` |
| `CLOUDFLARE_PAGES_PROJECT_NAME` | Pages project name for dashboard deploys | Cloudflare dashboard `Workers & Pages` |
| `CLOUDFLARE_PAGES_PRODUCTION_BRANCH` | Branch Cloudflare treats as the production branch | Cloudflare Pages project settings |
| `SUPABASE_ORGANIZATION_ID` | Supabase organization identifier | Supabase dashboard or Management API organization listing |
| `SUPABASE_PROJECT_NAME` | Supabase project name | Supabase dashboard project overview |
| `SUPABASE_REGION` | Supabase project region | Supabase project overview / creation settings |
| `TERRAFORM_STATE_BUCKET` | GCS bucket used by Terraform remote state for this environment | Terraform `state-backend` output |
| `RUNTIME_PLAIN_ENV_JSON` | JSON object of non-secret runtime keys | Assemble from the template in section 6 |

## 5. GitHub environment secrets

Set the following for both `staging` and `production` environments.

| Key | What it is | Where to get it |
| --- | --- | --- |
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | Full Workload Identity Provider resource name | Google Cloud `IAM & Admin -> Workload Identity Federation` |
| `GCP_DEPLOYER_SERVICE_ACCOUNT` | Service account email used by deploy workflow | Google Cloud `IAM & Admin -> Service Accounts` |
| `GCP_ARTIFACT_PUBLISHER_SERVICE_ACCOUNT` | Service account email used by publish workflow | Google Cloud `IAM & Admin -> Service Accounts` |
| `CLOUDFLARE_API_TOKEN` | Token used by Terraform and Pages deploys; include Zone `Bot Management:Edit`, DNS, Rulesets/WAF, and Pages permissions | Cloudflare API Tokens |
| `SUPABASE_ACCESS_TOKEN` | Supabase personal access token | Supabase `Account -> Access Tokens` |
| `SUPABASE_DATABASE_PASSWORD` | Database password for the target project | Supabase project database settings / reset flow |
| `RUNTIME_SECRET_ENV_JSON` | JSON object of runtime secrets | Assemble from the template in section 7 |

Cloudflare Bot Fight Mode cannot be bypassed by WAF Skip rules. The release
preflight checks Bot Management API access because Terraform must disable Bot
Fight Mode for API health probes.

## 6. `RUNTIME_PLAIN_ENV_JSON` template

This value must be a JSON object with string values only.

`DATABASE_URL` is intentionally excluded from this non-secret payload. Keep it
only in `RUNTIME_SECRET_ENV_JSON`.

```json
{
  "ENVIRONMENT": "staging",
  "API_URL": "https://api.example.com",
  "FRONTEND_URL": "https://app.example.com",
  "GCP_PROJECT_ID": "your-gcp-project-id",
  "GCP_REGION": "us-central1",
  "GCP_CLOUD_TASKS_QUEUE": "valdrics-managed-work",
  "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL": "tasks@your-project.iam.gserviceaccount.com",
  "GCP_CLOUD_RUN_SERVICE_NAME": "valdrics-api",
  "GCP_CLOUD_RUN_BATCH_JOB_NAME": "valdrics-batch",
  "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS": "[\"tasks@your-project.iam.gserviceaccount.com\",\"scheduler@your-project.iam.gserviceaccount.com\"]",
  "TRUSTED_PROXY_CIDRS": "[\"173.245.48.0/20\",\"103.21.244.0/22\"]",
  "PLATFORM_RUNTIME_PROFILE": "gcp",
  "OBSERVABILITY_BACKEND": "gcp",
  "PUBLIC_API_RATE_LIMITING_BACKEND": "cloudflare",
  "RATELIMIT_ENABLED": "false",
  "SUPABASE_URL": "https://your-project-ref.supabase.co",
  "SUPABASE_ANON_KEY": "sb_publishable_or_anon_key",
  "LLM_PROVIDER": "groq",
  "EXPOSE_API_DOCUMENTATION_PUBLICLY": "false",
  "SAAS_STRICT_INTEGRATIONS": "true",
  "TRUST_PROXY_HEADERS": "true"
}
```

Fill these values from the following sources:

- `API_URL` and `FRONTEND_URL`: Cloudflare-managed public hostnames
- `GCP_*`: Google Cloud project, region, queue, service names, and service
  account emails chosen for the target environment
- `TRUSTED_PROXY_CIDRS`: current Cloudflare origin CIDR allowlist that your
  load balancer and Cloud Armor policy are designed to trust
- `SUPABASE_URL` and `SUPABASE_ANON_KEY`: Supabase project `Connect` dialog or
  `Settings -> API Keys`

Notes:

- `API_URL` and `FRONTEND_URL` must be real HTTPS public hostnames.
- `API_URL` must not be the raw `run.app` URL.
- `GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS` and `TRUSTED_PROXY_CIDRS` must be
  encoded as JSON arrays inside string values because the GitHub environment
  contract expects strings.
- For persistent backend traffic, prefer a Supabase direct connection string
  when your environment supports IPv6. If IPv4 is required, use the session
  pooler. Supabase documents both in the `Connect` dialog.

## 7. `RUNTIME_SECRET_ENV_JSON` template

This value must also be a JSON object with string values only. Keep the source
template empty, then paste real values only into the GitHub environment secret.

```json
{
  "DATABASE_URL": "postgresql://...",
  "SUPABASE_JWT_SECRET": "",
  "PAYSTACK_SECRET_KEY": "",
  "PAYSTACK_PUBLIC_KEY": "",
  "INTERNAL_METRICS_AUTH_TOKEN": "",
  "CSRF_SECRET_KEY": "",
  "ENCRYPTION_KEY": "",
  "KDF_SALT": "",
  "ENFORCEMENT_APPROVAL_TOKEN_SECRET": "",
  "ENFORCEMENT_EXPORT_SIGNING_SECRET": "",
  "GROQ_API_KEY": ""
}
```

Source map:

- `DATABASE_URL`: Supabase `Connect` dialog
- `SUPABASE_JWT_SECRET`: Supabase project auth/JWT configuration
- `PAYSTACK_*`: Paystack production dashboard
- `INTERNAL_METRICS_AUTH_TOKEN`, `CSRF_SECRET_KEY`, `ENCRYPTION_KEY`,
  `KDF_SALT`, `ENFORCEMENT_*`: generate and store in your team secret manager or
  password vault
- LLM provider key: vendor dashboard for the provider selected by
  `LLM_PROVIDER`

Notes:

- `DATABASE_URL` is intentionally secret-classified and must stay in
  `RUNTIME_SECRET_ENV_JSON`; the deploy workflow rejects it if it is placed in
  `RUNTIME_PLAIN_ENV_JSON`.
- Managed migrations default to `DB_SSL_MODE=require`, which requires TLS but
  does not validate the database certificate chain. Use `verify-ca` or
  `verify-full` only when you also provide `DB_SSL_CA_CERT_PATH`.
- Only include the API key that matches `LLM_PROVIDER`.
- Keep this JSON out of source control.
- Treat every value here as a secret.

## 8. Release artifacts you must collect

### From the publish job

Artifact name:

- `artifact-registry-release-<release-tag>`

Files:

- `release/artifact-registry-release.json`
- `release/artifact-registry-release.env`

Where to get it:

- GitHub Actions run summary for `.github/workflows/release-unified-platform.yml`

Why it matters:

- this is the immutable promotion contract
- it contains `api_promotion_ref` and `batch_promotion_ref`
- production must reuse the same digest that passed staging

### From each deploy job

Artifact name:

- `managed-deployment-bundle-staging-<release-tag>`
- `managed-deployment-bundle-production-<release-tag>`

Files:

- `.runtime/<environment>.report.json`
- `.runtime/<environment>.migrate.report.json`
- `.runtime/deploy/<environment>/unified-platform-manifest.json`
- `.runtime/deploy/<environment>/cloudflare-pages-env.json`
- `.runtime/deploy/<environment>/artifact-registry-release.json`
- `.runtime/deploy/<environment>/deployment.report.json`
- `.runtime/deploy/<environment>/technology-value-admission-receipt.json`
- `.runtime/deploy/<environment>/operator-handoff.md`

Where to get it:

- GitHub Actions run summary for the deploy job

Why it matters:

- this is the environment evidence packet for operator review
- it is the packet you use when rerunning verification on a clean machine

### From the full promotion run

Artifact name:

- `managed-release-blocker-summary-<release-tag>`

File:

- `.runtime/deploy/managed-release-blockers.md`

Where to get it:

- GitHub Actions run summary for `.github/workflows/release-unified-platform.yml`
- uploaded only when `promote_production=true`

Why it matters:

- it is the cross-environment staging plus production release review summary

## 9. Staging then production execution sequence

### Local preflight

Run before the first real workflow dispatch or before incident repair:

```bash
uv run python scripts/generate_managed_runtime_env.py --environment staging
uv run python scripts/generate_managed_migration_env.py --environment staging
uv run python scripts/validate_runtime_env.py --environment staging --env-file .runtime/staging.env
uv run python scripts/validate_migration_env.py --env-file .runtime/staging.migrate.env
uv run python scripts/verify_dashboard_runtime_contract.py --build
```

### Staging cutover

1. Confirm the `staging` GitHub environment contains every variable and secret
   from sections 4 to 7.
2. Dispatch `.github/workflows/release-unified-platform.yml` with:
   - `release_tag=<release-tag>`
   - optional `git_ref=<sha-or-ref>`
   - `promote_production=false`
3. Download:
   - `artifact-registry-release-<release-tag>`
   - `managed-deployment-bundle-staging-<release-tag>`
4. Review `operator-handoff.md` and `deployment.report.json`.
5. Run clean-machine verification against the downloaded staging bundle:

```bash
uv run python scripts/verify_managed_release_readiness.py \
  --environment staging \
  --runtime-report .runtime/staging.report.json \
  --migration-report .runtime/staging.migrate.report.json \
  --deployment-report .runtime/deploy/staging/deployment.report.json \
  --non-secret-deployment-bundle \
  --skip-webserver
```

6. Validate live staging:
   - `${API_URL}/health/live`
   - background task dispatch
   - Cloud Scheduler execution
   - Cloud Run Job execution
   - public dashboard browser checks
   - rollback rehearsal

### Production promotion

1. Do not change the release tag or digest refs between staging and production.
2. Confirm the `production` GitHub environment contains every variable and
   secret from sections 4 to 7.
3. Dispatch `.github/workflows/release-unified-platform.yml` with:
   - the same `release_tag`
   - the same `git_ref`
   - `promote_production=true`
4. Download:
   - `managed-deployment-bundle-production-<release-tag>`
   - `managed-release-blocker-summary-<release-tag>`
5. Review:
   - `.runtime/deploy/production/operator-handoff.md`
   - `.runtime/deploy/managed-release-blockers.md`
6. Confirm the production bundle still points to the same immutable promotion
   refs that passed staging.

## 10. Fast retrieval cheatsheet

Use this when you are filling the GitHub environment forms.

| Need | Where to get it |
| --- | --- |
| Artifact Registry project, region, repository | Google Cloud `Artifact Registry -> Repositories` |
| Workload Identity Provider resource name | Google Cloud `IAM & Admin -> Workload Identity Federation` |
| Deployer and publisher service account emails | Google Cloud `IAM & Admin -> Service Accounts` |
| GitHub WIF principal grant | Service account `Permissions -> Grant Access -> Workload Identity User` |
| Cloudflare account ID | Cloudflare `Workers & Pages` or `Account Home` |
| Cloudflare zone ID | Cloudflare `Account Home -> Overview -> API` |
| Cloudflare Pages project name and production branch | Cloudflare `Workers & Pages -> <project>` |
| Cloudflare API token | Cloudflare `My Profile -> API Tokens` |
| Supabase access token | Supabase `Account -> Access Tokens` |
| Supabase project URL and anon/publishable key | Supabase project `Connect` or `Settings -> API Keys` |
| Supabase database connection string | Supabase project `Connect` |
| Supabase database password | Supabase project database settings / reset flow |
| Supabase organization ID | Supabase dashboard or `GET /v1/organizations` |
| Supabase project name and region | Supabase project overview |
| `api_promotion_ref` and `batch_promotion_ref` | `release/artifact-registry-release.json` or `.env` from publish artifact |
| Staging or production evidence packet | GitHub Actions artifact `managed-deployment-bundle-<environment>-<release-tag>` |
| Cross-environment blocker summary | GitHub Actions artifact `managed-release-blocker-summary-<release-tag>` |

## 11. Stop conditions

Do not promote production if any of the following is true:

- `managed-deployment-bundle-staging-<release-tag>` is missing
- `scripts/verify_managed_release_readiness.py` fails on the staging bundle
- staging `/health/live` is not healthy
- the published artifact digest changed between staging and production
- the operator handoff or blocker summary still shows unresolved blockers
