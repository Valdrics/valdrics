#!/usr/bin/env python3
"""Run a deterministic webhook/job reliability drill against repository-managed checks."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
from dataclasses import dataclass
from datetime import datetime, timezone
import subprocess
import sys
import tempfile

from alembic.config import Config
from alembic.script import ScriptDirectory


REPO_ROOT = Path(__file__).resolve().parents[1]
LOCAL_DRILL_ENV_SEED = "valdrics-webhook-job-reliability-drill-v1"


@dataclass(frozen=True)
class DrillScenario:
    name: str
    description: str
    pytest_targets: tuple[str, ...]


DRILL_SCENARIOS: tuple[DrillScenario, ...] = (
    DrillScenario(
        name="duplicate_paystack_redelivery",
        description="Replay duplicate Paystack webhook deliveries and verify deterministic dedup/queue semantics.",
        pytest_targets=(
            "tests/unit/modules/reporting/test_webhook_retry.py::TestWebhookStorage::test_store_webhook_duplicate_returns_none",
            "tests/unit/modules/reporting/test_webhook_retry.py::TestWebhookStorage::test_store_webhook_already_queued_returns_none",
            "tests/unit/modules/reporting/test_webhook_retry.py::TestWebhookStorage::test_store_webhook_requeues_failed_existing_job",
        ),
    ),
    DrillScenario(
        name="burst_concurrent_deliveries",
        description="Replay a burst of concurrent duplicate Paystack deliveries and verify a single durable queue winner with stable deduplication keys.",
        pytest_targets=(
            "tests/unit/modules/reporting/test_webhook_retry.py::TestWebhookStorage::test_store_webhook_burst_duplicate_redeliveries_share_single_queue_entry",
            "tests/unit/modules/reporting/test_webhook_retry.py::TestWebhookStorage::test_store_webhook_concurrent_burst_duplicate_redeliveries_share_single_queue_entry",
        ),
    ),
    DrillScenario(
        name="worker_crash_running_job_recovery",
        description="Simulate worker death while jobs are RUNNING and verify stale-job recovery plus recovery metrics.",
        pytest_targets=(
            "tests/unit/governance/jobs/test_job_processor.py::test_recover_stale_running_jobs_records_requeue_metric",
            "tests/unit/governance/jobs/test_job_processor.py::test_recover_stale_running_jobs_records_dead_letter_metric_outcome",
        ),
    ),
    DrillScenario(
        name="dead_letter_routing",
        description="Verify permanently failing work transitions into dead-letter state instead of silent success.",
        pytest_targets=(
            "tests/unit/governance/jobs/test_job_processor.py::test_process_single_job_dead_letter",
            "tests/unit/governance/domain/jobs/handlers/test_base_handler.py::test_transition_to_dead_letter_swallows_recoverable_alert_failures",
        ),
    ),
    DrillScenario(
        name="retention_cleanup",
        description="Verify terminal background-job retention purges completed, failed, and dead-letter rows deterministically.",
        pytest_targets=(
            "tests/unit/tasks/test_scheduler_background_job_retention_ops.py::test_purge_terminal_background_jobs_batches_until_empty",
            "tests/unit/tasks/test_scheduler_background_job_retention_ops.py::test_purge_terminal_background_jobs_defaults_on_invalid_settings",
        ),
    ),
    DrillScenario(
        name="scheduler_inline_fallback",
        description="Verify broker/Celery dispatch failures fall back inline and emit the scheduler fallback signal.",
        pytest_targets=(
            "tests/unit/governance/scheduler/test_orchestrator.py::test_background_job_processing_falls_back_inline_when_celery_unavailable",
            "tests/unit/governance/scheduler/test_orchestrator_branches.py::test_dispatch_task_returns_false_when_inline_fallback_also_fails",
        ),
    ),
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run deterministic webhook/job reliability drill checks."
    )
    parser.add_argument(
        "--out",
        default="",
        help="Optional path for the JSON drill report.",
    )
    parser.add_argument(
        "--skip-local-bootstrap",
        action="store_true",
        help="Skip the local sqlite bootstrap step.",
    )
    return parser.parse_args(argv)


def _current_alembic_heads() -> tuple[str, ...]:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    return tuple(sorted(script.get_heads()))


def _tail(text: str, *, lines: int = 40) -> str:
    items = str(text or "").splitlines()
    return "\n".join(items[-lines:])


def _parse_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            continue
        key, _, value = raw_line.partition("=")
        rendered_value = value.strip()
        if rendered_value == "":
            env[key.strip()] = ""
            continue
        parsed = shlex.split(rendered_value, posix=True)
        env[key.strip()] = parsed[0] if parsed else ""
    return env


def _build_local_bootstrap_env(database_url: str) -> dict[str, str]:
    from scripts.generate_local_dev_env import generate_local_dev_env

    env = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="valdrics-drill-env-") as tmp_dir:
        env_path = Path(tmp_dir) / ".env.dev"
        generate_local_dev_env(
            template_path=REPO_ROOT / ".env.example",
            output_path=env_path,
            seed=LOCAL_DRILL_ENV_SEED,
        )
        env.update(_parse_env_file(env_path))

    env["DATABASE_URL"] = database_url
    env["DB_SSL_MODE"] = "disable"
    env["ENVIRONMENT"] = env.get("ENVIRONMENT", "local") or "local"
    env["LOCAL_SQLITE_BOOTSTRAP"] = "true"
    return env


def _run_subprocess(
    args: list[str],
    *,
    env: dict[str, str] | None = None,
) -> dict[str, object]:
    completed = subprocess.run(
        args,
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "command": " ".join(args),
        "exit_code": int(completed.returncode),
        "stdout_tail": _tail(completed.stdout),
        "stderr_tail": _tail(completed.stderr),
        "passed": completed.returncode == 0,
    }


def _build_local_bootstrap_database_path() -> Path:
    database_root = Path(
        tempfile.mkdtemp(prefix="valdrics_webhook_job_reliability_drill_")
    )
    return database_root / "drill.sqlite3"


def _run_local_sqlite_bootstrap() -> dict[str, object]:
    database_path = _build_local_bootstrap_database_path()
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    env = _build_local_bootstrap_env(database_url)

    result = _run_subprocess(
        [
            sys.executable,
            "scripts/bootstrap_local_sqlite_schema.py",
            "--database-url",
            database_url,
        ],
        env=env,
    )
    result["database_url"] = database_url
    result["database_path"] = database_path.as_posix()
    result["database_isolation"] = "unique_temp_path_per_run"
    return result


def _run_pytest_targets(targets: tuple[str, ...]) -> dict[str, object]:
    env = os.environ.copy()
    env["DEBUG"] = "false"
    return _run_subprocess(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--no-cov",
            *targets,
        ],
        env=env,
    )


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    captured_at = datetime.now(timezone.utc).isoformat()
    report: dict[str, object] = {
        "runner": "scripts/run_webhook_job_reliability_drill.py",
        "captured_at": captured_at,
        "alembic_heads": list(_current_alembic_heads()),
        "scenarios": [],
    }

    if not args.skip_local_bootstrap:
        report["local_sqlite_bootstrap"] = _run_local_sqlite_bootstrap()

    scenario_reports: list[dict[str, object]] = []
    for scenario in DRILL_SCENARIOS:
        scenario_report = {
            "name": scenario.name,
            "description": scenario.description,
            "pytest_targets": list(scenario.pytest_targets),
            "result": _run_pytest_targets(scenario.pytest_targets),
        }
        scenario_reports.append(scenario_report)

    report["scenarios"] = scenario_reports
    report["all_passed"] = bool(
        all(
            bool(scenario["result"]["passed"])
            for scenario in scenario_reports
        )
        and (
            args.skip_local_bootstrap
            or bool(report["local_sqlite_bootstrap"]["passed"])
        )
    )

    rendered = json.dumps(report, indent=2, sort_keys=True)
    print(rendered)
    if args.out:
        Path(args.out).write_text(rendered, encoding="utf-8")

    if not report["all_passed"]:
        raise SystemExit("Webhook/job reliability drill failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
