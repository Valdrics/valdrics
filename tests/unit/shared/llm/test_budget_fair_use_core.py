from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.shared.core.pricing import PricingTier
from app.shared.llm import budget_fair_use
from tests.unit.shared.llm.budget_fair_use_test_helpers import DummyManager


def test_fair_use_daily_soft_cap_parsing() -> None:
    settings = SimpleNamespace(
        LLM_FAIR_USE_PRO_DAILY_SOFT_CAP="1500",
        LLM_FAIR_USE_ENTERPRISE_DAILY_SOFT_CAP=0,
    )
    with patch("app.shared.llm.budget_manager.get_settings", return_value=settings):
        assert budget_fair_use.fair_use_daily_soft_cap(PricingTier.PRO) == 1500
        assert budget_fair_use.fair_use_daily_soft_cap(PricingTier.ENTERPRISE) is None
        assert budget_fair_use.fair_use_daily_soft_cap(PricingTier.FREE) is None


def test_fair_use_daily_soft_cap_invalid_values() -> None:
    settings = SimpleNamespace(
        LLM_FAIR_USE_PRO_DAILY_SOFT_CAP="not-a-number",
        LLM_FAIR_USE_ENTERPRISE_DAILY_SOFT_CAP="-10",
    )
    with patch("app.shared.llm.budget_manager.get_settings", return_value=settings):
        assert budget_fair_use.fair_use_daily_soft_cap(PricingTier.PRO) is None
        assert budget_fair_use.fair_use_daily_soft_cap(PricingTier.ENTERPRISE) is None


def test_as_bool_and_as_int_edge_cases() -> None:
    assert budget_fair_use._as_bool(True, default=False) is True
    assert budget_fair_use._as_bool(0, default=True) is False
    assert budget_fair_use._as_bool("yes", default=False) is True
    assert budget_fair_use._as_bool("off", default=True) is False
    assert budget_fair_use._as_bool("not-a-bool", default=True) is True
    assert budget_fair_use._as_bool(object(), default=False) is False

    assert budget_fair_use._as_int(True, default=7) == 7
    assert budget_fair_use._as_int(5, default=0) == 5
    assert budget_fair_use._as_int(5.9, default=0) == 5
    assert budget_fair_use._as_int(" 19 ", default=0) == 19
    assert budget_fair_use._as_int("bad", default=3) == 3
    assert budget_fair_use._as_int(object(), default=2) == 2


@pytest.mark.asyncio
async def test_count_requests_in_window_with_and_without_end() -> None:
    tenant_id = uuid4()
    db = MagicMock()
    result = MagicMock()
    result.scalar.return_value = 7
    db.execute = AsyncMock(return_value=result)

    start = datetime.now(timezone.utc) - timedelta(days=1)
    end = datetime.now(timezone.utc)

    with_end = await budget_fair_use.count_requests_in_window(
        tenant_id=tenant_id, db=db, start=start, end=end
    )
    no_end = await budget_fair_use.count_requests_in_window(
        tenant_id=tenant_id, db=db, start=start
    )

    assert with_end == 7
    assert no_end == 7
    assert db.execute.await_count == 2


@pytest.mark.asyncio
async def test_count_requests_in_window_user_filter_and_none_scalar() -> None:
    tenant_id = uuid4()
    db = MagicMock()
    result = MagicMock()
    result.scalar.return_value = None
    db.execute = AsyncMock(return_value=result)

    value = await budget_fair_use.count_requests_in_window(
        tenant_id=tenant_id,
        db=db,
        start=datetime.now(timezone.utc) - timedelta(minutes=5),
        end=datetime.now(timezone.utc),
        user_id=uuid4(),
    )

    assert value == 0
    db.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_acquire_inflight_slot_redis_success_and_over_limit() -> None:
    tenant_id = uuid4()
    redis_client = SimpleNamespace(
        incr=AsyncMock(side_effect=[1, 4]),
        decr=AsyncMock(),
        expire=AsyncMock(),
    )
    cache = SimpleNamespace(enabled=True, client=redis_client)

    with patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache):
        ok, current = await budget_fair_use.acquire_fair_use_inflight_slot(
            DummyManager, tenant_id, max_inflight=2, ttl_seconds=60
        )
        denied, denied_current = await budget_fair_use.acquire_fair_use_inflight_slot(
            DummyManager, tenant_id, max_inflight=2, ttl_seconds=60
        )

    assert ok is True
    assert current == 1
    assert denied is False
    assert denied_current == 3
    redis_client.expire.assert_awaited()
    redis_client.decr.assert_awaited_once()


@pytest.mark.asyncio
async def test_acquire_inflight_slot_redis_failure_falls_back_to_local() -> None:
    tenant_id = uuid4()
    redis_client = SimpleNamespace(
        incr=AsyncMock(side_effect=RuntimeError("redis unavailable")),
        decr=AsyncMock(),
        expire=AsyncMock(),
    )
    cache = SimpleNamespace(enabled=True, client=redis_client)

    with patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache):
        ok, current = await budget_fair_use.acquire_fair_use_inflight_slot(
            DummyManager, tenant_id, max_inflight=2, ttl_seconds=60
        )

    assert ok is True
    assert current == 1
    assert (
        DummyManager._local_inflight_counts[
            budget_fair_use.fair_use_inflight_key(tenant_id)
        ]
        == 1
    )


