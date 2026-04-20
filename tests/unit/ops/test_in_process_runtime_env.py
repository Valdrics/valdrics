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
        assert os.environ["ALLOW_TEST_DATABASE_URL"] == "true"

    assert os.environ == original_environment


def test_configure_isolated_test_environment_allows_explicit_postgres_runtime(monkeypatch) -> None:
    monkeypatch.delenv("ALLOW_TEST_DATABASE_URL", raising=False)

    with configure_isolated_test_environment(
        database_url="postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/valdrics_ci"
    ) as overrides:
        assert overrides["DATABASE_URL"].startswith("postgresql+asyncpg://")
        assert overrides["ALLOW_TEST_DATABASE_URL"] == "true"
        assert os.environ["DATABASE_URL"] == overrides["DATABASE_URL"]
        assert os.environ["ALLOW_TEST_DATABASE_URL"] == "true"
