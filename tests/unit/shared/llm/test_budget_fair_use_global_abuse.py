from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.shared.core.exceptions import LLMFairUseExceededError
from app.shared.core.pricing import PricingTier
from app.shared.llm import budget_fair_use
from tests.unit.shared.llm.budget_fair_use_test_helpers import DummyManager, MetricStub


@pytest.mark.asyncio
async def test_enforce_global_abuse_guard_triggers_burst_block() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()
    DummyManager._local_global_abuse_block_until = None
    settings = SimpleNamespace(
        LLM_GLOBAL_ABUSE_GUARDS_ENABLED=True,
        LLM_GLOBAL_ABUSE_KILL_SWITCH=False,
        LLM_GLOBAL_ABUSE_PER_MINUTE_CAP=9,
        LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD=3,
        LLM_GLOBAL_ABUSE_BLOCK_SECONDS=60,
    )
    result = MagicMock()
    result.one_or_none.return_value = (9, 3)
    db.execute = AsyncMock(return_value=result)
    cache = SimpleNamespace(enabled=False, client=None)

    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
        patch("app.shared.llm.budget_manager.audit_log"),
    ):
        with pytest.raises(LLMFairUseExceededError) as exc:
            await budget_fair_use.enforce_global_abuse_guard(
                DummyManager,
                tenant_id,
                db,
                PricingTier.PRO,
            )

    assert exc.value.details.get("gate") == "global_abuse"
    assert exc.value.details.get("reason") == "burst_detected"


@pytest.mark.asyncio
async def test_enforce_global_abuse_guard_kill_switch() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()
    settings = SimpleNamespace(
        LLM_GLOBAL_ABUSE_GUARDS_ENABLED=True,
        LLM_GLOBAL_ABUSE_KILL_SWITCH=True,
        LLM_GLOBAL_ABUSE_PER_MINUTE_CAP=9,
        LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD=3,
        LLM_GLOBAL_ABUSE_BLOCK_SECONDS=60,
    )

    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
    ):
        with pytest.raises(LLMFairUseExceededError) as exc:
            await budget_fair_use.enforce_global_abuse_guard(
                DummyManager,
                tenant_id,
                db,
                PricingTier.PRO,
            )

    assert exc.value.details.get("reason") == "kill_switch"


@pytest.mark.asyncio
async def test_enforce_global_abuse_guard_disabled_and_temporal_block() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()

    disabled = SimpleNamespace(LLM_GLOBAL_ABUSE_GUARDS_ENABLED=False)
    with patch("app.shared.llm.budget_manager.get_settings", return_value=disabled):
        await budget_fair_use.enforce_global_abuse_guard(
            DummyManager, tenant_id, db, PricingTier.PRO
        )

    settings = SimpleNamespace(
        LLM_GLOBAL_ABUSE_GUARDS_ENABLED=True,
        LLM_GLOBAL_ABUSE_KILL_SWITCH=False,
        LLM_GLOBAL_ABUSE_PER_MINUTE_CAP=999,
        LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD=999,
        LLM_GLOBAL_ABUSE_BLOCK_SECONDS=90,
    )
    DummyManager._local_global_abuse_block_until = datetime.now(timezone.utc) + timedelta(
        seconds=120
    )
    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
    ):
        with pytest.raises(LLMFairUseExceededError) as exc:
            await budget_fair_use.enforce_global_abuse_guard(
                DummyManager, tenant_id, db, PricingTier.PRO
            )
    assert exc.value.details.get("reason") == "temporal_block"


@pytest.mark.asyncio
async def test_enforce_global_abuse_guard_cache_get_and_result_fallbacks() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()
    settings = SimpleNamespace(
        LLM_GLOBAL_ABUSE_GUARDS_ENABLED=True,
        LLM_GLOBAL_ABUSE_KILL_SWITCH=False,
        LLM_GLOBAL_ABUSE_PER_MINUTE_CAP=100,
        LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD=100,
        LLM_GLOBAL_ABUSE_BLOCK_SECONDS=60,
    )

    cache_blocking = SimpleNamespace(
        enabled=True,
        client=SimpleNamespace(get=AsyncMock(return_value="1")),
    )
    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache_blocking),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
    ):
        with pytest.raises(LLMFairUseExceededError) as exc:
            await budget_fair_use.enforce_global_abuse_guard(
                DummyManager, tenant_id, db, PricingTier.PRO
            )
    assert exc.value.details.get("reason") == "temporal_block"

    result = SimpleNamespace(first=lambda: None)
    db.execute = AsyncMock(return_value=result)
    cache_erroring = SimpleNamespace(
        enabled=True,
        client=SimpleNamespace(get=AsyncMock(side_effect=RuntimeError("redis-get-error"))),
    )
    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache_erroring),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
    ):
        await budget_fair_use.enforce_global_abuse_guard(
            DummyManager, tenant_id, db, PricingTier.PRO
        )


