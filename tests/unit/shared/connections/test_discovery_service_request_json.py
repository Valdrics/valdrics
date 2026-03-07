from __future__ import annotations

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.shared.connections.discovery import DiscoveryWizardService
from tests.unit.shared.connections.discovery_service_test_helpers import (
    _FakeHttpClient,
    _json_response,
)


async def test_request_json_allows_404_retries_and_normalizes_list_payloads() -> None:
    service = DiscoveryWizardService(MagicMock())
    client = _FakeHttpClient(
        [
            _json_response(404, {"ignored": True}),
            _json_response(500, {"error": "retry"}),
            _json_response(200, [{"id": "a"}]),
        ]
    )

    with patch("app.shared.connections.discovery.get_http_client", return_value=client):
        assert (
            await service._request_json(
                "GET",
                "https://example.invalid/not-found",
                headers={"Authorization": "Bearer t"},
                allow_404=True,
            )
            == {}
        )
        payload = await service._request_json(
            "GET",
            "https://example.invalid/list",
            headers={"Authorization": "Bearer t"},
        )

    assert payload == {"value": [{"id": "a"}]}
    assert len(client.calls) == 3


async def test_request_json_raises_after_exhausted_errors() -> None:
    service = DiscoveryWizardService(MagicMock())

    invalid_payload_client = _FakeHttpClient(
        [
            _json_response(200, "bad"),
            _json_response(200, "bad"),
            _json_response(200, "bad"),
        ]
    )
    with patch(
        "app.shared.connections.discovery.get_http_client",
        return_value=invalid_payload_client,
    ):
        with pytest.raises(ValueError, match="request_failed:https://example.invalid/payload"):
            await service._request_json(
                "GET",
                "https://example.invalid/payload",
                headers={"Authorization": "Bearer t"},
            )

    transport_error_client = _FakeHttpClient(
        [
            httpx.ConnectError("c1"),
            httpx.ConnectError("c2"),
            httpx.ConnectError("c3"),
        ]
    )
    with patch(
        "app.shared.connections.discovery.get_http_client",
        return_value=transport_error_client,
    ):
        with pytest.raises(ValueError, match="request_failed:https://example.invalid/network"):
            await service._request_json(
                "GET",
                "https://example.invalid/network",
                headers={"Authorization": "Bearer t"},
            )


async def test_request_json_returns_dict_payload_directly() -> None:
    service = DiscoveryWizardService(MagicMock())
    client = _FakeHttpClient([_json_response(200, {"ok": True})])
    with patch("app.shared.connections.discovery.get_http_client", return_value=client):
        payload = await service._request_json(
            "GET",
            "https://example.invalid/dict",
            headers={"Authorization": "Bearer t"},
        )
    assert payload == {"ok": True}


async def test_request_json_retry_loop_fallthrough_raises_last_error() -> None:
    service = DiscoveryWizardService(MagicMock())
    client = _FakeHttpClient([httpx.ConnectError("c1"), httpx.ConnectError("c2")])
    with (
        patch("app.shared.connections.discovery.get_http_client", return_value=client),
        patch("app.shared.connections.discovery.range", return_value=[1, 2]),
    ):
        with pytest.raises(ValueError, match="request_failed:https://example.invalid/fallthrough"):
            await service._request_json(
                "GET",
                "https://example.invalid/fallthrough",
                headers={"Authorization": "Bearer t"},
            )

