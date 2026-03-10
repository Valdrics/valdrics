from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.core.pricing import PricingTier
from app.shared.core.async_utils import maybe_await


async def enforce_daily_analysis_limit_impl(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    *,
    user_id: UUID | None,
    actor_type: str,
    count_requests_in_window_fn: Any,
) -> None:
    """Enforce tier-based per-day LLM analysis quota before budget reservation."""
    from app.shared.core.pricing import get_tier_limit
    import app.shared.llm.budget_manager as manager_module

    del manager_cls
    normalized_actor_type = str(actor_type or "").strip().lower()
    if normalized_actor_type not in {"user", "system"}:
        normalized_actor_type = "user" if user_id is not None else "system"
    if user_id is not None and normalized_actor_type == "system":
        normalized_actor_type = "user"
    if normalized_actor_type == "user" and user_id is None:
        manager_module.LLM_PRE_AUTH_DENIALS.labels(
            reason="missing_user_actor_context",
            tenant_tier="unknown",
        ).inc()
        raise manager_module.BudgetExceededError(
            "User-scoped LLM request missing actor identity.",
            details={
                "gate": "actor_context",
                "actor_type": normalized_actor_type,
            },
        )

    tier = await manager_module.get_tenant_tier(tenant_id, db)
    raw_limit = get_tier_limit(tier, "llm_analyses_per_day")
    if raw_limit is None:
        return

    try:
        daily_limit = int(raw_limit)
    except (TypeError, ValueError):
        manager_module.logger.warning(
            "invalid_llm_daily_limit",
            tenant_id=str(tenant_id),
            tier=tier.value,
            raw_limit=raw_limit,
        )
        return

    if daily_limit <= 0:
        raise manager_module.BudgetExceededError(
            "LLM analysis is not available on your current plan.",
            details={"daily_limit": daily_limit, "requests_today": 0},
        )

    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    requests_today = await count_requests_in_window_fn(
        tenant_id=tenant_id,
        db=db,
        start=day_start,
        end=day_end,
    )
    if requests_today >= daily_limit:
        manager_module.LLM_PRE_AUTH_DENIALS.labels(
            reason="daily_tenant_limit_exceeded",
            tenant_tier=tier.value,
        ).inc()
        await maybe_await(
            manager_module.audit_log(
                event="llm_quota_denied",
                user_id=str(user_id or "system"),
                tenant_id=str(tenant_id),
                details={
                    "gate": "daily_tenant",
                    "tier": tier.value,
                    "limit": daily_limit,
                    "observed": requests_today,
                    "actor_type": normalized_actor_type,
                },
                db=db,
                isolated=True,
            )
        )
        raise manager_module.BudgetExceededError(
            "Daily LLM analysis limit reached for your current plan.",
            details={
                "gate": "daily_tenant",
                "daily_limit": daily_limit,
                "requests_today": requests_today,
                "actor_type": normalized_actor_type,
            },
        )

    if normalized_actor_type == "system":
        raw_system_limit = get_tier_limit(tier, "llm_system_analyses_per_day")
        if raw_system_limit is None:
            return
        try:
            system_daily_limit = int(raw_system_limit)
        except (TypeError, ValueError):
            manager_module.logger.warning(
                "invalid_llm_daily_system_limit",
                tenant_id=str(tenant_id),
                tier=tier.value,
                raw_limit=raw_system_limit,
            )
            return
        if system_daily_limit <= 0:
            manager_module.LLM_PRE_AUTH_DENIALS.labels(
                reason="daily_system_limit_exceeded",
                tenant_tier=tier.value,
            ).inc()
            raise manager_module.BudgetExceededError(
                "System LLM analysis is not available on your current plan.",
                details={
                    "gate": "daily_system",
                    "daily_system_limit": system_daily_limit,
                    "system_requests_today": 0,
                },
            )

        system_requests_today = await count_requests_in_window_fn(
            tenant_id=tenant_id,
            db=db,
            start=day_start,
            end=day_end,
            actor_type="system",
        )
        if system_requests_today >= system_daily_limit:
            manager_module.LLM_PRE_AUTH_DENIALS.labels(
                reason="daily_system_limit_exceeded",
                tenant_tier=tier.value,
            ).inc()
            await maybe_await(
                manager_module.audit_log(
                    event="llm_quota_denied",
                    user_id="system",
                    tenant_id=str(tenant_id),
                    details={
                        "gate": "daily_system",
                        "tier": tier.value,
                        "limit": system_daily_limit,
                        "observed": system_requests_today,
                    },
                    db=db,
                    isolated=True,
                )
            )
            raise manager_module.BudgetExceededError(
                "Daily system LLM analysis limit reached for your current plan.",
                details={
                    "gate": "daily_system",
                    "daily_system_limit": system_daily_limit,
                    "system_requests_today": system_requests_today,
                },
            )
        return

    raw_user_limit = get_tier_limit(tier, "llm_analyses_per_user_per_day")
    if raw_user_limit is None:
        return

    try:
        user_daily_limit = int(raw_user_limit)
    except (TypeError, ValueError):
        manager_module.logger.warning(
            "invalid_llm_daily_user_limit",
            tenant_id=str(tenant_id),
            user_id=str(user_id),
            tier=tier.value,
            raw_limit=raw_user_limit,
        )
        return

    if user_daily_limit <= 0:
        manager_module.LLM_PRE_AUTH_DENIALS.labels(
            reason="daily_user_limit_exceeded",
            tenant_tier=tier.value,
        ).inc()
        await maybe_await(
            manager_module.audit_log(
                event="llm_quota_denied",
                user_id=str(user_id),
                tenant_id=str(tenant_id),
                details={
                    "gate": "daily_user",
                    "tier": tier.value,
                    "limit": user_daily_limit,
                    "observed": 0,
                },
                db=db,
                isolated=True,
            )
        )
        raise manager_module.BudgetExceededError(
            "Daily per-user LLM analysis limit reached for your current plan.",
            details={
                "gate": "daily_user",
                "daily_user_limit": user_daily_limit,
                "user_requests_today": 0,
                "actor_type": normalized_actor_type,
            },
        )

    user_requests_today = await count_requests_in_window_fn(
        tenant_id=tenant_id,
        db=db,
        start=day_start,
        end=day_end,
        user_id=user_id,
        actor_type="user",
    )
    if user_requests_today >= user_daily_limit:
        manager_module.LLM_PRE_AUTH_DENIALS.labels(
            reason="daily_user_limit_exceeded",
            tenant_tier=tier.value,
        ).inc()
        await maybe_await(
            manager_module.audit_log(
                event="llm_quota_denied",
                user_id=str(user_id),
                tenant_id=str(tenant_id),
                details={
                    "gate": "daily_user",
                    "tier": tier.value,
                    "limit": user_daily_limit,
                    "observed": user_requests_today,
                },
                db=db,
                isolated=True,
            )
        )
        raise manager_module.BudgetExceededError(
            "Daily per-user LLM analysis limit reached for your current plan.",
            details={
                "gate": "daily_user",
                "daily_user_limit": user_daily_limit,
                "user_requests_today": user_requests_today,
                "actor_type": normalized_actor_type,
            },
        )


