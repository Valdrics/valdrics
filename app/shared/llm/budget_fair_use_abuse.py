from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.core.pricing import PricingTier
from app.shared.core.async_utils import maybe_await


def classify_client_ip(client_ip: str | None) -> tuple[str, int]:
    import ipaddress

    raw = str(client_ip or "").strip()
    if not raw:
        return "unknown", 50
    try:
        parsed = ipaddress.ip_address(raw)
    except ValueError:
        return "invalid", 80
    if parsed.is_loopback:
        return "loopback", 75
    if parsed.is_link_local:
        return "link_local", 65
    if parsed.is_private:
        return "private", 40
    if parsed.is_reserved or parsed.is_multicast:
        return "reserved", 70
    if parsed.version == 4:
        return "public_v4", 20
    return "public_v6", 20


async def record_authenticated_abuse_signal_impl(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    tier: PricingTier,
    actor_type: str,
    user_id: UUID | None,
    client_ip: str | None,
    *,
    classify_client_ip_fn: Any,
) -> None:
    import app.shared.llm.budget_manager as manager_module

    del manager_cls
    normalized_actor_type = str(actor_type or "").strip().lower()
    if normalized_actor_type not in {"user", "system"}:
        normalized_actor_type = "user" if user_id is not None else "system"
    if user_id is not None and normalized_actor_type == "system":
        normalized_actor_type = "user"
    ip_bucket, risk_score = classify_client_ip_fn(client_ip)
    manager_module.LLM_AUTH_ABUSE_SIGNALS.labels(
        tenant_tier=tier.value,
        actor_type=normalized_actor_type,
        ip_bucket=ip_bucket,
    ).inc()
    manager_module.LLM_AUTH_IP_RISK_SCORE.labels(
        tenant_tier=tier.value,
        actor_type=normalized_actor_type,
    ).set(risk_score)

    if risk_score < 70:
        return

    await maybe_await(
        manager_module.audit_log(
            event="llm_authenticated_abuse_signal",
            user_id=str(user_id or "system"),
            tenant_id=str(tenant_id),
            details={
                "actor_type": normalized_actor_type,
                "ip_bucket": ip_bucket,
                "risk_score": risk_score,
            },
            db=db,
            isolated=True,
        )
    )


