import os

from scripts.in_process_runtime_env import configure_isolated_test_environment


def test_configure_isolated_test_environment_restores_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://db.example.com/app")
    monkeypatch.setenv("TESTING", "false")
    original_environment = dict(os.environ)

    with configure_isolated_test_environment(
        database_url="sqlite+aiosqlite:///tmp/in-process.sqlite3"
    ) as overrides:
        assert overrides["DATABASE_URL"] == "sqlite+aiosqlite:///tmp/in-process.sqlite3"
        assert os.environ["DATABASE_URL"] == overrides["DATABASE_URL"]
        assert os.environ["TESTING"] == "true"

    assert os.environ == original_environment
