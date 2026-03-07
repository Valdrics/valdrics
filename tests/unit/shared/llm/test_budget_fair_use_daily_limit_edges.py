from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.shared.core.exceptions import BudgetExceededError
from app.shared.core.pricing import PricingTier
from app.shared.llm import budget_fair_use
from tests.unit.shared.llm.budget_fair_use_test_helpers import DummyManager, MetricStub


@pytest.mark.asyncio
async def test_enforce_daily_analysis_limit_short_circuit_paths() -> None:
    tenant_id = uuid4()
    db = AsyncMock()

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", return_value=None),
    ):
        await budget_fair_use.enforce_daily_analysis_limit(DummyManager, tenant_id, db)

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", return_value=10),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=1),
        ),
    ):
        await budget_fair_use.enforce_daily_analysis_limit(DummyManager, tenant_id, db)


@pytest.mark.asyncio
async def test_enforce_daily_analysis_limit_user_limit_edges() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()

    def _invalid_user_limit(_tier: PricingTier, limit_name: str) -> object:
        if limit_name == "llm_analyses_per_day":
            return 10
        if limit_name == "llm_analyses_per_user_per_day":
            return "invalid"
        return None

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", side_effect=_invalid_user_limit),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=1),
        ),
    ):
        await budget_fair_use.enforce_daily_analysis_limit(
            DummyManager, tenant_id, db, user_id=user_id
        )

    def _zero_user_limit(_tier: PricingTier, limit_name: str) -> object:
        if limit_name == "llm_analyses_per_day":
            return 10
        if limit_name == "llm_analyses_per_user_per_day":
            return 0
        return None

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", side_effect=_zero_user_limit),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=0),
        ),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.audit_log"),
    ):
        with pytest.raises(BudgetExceededError) as exc:
            await budget_fair_use.enforce_daily_analysis_limit(
                DummyManager, tenant_id, db, user_id=user_id
            )
    assert exc.value.details.get("gate") == "daily_user"
    assert exc.value.details.get("user_requests_today") == 0

    def _valid_user_limit(_tier: PricingTier, limit_name: str) -> object:
        if limit_name == "llm_analyses_per_day":
            return 10
        if limit_name == "llm_analyses_per_user_per_day":
            return 5
        return None

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", side_effect=_valid_user_limit),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(side_effect=[1, 2]),
        ),
    ):
        await budget_fair_use.enforce_daily_analysis_limit(
            DummyManager, tenant_id, db, user_id=user_id
        )


@pytest.mark.asyncio
async def test_count_requests_and_daily_limit_normalization_branches() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    db.execute = AsyncMock(return_value=SimpleNamespace(scalar=lambda: 0))

    await budget_fair_use.count_requests_in_window(
        tenant_id=tenant_id,
        db=db,
        start=datetime.now(timezone.utc) - timedelta(hours=1),
        actor_type="user",
    )

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", return_value=None),
    ):
        await budget_fair_use.enforce_daily_analysis_limit(
            DummyManager,
            tenant_id,
            db,
            actor_type="invalid",
        )

    def _no_system_limit(_tier: PricingTier, key: str) -> object:
        if key == "llm_analyses_per_day":
            return 10
        if key == "llm_system_analyses_per_day":
            return None
        return None

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", side_effect=_no_system_limit),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=0),
        ),
    ):
        await budget_fair_use.enforce_daily_analysis_limit(
            DummyManager,
            tenant_id,
            db,
            actor_type="system",
        )


@pytest.mark.asyncio
async def test_enforce_daily_limit_system_and_user_short_circuit_branches() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()

    def _invalid_system_limit(_tier: PricingTier, key: str) -> object:
        if key == "llm_analyses_per_day":
            return 5
        if key == "llm_system_analyses_per_day":
            return "invalid"
        return None

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", side_effect=_invalid_system_limit),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=0),
        ),
    ):
        await budget_fair_use.enforce_daily_analysis_limit(
            DummyManager,
            tenant_id,
            db,
            actor_type="system",
        )

    def _zero_system_limit(_tier: PricingTier, key: str) -> object:
        if key == "llm_analyses_per_day":
            return 5
        if key == "llm_system_analyses_per_day":
            return 0
        return None

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", side_effect=_zero_system_limit),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=0),
        ),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
    ):
        with pytest.raises(BudgetExceededError) as exc:
            await budget_fair_use.enforce_daily_analysis_limit(
                DummyManager,
                tenant_id,
                db,
                actor_type="system",
            )
    assert exc.value.details["gate"] == "daily_system"

    def _no_user_limit(_tier: PricingTier, key: str) -> object:
        if key == "llm_analyses_per_day":
            return 5
        if key == "llm_analyses_per_user_per_day":
            return None
        return None

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", side_effect=_no_user_limit),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=0),
        ),
    ):
        await budget_fair_use.enforce_daily_analysis_limit(
            DummyManager,
            tenant_id,
            db,
            user_id=uuid4(),
        )

    with (
        patch(
            "app.shared.llm.budget_manager.get_tenant_tier",
            new=AsyncMock(return_value=PricingTier.PRO),
        ),
        patch("app.shared.core.pricing.get_tier_limit", return_value=5),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=0),
        ),
    ):
        await budget_fair_use.enforce_daily_analysis_limit(
            DummyManager,
            tenant_id,
            db,
            user_id=None,
            actor_type="system",
        )
