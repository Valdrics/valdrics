# AWS Tenant Smoke Runbook

Archived reference as of 2026-04-14. This provider-specific smoke flow is not
part of the release-critical managed GCP + Cloudflare + Supabase operator
contract and is retained only for historical tenant-validation reference.

This runbook covers the provider-specific AWS tenant journey:

`connect AWS -> scan -> create remediation from finding -> approve -> execute -> confirm resolved finding -> confirm savings proof`

It is not the release-critical managed deployment contract for the unified
GCP + Cloudflare + Supabase platform. Use it only when validating the AWS
tenant integration surface itself.

## Preconditions

1. Staging must be on the target application build.
2. Alembic must be at head.
3. The staging tenant must be on a tier that includes:
   - auto remediation
   - policy preview
   - savings proof
4. Use an AWS staging account with disposable low-risk resources only.
5. If you serve AWS onboarding templates from the product, set
   `AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN` in the runtime explicitly for this
   provider flow. That value is provider-specific and not part of the unified
   managed deployment contract.

## Apply Database State

Run the staging release workflow first and confirm the reusable deploy job applies the generated migration env before the smoke test:

```bash
uv run python scripts/generate_managed_runtime_env.py --environment staging
uv run python scripts/generate_managed_migration_env.py --environment staging
uv run python scripts/validate_migration_env.py --env-file .runtime/staging.migrate.env
uv run python scripts/generate_managed_deployment_artifacts.py --environment staging --runtime-env-file .runtime/staging.env --release-tag <release-tag> --api-promotion-ref <repo@sha256:...> --batch-promotion-ref <repo@sha256:...>
uv run python scripts/verify_managed_deployment_bundle.py --environment staging
```

Verify the staging deploy workflow migration step succeeded before proceeding.

## Prepare AWS Test Account

1. Ensure the AWS test account has an assumable Valdrics role and cost visibility configured.
2. Seed one intentionally remediable low-risk resource in the account, for example:
   - an idle EC2 instance in a non-production subnet
3. Confirm the resource is in a region enabled for the connection.

## Connect AWS

1. In the Valdrics settings flow, create or verify the AWS connection.
2. Confirm the connection status is `active`.
3. If AWS Organizations discovery is enabled for the test account, verify the management account status is still `active` before continuing.

Expected failure states:
- `403` or feature gate failure: wrong tier or role
- connection verify failure: invalid role trust, missing external ID, expired trust

Check:
- application logs for `aws_connection_verified`
- Ops Center connection status

## Run Zombie Scan

1. Run the AWS scan from the dashboard or `GET /api/v1/zombies?region=<region>`.
2. Confirm at least one actionable result returns a persisted `finding_id`.
3. If AI analysis is enabled in staging, confirm any AI-enriched row still preserves the same `finding_id`.

Expected failure states:
- no `finding_id`: release blocker for this flow
- scan job enqueued but not completed: inspect job processor health

Check:
- logs for `aws_parallel_scan_starting` and the returned scan payload containing persisted `finding_id`
- `/api/v1/zombies/pending` remains unchanged until a request is created

## Create Remediation From Finding

1. Create the remediation request using the persisted `finding_id`.
2. Confirm the request succeeds and returns `request_id`.
3. Repeat the same request immediately and confirm duplicate open request protection returns `409`.

Expected failure states:
- `404`: stale or non-tenant finding
- `409`: duplicate open request, expected only on replay
- `400`: inactive or mismatched connection binding

Check:
- logs for `remediation_request_created_from_finding`
- logs for `remediation_request_duplicate_open_finding` on replay

## Approve And Execute

1. Approve the request from Ops Center or `POST /api/v1/zombies/approve/{request_id}`.
2. Execute the request.
3. In staging only, use grace-period bypass when required for the smoke test:

```bash
POST /api/v1/zombies/execute/{request_id}?bypass_grace_period=true
```

4. Confirm the remediation completes successfully.

Expected failure states:
- `403`: missing explicit remediation approval permission
- `400`: stale finding binding or inactive connection
- `500`: provider execution failure

Check:
- logs for `remediation_execution_started`
- logs for `remediation_executed`
- `409 remediation_finding_context_mismatch` if execution fails closed on stale binding

## Verify Resolved Finding In Ops Center

1. Open Ops Center.
2. Confirm the request disappears from the pending queue.
3. Confirm it appears in **Recent completions**.
4. Confirm the row shows:
   - resource
   - action
   - completion time
   - finding category
   - `Resolved` finding status

Release blocker:
- completed request visible without resolved finding linkage

## Verify Savings Proof

1. Trigger realized savings computation for a window that includes the completed remediation:

```bash
POST /api/v1/savings/realized/compute?start_date=<window-start>&end_date=<window-end>&baseline_days=7&measurement_days=7&gap_days=1&monthly_multiplier_days=30&require_final=true
```

2. Confirm the compute response reports the remediation as either:
   - `computed`
   - or explicitly `skipped` for a deterministic reason such as insufficient finalized ledger data
3. Open the Savings Proof page for the same time window.
4. Confirm the realized evidence section includes the completed remediation.
5. Confirm the row shows:
   - `finding_category`
   - `finding_id`
   - `remediation_request_id`
   - realized monthly savings
6. Switch drilldown to `finding_category` and confirm the executed remediation contributes to the expected bucket.
7. Export CSV and confirm the exported row retains:
   - `finding_id`
   - `finding_category`
   - `remediation_request_id`
   - `realized_monthly_savings_usd`

Expected failure states:
- realized event missing because ledger prerequisites are incomplete
- provenance fields missing in JSON or CSV
- drilldown bucket mismatch

Check:
- logs for `realized_savings_computed`
- logs for `savings_proof_drilldown_generated`

## Required Metrics And Logs

Confirm these signals are present during the smoke run:

- duplicate remediation request rejection count
- finding-binding mismatch failures (`remediation_finding_context_mismatch`)
- realized savings compute skip reasons
- remediation history fetch errors
- savings drilldown generation logs

Minimum expected structured events:

- `remediation_request_created_from_finding`
- `remediation_request_duplicate_open_finding`
- `remediation_executed`
- `realized_savings_computed`
- `savings_proof_drilldown_generated`

## Exit Criteria

Promotion is blocked unless all of the following pass:

1. AWS connection is active and verified.
2. Scan returns actionable results with persisted `finding_id`.
3. Remediation request is created from `finding_id`.
4. Duplicate open request replay is rejected with `409`.
5. Approval and execution succeed.
6. The finding is resolved and visible as resolved in Ops Center history.
7. Savings Proof shows the completed remediation with provenance intact in JSON and CSV.

After the staging smoke run passes, complete the broader deployment flow in
[production_env_checklist.md](/home/daretechie/DevProject/GitHub/CloudSentinel-AI/docs/runbooks/production_env_checklist.md).
