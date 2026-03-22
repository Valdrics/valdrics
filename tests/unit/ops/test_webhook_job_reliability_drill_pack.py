from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

import scripts.run_webhook_job_reliability_drill as reliability_drill
from scripts.run_webhook_job_reliability_drill import (
    DRILL_SCENARIOS,
    LOCAL_DRILL_ENV_SEED,
    _build_local_bootstrap_database_path,
    _build_local_bootstrap_env,
    main,
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


def test_webhook_job_reliability_drill_uses_unique_database_paths_per_run() -> None:
    first = _build_local_bootstrap_database_path()
    second = _build_local_bootstrap_database_path()

    assert first != second
    assert first.name == "drill.sqlite3"
    assert second.name == "drill.sqlite3"
    assert first.parent != second.parent


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


def test_main_resolves_relative_output_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = reliability_drill.REPO_ROOT
    output_path = repo_root / "tmp-webhook-drill.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        reliability_drill,
        "_current_alembic_heads",
        lambda: ("abc123",),
    )
    monkeypatch.setattr(
        reliability_drill,
        "_run_local_sqlite_bootstrap",
        lambda: {"passed": True},
    )
    monkeypatch.setattr(
        reliability_drill,
        "_run_pytest_targets",
        lambda targets: {"passed": True, "targets": list(targets)},
    )
    try:
        assert main(["--out", "tmp-webhook-drill.json"]) == 0
        assert output_path.exists()
    finally:
        output_path.unlink(missing_ok=True)


def test_main_rejects_relative_output_repo_escape() -> None:
    assert main(["--out", os.path.join("..", "escape.json")]) == 2


def test_main_rejects_directory_output_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    assert main(["--out", str(output_dir)]) == 2


def test_main_returns_two_when_report_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        reliability_drill,
        "_current_alembic_heads",
        lambda: ("abc123",),
    )
    monkeypatch.setattr(
        reliability_drill,
        "_run_local_sqlite_bootstrap",
        lambda: {"passed": True},
    )
    monkeypatch.setattr(
        reliability_drill,
        "_run_pytest_targets",
        lambda targets: {"passed": True, "targets": list(targets)},
    )
    monkeypatch.setattr(
        reliability_drill,
        "stage_text_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    assert main(["--out", str(tmp_path / "report.json")]) == 2
