from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request

from app.modules.governance.api.v1 import admin as admin_api
from app.modules.governance.api.v1.health_dashboard_models import (
    LandingFunnelHealth,
    LandingFunnelWeeklyDelta,
    LandingFunnelWindowSummary,
)


def _all_result(rows: list[object]) -> MagicMock:
    result = MagicMock()
    result.all.return_value = rows
    return result


@pytest.mark.asyncio
async def test_get_landing_campaign_metrics_excludes_stale_zero_activity_campaigns() -> None:
    request = MagicMock(spec=Request)
    now = datetime.now(timezone.utc)
    db = MagicMock()
    db.execute = AsyncMock(
        side_effect=[
            _all_result([]),
            _all_result(
                [
                    SimpleNamespace(
                        utm_source="newsletter",
                        utm_medium="email",
                        utm_campaign="stale-campaign",
                        onboarded_tenants=0,
                        connected_tenants=0,
                        first_value_tenants=0,
                        pql_tenants=0,
                        pricing_view_tenants=0,
                        checkout_started_tenants=0,
                        paid_tenants=0,
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                ]
            ),
        ]
    )

    with (
        patch.object(
            admin_api,
            "_load_rollup_window_summary",
            new=AsyncMock(
                return_value={
                    "total_events": 0,
                    "cta_events": 0,
                    "signup_intent_events": 0,
                }
            ),
        ),
        patch.object(
            admin_api,
            "_load_funnel_window_summary",
            new=AsyncMock(
                return_value={
                    "onboarded_tenants": 0,
                    "connected_tenants": 0,
                    "first_value_tenants": 0,
                    "pql_tenants": 0,
                    "pricing_view_tenants": 0,
                    "checkout_started_tenants": 0,
                    "paid_tenants": 0,
                }
            ),
        ),
        patch.object(
            admin_api,
            "_get_landing_funnel_health",
            new=AsyncMock(
                return_value=LandingFunnelHealth(
                    weekly_current=LandingFunnelWindowSummary(),
                    weekly_previous=LandingFunnelWindowSummary(),
                    weekly_delta=LandingFunnelWeeklyDelta(),
                    alerts=[],
                )
            ),
        ),
    ):
        response = await admin_api.get_landing_campaign_metrics(
            request=request,
            days=30,
            limit=10,
            db=db,
            user=SimpleNamespace(tenant_id=None),
        )

    assert response.items == []


@pytest.mark.asyncio
async def test_get_landing_campaign_metrics_requires_platform_scope() -> None:
    request = MagicMock(spec=Request)
    db = MagicMock()

    with pytest.raises(admin_api.HTTPException) as exc:
        await admin_api.get_landing_campaign_metrics(
            request=request,
            days=30,
            limit=10,
            db=db,
            user=SimpleNamespace(id="user-123", tenant_id="tenant-123", role="admin"),
        )

    assert exc.value.status_code == 403
    assert exc.value.detail == "Platform operator access is required"
