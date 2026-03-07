from __future__ import annotations

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.shared.core.exceptions import BudgetExceededError
from app.shared.core.pricing import PricingTier
from app.shared.llm import budget_fair_use
from tests.unit.shared.llm.budget_fair_use_test_helpers import DummyManager, MetricStub


@pytest.mark.asyncio
async def test_enforce_daily_analysis_limit_invalid_or_exhausted_limits() -> None:
    tenant_id = uuid4()
    db = AsyncMock()

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", return_value="invalid"),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(),
        ) as count_window,
    ):
        await budget_fair_use.enforce_daily_analysis_limit(DummyManager, tenant_id, db)
        count_window.assert_not_awaited()

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", return_value=0),
    ):
        with pytest.raises(BudgetExceededError):
            await budget_fair_use.enforce_daily_analysis_limit(DummyManager, tenant_id, db)


@pytest.mark.asyncio
async def test_enforce_daily_analysis_limit_requires_user_context_for_user_actor() -> None:
    tenant_id = uuid4()
    db = AsyncMock()

    with pytest.raises(BudgetExceededError) as exc:
        await budget_fair_use.enforce_daily_analysis_limit(
            DummyManager,
            tenant_id,
            db,
            user_id=None,
            actor_type="user",
        )
    assert exc.value.details.get("gate") == "actor_context"


@pytest.mark.asyncio
async def test_enforce_daily_analysis_limit_enforces_system_cap() -> None:
    tenant_id = uuid4()
    db = AsyncMock()

    def _tier_limit_side_effect(_tier: PricingTier, key: str):
        mapping = {
            "llm_analyses_per_day": 100,
            "llm_system_analyses_per_day": 1,
        }
        return mapping.get(key)

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.STARTER),
        ),
        patch(
            "app.shared.core.pricing.get_tier_limit",
            side_effect=_tier_limit_side_effect,
        ),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(side_effect=[0, 1]),
        ),
    ):
        with pytest.raises(BudgetExceededError) as exc:
            await budget_fair_use.enforce_daily_analysis_limit(
                DummyManager,
                tenant_id,
                db,
                actor_type="system",
            )
    assert exc.value.details.get("gate") == "daily_system"

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", return_value=2),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=2),
        ),
    ):
        with pytest.raises(BudgetExceededError):
            await budget_fair_use.enforce_daily_analysis_limit(DummyManager, tenant_id, db)


@pytest.mark.asyncio
async def test_enforce_daily_analysis_limit_applies_per_user_quota() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()

    def _tier_limit(_tier: PricingTier, limit_name: str) -> int:
        if limit_name == "llm_analyses_per_day":
            return 10
        if limit_name == "llm_analyses_per_user_per_day":
            return 1
        return 0

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", side_effect=_tier_limit),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(side_effect=[0, 1]),
        ),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.audit_log"),
    ):
        with pytest.raises(BudgetExceededError) as exc:
            await budget_fair_use.enforce_daily_analysis_limit(
                DummyManager,
                tenant_id,
                db,
                user_id=user_id,
            )

    assert exc.value.details.get("gate") == "daily_user"
    assert exc.value.details.get("daily_user_limit") == 1
    assert exc.value.details.get("user_requests_today") == 1
