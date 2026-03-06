from __future__ import annotations

from decimal import InvalidOperation

from httpx import HTTPError
from sqlalchemy.exc import SQLAlchemyError

EXCHANGE_RATE_DB_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
)
EXCHANGE_RATE_CACHE_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
)
EXCHANGE_RATE_DECIMAL_PARSE_ERRORS: tuple[type[Exception], ...] = (
    InvalidOperation,
    TypeError,
    ValueError,
)
EXCHANGE_RATE_LIVE_PROVIDER_ERRORS: tuple[type[Exception], ...] = (
    HTTPError,
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    InvalidOperation,
)
