from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from scripts import (
    audit_schema,
    check_partitions,
    cleanup_partitions,
    create_partitions,
    manage_partitions,
    remediate_rls_gaps,
    run_archival_setup,
    seed_final,
    supabase_cleanup,
    verify_rls,
)


class _AsyncContextManager:
    def __init__(self, value: object) -> None:
        self._value = value

    async def __aenter__(self) -> object:
        return self._value

    async def __aexit__(self, exc_type, exc, tb) -> None:
        del exc_type, exc, tb
        return None


def _result(
    *,
    fetchall: object | None = None,
    scalar: object | None = None,
    first: object | None = None,
) -> MagicMock:
    result = MagicMock()
    if fetchall is not None:
        result.fetchall.return_value = fetchall
    if scalar is not None:
        result.scalar.return_value = scalar
    if first is not None:
        result.first.return_value = first
    return result


@pytest.mark.asyncio
async def test_audit_schema_marks_rls_exempt_tables(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    conn = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _result(
                    fetchall=[
                        SimpleNamespace(
                            table_name="users",
                            rls_enabled=False,
                            rls_forced=False,
                            total_size="8 kB",
                            index_count=1,
                        )
                    ]
                ),
                _result(scalar=1),
                _result(fetchall=[]),
            ]
        )
    )
    engine = SimpleNamespace(
        connect=lambda: _AsyncContextManager(conn),
        dispose=AsyncMock(),
    )
    monkeypatch.setattr(audit_schema, "get_engine", lambda: engine)

    await audit_schema.audit_schema()

    output = capsys.readouterr().out
    assert "RLS EXEMPT" in output
    assert "RLS NOT ENABLED" not in output


@pytest.mark.asyncio
async def test_verify_rls_ignores_exempt_tables(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    conn = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _result(fetchall=[("cloud_accounts",)]),
                _result(fetchall=[("users",), ("cloud_accounts",)]),
                _result(fetchall=[("users",), ("cloud_accounts",)]),
            ]
        )
    )
    engine = SimpleNamespace(
        connect=lambda: _AsyncContextManager(conn),
        dispose=AsyncMock(),
    )
    monkeypatch.setattr(verify_rls, "get_engine", lambda: engine)

    await verify_rls.check()

    output = capsys.readouterr().out
    assert "cloud_accounts" in output
    assert "users" not in output


@pytest.mark.asyncio
async def test_remediate_rls_gaps_skips_exempt_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = SimpleNamespace(
        execute=AsyncMock(side_effect=[[("users",), ("cloud_accounts",)], None, None]),
        commit=AsyncMock(),
        dialect=SimpleNamespace(
            identifier_preparer=SimpleNamespace(quote=lambda identifier: identifier)
        ),
    )
    engine = SimpleNamespace(
        connect=lambda: _AsyncContextManager(conn),
        dispose=AsyncMock(),
    )
    monkeypatch.setattr(remediate_rls_gaps, "get_engine", lambda: engine)

    await remediate_rls_gaps.remediate_rls()

    statements = [str(call.args[0]) for call in conn.execute.await_args_list[1:]]
    assert all("cloud_accounts" in statement for statement in statements)
    assert all("users" not in statement for statement in statements)


@pytest.mark.asyncio
async def test_seed_final_uses_tenant_scoped_blind_indexes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generated_indexes: list[tuple[str, object | None]] = []

    def _fake_generate_blind_index(value: str, tenant_id: object | None = None) -> str:
        generated_indexes.append((value, tenant_id))
        return f"bidx:{value}"

    first_result = MagicMock()
    first_result.first.return_value = None
    session = SimpleNamespace(
        execute=AsyncMock(side_effect=[first_result, _result(), _result()]),
        begin=lambda: _AsyncContextManager(None),
    )
    engine = SimpleNamespace(dispose=AsyncMock())

    monkeypatch.setattr(seed_final, "async_session_maker", lambda: _AsyncContextManager(session))
    monkeypatch.setattr(seed_final, "encrypt_string", lambda value: f"enc:{value}")
    monkeypatch.setattr(seed_final, "generate_blind_index", _fake_generate_blind_index)
    monkeypatch.setattr(seed_final, "get_engine", lambda: engine)

    await seed_final.seed_data()

    assert len(generated_indexes) == 2
    assert generated_indexes[0][1] is not None
    assert generated_indexes[0][1] == generated_indexes[1][1]


