from __future__ import annotations

import sqlite3
from datetime import date, datetime, timezone

from app.shared.db import sqlite_datetime


def test_register_sqlite_datetime_adapters_is_idempotent(monkeypatch) -> None:
    registered: list[tuple[object, object]] = []

    monkeypatch.setattr(sqlite_datetime, "_sqlite_adapters_registered", False)
    monkeypatch.setattr(
        sqlite3,
        "register_adapter",
        lambda value_type, serializer: registered.append((value_type, serializer)),
    )

    sqlite_datetime.register_sqlite_datetime_adapters()
    sqlite_datetime.register_sqlite_datetime_adapters()

    assert registered == [
        (date, sqlite_datetime._serialize_sqlite_date),
        (datetime, sqlite_datetime._serialize_sqlite_datetime),
    ]


def test_sqlite_datetime_serializers_are_explicit() -> None:
    assert sqlite_datetime._serialize_sqlite_date(date(2026, 3, 19)) == "2026-03-19"
    assert (
        sqlite_datetime._serialize_sqlite_datetime(
            datetime(2026, 3, 19, 12, 30, tzinfo=timezone.utc)
        )
        == "2026-03-19 12:30:00+00:00"
    )
