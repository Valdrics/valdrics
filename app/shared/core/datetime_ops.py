from __future__ import annotations

from datetime import datetime, timezone


def as_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def as_utc_datetime_or_none(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return as_utc_datetime(value)
