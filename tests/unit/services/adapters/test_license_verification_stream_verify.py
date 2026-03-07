from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import app.shared.adapters.license_native_dispatch as native_dispatch
import app.shared.adapters.license_vendor_verify as vendor_verify
from app.shared.adapters.license import LicenseAdapter
from app.shared.core.exceptions import ExternalAPIError
from tests.unit.services.adapters.license_verification_stream_test_helpers import (
    Secret,
    build_connection,
)


@pytest.mark.asyncio
async def test_verify_connection_accepts_valid_manual_feed_and_coerce_bool_unknown_string() -> None:
    adapter = LicenseAdapter(
        build_connection(
            vendor="custom",
            auth_method="manual",
            license_feed=[{"timestamp": "2026-01-01T00:00:00Z", "cost_usd": 1.0}],
        )
    )
    assert await adapter.verify_connection() is True
    assert LicenseAdapter._coerce_bool("unknown-flag") is False


@pytest.mark.asyncio
async def test_verify_connection_native_success_and_manual_last_error_preserved() -> None:
    native = LicenseAdapter(build_connection(vendor="google_workspace", auth_method="oauth"))
    with patch(
        "app.shared.adapters.license.verify_native_vendor",
        new=AsyncMock(return_value=None),
    ):
        assert await native.verify_connection() is True

    manual = LicenseAdapter(build_connection(vendor="custom", auth_method="manual"))

    def _validate_and_set_error(_feed: object) -> bool:
        manual.last_error = "custom-invalid"
        return False

    with patch.object(manual, "_validate_manual_feed", side_effect=_validate_and_set_error):
        assert await manual.verify_connection() is False
    assert manual.last_error == "custom-invalid"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("vendor",),
    [
        ("google_workspace",),
        ("microsoft_365",),
        ("github",),
        ("slack",),
        ("zoom",),
        ("salesforce",),
    ],
)
async def test_list_users_activity_dispatches_all_native_vendors(vendor: str) -> None:
    adapter = LicenseAdapter(build_connection(vendor=vendor, auth_method="oauth"))
    mocked = AsyncMock(return_value=[{"vendor": vendor}])
    with patch.dict(
        native_dispatch._ACTIVITY_FN_BY_VENDOR,
        {vendor: mocked},
        clear=False,
    ):
        rows = await adapter.list_users_activity()
    assert rows == [{"vendor": vendor}]
    mocked.assert_awaited_once_with(adapter)


@pytest.mark.asyncio
async def test_verify_native_vendor_dispatches_remaining_handlers_and_unsupported() -> None:
    adapter = LicenseAdapter(build_connection(vendor="slack", auth_method="oauth"))
    verify_slack = AsyncMock(return_value=None)
    verify_zoom = AsyncMock(return_value=None)
    verify_salesforce = AsyncMock(return_value=None)
    with patch.dict(
        native_dispatch._VERIFY_FN_BY_VENDOR,
        {
            "slack": verify_slack,
            "zoom": verify_zoom,
            "salesforce": verify_salesforce,
        },
        clear=False,
    ):
        await native_dispatch.verify_native_vendor(adapter, "slack")
        await native_dispatch.verify_native_vendor(adapter, "zoom")
        await native_dispatch.verify_native_vendor(adapter, "salesforce")

    verify_slack.assert_awaited_once_with(adapter)
    verify_zoom.assert_awaited_once_with(adapter)
    verify_salesforce.assert_awaited_once_with(adapter)

    with pytest.raises(ExternalAPIError, match="Unsupported native license vendor"):
        await native_dispatch.verify_native_vendor(adapter, "unknown")