@pytest.mark.asyncio
async def test_cleanup_partitions_returns_failure_on_drop_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    conn = SimpleNamespace(
        execution_options=AsyncMock(return_value=None),
        execute=AsyncMock(side_effect=[[("cost_records_2025_01",)], RuntimeError("drop failed")]),
        dialect=SimpleNamespace(
            identifier_preparer=SimpleNamespace(quote=lambda identifier: identifier)
        ),
    )
    engine = SimpleNamespace(
        connect=lambda: _AsyncContextManager(conn),
        dispose=AsyncMock(),
    )
    monkeypatch.setattr(cleanup_partitions, "get_engine", lambda: engine)

    assert await cleanup_partitions.cleanup_old_partitions(execute=True) == 1
    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_supabase_cleanup_returns_failure_when_detection_step_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = SimpleNamespace(execute=AsyncMock())
    engine = SimpleNamespace(dispose=AsyncMock())

    monkeypatch.setattr(supabase_cleanup, "get_engine", lambda: engine)
    monkeypatch.setattr(
        supabase_cleanup,
        "async_session_maker",
        lambda: _AsyncContextManager(session),
    )
    monkeypatch.setattr(
        supabase_cleanup,
        "monitor_usage",
        AsyncMock(side_effect=RuntimeError("monitor failed")),
    )

    assert await supabase_cleanup.run_cleanup() == 1
    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_supabase_cleanup_returns_failure_when_vacuum_step_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = SimpleNamespace(execute=AsyncMock(return_value=[("cost_records_2025_01",)]))
    conn = SimpleNamespace(
        execution_options=AsyncMock(return_value=None),
        execute=AsyncMock(side_effect=RuntimeError("vacuum failed")),
    )
    engine = SimpleNamespace(
        connect=lambda: _AsyncContextManager(conn),
        dispose=AsyncMock(),
    )

    monkeypatch.setattr(supabase_cleanup, "get_engine", lambda: engine)
    monkeypatch.setattr(
        supabase_cleanup,
        "async_session_maker",
        lambda: _AsyncContextManager(session),
    )
    monkeypatch.setattr(
        supabase_cleanup,
        "monitor_usage",
        AsyncMock(return_value=None),
    )

    assert await supabase_cleanup.run_cleanup() == 1
    engine.dispose.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_partitions_rolls_back_failures_and_closes_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    call_count = {"value": 0}

    async def _execute(*args, **kwargs):
        del args, kwargs
        call_count["value"] += 1
        if call_count["value"] == 1:
            raise RuntimeError("ddl failed")
        return None

    session = SimpleNamespace(
        execute=AsyncMock(side_effect=_execute),
        commit=AsyncMock(),
        rollback=AsyncMock(),
        close=AsyncMock(),
    )
    monkeypatch.setattr(create_partitions, "async_session_maker", lambda: session)

    await create_partitions.create_partitions()

    session.rollback.assert_awaited_once()
    session.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_manage_partitions_create_uses_partition_service(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = SimpleNamespace(commit=AsyncMock())
    service = SimpleNamespace(create_future_partitions=AsyncMock(return_value=2))

    monkeypatch.setattr(
        manage_partitions,
        "async_session_maker",
        lambda: _AsyncContextManager(session),
    )
    monkeypatch.setattr(
        manage_partitions,
        "PartitionMaintenanceService",
        lambda _: service,
    )

    await manage_partitions.create_partitions(4)

    service.create_future_partitions.assert_awaited_once_with(months_ahead=4)
    session.commit.assert_awaited_once()
    assert "Partitions created: 2" in capsys.readouterr().out


@pytest.mark.asyncio
async def test_manage_partitions_validate_reports_missing_partition(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = SimpleNamespace(scalar=AsyncMock(side_effect=[True, False]))

    monkeypatch.setattr(
        manage_partitions,
        "async_session_maker",
        lambda: _AsyncContextManager(session),
    )
    monkeypatch.setattr(
        manage_partitions.PartitionMaintenanceService,
        "SUPPORTED_TABLES",
        ("cost_records", "audit_logs"),
    )

    await manage_partitions.validate_partitions(0)

    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["missing"]["audit_logs"]


@pytest.mark.asyncio
async def test_check_partitions_reports_partitions(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = SimpleNamespace(
        execute=AsyncMock(
            side_effect=[
                _result(scalar=True),
                _result(fetchall=[SimpleNamespace(child_table="audit_logs_p2026_03")]),
            ]
        )
    )
    monkeypatch.setattr(
        check_partitions,
        "async_session_maker",
        lambda: _AsyncContextManager(session),
    )

    await check_partitions.check()

    output = capsys.readouterr().out
    assert "Found 1 partitions" in output
    assert "audit_logs_p2026_03" in output


@pytest.mark.asyncio
async def test_run_archival_setup_invokes_partition_maintenance_service(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = SimpleNamespace(commit=AsyncMock())
    service = SimpleNamespace(
        create_future_partitions=AsyncMock(return_value=2),
        archive_old_partitions=AsyncMock(return_value=5),
    )

    monkeypatch.setattr(
        run_archival_setup,
        "_parse_args",
        lambda: SimpleNamespace(months_old=13, months_ahead=3),
    )
    monkeypatch.setattr(
        run_archival_setup,
        "async_session_maker",
        lambda: _AsyncContextManager(session),
    )
    monkeypatch.setattr(
        run_archival_setup,
        "PartitionMaintenanceService",
        lambda _: service,
    )

    await run_archival_setup.main()

    service.create_future_partitions.assert_awaited_once_with(months_ahead=3)
    service.archive_old_partitions.assert_awaited_once_with(months_old=13)
    session.commit.assert_awaited_once()
    assert "created=2 archived=5" in capsys.readouterr().out
