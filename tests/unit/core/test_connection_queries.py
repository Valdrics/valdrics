from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.shared.core import connection_queries as cq


def _result(rows: list[object]) -> MagicMock:
    result = MagicMock()
    result.scalars.return_value.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_list_connections_respects_global_limit_across_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _result([SimpleNamespace(id="aws-1"), SimpleNamespace(id="aws-2")]),
            _result([SimpleNamespace(id="azure-1")]),
        ]
    )

    monkeypatch.setattr(
        cq,
        "_iter_model_pairs",
        lambda providers=None: [("aws", cq.AWSConnection), ("azure", cq.AzureConnection)],
    )

    rows = await cq.list_connections(db, limit=3)

    assert [row.id for row in rows] == ["aws-1", "aws-2", "azure-1"]
    first_stmt = db.execute.await_args_list[0].args[0]
    second_stmt = db.execute.await_args_list[1].args[0]
    assert getattr(getattr(first_stmt, "_limit_clause", None), "value", None) == 3
    assert getattr(getattr(second_stmt, "_limit_clause", None), "value", None) == 1


@pytest.mark.asyncio
async def test_list_active_connections_all_tenants_passes_limit_and_locking(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock()
    db.execute = AsyncMock(return_value=_result([SimpleNamespace(id="aws-1")]))

    monkeypatch.setattr(
        cq,
        "_iter_model_pairs",
        lambda providers=None: [("aws", cq.AWSConnection)],
    )

    await cq.list_active_connections_all_tenants(
        db,
        with_for_update=True,
        skip_locked=True,
        limit=2,
    )

    stmt = db.execute.await_args.args[0]
    assert getattr(getattr(stmt, "_limit_clause", None), "value", None) == 2
    assert stmt._for_update_arg is not None
    assert stmt._for_update_arg.skip_locked is True
