from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.shared.db.local_sqlite_bootstrap import (
    _set_system_context_marker,
    bootstrap_local_sqlite_schema,
    get_alembic_heads,
    resolve_sqlite_database_path,
    should_bootstrap_local_sqlite,
)


def _settings(**overrides: object) -> SimpleNamespace:
    values: dict[str, object] = {
        "ENVIRONMENT": "local",
        "TESTING": False,
        "LOCAL_SQLITE_BOOTSTRAP": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_should_bootstrap_local_sqlite_requires_non_testing_local_sqlite() -> None:
    assert should_bootstrap_local_sqlite(
        _settings(),
        "sqlite+aiosqlite:///./valdrics_local_dev.sqlite3",
    )
    assert not should_bootstrap_local_sqlite(
        _settings(TESTING=True),
        "sqlite+aiosqlite:///./valdrics_local_dev.sqlite3",
    )
    assert not should_bootstrap_local_sqlite(
        _settings(LOCAL_SQLITE_BOOTSTRAP=False),
        "sqlite+aiosqlite:///./valdrics_local_dev.sqlite3",
    )
    assert not should_bootstrap_local_sqlite(
        _settings(ENVIRONMENT="production"),
        "sqlite+aiosqlite:///./valdrics_local_dev.sqlite3",
    )
    assert not should_bootstrap_local_sqlite(
        _settings(),
        "postgresql+asyncpg://postgres:postgres@localhost/valdrics",
    )


def test_resolve_sqlite_database_path_handles_relative_and_memory_urls(tmp_path: Path) -> None:
    relative_path = resolve_sqlite_database_path("sqlite+aiosqlite:///./test_local.sqlite")
    assert relative_path is not None
    assert relative_path.name == "test_local.sqlite"
    assert relative_path.is_absolute()

    absolute = resolve_sqlite_database_path(
        f"sqlite+aiosqlite:///{(tmp_path / 'db.sqlite').as_posix()}"
    )
    assert absolute == (tmp_path / "db.sqlite")
    assert resolve_sqlite_database_path("sqlite+aiosqlite:///:memory:") is None


def test_set_system_context_marker_updates_sync_connection_info() -> None:
    class _SyncConnection:
        def __init__(self) -> None:
            self.info: dict[str, object] = {}

    class _AsyncConnection:
        def __init__(self) -> None:
            self.sync_connection = _SyncConnection()

    connection = _AsyncConnection()
    _set_system_context_marker(connection, True)
    assert connection.sync_connection.info["rls_system_context"] is True

    _set_system_context_marker(connection, False)
    assert "rls_system_context" not in connection.sync_connection.info


@pytest.mark.asyncio
async def test_bootstrap_local_sqlite_schema_creates_tables_and_stamps_head(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "bootstrapped.sqlite"
    database_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"
    engine = create_async_engine(database_url)
    try:
        result = await bootstrap_local_sqlite_schema(
            engine=engine,
            effective_url=database_url,
            settings_obj=_settings(),
        )

        assert result["enabled"] is True
        assert result["bootstrapped"] is True
        assert result["database_preexisted"] is False
        assert result["database_path"] == db_path.as_posix()
        assert result["alembic_heads"] == get_alembic_heads()
        assert result["table_count"] > 0

        async with engine.connect() as connection:
            tables_result = await connection.execute(
                text(
                    "SELECT name FROM sqlite_master "
                    "WHERE type = 'table' AND name IN ('tenants', 'background_jobs', 'alembic_version') "
                    "ORDER BY name"
                )
            )
            assert [str(row[0]) for row in tables_result.all()] == [
                "alembic_version",
                "background_jobs",
                "tenants",
            ]

            head_result = await connection.execute(
                text("SELECT version_num FROM alembic_version ORDER BY version_num")
            )
            assert tuple(str(row[0]) for row in head_result.all()) == get_alembic_heads()

        second = await bootstrap_local_sqlite_schema(
            engine=engine,
            effective_url=database_url,
            settings_obj=_settings(),
        )
        assert second["database_preexisted"] is True
        assert second["alembic_heads"] == get_alembic_heads()
    finally:
        await engine.dispose()