async def enforce_fair_use_guards_impl(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    tier: PricingTier,
    *,
    count_requests_in_window_fn: Any,
    acquire_fair_use_inflight_slot_fn: Any,
    fair_use_daily_soft_cap_fn: Any,
    fair_use_tier_allowed_fn: Any,
) -> bool:
    """Enforce tier-gated fair-use limits and return whether a slot was acquired."""
    import app.shared.llm.budget_manager as manager_module

    settings = manager_module.get_settings()
    tier_label = tier.value
    if not settings.LLM_FAIR_USE_GUARDS_ENABLED:
        return False
    if not fair_use_tier_allowed_fn(tier):
        return False

    now = datetime.now(timezone.utc)

    daily_soft_cap = fair_use_daily_soft_cap_fn(tier)
    if daily_soft_cap is not None:
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        requests_today = await count_requests_in_window_fn(
            tenant_id=tenant_id, db=db, start=day_start, end=day_end
        )
        manager_module.LLM_FAIR_USE_OBSERVED.labels(
            gate="soft_daily", tenant_tier=tier_label
        ).set(requests_today)
        if requests_today >= daily_soft_cap:
            manager_module.LLM_PRE_AUTH_DENIALS.labels(
                reason="fair_use_soft_daily", tenant_tier=tier_label
            ).inc()
            manager_module.LLM_FAIR_USE_DENIALS.labels(
                gate="soft_daily", tenant_tier=tier_label
            ).inc()
            manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
                gate="soft_daily", outcome="deny", tenant_tier=tier_label
            ).inc()
            await maybe_await(
                manager_module.audit_log(
                    event="llm_fair_use_denied",
                    user_id="system",
                    tenant_id=str(tenant_id),
                    details={
                        "gate": "soft_daily",
                        "tier": tier_label,
                        "limit": daily_soft_cap,
                        "observed": requests_today,
                    },
                    db=db,
                    isolated=True,
                )
            )
            raise manager_module.LLMFairUseExceededError(
                "Daily fair-use limit reached. Retry tomorrow or contact support to increase limits.",
                details={
                    "gate": "soft_daily",
                    "limit": daily_soft_cap,
                    "observed": requests_today,
                    "recommendation": "upgrade_or_contact_support",
                },
            )
        manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
            gate="soft_daily", outcome="allow", tenant_tier=tier_label
        ).inc()

    try:
        per_minute_cap = int(settings.LLM_FAIR_USE_PER_MINUTE_CAP)
    except (TypeError, ValueError):
        per_minute_cap = 0
    if per_minute_cap > 0:
        minute_start = now - timedelta(minutes=1)
        requests_last_minute = await count_requests_in_window_fn(
            tenant_id=tenant_id, db=db, start=minute_start
        )
        manager_module.LLM_FAIR_USE_OBSERVED.labels(
            gate="per_minute", tenant_tier=tier_label
        ).set(requests_last_minute)
        if requests_last_minute >= per_minute_cap:
            manager_module.LLM_PRE_AUTH_DENIALS.labels(
                reason="fair_use_per_minute", tenant_tier=tier_label
            ).inc()
            manager_module.LLM_FAIR_USE_DENIALS.labels(
                gate="per_minute", tenant_tier=tier_label
            ).inc()
            manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
                gate="per_minute", outcome="deny", tenant_tier=tier_label
            ).inc()
            await maybe_await(
                manager_module.audit_log(
                    event="llm_fair_use_denied",
                    user_id="system",
                    tenant_id=str(tenant_id),
                    details={
                        "gate": "per_minute",
                        "tier": tier_label,
                        "limit": per_minute_cap,
                        "observed": requests_last_minute,
                    },
                    db=db,
                    isolated=True,
                )
            )
            raise manager_module.LLMFairUseExceededError(
                "Rate limit reached for this tenant. Retry in about 60 seconds or contact support for higher throughput.",
                details={
                    "gate": "per_minute",
                    "limit": per_minute_cap,
                    "observed": requests_last_minute,
                    "retry_after_seconds": 60,
                    "recommendation": "upgrade_or_contact_support",
                },
            )
        manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
            gate="per_minute", outcome="allow", tenant_tier=tier_label
        ).inc()

    try:
        max_concurrency = int(settings.LLM_FAIR_USE_PER_TENANT_CONCURRENCY_CAP)
    except (TypeError, ValueError):
        max_concurrency = 0
    if max_concurrency <= 0:
        return False

    try:
        lease_ttl = int(settings.LLM_FAIR_USE_CONCURRENCY_LEASE_TTL_SECONDS)
    except (TypeError, ValueError):
        lease_ttl = 180

    acquired, current_inflight = await acquire_fair_use_inflight_slot_fn(
        manager_cls=manager_cls,
        tenant_id=tenant_id,
        max_inflight=max_concurrency,
        ttl_seconds=max(30, lease_ttl),
    )
    manager_module.LLM_FAIR_USE_OBSERVED.labels(
        gate="concurrency", tenant_tier=tier_label
    ).set(current_inflight)
    if not acquired:
        manager_module.LLM_PRE_AUTH_DENIALS.labels(
            reason="fair_use_concurrency", tenant_tier=tier_label
        ).inc()
        manager_module.LLM_FAIR_USE_DENIALS.labels(
            gate="concurrency", tenant_tier=tier_label
        ).inc()
        manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
            gate="concurrency", outcome="deny", tenant_tier=tier_label
        ).inc()
        await maybe_await(
            manager_module.audit_log(
                event="llm_fair_use_denied",
                user_id="system",
                tenant_id=str(tenant_id),
                details={
                    "gate": "concurrency",
                    "tier": tier_label,
                    "limit": max_concurrency,
                    "observed": current_inflight,
                },
                db=db,
                isolated=True,
            )
        )
        raise manager_module.LLMFairUseExceededError(
            "Too many in-flight LLM requests for this tenant. Retry shortly or contact support for higher throughput.",
            details={
                "gate": "concurrency",
                "limit": max_concurrency,
                "observed": current_inflight,
                "retry_after_seconds": max(5, min(lease_ttl, 60)),
                "recommendation": "upgrade_or_contact_support",
            },
        )
    manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
        gate="concurrency", outcome="allow", tenant_tier=tier_label
    ).inc()
    return True
