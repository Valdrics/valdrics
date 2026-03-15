from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
import sqlalchemy as sa

from app.modules.governance.domain.security.audit_log import AuditLog, SystemAuditLog
from app.tasks.scheduler_audit_log_retention_ops import purge_expired_audit_logs


def _select_result(rows: list[SimpleNamespace]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


def _delete_result(rowcount: int | object) -> MagicMock:
    result = MagicMock()
    result.rowcount = rowcount
    return result


def _delete_result_with_rows(
    *,
    rowcount: int | object,
    rows: list[SimpleNamespace],
) -> MagicMock:
    result = _delete_result(rowcount)
    result.fetchall.return_value = rows
    return result


@pytest.mark.asyncio
async def test_purge_expired_audit_logs_batches_until_empty() -> None:
    tenant_id = uuid4()
    stale_a = SimpleNamespace(
        id=uuid4(),
        event_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    stale_b = SimpleNamespace(
        id=uuid4(),
        event_timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _select_result([stale_a, stale_b]),
            _delete_result(2),
            _select_result([]),
        ]
    )
    logger = MagicMock()

    summary = await purge_expired_audit_logs(
        db=db,
        sa=sa,
        logger=logger,
        audit_log_model=AuditLog,
        datetime_cls=datetime,
        timezone_obj=timezone,
        timedelta_cls=timedelta,
        get_settings_fn=lambda: SimpleNamespace(
            AUDIT_LOG_RETENTION_DAYS=90,
            AUDIT_LOG_RETENTION_PURGE_BATCH_SIZE=5000,
            AUDIT_LOG_RETENTION_PURGE_MAX_BATCHES=20,
        ),
    )

    assert summary["total_deleted"] == 2
    assert summary["retention_days"] == 90
    assert summary["tenant_reports"] == [
        {"tenant_id": tenant_id, "deleted_count": 2}
    ]
    assert db.execute.await_count == 3
    logger.info.assert_any_call(
        "maintenance_audit_logs_purged",
        deleted=2,
        retention_days=90,
        batch_size=5000,
        max_batches=20,
    )


@pytest.mark.asyncio
async def test_purge_expired_audit_logs_defaults_on_invalid_settings() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_select_result([])])

    summary = await purge_expired_audit_logs(
        db=db,
        sa=sa,
        logger=MagicMock(),
        audit_log_model=AuditLog,
        datetime_cls=datetime,
        timezone_obj=timezone,
        timedelta_cls=timedelta,
        get_settings_fn=lambda: SimpleNamespace(
            AUDIT_LOG_RETENTION_DAYS=0,
            AUDIT_LOG_RETENTION_PURGE_BATCH_SIZE=10,
            AUDIT_LOG_RETENTION_PURGE_MAX_BATCHES=0,
        ),
    )

    assert summary["retention_days"] == 90
    assert summary["batch_size"] == 5000
    assert summary["max_batches"] == 20
    assert summary["total_deleted"] == 0


@pytest.mark.asyncio
async def test_purge_expired_audit_logs_uses_selected_row_count_when_rowcount_missing() -> None:
    tenant_id = uuid4()
    stale = SimpleNamespace(
        id=uuid4(),
        event_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        tenant_id=tenant_id,
    )
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _select_result([stale]),
            _delete_result("not-an-int"),
            _select_result([]),
        ]
    )

    summary = await purge_expired_audit_logs(
        db=db,
        sa=sa,
        logger=MagicMock(),
        audit_log_model=AuditLog,
        datetime_cls=datetime,
        timezone_obj=timezone,
        timedelta_cls=timedelta,
        get_settings_fn=lambda: SimpleNamespace(),
    )

    assert summary["total_deleted"] == 1
    assert summary["tenant_reports"] == [
        {"tenant_id": tenant_id, "deleted_count": 1}
    ]


@pytest.mark.asyncio
async def test_purge_expired_audit_logs_toggles_retention_delete_flag() -> None:
    db = AsyncMock()
    db.execute = AsyncMock(side_effect=[_select_result([])])
    toggle = AsyncMock()

    await purge_expired_audit_logs(
        db=db,
        sa=sa,
        logger=MagicMock(),
        audit_log_model=AuditLog,
        datetime_cls=datetime,
        timezone_obj=timezone,
        timedelta_cls=timedelta,
        get_settings_fn=lambda: SimpleNamespace(),
        set_audit_retention_purge_flag_fn=toggle,
    )

    assert toggle.await_args_list[0].args == (db, True)
    assert toggle.await_args_list[1].args == (db, False)


@pytest.mark.asyncio
async def test_purge_expired_audit_logs_supports_system_scope_model_without_tenant_id() -> None:
    stale = SimpleNamespace(
        id=uuid4(),
        event_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
    )
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _select_result([stale]),
            _delete_result(1),
            _select_result([]),
        ]
    )

    summary = await purge_expired_audit_logs(
        db=db,
        sa=sa,
        logger=MagicMock(),
        audit_log_model=SystemAuditLog,
        datetime_cls=datetime,
        timezone_obj=timezone,
        timedelta_cls=timedelta,
        get_settings_fn=lambda: SimpleNamespace(),
    )

    assert summary["total_deleted"] == 1
    assert summary["tenant_reports"] == []


@pytest.mark.asyncio
async def test_purge_expired_audit_logs_skips_inexact_tenant_attribution_without_returning_rows() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    stale_a = SimpleNamespace(
        id=uuid4(),
        event_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        tenant_id=tenant_a,
    )
    stale_b = SimpleNamespace(
        id=uuid4(),
        event_timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
        tenant_id=tenant_b,
    )
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _select_result([stale_a, stale_b]),
            _delete_result(1),
            _select_result([]),
        ]
    )
    logger = MagicMock()

    summary = await purge_expired_audit_logs(
        db=db,
        sa=sa,
        logger=logger,
        audit_log_model=AuditLog,
        datetime_cls=datetime,
        timezone_obj=timezone,
        timedelta_cls=timedelta,
        get_settings_fn=lambda: SimpleNamespace(),
    )

    assert summary["total_deleted"] == 1
    assert summary["tenant_reports"] == []
    logger.warning.assert_called_once()


@pytest.mark.asyncio
async def test_purge_expired_audit_logs_uses_returned_rows_for_exact_tenant_attribution() -> None:
    tenant_a = uuid4()
    tenant_b = uuid4()
    stale_a = SimpleNamespace(
        id=uuid4(),
        event_timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
        tenant_id=tenant_a,
    )
    stale_b = SimpleNamespace(
        id=uuid4(),
        event_timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
        tenant_id=tenant_b,
    )
    returned_a = SimpleNamespace(id=stale_a.id, tenant_id=tenant_a)
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _select_result([stale_a, stale_b]),
            _delete_result_with_rows(rowcount=1, rows=[returned_a]),
            _select_result([]),
        ]
    )

    summary = await purge_expired_audit_logs(
        db=db,
        sa=sa,
        logger=MagicMock(),
        audit_log_model=AuditLog,
        datetime_cls=datetime,
        timezone_obj=timezone,
        timedelta_cls=timedelta,
        get_settings_fn=lambda: SimpleNamespace(),
    )

    assert summary["total_deleted"] == 1
    assert summary["tenant_reports"] == [
        {"tenant_id": tenant_a, "deleted_count": 1}
    ]
