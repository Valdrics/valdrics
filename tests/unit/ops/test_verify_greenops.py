from __future__ import annotations

from types import SimpleNamespace

import httpx
import pytest

import scripts.verify_greenops as greenops_verifier


class _FakeAsyncClient:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls: list[tuple[str, dict[str, str]]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, *, headers):
        self.calls.append((url, headers))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


@pytest.mark.asyncio
async def test_verify_greenops_returns_failure_without_auth_in_production(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        greenops_verifier,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="production", ADMIN_API_KEY=""),
    )
    monkeypatch.delenv("VERIFICATION_TOKEN", raising=False)
    monkeypatch.delenv("ADMIN_API_KEY", raising=False)

    assert await greenops_verifier.verify_greenops_api() == 1


@pytest.mark.asyncio
async def test_verify_greenops_returns_success_when_both_checks_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeAsyncClient(
        [
            httpx.Response(200, json={"source": "forecast"}),
            httpx.Response(200, json={"recommendation": "shift"}),
        ]
    )
    monkeypatch.setattr(
        greenops_verifier,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="staging", ADMIN_API_KEY="admin-key"),
    )
    monkeypatch.setattr(greenops_verifier.httpx, "AsyncClient", lambda timeout: fake_client)

    assert await greenops_verifier.verify_greenops_api() == 0
    assert fake_client.calls[0][1] == {"X-Admin-API-Key": "admin-key"}


@pytest.mark.asyncio
async def test_verify_greenops_returns_failure_when_endpoint_auth_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeAsyncClient(
        [
            httpx.Response(401, text="unauthorized"),
            httpx.Response(200, json={"recommendation": "shift"}),
        ]
    )
    monkeypatch.setattr(
        greenops_verifier,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="staging", ADMIN_API_KEY=""),
    )
    monkeypatch.setenv("VERIFICATION_TOKEN", "bearer-token")
    monkeypatch.setattr(greenops_verifier.httpx, "AsyncClient", lambda timeout: fake_client)

    assert await greenops_verifier.verify_greenops_api() == 1


@pytest.mark.asyncio
async def test_verify_greenops_returns_failure_on_connection_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeAsyncClient(
        [
            httpx.ConnectError("boom"),
            httpx.Response(200, json={"recommendation": "shift"}),
        ]
    )
    monkeypatch.setattr(
        greenops_verifier,
        "get_settings",
        lambda: SimpleNamespace(ENVIRONMENT="staging", ADMIN_API_KEY=""),
    )
    monkeypatch.setenv("VERIFICATION_TOKEN", "bearer-token")
    monkeypatch.setattr(greenops_verifier.httpx, "AsyncClient", lambda timeout: fake_client)

    assert await greenops_verifier.verify_greenops_api() == 1
