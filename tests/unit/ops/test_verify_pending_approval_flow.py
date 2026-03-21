from __future__ import annotations

import httpx
import pytest

import scripts.verify_pending_approval_flow as pending_flow
from scripts.verify_pending_approval_flow import (
    REQUEST_TIMEOUT,
    _api_get,
    _api_post,
    _build_client,
    main,
)


def test_pending_approval_flow_uses_bounded_client_timeout() -> None:
    client = _build_client()
    assert isinstance(client.timeout, httpx.Timeout)
    assert client.timeout.connect == REQUEST_TIMEOUT.connect
    assert client.timeout.read == REQUEST_TIMEOUT.read
    assert client.timeout.write == REQUEST_TIMEOUT.write
    assert client.timeout.pool == REQUEST_TIMEOUT.pool
    client.close()


def test_api_get_uses_bounded_request_timeout() -> None:
    captured: dict[str, object] = {}

    class _Client:
        def get(self, url, *, headers, timeout):
            captured["timeout"] = timeout
            return httpx.Response(200, json={"ok": True})

    payload = _api_get(_Client(), "https://example.com", {"Authorization": "Bearer token"})

    assert payload == {"ok": True}
    assert captured["timeout"] == REQUEST_TIMEOUT


def test_api_post_uses_bounded_request_timeout() -> None:
    captured: dict[str, object] = {}

    class _Client:
        def post(self, url, *, headers, json, timeout):
            captured["timeout"] = timeout
            return httpx.Response(200, json={"ok": True})

    payload = _api_post(
        _Client(),
        "https://example.com",
        {"Authorization": "Bearer token"},
        {"hello": "world"},
    )

    assert payload == {"ok": True}
    assert captured["timeout"] == REQUEST_TIMEOUT


def test_main_rejects_execute_after_approve_without_approve(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(pending_flow, "_must_env", lambda _name: "header.payload.signature")
    monkeypatch.setattr(pending_flow, "sanitize_bearer_token", lambda token: token)

    with pytest.raises(SystemExit, match="--execute-after-approve requires --approve"):
        main(["--execute-after-approve"])
