from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch


from app.shared.connections.discovery import DiscoveryWizardService


async def test_scan_microsoft_enterprise_apps_paginates_and_handles_errors() -> None:
    service = DiscoveryWizardService(MagicMock())
    payload_one = {
        "value": [{"displayName": "Slack"}, {"displayName": "AWS"}, "bad-entry"],
        "@odata.nextLink": "https://graph.microsoft.com/next-page",
    }
    payload_two = {
        "value": [{"displayName": "Slack"}, {"displayName": "Datadog"}, {"displayName": ""}]
    }

    with patch.object(
        service,
        "_request_json",
        new=AsyncMock(side_effect=[payload_one, payload_two]),
    ):
        names, warnings = await service._scan_microsoft_enterprise_apps("token")

    assert warnings == []
    assert names == ["AWS", "Datadog", "Slack"]

    with patch.object(
        service,
        "_request_json",
        new=AsyncMock(side_effect=ValueError("graph unavailable")),
    ):
        names, warnings = await service._scan_microsoft_enterprise_apps("token")

    assert names == []
    assert warnings and warnings[0].startswith("microsoft_graph_scan_failed:")


async def test_scan_google_workspace_apps_collects_items_and_limits_users() -> None:
    service = DiscoveryWizardService(MagicMock())
    users_payload = {
        "users": [
            {"primaryEmail": "a@example.com"},
            {"primaryEmail": "b@example.com"},
            {"primaryEmail": "c@example.com"},
            "not-a-user",
            {"primaryEmail": ""},
        ]
    }

    async def fake_request(
        _method: str,
        url: str,
        *,
        headers: dict[str, str],
        allow_404: bool = False,
    ) -> dict[str, object]:
        assert headers["Authorization"].startswith("Bearer ")
        if "users?customer=my_customer" in url:
            return users_payload
        if "/a@example.com/tokens" in url:
            assert allow_404 is True
            return {"items": [{"displayText": "Slack"}, {"clientId": "client-a"}]}
        if "/b@example.com/tokens" in url:
            return {"items": "bad-shape"}
        raise AssertionError(f"Unexpected token URL: {url}")

    with patch.object(service, "_request_json", new=AsyncMock(side_effect=fake_request)):
        names, warnings = await service._scan_google_workspace_apps("token", max_users=2)

    assert warnings == []
    assert set(names) == {"Slack", "client-a"}


async def test_scan_google_workspace_apps_user_scan_failure_and_repeated_403_abort() -> None:
    service = DiscoveryWizardService(MagicMock())

    with patch.object(
        service,
        "_request_json",
        new=AsyncMock(side_effect=ValueError("directory error")),
    ):
        names, warnings = await service._scan_google_workspace_apps("token", max_users=5)

    assert names == []
    assert warnings and warnings[0].startswith("google_workspace_user_scan_failed:")

    state = {"token_calls": 0}

    async def fake_request(
        _method: str,
        url: str,
        *,
        headers: dict[str, str],
        allow_404: bool = False,
    ) -> dict[str, object]:
        assert headers["Authorization"].startswith("Bearer ")
        if "users?customer=my_customer" in url:
            return {
                "users": [
                    {"primaryEmail": "u1@example.com"},
                    {"primaryEmail": "u2@example.com"},
                    {"primaryEmail": "u3@example.com"},
                    {"primaryEmail": "u4@example.com"},
                ]
            }
        state["token_calls"] += 1
        assert allow_404 is True
        raise ValueError("status 403 forbidden")

    with patch.object(service, "_request_json", new=AsyncMock(side_effect=fake_request)):
        names, warnings = await service._scan_google_workspace_apps("token", max_users=20)

    assert names == []
    assert state["token_calls"] == 3
    assert any("google_workspace_token_scan_aborted" in warning for warning in warnings)


async def test_scan_google_workspace_apps_non_403_token_error_keeps_scanning() -> None:
    service = DiscoveryWizardService(MagicMock())

    async def fake_request(
        _method: str,
        url: str,
        *,
        headers: dict[str, str],
        allow_404: bool = False,
    ) -> dict[str, object]:
        assert headers["Authorization"].startswith("Bearer ")
        if "users?customer=my_customer" in url:
            return {
                "users": [
                    {"primaryEmail": "u1@example.com"},
                    {"primaryEmail": "u2@example.com"},
                ]
            }
        if "/u1@example.com/tokens" in url:
            assert allow_404 is True
            raise ValueError("status 500 internal")
        if "/u2@example.com/tokens" in url:
            assert allow_404 is True
            return {"items": [{"displayText": "Slack"}]}
        raise AssertionError(f"Unexpected URL: {url}")

    with patch.object(service, "_request_json", new=AsyncMock(side_effect=fake_request)):
        names, warnings = await service._scan_google_workspace_apps("token", max_users=5)

    assert names == ["Slack"]
    assert any("google_workspace_token_scan_failed:u1@example.com:status 500 internal" in w for w in warnings)
    assert not any("google_workspace_token_scan_aborted" in w for w in warnings)


async def test_scan_microsoft_and_google_workspace_additional_edge_branches() -> None:
    service = DiscoveryWizardService(MagicMock())

    with patch.object(
        service,
        "_request_json",
        new=AsyncMock(return_value={"value": "bad-shape"}),
    ):
        names, warnings = await service._scan_microsoft_enterprise_apps("token")
    assert names == []
    assert warnings == []

    async def fake_request(
        _method: str,
        url: str,
        *,
        headers: dict[str, str],
        allow_404: bool = False,
    ) -> dict[str, object]:
        assert headers["Authorization"].startswith("Bearer ")
        if "users?customer=my_customer" in url:
            return {
                "users": [
                    "skip-non-dict",
                    {"primaryEmail": ""},
                    {"primaryEmail": "a@example.com"},
                ]
            }
        assert allow_404 is True
        return {"items": ["skip-non-dict", {"displayText": ""}, {"displayText": "App-X"}]}

    with patch.object(service, "_request_json", new=AsyncMock(side_effect=fake_request)):
        names, warnings = await service._scan_google_workspace_apps("token", max_users=10)
    assert names == ["App-X"]
    assert warnings == []

    with patch.object(
        service,
        "_request_json",
        new=AsyncMock(return_value={"users": "not-a-list"}),
    ):
        names, warnings = await service._scan_google_workspace_apps("token", max_users=10)
    assert names == []
    assert warnings == []

