from __future__ import annotations

import httpx

from app.shared.core.exceptions import ExternalAPIError


class FakeResponse:
    def __init__(
        self,
        payload: dict,
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ):
        self._payload = payload
        self.status_code = status_code
        self.headers: dict[str, str] = headers or {}

    def json(self) -> dict:
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
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self) -> "FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        return False

    async def get(self, url: str, headers=None, params=None):  # type: ignore[no-untyped-def]
        assert url
        self.calls.append(
            {"method": "GET", "url": url, "headers": headers, "params": params}
        )
        if not self.responses:
            raise AssertionError("No fake responses configured for HTTP call")
        next_item = self.responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item

    async def post(self, url: str, headers=None, params=None, json=None, auth=None):  # type: ignore[no-untyped-def]
        assert url
        self.calls.append(
            {
                "method": "POST",
                "url": url,
                "headers": headers,
                "params": params,
                "json": json,
                "auth": auth,
            }
        )
        if not self.responses:
            raise AssertionError("No fake responses configured for HTTP call")
        next_item = self.responses.pop(0)
        if isinstance(next_item, Exception):
            raise next_item
        return next_item


class InvalidJSONResponse(FakeResponse):
    def json(self) -> dict:  # type: ignore[override]
        raise ValueError("invalid json")


async def raise_external_api_error(*_args, **_kwargs):
    raise ExternalAPIError("upstream down")
    yield {}  # pragma: no cover


def http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.invalid")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError(
        message=f"status={status_code}",
        request=request,
        response=response,
    )
