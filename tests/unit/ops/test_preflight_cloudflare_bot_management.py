from __future__ import annotations

import json
from typing import Any
from urllib.error import HTTPError

import pytest

from scripts import preflight_cloudflare_bot_management


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def __enter__(self) -> "_FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self._payload).encode("utf-8")

    def close(self) -> None:
        return None


def test_enforce_bot_fight_mode_disabled_writes_desired_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def fake_urlopen(request: Any, *, timeout: int) -> _FakeResponse:
        captured["method"] = request.get_method()
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return _FakeResponse({"success": True, "result": {"fight_mode": False}})

    monkeypatch.setattr(preflight_cloudflare_bot_management, "urlopen", fake_urlopen)

    result = preflight_cloudflare_bot_management.enforce_bot_fight_mode_disabled(
        cloudflare_zone_id="zone-id",
        cloudflare_api_token="token",
    )

    assert result == {"cloudflare_zone_id": "zone-id", "fight_mode": "false"}
    assert captured["method"] == "PUT"
    assert captured["url"].endswith("/zones/zone-id/bot_management")
    assert captured["headers"]["Authorization"] == "Bearer token"
    assert (
        captured["headers"]["User-agent"]
        == preflight_cloudflare_bot_management.CLOUDFLARE_API_USER_AGENT
    )
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["body"] == {"fight_mode": False}
    assert captured["timeout"] == 20


def test_enforce_bot_fight_mode_disabled_rejects_missing_token() -> None:
    with pytest.raises(ValueError, match="CLOUDFLARE_API_TOKEN"):
        preflight_cloudflare_bot_management.enforce_bot_fight_mode_disabled(
            cloudflare_zone_id="zone-id",
            cloudflare_api_token="",
        )


def test_enforce_bot_fight_mode_disabled_rejects_failed_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: Any, *, timeout: int) -> None:
        del request, timeout
        raise HTTPError(
            url="https://api.cloudflare.com/client/v4/zones/zone-id/bot_management",
            code=403,
            msg="Forbidden",
            hdrs=None,
            fp=_FakeResponse(
                {
                    "success": False,
                    "errors": [{"code": 10000, "message": "Authentication error"}],
                }
            ),
        )

    monkeypatch.setattr(preflight_cloudflare_bot_management, "urlopen", fake_urlopen)

    with pytest.raises(RuntimeError, match="Bot Management > Edit"):
        preflight_cloudflare_bot_management.enforce_bot_fight_mode_disabled(
            cloudflare_zone_id="zone-id",
            cloudflare_api_token="token",
        )


def test_enforce_bot_fight_mode_disabled_rejects_still_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        preflight_cloudflare_bot_management,
        "urlopen",
        lambda _request, *, timeout: _FakeResponse(
            {"success": True, "result": {"fight_mode": True}}
        ),
    )

    with pytest.raises(ValueError, match="still enabled"):
        preflight_cloudflare_bot_management.enforce_bot_fight_mode_disabled(
            cloudflare_zone_id="zone-id",
            cloudflare_api_token="token",
        )
