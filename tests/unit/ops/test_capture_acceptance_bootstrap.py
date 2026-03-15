from __future__ import annotations

import os

from scripts.capture_acceptance_bootstrap import ensure_test_env_for_in_process


def test_capture_acceptance_bootstrap_overrides_shell_database_url(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@db.example.com:5432/app",
    )

    safe_database_url = "sqlite+aiosqlite:///tmp/acceptance-evidence.sqlite3"
    ensure_test_env_for_in_process(safe_database_url)

    assert os.environ["DATABASE_URL"] == safe_database_url
    assert os.environ["TESTING"] == "true"
    assert os.environ["DB_SSL_MODE"] == "disable"
