from __future__ import annotations

from pathlib import Path

from scripts.smoke_test_local_sqlite_bootstrap import (
    run_local_sqlite_bootstrap_smoke,
)


def test_run_local_sqlite_bootstrap_smoke_reaches_healthy_app(tmp_path: Path) -> None:
    result = run_local_sqlite_bootstrap_smoke(
        database_path=tmp_path / "local-smoke.sqlite3"
    )

    assert result["status"] == "healthy"
    assert result["database_status"] == "up"
    assert result["database_engine"] == "sqlite"
    assert result["cache_status"] == "disabled"
    assert result["aws_status"] == "healthy"
    assert result["background_jobs_status"] == "healthy"
