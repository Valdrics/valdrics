from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts import (
    run_rls_optimization,
    seed_dev_data,
    seed_pricing_plans,
    test_tenant_import,
    truncate_cost_records,
)


class _AsyncContextManager:
    def __init__(self, value: object) -> None:
        self._value = value

    async def __aenter__(self) -> object:
        return self._value

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        return None


def test_run_rls_optimization_uses_repo_root_sql_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sql_path = tmp_path / "scripts" / "optimize_performance_and_security.sql"
    sql_path.parent.mkdir(parents=True)
    sql_path.write_text("SELECT 1;", encoding="utf-8")

    driver_connection = SimpleNamespace(execute=AsyncMock())
    raw_conn = SimpleNamespace(driver_connection=driver_connection)
    connection = SimpleNamespace(get_raw_connection=AsyncMock(return_value=raw_conn))
    session = SimpleNamespace(connection=AsyncMock(return_value=connection))

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    monkeypatch.setattr(run_rls_optimization, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        run_rls_optimization,
        "async_session_maker",
        lambda: _AsyncContextManager(session),
    )

    assert run_rls_optimization.main([]) == 0
    driver_connection.execute.assert_awaited_once_with("SELECT 1;")


@pytest.mark.asyncio
async def test_test_tenant_import_fails_closed_on_orm_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    raw_result = SimpleNamespace(all=lambda: [1])

    async def _execute(statement):
        if "SELECT id FROM users" in str(statement):
            return raw_result
        raise RuntimeError("orm failed")

    session = SimpleNamespace(
        begin=lambda: _AsyncContextManager(None),
        execute=AsyncMock(side_effect=_execute),
        add=lambda _value: None,
    )
    engine = SimpleNamespace(dispose=AsyncMock())

    monkeypatch.setattr(
        test_tenant_import,
        "async_session_maker",
        lambda: _AsyncContextManager(session),
    )
    monkeypatch.setattr(test_tenant_import, "get_engine", lambda: engine)

    assert await test_tenant_import.seed_data() == 1
    engine.dispose.assert_awaited_once()
    assert "Tenant import failed" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_truncate_cost_data_returns_failure_without_database_url(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        truncate_cost_records,
        "get_settings",
        lambda: SimpleNamespace(DATABASE_URL=""),
    )

    assert await truncate_cost_records.truncate_cost_data() == 1
    assert "DATABASE_URL not set." in capsys.readouterr().out


@pytest.mark.asyncio
async def test_truncate_cost_data_returns_failure_on_execution_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    connection = SimpleNamespace(
        execution_options=AsyncMock(return_value=None),
        execute=AsyncMock(side_effect=RuntimeError("truncate failed")),
    )
    engine = SimpleNamespace(
        connect=lambda: _AsyncContextManager(connection),
        dispose=AsyncMock(),
    )

    monkeypatch.setattr(
        truncate_cost_records,
        "get_settings",
        lambda: SimpleNamespace(DATABASE_URL="postgresql+asyncpg://user:pass@db.example.com/db"),
    )
    monkeypatch.setattr(truncate_cost_records, "create_async_engine", lambda _url: engine)

    assert await truncate_cost_records.truncate_cost_data() == 1
    engine.dispose.assert_awaited_once()
    assert "truncate failed" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_seed_dev_data_uses_get_engine_and_disposes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = SimpleNamespace(scalars=lambda: SimpleNamespace(first=lambda: object()))
    session = SimpleNamespace(
        begin=lambda: _AsyncContextManager(None),
        execute=AsyncMock(return_value=result),
    )
    engine = SimpleNamespace(dispose=AsyncMock())

    monkeypatch.setattr(seed_dev_data, "async_session_maker", lambda: _AsyncContextManager(session))
    monkeypatch.setattr(seed_dev_data, "get_engine", lambda: engine)

    assert await seed_dev_data.seed_data() == 0
    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_seed_pricing_plans_returns_failure_and_disposes_on_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = SimpleNamespace(
        begin=lambda: _AsyncContextManager(None),
        execute=AsyncMock(side_effect=RuntimeError("pricing failed")),
    )
    engine = SimpleNamespace(dispose=AsyncMock())

    monkeypatch.setattr(
        seed_pricing_plans,
        "async_session_maker",
        lambda: _AsyncContextManager(session),
    )
    monkeypatch.setattr(seed_pricing_plans, "get_engine", lambda: engine)

    assert await seed_pricing_plans.seed_data() == 1
    engine.dispose.assert_awaited_once()
    assert "pricing failed" in capsys.readouterr().out
