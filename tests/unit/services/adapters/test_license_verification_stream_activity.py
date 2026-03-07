from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

import app.shared.adapters.feed_utils as feed_utils
import app.shared.adapters.license_vendor_github as vendor_github
import app.shared.adapters.license_vendor_google as vendor_google
import app.shared.adapters.license_vendor_microsoft as vendor_microsoft
import app.shared.adapters.license_vendor_salesforce as vendor_salesforce
import app.shared.adapters.license_vendor_slack as vendor_slack
import app.shared.adapters.license_vendor_zoom as vendor_zoom
from app.shared.adapters.license import LicenseAdapter
from tests.unit.services.adapters.license_verification_stream_test_helpers import (
    build_connection,
    parse_or_raise,
)


def test_list_manual_feed_activity_covers_parse_exception_and_merge_branches() -> None:
    feed = [
        {"user_id": "u1", "last_active_at": "raise-me", "timestamp": "2026-01-10T00:00:00Z"},
        {"user_id": "u1", "email": "U1@example.com", "display_name": "User One"},
        {"timestamp": "2026-01-05T00:00:00Z"},
        {"user_id": "u1", "timestamp": "2026-01-01T00:00:00Z"},
    ]
    adapter = LicenseAdapter(build_connection(vendor="custom", auth_method="manual", license_feed=feed))

    with patch("app.shared.adapters.license.parse_timestamp", side_effect=parse_or_raise):
        rows = adapter._list_manual_feed_activity()

    assert len(rows) == 1
    assert rows[0]["email"] == "u1@example.com"
    assert rows[0]["full_name"] == "User One"
    assert rows[0]["last_active_at"] == datetime(2026, 1, 10, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_activity_list_methods_handle_parse_exceptions_for_vendor_records() -> None:
    m365 = LicenseAdapter(build_connection(vendor="microsoft_365", auth_method="oauth"))
    zoom = LicenseAdapter(build_connection(vendor="zoom", auth_method="oauth"))
    salesforce = LicenseAdapter(
        build_connection(
            vendor="salesforce",
            auth_method="oauth",
            connector_config={"instance_url": "https://acme.my.salesforce.com"},
        )
    )
    google = LicenseAdapter(build_connection(vendor="google_workspace", auth_method="oauth"))

    with patch(
        "app.shared.adapters.feed_utils.parse_timestamp",
        side_effect=ValueError("bad"),
    ):
        with patch.object(
            m365,
            "_get_json",
            new=AsyncMock(
                return_value={
                    "value": [
                        {
                            "id": "u1",
                            "userPrincipalName": "user@example.com",
                            "signInActivity": {"lastSignInDateTime": "bad"},
                        }
                    ]
                }
            ),
        ):
            m365_rows = await vendor_microsoft.list_microsoft_365_activity(
                m365,
                parse_timestamp_fn=feed_utils.parse_timestamp,
            )

        with patch.object(
            zoom,
            "_get_json",
            new=AsyncMock(
                return_value={
                    "users": [{"id": "u2", "last_login_time": "bad", "status": "active"}]
                }
            ),
        ):
            zoom_rows = await vendor_zoom.list_zoom_activity(
                zoom,
                parse_timestamp_fn=feed_utils.parse_timestamp,
            )

        with patch.object(
            salesforce,
            "_get_json",
            new=AsyncMock(
                return_value={
                    "records": [{"Id": "u3", "LastLoginDate": "bad", "Profile": {}}]
                }
            ),
        ):
            salesforce_rows = await vendor_salesforce.list_salesforce_activity(
                salesforce,
                parse_timestamp_fn=feed_utils.parse_timestamp,
            )

        with patch.object(
            google,
            "_get_json",
            new=AsyncMock(
                return_value={
                    "users": [{"primaryEmail": "u4@example.com", "lastLoginTime": "bad"}]
                }
            ),
        ):
            google_rows = await vendor_google.list_google_workspace_activity(
                google,
                parse_timestamp_fn=feed_utils.parse_timestamp,
            )

    assert m365_rows[0]["last_active_at"] is None
    assert zoom_rows[0]["last_active_at"] is None
    assert salesforce_rows[0]["last_active_at"] is None
    assert google_rows[0]["last_active_at"] is None


@pytest.mark.asyncio
async def test_list_github_activity_handles_non_list_payload_shapes() -> None:
    adapter = LicenseAdapter(
        build_connection(vendor="github", auth_method="oauth", connector_config={"github_org": "acme"})
    )
    with patch.object(
        adapter,
        "_get_json",
        new=AsyncMock(
            side_effect=[
                {"members": {"bad": True}},
                {"events": {"bad": True}},
                {"members": []},
                {"members": []},
            ]
        ),
    ):
        rows = await vendor_github.list_github_activity(
            adapter,
            parse_timestamp_fn=feed_utils.parse_timestamp,
        )
    assert rows == []


@pytest.mark.asyncio
async def test_list_github_activity_ignores_malformed_events_and_members() -> None:
    adapter = LicenseAdapter(
        build_connection(vendor="github", auth_method="oauth", connector_config={"github_org": "acme"})
    )
    with (
        patch(
            "app.shared.adapters.feed_utils.parse_timestamp",
            side_effect=parse_or_raise,
        ),
        patch.object(
            adapter,
            "_get_json",
            new=AsyncMock(
                side_effect=[
                    {
                        "members": [
                            "skip",
                            {"login": " "},
                            {"login": "alice", "site_admin": False},
                        ]
                    },
                    {
                        "events": [
                            "skip",
                            {"actor": "not-dict", "created_at": "2026-01-01T00:00:00Z"},
                            {"actor": {"login": "alice"}, "created_at": "raise-me"},
                            {"actor": {"login": "alice"}, "created_at": "2026-01-02T00:00:00Z"},
                        ]
                    },
                    {"members": []},
                    {"members": [{"login": "alice"}]},
                    {"role": "member", "state": "active"},
                ]
            ),
        ),
    ):
        rows = await vendor_github.list_github_activity(
            adapter,
            parse_timestamp_fn=feed_utils.parse_timestamp,
        )

    assert len(rows) == 1
    assert rows[0]["user_id"] == "alice"
    assert rows[0]["org_role"] == "member"
    assert rows[0]["membership_state"] == "active"
    assert rows[0]["mfa_enabled"] is False
    assert rows[0]["last_active_at"] == datetime(2026, 1, 2, tzinfo=timezone.utc)


@pytest.mark.asyncio
async def test_list_slack_activity_ignores_logs_without_timestamp_or_user() -> None:
    adapter = LicenseAdapter(build_connection(vendor="slack", auth_method="oauth"))
    with patch.object(
        adapter,
        "_get_json",
        new=AsyncMock(
            side_effect=[
                {
                    "ok": True,
                    "logins": [
                        {"user_id": "U1"},
                        {"date_last": 1700000000},
                    ],
                },
                {"members": [{"id": "U1", "profile": {}, "name": "Slack User"}]},
            ]
        ),
    ):
        rows = await vendor_slack.list_slack_activity(adapter)

    assert len(rows) == 1
    assert rows[0]["user_id"] == "U1"
    assert rows[0]["last_active_at"] is None


def test_license_manual_activity_non_list_feed_returns_empty() -> None:
    adapter = LicenseAdapter(build_connection(vendor="custom", auth_method="manual", license_feed={}))
    assert adapter._list_manual_feed_activity() == []
