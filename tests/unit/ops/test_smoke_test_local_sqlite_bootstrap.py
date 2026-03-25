from __future__ import annotations

from pathlib import Path

import scripts.smoke_test_local_sqlite_bootstrap as sqlite_smoke
from scripts.smoke_test_local_sqlite_bootstrap import (
    _resolve_database_path,
    main,
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


def test_run_local_sqlite_bootstrap_smoke_rejects_directory_database_path(
    tmp_path: Path,
) -> None:
    with_path = tmp_path / "db-dir"
    with_path.mkdir()

    try:
        run_local_sqlite_bootstrap_smoke(database_path=with_path)
    except ValueError as exc:
        assert "database_path must be a file path" in str(exc)
    else:
        raise AssertionError("Expected directory database path to be rejected")


def test_main_returns_two_for_invalid_database_path(tmp_path: Path, capsys) -> None:
    env_dir = tmp_path / "db-dir"
    env_dir.mkdir()

    assert main(["--database-path", str(env_dir)]) == 2
    assert "invalid input" in capsys.readouterr().out


def test_resolve_database_path_uses_repo_root_not_caller_cwd(
    tmp_path: Path, monkeypatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    monkeypatch.setattr(sqlite_smoke, "_repo_root", lambda: repo_root)
    monkeypatch.chdir(outside)

    resolved = _resolve_database_path(Path("var/local-smoke.sqlite3"))

    assert resolved == (repo_root / "var/local-smoke.sqlite3").resolve()
