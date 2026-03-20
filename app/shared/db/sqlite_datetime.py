from __future__ import annotations

import sqlite3
from datetime import date, datetime
from threading import Lock

_sqlite_adapters_registered = False
_sqlite_adapters_lock = Lock()


def _serialize_sqlite_date(value: date) -> str:
    return value.isoformat()


def _serialize_sqlite_datetime(value: datetime) -> str:
    return value.isoformat(sep=" ")


def register_sqlite_datetime_adapters() -> None:
    """Register explicit sqlite adapters for date/datetime values.

    Python 3.12 deprecates sqlite3's implicit datetime adapter. SQLite is only
    used in tests/local runtime scaffolds here, but those paths should still use
    explicit adapters instead of relying on deprecated interpreter defaults.
    """

    global _sqlite_adapters_registered
    if _sqlite_adapters_registered:
        return

    with _sqlite_adapters_lock:
        if _sqlite_adapters_registered:
            return
        sqlite3.register_adapter(date, _serialize_sqlite_date)
        sqlite3.register_adapter(datetime, _serialize_sqlite_datetime)
        _sqlite_adapters_registered = True
