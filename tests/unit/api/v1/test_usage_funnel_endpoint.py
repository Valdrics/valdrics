from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.reporting.api.v1.usage import (
    GrowthFunnelAttributionPayload,
    GrowthFunnelStageRequest,
    GrowthFunnelUtmPayload,
    record_growth_funnel_stage,
)
from app.shared.core.auth import CurrentUser, UserRole
from app.shared.core.pricing import PricingTier


def _user() -> CurrentUser:
    return CurrentUser(
        id=uuid4(),
        email="growth@example.com",
        tenant_id=uuid4(),
        role=UserRole.MEMBER,
        tier=PricingTier.GROWTH,
    )


@pytest.mark.asyncio
async def test_record_growth_funnel_stage_returns_pql_status() -> None:
    user = _user()
    db = MagicMock()
    qualified_at = datetime.now(timezone.utc)
    snapshot = MagicMock(pql_qualified_at=qualified_at)

    with patch(
        "app.modules.reporting.api.v1.usage.record_tenant_growth_funnel_stage",
        new=AsyncMock(return_value=snapshot),
    ) as record_stage:
        response = await record_growth_funnel_stage(
            payload=GrowthFunnelStageRequest(
                stage="first_value_activated",
                current_tier="growth",
                source="dashboard_first_value",
                attribution=GrowthFunnelAttributionPayload(
                    persona="finance",
                    intent="roi_assessment",
                    page_path="/?start_date=2026-03-01&end_date=2026-03-09",
                    utm=GrowthFunnelUtmPayload(
                        source="google", medium="cpc", campaign="launch"
                    ),
                ),
            ),
            user=user,
            db=db,
        )

    assert response.status == "accepted"
    assert response.tenant_id == user.tenant_id
    assert response.stage == "first_value_activated"
    assert response.pql_qualified is True
    assert response.pql_qualified_at == qualified_at.isoformat()
    record_stage.assert_awaited_once()
    assert record_stage.await_args.kwargs["tenant_id"] == user.tenant_id
    assert record_stage.await_args.kwargs["stage"] == "first_value_activated"
    assert record_stage.await_args.kwargs["commit"] is True


@pytest.mark.asyncio
async def test_record_growth_funnel_stage_uses_user_tier_when_current_tier_missing() -> None:
    user = _user()
    db = MagicMock()
    snapshot = MagicMock(pql_qualified_at=None)

    with patch(
        "app.modules.reporting.api.v1.usage.record_tenant_growth_funnel_stage",
        new=AsyncMock(return_value=snapshot),
    ) as record_stage:
        response = await record_growth_funnel_stage(
            payload=GrowthFunnelStageRequest(
                stage="pricing_viewed",
                source="pricing_page",
            ),
            user=user,
            db=db,
        )

    assert response.pql_qualified is False
    assert record_stage.await_args.kwargs["current_tier"] == user.tier
