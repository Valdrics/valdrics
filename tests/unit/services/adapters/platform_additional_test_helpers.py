from __future__ import annotations

from unittest.mock import MagicMock

import httpx

from app.shared.core.exceptions import ExternalAPIError


class _FakeResponse:
    def __init__(
        self,
        payload: object,
        *,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}

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


class _InvalidJSONResponse(_FakeResponse):
    def json(self) -> object:  # type: ignore[override]
        raise ValueError("invalid-json")


class _FakeAsyncClient:
    def __init__(self, responses: list[object]):
        self.responses = list(responses)
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        return False

    async def get(  # type: ignore[no-untyped-def]
        self,
        url: str,
        headers=None,
        params=None,
        timeout=None,
        **kwargs,
    ):
        self.calls.append(
            {
                "method": "GET",
                "url": url,
                "headers": headers,
                "params": params,
                "timeout": timeout,
                **kwargs,
            }
        )
        if not self.responses:
            raise AssertionError("No fake responses configured")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    async def post(  # type: ignore[no-untyped-def]
        self,
        url: str,
        headers=None,
        params=None,
        json=None,
        auth=None,
        timeout=None,
        **kwargs,
    ):
        self.calls.append(
            {
                "method": "POST",
                "url": url,
                "headers": headers,
                "params": params,
                "json": json,
                "auth": auth,
                "timeout": timeout,
                **kwargs,
            }
        )
        if not self.responses:
            raise AssertionError("No fake responses configured")
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _conn(
    *,
    vendor: str = "generic",
    auth_method: str = "manual",
    api_key: object | None = "token-123",
    api_secret: object | None = "secret-123",
    connector_config: dict | None = None,
    spend_feed: object | None = None,
) -> MagicMock:
    conn = MagicMock()
    conn.vendor = vendor
    conn.auth_method = auth_method
    conn.api_key = api_key
    conn.api_secret = api_secret
    conn.connector_config = connector_config or {}
    conn.spend_feed = [] if spend_feed is None else spend_feed
    return conn


def _http_status_error(status_code: int, *, method: str = "GET") -> httpx.HTTPStatusError:
    request = httpx.Request(method, "https://example.invalid")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        message=f"status={status_code}",
        request=request,
        response=response,
    )


async def _raise_external_api_error(*_args, **_kwargs):
    raise ExternalAPIError("native upstream down")
    yield {}  # pragma: no cover


class _Secret:
    def __init__(self, value: str):
        self._value = value

    def get_secret_value(self) -> str:
        return self._value


def _single_row_gen(row: dict[str, object]):
    async def _gen(*_args, **_kwargs):
        yield row

    return _gen