@pytest.mark.asyncio
async def test_release_slot_respects_guards_disabled_and_clears_local() -> None:
    tenant_id = uuid4()
    key = budget_fair_use.fair_use_inflight_key(tenant_id)
    DummyManager._local_inflight_counts[key] = 3

    settings = SimpleNamespace(LLM_FAIR_USE_GUARDS_ENABLED=False)
    with patch("app.shared.llm.budget_manager.get_settings", return_value=settings):
        await budget_fair_use.release_fair_use_inflight_slot(DummyManager, tenant_id)

    assert key not in DummyManager._local_inflight_counts


@pytest.mark.asyncio
async def test_release_slot_redis_negative_counter_is_clamped() -> None:
    tenant_id = uuid4()
    settings = SimpleNamespace(LLM_FAIR_USE_GUARDS_ENABLED=True)
    redis_client = SimpleNamespace(
        decr=AsyncMock(return_value=-1),
        set=AsyncMock(),
    )
    cache = SimpleNamespace(enabled=True, client=redis_client)

    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache),
    ):
        await budget_fair_use.release_fair_use_inflight_slot(DummyManager, tenant_id)

    redis_client.set.assert_awaited_once()


@pytest.mark.asyncio
async def test_release_slot_redis_failure_falls_back_to_local_decrement() -> None:
    tenant_id = uuid4()
    key = budget_fair_use.fair_use_inflight_key(tenant_id)
    DummyManager._local_inflight_counts[key] = 2

    settings = SimpleNamespace(LLM_FAIR_USE_GUARDS_ENABLED=True)
    redis_client = SimpleNamespace(decr=AsyncMock(side_effect=RuntimeError("boom")))
    cache = SimpleNamespace(enabled=True, client=redis_client)

    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache),
    ):
        await budget_fair_use.release_fair_use_inflight_slot(DummyManager, tenant_id)

    assert DummyManager._local_inflight_counts[key] == 1


@pytest.mark.asyncio
async def test_acquire_slot_additional_cache_and_local_branches() -> None:
    tenant_id = uuid4()

    cache_no_expire = SimpleNamespace(
        enabled=True,
        client=SimpleNamespace(
            incr=AsyncMock(return_value=1),
            decr=AsyncMock(),
            expire=None,
        ),
    )
    with patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache_no_expire):
        ok, current = await budget_fair_use.acquire_fair_use_inflight_slot(
            DummyManager, tenant_id, max_inflight=2, ttl_seconds=60
        )
    assert ok is True
    assert current == 1

    cache_missing_decr = SimpleNamespace(
        enabled=True,
        client=SimpleNamespace(incr=AsyncMock(return_value=1)),
    )
    with patch(
        "app.shared.llm.budget_manager.get_cache_service",
        return_value=cache_missing_decr,
    ):
        ok_local, current_local = await budget_fair_use.acquire_fair_use_inflight_slot(
            DummyManager, tenant_id, max_inflight=1, ttl_seconds=60
        )
    assert ok_local is True
    assert current_local >= 1

    local_tenant_id = uuid4()
    cache_disabled = SimpleNamespace(enabled=False, client=None)
    with patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache_disabled):
        allowed, _ = await budget_fair_use.acquire_fair_use_inflight_slot(
            DummyManager, local_tenant_id, max_inflight=1, ttl_seconds=60
        )
        denied, denied_current = await budget_fair_use.acquire_fair_use_inflight_slot(
            DummyManager, local_tenant_id, max_inflight=1, ttl_seconds=60
        )
    assert allowed is True
    assert denied is False
    assert denied_current >= 0


@pytest.mark.asyncio
async def test_release_slot_additional_local_fallback_paths() -> None:
    tenant_id = uuid4()
    key = budget_fair_use.fair_use_inflight_key(tenant_id)
    DummyManager._local_inflight_counts[key] = 1

    settings = SimpleNamespace(LLM_FAIR_USE_GUARDS_ENABLED=True)
    cache_without_decr = SimpleNamespace(enabled=True, client=SimpleNamespace(decr=None))
    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch(
            "app.shared.llm.budget_manager.get_cache_service",
            return_value=cache_without_decr,
        ),
    ):
        await budget_fair_use.release_fair_use_inflight_slot(DummyManager, tenant_id)
    assert key not in DummyManager._local_inflight_counts

    DummyManager._local_inflight_counts[key] = 2
    cache_negative_no_set = SimpleNamespace(
        enabled=True,
        client=SimpleNamespace(decr=AsyncMock(return_value=-2), set=None),
    )
    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch(
            "app.shared.llm.budget_manager.get_cache_service",
            return_value=cache_negative_no_set,
        ),
    ):
        await budget_fair_use.release_fair_use_inflight_slot(DummyManager, tenant_id)


@pytest.mark.asyncio
async def test_inflight_slot_local_zero_pop_and_release_non_negative_decr() -> None:
    tenant_id = uuid4()
    cache_disabled = SimpleNamespace(enabled=False, client=None)
    with patch("app.shared.llm.budget_manager.get_cache_service", return_value=cache_disabled):
        ok, current = await budget_fair_use.acquire_fair_use_inflight_slot(
            DummyManager, tenant_id, max_inflight=0, ttl_seconds=30
        )
    assert ok is False
    assert current == 0

    settings = SimpleNamespace(LLM_FAIR_USE_GUARDS_ENABLED=True)
    cache_non_negative = SimpleNamespace(
        enabled=True,
        client=SimpleNamespace(decr=AsyncMock(return_value=0)),
    )
    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch(
            "app.shared.llm.budget_manager.get_cache_service",
            return_value=cache_non_negative,
        ),
    ):
        await budget_fair_use.release_fair_use_inflight_slot(DummyManager, tenant_id)