async def enforce_global_abuse_guard_impl(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    tier: PricingTier,
    *,
    fair_use_global_abuse_block_key_fn: Any,
    as_bool_fn: Any,
    as_int_fn: Any,
    fair_use_cache_recoverable_errors: tuple[type[Exception], ...],
    fair_use_parse_recoverable_errors: tuple[type[Exception], ...],
) -> None:
    import app.shared.llm.budget_manager as manager_module

    settings = manager_module.get_settings()
    if not as_bool_fn(
        getattr(settings, "LLM_GLOBAL_ABUSE_GUARDS_ENABLED", True),
        default=True,
    ):
        return

    tier_label = tier.value
    kill_switch_enabled = as_bool_fn(
        getattr(settings, "LLM_GLOBAL_ABUSE_KILL_SWITCH", False),
        default=False,
    )
    if kill_switch_enabled:
        manager_module.LLM_PRE_AUTH_DENIALS.labels(
            reason="global_abuse_kill_switch",
            tenant_tier=tier_label,
        ).inc()
        manager_module.LLM_FAIR_USE_DENIALS.labels(
            gate="global_abuse",
            tenant_tier=tier_label,
        ).inc()
        manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
            gate="global_abuse", outcome="deny", tenant_tier=tier_label
        ).inc()
        raise manager_module.LLMFairUseExceededError(
            "Global abuse protections are active. LLM analysis is temporarily unavailable.",
            details={
                "gate": "global_abuse",
                "reason": "kill_switch",
            },
        )

    block_key = fair_use_global_abuse_block_key_fn()
    block_seconds_raw = getattr(settings, "LLM_GLOBAL_ABUSE_BLOCK_SECONDS", 120)
    block_seconds = max(30, as_int_fn(block_seconds_raw, default=120))
    cache = manager_module.get_cache_service()
    local_until = getattr(manager_cls, "_local_global_abuse_block_until", None)
    now = datetime.now(timezone.utc)
    if isinstance(local_until, datetime) and local_until > now:
        manager_module.LLM_PRE_AUTH_DENIALS.labels(
            reason="global_abuse_temporal_block",
            tenant_tier=tier_label,
        ).inc()
        manager_module.LLM_FAIR_USE_DENIALS.labels(
            gate="global_abuse",
            tenant_tier=tier_label,
        ).inc()
        manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
            gate="global_abuse", outcome="deny", tenant_tier=tier_label
        ).inc()
        raise manager_module.LLMFairUseExceededError(
            "Global abuse protections are active. Retry shortly.",
            details={
                "gate": "global_abuse",
                "reason": "temporal_block",
                "retry_after_seconds": int((local_until - now).total_seconds()),
            },
        )
    if cache.enabled and cache.client is not None:
        try:
            get_fn = getattr(cache.client, "get", None)
            if callable(get_fn) and await get_fn(block_key):
                manager_module.LLM_PRE_AUTH_DENIALS.labels(
                    reason="global_abuse_temporal_block",
                    tenant_tier=tier_label,
                ).inc()
                manager_module.LLM_FAIR_USE_DENIALS.labels(
                    gate="global_abuse",
                    tenant_tier=tier_label,
                ).inc()
                manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
                    gate="global_abuse", outcome="deny", tenant_tier=tier_label
                ).inc()
                raise manager_module.LLMFairUseExceededError(
                    "Global abuse protections are active. Retry shortly.",
                    details={
                        "gate": "global_abuse",
                        "reason": "temporal_block",
                        "retry_after_seconds": block_seconds,
                    },
                )
        except manager_module.LLMFairUseExceededError:
            raise
        except fair_use_cache_recoverable_errors as exc:
            manager_module.logger.warning(
                "llm_global_abuse_cache_get_failed",
                error=str(exc),
            )

    minute_start = now - timedelta(minutes=1)
    stmt = select(
        func.count(manager_module.LLMUsage.id),
        func.count(func.distinct(manager_module.LLMUsage.tenant_id)),
    ).where(manager_module.LLMUsage.created_at >= minute_start)
    result = await db.execute(stmt)
    row: Any = None
    row_getter = getattr(result, "one_or_none", None)
    if callable(row_getter):
        row = row_getter()
    if row is None:
        first_getter = getattr(result, "first", None)
        if callable(first_getter):
            row = first_getter()
    if row is None:
        row = (0, 0)
    try:
        global_requests_last_minute = int((row[0] if row else 0) or 0)
    except fair_use_parse_recoverable_errors:
        global_requests_last_minute = 0
    try:
        active_tenants_last_minute = int((row[1] if row else 0) or 0)
    except fair_use_parse_recoverable_errors:
        active_tenants_last_minute = 0

    manager_module.LLM_FAIR_USE_OBSERVED.labels(
        gate="global_rpm", tenant_tier=tier_label
    ).set(global_requests_last_minute)
    manager_module.LLM_FAIR_USE_OBSERVED.labels(
        gate="global_tenant_count", tenant_tier=tier_label
    ).set(active_tenants_last_minute)

    rpm_threshold_raw = getattr(settings, "LLM_GLOBAL_ABUSE_PER_MINUTE_CAP", 600)
    tenant_threshold_raw = getattr(
        settings, "LLM_GLOBAL_ABUSE_UNIQUE_TENANTS_THRESHOLD", 30
    )
    rpm_threshold = max(1, as_int_fn(rpm_threshold_raw, default=600))
    tenant_threshold = max(1, as_int_fn(tenant_threshold_raw, default=30))

    triggered = (
        global_requests_last_minute >= rpm_threshold
        and active_tenants_last_minute >= tenant_threshold
    )
    if triggered:
        manager_module.LLM_PRE_AUTH_DENIALS.labels(
            reason="global_abuse_triggered",
            tenant_tier=tier_label,
        ).inc()
        manager_module.LLM_FAIR_USE_DENIALS.labels(
            gate="global_abuse",
            tenant_tier=tier_label,
        ).inc()
        manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
            gate="global_abuse", outcome="deny", tenant_tier=tier_label
        ).inc()
        await maybe_await(
            manager_module.audit_log(
                event="llm_global_abuse_triggered",
                user_id="system",
                tenant_id=str(tenant_id),
                details={
                    "gate": "global_abuse",
                    "global_requests_last_minute": global_requests_last_minute,
                    "active_tenants_last_minute": active_tenants_last_minute,
                    "rpm_threshold": rpm_threshold,
                    "tenant_threshold": tenant_threshold,
                    "block_seconds": block_seconds,
                },
                db=db,
                isolated=True,
            )
        )
        manager_cls._local_global_abuse_block_until = now + timedelta(
            seconds=block_seconds
        )
        if cache.enabled and cache.client is not None:
            try:
                set_fn = getattr(cache.client, "set", None)
                if callable(set_fn):
                    await set_fn(block_key, "1", ex=block_seconds)
            except fair_use_cache_recoverable_errors as exc:
                manager_module.logger.warning(
                    "llm_global_abuse_cache_set_failed",
                    error=str(exc),
                )
        raise manager_module.LLMFairUseExceededError(
            "Global anti-abuse throttle is active. Retry shortly.",
            details={
                "gate": "global_abuse",
                "reason": "burst_detected",
                "global_requests_last_minute": global_requests_last_minute,
                "active_tenants_last_minute": active_tenants_last_minute,
                "rpm_threshold": rpm_threshold,
                "tenant_threshold": tenant_threshold,
                "retry_after_seconds": block_seconds,
            },
        )

    manager_module.LLM_FAIR_USE_EVALUATIONS.labels(
        gate="global_abuse", outcome="allow", tenant_tier=tier_label
    ).inc()