@pytest.mark.asyncio
async def test_verify_native_vendor_dispatches_microsoft_google_and_github() -> None:
    adapter = LicenseAdapter(build_connection(vendor="google_workspace", auth_method="oauth"))
    verify_m365 = AsyncMock(return_value=None)
    verify_google = AsyncMock(return_value=None)
    verify_github = AsyncMock(return_value=None)
    with patch.dict(
        native_dispatch._VERIFY_FN_BY_VENDOR,
        {
            "microsoft_365": verify_m365,
            "google_workspace": verify_google,
            "github": verify_github,
        },
        clear=False,
    ):
        await native_dispatch.verify_native_vendor(adapter, "microsoft_365")
        await native_dispatch.verify_native_vendor(adapter, "google_workspace")
        await native_dispatch.verify_native_vendor(adapter, "github")

    verify_m365.assert_awaited_once_with(adapter)
    verify_google.assert_awaited_once_with(adapter)
    verify_github.assert_awaited_once_with(adapter)


@pytest.mark.asyncio
async def test_verify_slack_zoom_and_salesforce_paths() -> None:
    slack = LicenseAdapter(build_connection(vendor="slack", auth_method="oauth"))
    with patch.object(slack, "_get_json", new=AsyncMock(return_value={"ok": True})):
        await vendor_verify.verify_slack(slack)

    with patch.object(slack, "_get_json", new=AsyncMock(return_value={"ok": False, "error": "denied"})):
        with pytest.raises(ExternalAPIError, match="Slack auth.test failed"):
            await vendor_verify.verify_slack(slack)

    zoom = LicenseAdapter(build_connection(vendor="zoom", auth_method="oauth"))
    with patch.object(zoom, "_get_json", new=AsyncMock(return_value={"id": "u1"})) as zoom_get:
        await vendor_verify.verify_zoom(zoom)
    zoom_get.assert_awaited_once()
    assert zoom_get.await_args.kwargs["headers"]["Authorization"].startswith("Bearer ")

    salesforce = LicenseAdapter(
        build_connection(
            vendor="salesforce",
            auth_method="oauth",
            connector_config={"instance_url": "https://acme.my.salesforce.com/"},
        )
    )
    with patch.object(salesforce, "_get_json", new=AsyncMock(return_value={"limits": []})) as sf_get:
        await vendor_verify.verify_salesforce(salesforce)
    sf_url = sf_get.await_args.args[0]
    assert sf_url == "https://acme.my.salesforce.com/services/data/v60.0/limits"

    bad = LicenseAdapter(
        build_connection(
            vendor="salesforce",
            auth_method="oauth",
            connector_config={"instance_url": "ftp://example.local"},
        )
    )
    with pytest.raises(ExternalAPIError, match="http\\(s\\) URL"):
        bad._salesforce_instance_url()


@pytest.mark.asyncio
async def test_license_helper_and_verify_connection_branch_edges() -> None:
    with pytest.raises(ExternalAPIError, match="Missing API token"):
        LicenseAdapter(build_connection(auth_method="oauth", api_key=None))._resolve_api_key()
    with pytest.raises(ExternalAPIError, match="Missing API token"):
        LicenseAdapter(build_connection(auth_method="oauth", api_key=Secret(" ")))._resolve_api_key()

    assert LicenseAdapter(build_connection(vendor="custom", auth_method="manual"))._native_vendor is None
    assert LicenseAdapter._normalize_email("not-an-email") is None
    assert LicenseAdapter._coerce_bool(1) is True
    assert LicenseAdapter._coerce_bool("yes") is True
    assert LicenseAdapter._coerce_bool("off") is False

    unsupported = LicenseAdapter(build_connection(vendor="custom", auth_method="oauth"))
    assert await unsupported.verify_connection() is False
    assert "not supported for vendor" in (unsupported.last_error or "")

    native_error = LicenseAdapter(build_connection(vendor="google_workspace", auth_method="oauth"))
    with patch(
        "app.shared.adapters.license.verify_native_vendor",
        new=AsyncMock(side_effect=ExternalAPIError("native verify failed")),
    ):
        assert await native_error.verify_connection() is False
    assert "native verify failed" in (native_error.last_error or "")

    manual_default_error = LicenseAdapter(build_connection(vendor="custom", auth_method="manual"))
    with patch.object(
        manual_default_error, "_validate_manual_feed", return_value=False
    ) as validate_mock:
        assert await manual_default_error.verify_connection() is False
    validate_mock.assert_called_once()
    assert "missing or invalid" in (manual_default_error.last_error or "").lower()
