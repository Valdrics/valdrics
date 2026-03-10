from __future__ import annotations

import asyncio
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator

import structlog
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

import app.models  # noqa: F401
from app.shared.db.base import Base

logger = structlog.get_logger()

_STRICT_ENVIRONMENTS = frozenset({"production", "staging"})
_bootstrap_lock = asyncio.Lock()

fcntl: ModuleType | None

try:  # pragma: no cover - exercised on Linux; guarded for portability.
    import fcntl as _fcntl
except ImportError:  # pragma: no cover
    fcntl = None
else:  # pragma: no cover - exercised on Linux; guarded for portability.
    fcntl = _fcntl


def should_bootstrap_local_sqlite(settings_obj: Any, effective_url: str) -> bool:
    environment = str(getattr(settings_obj, "ENVIRONMENT", "") or "").strip().lower()
    return bool(
        getattr(settings_obj, "LOCAL_SQLITE_BOOTSTRAP", False)
        and not bool(getattr(settings_obj, "TESTING", False))
        and "sqlite" in str(effective_url or "").strip().lower()
        and environment not in _STRICT_ENVIRONMENTS
    )


def resolve_sqlite_database_path(effective_url: str) -> Path | None:
    url = make_url(str(effective_url or "").strip())
    if url.get_backend_name() != "sqlite":
        return None
    database = str(url.database or "").strip()
    if not database or database == ":memory:":
        return None
    path = Path(database)
    if not path.is_absolute():
        path = path.resolve()
    return path


def _lock_path_for_database(db_path: Path) -> Path:
    suffix = f"{db_path.suffix}.bootstrap.lock" if db_path.suffix else ".bootstrap.lock"
    return db_path.with_suffix(suffix)


def _set_system_context_marker(connection: AsyncConnection, enabled: bool) -> None:
    sync_connection = getattr(connection, "sync_connection", None)
    if sync_connection is None:
        return
    if enabled:
        sync_connection.info["rls_system_context"] = True
        return
    sync_connection.info.pop("rls_system_context", None)


@contextmanager
def _bootstrap_file_lock(db_path: Path | None) -> Iterator[None]:
    if db_path is None or fcntl is None:
        yield
        return

    db_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = _lock_path_for_database(db_path)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@lru_cache(maxsize=1)
def get_alembic_heads() -> tuple[str, ...]:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)
    heads = tuple(sorted(script.get_heads()))
    if not heads:
        raise RuntimeError("Alembic script directory has no heads to stamp.")
    return heads


async def _stamp_alembic_heads(
    connection: AsyncConnection,
    heads: tuple[str, ...],
) -> tuple[str, ...]:
    await connection.execute(
        text(
            "CREATE TABLE IF NOT EXISTS alembic_version ("
            "version_num VARCHAR(32) NOT NULL PRIMARY KEY)"
        )
    )
    result = await connection.execute(text("SELECT version_num FROM alembic_version"))
    existing = tuple(sorted(str(row[0]) for row in result.all()))
    if existing == heads:
        return existing

    await connection.execute(text("DELETE FROM alembic_version"))
    for head in heads:
        await connection.execute(
            text("INSERT INTO alembic_version (version_num) VALUES (:version_num)"),
            {"version_num": head},
        )
    return heads


async def _count_sqlite_tables(connection: AsyncConnection) -> int:
    result = await connection.execute(
        text(
            "SELECT COUNT(*) FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    )
    count = result.scalar_one()
    return int(count or 0)


async def bootstrap_local_sqlite_schema(
    *,
    engine: AsyncEngine,
    effective_url: str,
    settings_obj: Any,
) -> dict[str, Any]:
    if not should_bootstrap_local_sqlite(settings_obj, effective_url):
        return {"enabled": False, "bootstrapped": False}

    db_path = resolve_sqlite_database_path(effective_url)
    existed_before = db_path.exists() if db_path is not None else False
    heads = get_alembic_heads()

    async with _bootstrap_lock:
        with _bootstrap_file_lock(db_path):
            if db_path is not None:
                db_path.parent.mkdir(parents=True, exist_ok=True)
            async with engine.begin() as connection:
                _set_system_context_marker(connection, True)
                try:
                    await connection.run_sync(Base.metadata.create_all)
                    stamped_heads = await _stamp_alembic_heads(connection, heads)
                    table_count = await _count_sqlite_tables(connection)
                finally:
                    _set_system_context_marker(connection, False)

    payload = {
        "enabled": True,
        "bootstrapped": True,
        "database_path": db_path.as_posix() if db_path is not None else ":memory:",
        "database_preexisted": existed_before,
        "alembic_heads": stamped_heads,
        "table_count": table_count,
    }
    logger.info("local_sqlite_schema_bootstrapped", **payload)
    return payload
