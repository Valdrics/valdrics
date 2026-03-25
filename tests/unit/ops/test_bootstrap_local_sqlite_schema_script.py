from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from scripts import bootstrap_local_sqlite_schema as bootstrap_script


def test_bootstrap_local_sqlite_schema_restores_environment(capsys) -> None:
    fake_settings = SimpleNamespace(
        DATABASE_URL="sqlite+aiosqlite:////tmp/bootstrap.sqlite",
        TESTING=False,
    )
    fake_engine = SimpleNamespace(dispose=AsyncMock())
    fake_result = {
        "database_path": "/tmp/bootstrap.sqlite",
        "table_count": 12,
        "alembic_heads": ["head123"],
    }

    with (
        patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql+asyncpg://prod.example/app",
                "LOCAL_SQLITE_BOOTSTRAP": "false",
            },
            clear=True,
        ),
        patch(
            "app.shared.core.config.reload_settings_from_environment",
            return_value=fake_settings,
        ),
        patch("app.shared.db.session.reset_db_runtime"),
        patch("app.shared.db.session.get_engine", return_value=fake_engine),
        patch(
            "app.shared.db.local_sqlite_bootstrap.bootstrap_local_sqlite_schema",
            new=AsyncMock(return_value=fake_result),
        ),
    ):
        result = asyncio.run(
            bootstrap_script._run("sqlite+aiosqlite:////tmp/bootstrap.sqlite")
        )

        assert result == 0
        assert dict(os.environ) == {
            "DATABASE_URL": "postgresql+asyncpg://prod.example/app",
            "LOCAL_SQLITE_BOOTSTRAP": "false",
        }

    fake_engine.dispose.assert_awaited_once()
    assert "[local-sqlite-bootstrap] ok database=/tmp/bootstrap.sqlite" in capsys.readouterr().out
