from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import httpx


def build_connection(
    *,
    vendor: str = "generic",
    auth_method: str = "manual",
    api_key: object | None = "token-123",
    connector_config: dict | None = None,
    license_feed: object | None = None,
) -> MagicMock:
    conn = MagicMock()
    conn.vendor = vendor
    conn.auth_method = auth_method
    conn.api_key = api_key
    conn.connector_config = connector_config or {}
    conn.license_feed = [] if license_feed is None else license_feed
    return conn


class FakeGetClient:
    def __init__(self, response: httpx.Response):
        self._response = response

    async def __aenter__(self) -> "FakeGetClient":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def get(  # type: ignore[no-untyped-def]
        self, url: str, *, headers=None, params=None
    ) -> httpx.Response:
        _ = url, headers, params
        return self._response


class FakeResponse:
    def __init__(self, payload: object, *, status_code: int = 200):
        self._payload = payload
        self.status_code = status_code

    def json(self) -> object:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code < 400:
            return
        request = httpx.Request("GET", "https://example.invalid")
        response = httpx.Response(self.status_code, request=request)
        raise httpx.HTTPStatusError(
            message=f"status={self.status_code}",
            request=request,
            response=response,
        )


class FakeAsyncClient:
    def __init__(self, responses: list[object]):
        self.responses = list(responses)

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        _ = exc_type, exc, tb
        return False

    async def get(self, _url: str, *, headers=None, params=None):  # type: ignore[no-untyped-def]
        _ = headers, params
        if not self.responses:
            raise AssertionError("No fake responses configured")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class Secret:
    def __init__(self, value: str):
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


def parse_or_raise(value: object) -> datetime:
    if value == "raise-me":
        raise ValueError("bad timestamp")
    text = str(value).replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def row_generator(row: dict[str, object]):
    async def _gen(*_args, **_kwargs):
        yield row

    return _gen


def http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.invalid")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        message=f"status={status_code}",
        request=request,
        response=response,
    )