@pytest.mark.asyncio
async def test_enforce_global_abuse_guard_trigger_with_cache_set_failure() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()
    settings = SimpleNamespace(
        LLM_GLOBAL_ABUSE_GUARDS_ENABLED=True,
        LLM_GLOBAL_ABUSE_KILL_SWITCH=False,
        LLM_GLOBAL_ABUSE_PER_MINUTE_CAP=1,
        LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD=1,
        LLM_GLOBAL_ABUSE_BLOCK_SECONDS=30,
    )
    result = MagicMock()
    result.one_or_none.return_value = (5, 2)
    db.execute = AsyncMock(return_value=result)
    cache = SimpleNamespace(
        enabled=True,
        client=SimpleNamespace(
            get=AsyncMock(return_value=None),
            set=AsyncMock(side_effect=RuntimeError("redis-set-error")),
        ),
    )

    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
        patch("app.shared.llm.budget_manager.audit_log"),
    ):
        with pytest.raises(LLMFairUseExceededError) as exc:
            await budget_fair_use.enforce_global_abuse_guard(
                DummyManager, tenant_id, db, PricingTier.PRO
            )
    assert exc.value.details.get("reason") == "burst_detected"


@pytest.mark.asyncio
async def test_global_abuse_guard_row_parsing_and_cache_set_non_callable() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()
    settings = SimpleNamespace(
        LLM_GLOBAL_ABUSE_GUARDS_ENABLED=True,
        LLM_GLOBAL_ABUSE_KILL_SWITCH=False,
        LLM_GLOBAL_ABUSE_PER_MINUTE_CAP=1,
        LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD=1,
        LLM_GLOBAL_ABUSE_BLOCK_SECONDS=45,
    )

    result = SimpleNamespace(first=lambda: ("not-int", object()))
    db.execute = AsyncMock(return_value=result)
    cache = SimpleNamespace(enabled=False, client=None)
    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
    ):
        await budget_fair_use.enforce_global_abuse_guard(
            DummyManager, tenant_id, db, PricingTier.PRO
        )

    result_triggered = MagicMock()
    result_triggered.one_or_none.return_value = (5, 5)
    db.execute = AsyncMock(return_value=result_triggered)
    cache_non_callable_set = SimpleNamespace(
        enabled=True,
        client=SimpleNamespace(get=AsyncMock(return_value=None), set=None),
    )
    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch(
            "app.shared.llm.budget_manager.get_cache_service",
            return_value=cache_non_callable_set,
        ),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
        patch("app.shared.llm.budget_manager.audit_log"),
    ):
        with pytest.raises(LLMFairUseExceededError):
            await budget_fair_use.enforce_global_abuse_guard(
                DummyManager, tenant_id, db, PricingTier.PRO
            )


@pytest.mark.asyncio
async def test_global_abuse_guard_result_without_first_and_one_or_none() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()
    settings = SimpleNamespace(
        LLM_GLOBAL_ABUSE_GUARDS_ENABLED=True,
        LLM_GLOBAL_ABUSE_KILL_SWITCH=False,
        LLM_GLOBAL_ABUSE_PER_MINUTE_CAP=1000,
        LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD=1000,
        LLM_GLOBAL_ABUSE_BLOCK_SECONDS=60,
    )
    db.execute = AsyncMock(return_value=SimpleNamespace())
    cache = SimpleNamespace(enabled=False, client=None)

    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
    ):
        await budget_fair_use.enforce_global_abuse_guard(
            DummyManager, tenant_id, db, PricingTier.PRO
        )
