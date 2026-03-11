# Webhook Job Reliability Drill

This runbook defines the release-critical reliability drill for the Paystack webhook ingestion path and the downstream `background_jobs` processor.

## Scope

The drill must verify all of the following controls before promotion:

1. Replay duplicate Paystack webhook deliveries without creating duplicate durable queue entries or duplicate financial actions.
2. Simulate burst duplicate deliveries and confirm the deduplication key remains stable for the entire burst.
3. Kill a worker while jobs are `RUNNING` and verify stale-job recovery requeues or dead-letters abandoned work.
4. Verify permanently failing jobs move to `DEAD_LETTER` instead of silently succeeding.
5. Verify terminal job retention cleanup deletes completed, failed, and dead-letter rows deterministically.
6. Verify broker dispatch failure falls back inline and increments the scheduler fallback signal.

## Repository-Managed Deterministic Drill

Run the deterministic local drill:

```bash
DEBUG=false uv run python3 scripts/run_webhook_job_reliability_drill.py --out /tmp/webhook_job_reliability_drill.json
```

The drill runner performs two classes of checks:

1. Local non-prod schema apply via `scripts/bootstrap_local_sqlite_schema.py`.
2. Scenario-specific pytest targets covering duplicate redelivery, stale recovery, dead-letter routing, retention cleanup, and scheduler inline fallback.

## Staging Drill

Use staging for the full operational rehearsal after the deterministic local drill passes.

1. Apply the pending migrations against staging:

```bash
uv run python scripts/generate_managed_migration_env.py --environment staging
uv run python scripts/generate_managed_runtime_env.py --environment staging
uv run python scripts/generate_managed_deployment_artifacts.py --environment staging --runtime-env-file .runtime/staging.env
uv run python scripts/verify_managed_deployment_bundle.py --environment staging
uv run python scripts/validate_migration_env.py --env-file .runtime/staging.migrate.env
set -a && source .runtime/staging.migrate.env && uv run alembic upgrade head
```

2. Replay duplicate Paystack webhook payloads against `POST /api/v1/billing/webhook`.
3. Send a burst of duplicate deliveries for the same Paystack reference and confirm only one durable queue entry remains active.
4. kill a worker while jobs are `RUNNING`, then verify the recovery sweep requeues or dead-letters them.
5. Verify terminal retention cleanup removes expired `background_jobs` rows.

## Required Metrics

Confirm these metrics are present and changing as expected during the drill:

- `valdrics_ops_background_jobs_stale_running_recovered_total`
- `valdrics_ops_background_jobs_dead_lettered_total`
- `valdrics_ops_background_jobs_overdue_pending_count`
- `valdrics_ops_audit_log_retention_failures_total`
- `valdrics_scheduler_inline_fallback_total`

## Required Alerts

Confirm these Prometheus rules exist before production promotion:

- `BackgroundJobStaleRunningRecoveryDetected`
- `BackgroundJobDeadLetterGrowth`
- `BackgroundJobsOverduePending`
- `AuditLogRetentionFailures`
- `SchedulerInlineFallbackActive`

## Exit Criteria

Promotion is blocked unless:

1. The deterministic drill report passes.
2. Staging migration apply completes successfully.
3. Duplicate redelivery does not create duplicate financial side effects.
4. Stale `RUNNING` jobs recover without manual database edits.
5. The dashboard panels and alerts show the expected signals during the drill window.

After the staging drill passes, execute the production rollout sequence in
[`docs/runbooks/production_env_checklist.md`](./production_env_checklist.md),
including `uv run python scripts/verify_managed_deployment_bundle.py --environment production`,
including `uv run python scripts/validate_migration_env.py --env-file .runtime/production.migrate.env`,
`set -a && source .runtime/production.migrate.env && uv run alembic upgrade head`,
and `uv run python scripts/validate_runtime_env.py --environment production --env-file .runtime/production.env`.
