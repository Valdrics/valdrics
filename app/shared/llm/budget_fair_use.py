from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.core.pricing import PricingTier
from app.shared.llm.budget_fair_use_abuse import (
    classify_client_ip as _classify_client_ip_impl,
    enforce_global_abuse_guard_impl,
    record_authenticated_abuse_signal_impl,
)
from app.shared.llm.budget_fair_use_limits import (
    enforce_daily_analysis_limit_impl,
    enforce_fair_use_guards_impl,
)

FAIR_USE_CACHE_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    AttributeError,
    Exception,
)
FAIR_USE_PARSE_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (TypeError, ValueError)


def fair_use_inflight_key(tenant_id: UUID) -> str:
    return f"llm:fair_use:inflight:{tenant_id}"


def fair_use_global_abuse_block_key() -> str:
    return "llm:fair_use:global_abuse_block"


def fair_use_tier_allowed(tier: PricingTier) -> bool:
    return tier in {PricingTier.PRO, PricingTier.ENTERPRISE}


def _as_bool(value: Any, *, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return default


def _as_int(value: Any, *, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except (TypeError, ValueError):
            return default
    return default


def fair_use_daily_soft_cap(tier: PricingTier) -> int | None:
    import app.shared.llm.budget_manager as manager_module

    settings = manager_module.get_settings()
    cap_map = {
        PricingTier.PRO: settings.LLM_FAIR_USE_PRO_DAILY_SOFT_CAP,
        PricingTier.ENTERPRISE: settings.LLM_FAIR_USE_ENTERPRISE_DAILY_SOFT_CAP,
    }
    cap = cap_map.get(tier)
    if cap is None:
        return None
    try:
        cap_int = int(cap)
    except (TypeError, ValueError):
        return None
    return cap_int if cap_int > 0 else None


async def count_requests_in_window(
    tenant_id: UUID,
    db: AsyncSession,
    start: datetime,
    end: datetime | None = None,
    user_id: UUID | None = None,
    actor_type: str | None = None,
) -> int:
    import app.shared.llm.budget_manager as manager_module

    query = select(func.count(manager_module.LLMUsage.id)).where(
        manager_module.LLMUsage.tenant_id == tenant_id,
        manager_module.LLMUsage.created_at >= start,
    )
    normalized_actor_type = str(actor_type or "").strip().lower()
    if normalized_actor_type in {"user", "system"}:
        query = query.where(
            manager_module.LLMUsage.request_type.like(f"{normalized_actor_type}:%")
        )
    if user_id is not None:
        query = query.where(manager_module.LLMUsage.user_id == user_id)
    if end is not None:
        query = query.where(manager_module.LLMUsage.created_at < end)
    result = await db.execute(query)
    return int(result.scalar() or 0)


async def enforce_daily_analysis_limit(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    user_id: UUID | None = None,
    actor_type: str = "system",
) -> None:
    await enforce_daily_analysis_limit_impl(
        manager_cls=manager_cls,
        tenant_id=tenant_id,
        db=db,
        user_id=user_id,
        actor_type=actor_type,
        count_requests_in_window_fn=count_requests_in_window,
    )


def _classify_client_ip(client_ip: str | None) -> tuple[str, int]:
    return _classify_client_ip_impl(client_ip)


async def record_authenticated_abuse_signal(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    tier: PricingTier,
    actor_type: str,
    user_id: UUID | None,
    client_ip: str | None,
) -> None:
    await record_authenticated_abuse_signal_impl(
        manager_cls=manager_cls,
        tenant_id=tenant_id,
        db=db,
        tier=tier,
        actor_type=actor_type,
        user_id=user_id,
        client_ip=client_ip,
        classify_client_ip_fn=_classify_client_ip,
    )


async def enforce_global_abuse_guard(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    tier: PricingTier,
) -> None:
    await enforce_global_abuse_guard_impl(
        manager_cls=manager_cls,
        tenant_id=tenant_id,
        db=db,
        tier=tier,
        fair_use_global_abuse_block_key_fn=fair_use_global_abuse_block_key,
        as_bool_fn=_as_bool,
        as_int_fn=_as_int,
        fair_use_cache_recoverable_errors=FAIR_USE_CACHE_RECOVERABLE_ERRORS,
        fair_use_parse_recoverable_errors=FAIR_USE_PARSE_RECOVERABLE_ERRORS,
    )


async def acquire_fair_use_inflight_slot(
    manager_cls: Any,
    tenant_id: UUID,
    max_inflight: int,
    ttl_seconds: int,
) -> tuple[bool, int]:
    """Acquire one in-flight request slot for a tenant."""
    import app.shared.llm.budget_manager as manager_module

    key = fair_use_inflight_key(tenant_id)

    cache = manager_module.get_cache_service()
    if cache.enabled and cache.client is not None:
        try:
            client = cache.client
            incr = getattr(client, "incr", None)
            decr = getattr(client, "decr", None)
            expire = getattr(client, "expire", None)
            if callable(incr) and callable(decr):
                current = int(await incr(key))
                if callable(expire):
                    await expire(key, ttl_seconds)
                if current > max_inflight:
                    await decr(key)
                    return False, max(current - 1, 0)
                return True, current
        except FAIR_USE_CACHE_RECOVERABLE_ERRORS as exc:
            manager_module.logger.warning(
                "llm_fair_use_redis_acquire_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
            )

    async with manager_cls._local_inflight_lock:
        current = manager_cls._local_inflight_counts.get(key, 0) + 1
        manager_cls._local_inflight_counts[key] = current
        if current > max_inflight:
            next_value = current - 1
            if next_value <= 0:
                manager_cls._local_inflight_counts.pop(key, None)
            else:
                manager_cls._local_inflight_counts[key] = next_value
            return False, max(next_value, 0)
        return True, current


async def release_fair_use_inflight_slot(manager_cls: Any, tenant_id: UUID) -> None:
    """Best-effort release for one in-flight request slot."""
    import app.shared.llm.budget_manager as manager_module

    key = fair_use_inflight_key(tenant_id)
    if not manager_module.get_settings().LLM_FAIR_USE_GUARDS_ENABLED:
        async with manager_cls._local_inflight_lock:
            manager_cls._local_inflight_counts.pop(key, None)
        return

    cache = manager_module.get_cache_service()
    if cache.enabled and cache.client is not None:
        try:
            decr = getattr(cache.client, "decr", None)
            if callable(decr):
                current = int(await decr(key))
                if current < 0:
                    set_fn = getattr(cache.client, "set", None)
                    if callable(set_fn):
                        await set_fn(key, "0", ex=60)
                return
        except FAIR_USE_CACHE_RECOVERABLE_ERRORS as exc:
            manager_module.logger.warning(
                "llm_fair_use_redis_release_failed",
                tenant_id=str(tenant_id),
                error=str(exc),
            )

    async with manager_cls._local_inflight_lock:
        current = manager_cls._local_inflight_counts.get(key, 0)
        if current <= 1:
            manager_cls._local_inflight_counts.pop(key, None)
        else:
            manager_cls._local_inflight_counts[key] = current - 1


async def enforce_fair_use_guards(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    tier: PricingTier,
) -> bool:
    return await enforce_fair_use_guards_impl(
        manager_cls=manager_cls,
        tenant_id=tenant_id,
        db=db,
        tier=tier,
        count_requests_in_window_fn=count_requests_in_window,
        acquire_fair_use_inflight_slot_fn=acquire_fair_use_inflight_slot,
        fair_use_daily_soft_cap_fn=fair_use_daily_soft_cap,
        fair_use_tier_allowed_fn=fair_use_tier_allowed,
    )
