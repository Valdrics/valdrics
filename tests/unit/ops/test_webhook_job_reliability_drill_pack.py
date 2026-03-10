from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.run_webhook_job_reliability_drill import (
    DRILL_SCENARIOS,
    LOCAL_DRILL_ENV_SEED,
    _build_local_bootstrap_env,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
RUNBOOK_PATH = REPO_ROOT / "docs" / "runbooks" / "webhook_job_reliability_drill.md"
SCRIPT_PATH = REPO_ROOT / "scripts" / "run_webhook_job_reliability_drill.py"


def test_webhook_job_reliability_drill_artifacts_exist() -> None:
    assert RUNBOOK_PATH.exists(), str(RUNBOOK_PATH)
    assert SCRIPT_PATH.exists(), str(SCRIPT_PATH)


def test_webhook_job_reliability_drill_scenarios_cover_required_failures() -> None:
    names = {scenario.name for scenario in DRILL_SCENARIOS}

    assert names == {
        "duplicate_paystack_redelivery",
        "burst_concurrent_deliveries",
        "worker_crash_running_job_recovery",
        "dead_letter_routing",
        "retention_cleanup",
        "scheduler_inline_fallback",
    }

    combined_targets = "\n".join(
        target
        for scenario in DRILL_SCENARIOS
        for target in scenario.pytest_targets
    )
    assert (
        "test_store_webhook_burst_duplicate_redeliveries_share_single_queue_entry"
        in combined_targets
    )
    assert (
        "test_store_webhook_concurrent_burst_duplicate_redeliveries_share_single_queue_entry"
        in combined_targets
    )
    assert "test_recover_stale_running_jobs_records_requeue_metric" in combined_targets
    assert "test_process_single_job_dead_letter" in combined_targets
    assert "test_purge_terminal_background_jobs_batches_until_empty" in combined_targets
    assert (
        "test_background_job_processing_falls_back_inline_when_celery_unavailable"
        in combined_targets
    )


def test_webhook_job_reliability_drill_builds_secure_local_bootstrap_env() -> None:
    with TemporaryDirectory(prefix="valdrics-drill-env-test-") as tmp_dir:
        database_url = f"sqlite+aiosqlite:///{Path(tmp_dir) / 'drill.sqlite3'}"
        env = _build_local_bootstrap_env(database_url)

    assert env["DATABASE_URL"] == database_url
    assert env["LOCAL_SQLITE_BOOTSTRAP"] == "true"
    assert env["ENVIRONMENT"] == "local"
    assert len(env["CSRF_SECRET_KEY"]) >= 32
    assert env["ENCRYPTION_KEY"]
    assert env["ADMIN_API_KEY"]
    assert LOCAL_DRILL_ENV_SEED == "valdrics-webhook-job-reliability-drill-v1"


def test_webhook_job_reliability_runbook_documents_required_metrics_and_alerts() -> None:
    text = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "scripts/run_webhook_job_reliability_drill.py" in text
    assert "scripts/bootstrap_local_sqlite_schema.py" in text
    assert "uv run alembic upgrade head" in text
    assert "kill a worker while jobs are `RUNNING`" in text
    assert "Send a burst of duplicate deliveries" in text
    assert "valdrics_ops_background_jobs_stale_running_recovered_total" in text
    assert "valdrics_ops_background_jobs_dead_lettered_total" in text
    assert "valdrics_ops_background_jobs_overdue_pending_count" in text
    assert "valdrics_ops_audit_log_retention_failures_total" in text
    assert "valdrics_scheduler_inline_fallback_total" in text
    assert "BackgroundJobDeadLetterGrowth" in text
    assert "SchedulerInlineFallbackActive" in text
