from __future__ import annotations

import uuid
from contextlib import suppress
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Union, cast

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.modules.governance.domain.security.auth import CurrentUser

from fastapi import HTTPException, status

import structlog

from app.shared.core.pricing_cache import (
    TENANT_TIER_LOOKUP_RECOVERABLE_EXCEPTIONS,
    clear_tenant_tier_cache,
    runtime_cache_get as _runtime_cache_get,
    runtime_cache_set as _runtime_cache_set,
)
from app.shared.core.pricing_catalog import (
    ENTERPRISE_FEATURES,
    FEATURE_MATURITY,
    TIER_CONFIG,
)
from app.shared.core.pricing_types import FeatureFlag, FeatureMaturity, PricingTier

logger = structlog.get_logger()

__all__ = [
    "PricingTier",
    "FeatureFlag",
    "FeatureMaturity",
    "TIER_CONFIG",
    "ENTERPRISE_FEATURES",
    "FEATURE_MATURITY",
    "normalize_tier",
    "get_tier_config",
    "is_feature_enabled",
    "get_tier_limit",
    "get_feature_maturity",
    "get_tier_feature_maturity",
    "requires_tier",
    "requires_feature",
    "get_tenant_tier",
    "clear_tenant_tier_cache",
    "TierGuard",
]


def get_feature_maturity(feature: FeatureFlag | str) -> FeatureMaturity:
    if isinstance(feature, str):
        try:
            feature = FeatureFlag(feature)
        except ValueError:
            return FeatureMaturity.PREVIEW
    return FEATURE_MATURITY.get(feature, FeatureMaturity.PREVIEW)


def get_tier_feature_maturity(tier: PricingTier | str) -> dict[str, str]:
    config = get_tier_config(tier)
    features = config.get("features", set())
    normalized: list[FeatureFlag] = []
    for feature in features:
        if isinstance(feature, FeatureFlag):
            normalized.append(feature)
            continue
        if isinstance(feature, str):
            with suppress(ValueError):
                normalized.append(FeatureFlag(feature))
    return {
        feature.value: get_feature_maturity(feature).value
        for feature in sorted(normalized, key=lambda item: item.value)
    }


def normalize_tier(tier: PricingTier | str | None) -> PricingTier:
    """Map arbitrary tier values to a supported PricingTier."""
    if isinstance(tier, PricingTier):
        return tier
    if isinstance(tier, str):
        candidate = tier.strip().lower()
        try:
            return PricingTier(candidate)
        except ValueError:
            return PricingTier.FREE
    return PricingTier.FREE


def get_tier_config(tier: PricingTier | str) -> dict[str, Any]:
    """Get configuration for a tier."""
    resolved = normalize_tier(tier)
    fallback = (
        TIER_CONFIG.get(PricingTier.FREE) or TIER_CONFIG.get(PricingTier.STARTER) or {}
    )
    return TIER_CONFIG.get(resolved, fallback)


def is_feature_enabled(tier: PricingTier | str, feature: str | FeatureFlag) -> bool:
    """Check if a feature is enabled for a tier."""
    if isinstance(feature, str):
        try:
            feature = FeatureFlag(feature)
        except ValueError:
            return False

    config = get_tier_config(tier)
    return feature in config.get("features", set())


def get_tier_limit(tier: PricingTier | str, limit_name: str) -> Any:
    """Get a limit value for a tier (None = unlimited)."""
    config = get_tier_config(tier)
    limits = cast(dict[str, Any], config.get("limits", {}))
    raw_limit = limits.get(limit_name, 0)
    if raw_limit is None:
        return None
    if isinstance(raw_limit, bool):
        return int(raw_limit)
    if isinstance(raw_limit, float):
        return int(raw_limit)
    return raw_limit


def requires_tier(
    *allowed_tiers: PricingTier,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to require specific tiers for an endpoint.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = kwargs.get("user") or kwargs.get("current_user")
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user_tier = normalize_tier(getattr(user, "tier", PricingTier.FREE))

            if user_tier not in allowed_tiers:
                tier_names = [t.value for t in allowed_tiers]
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"This feature requires {' or '.join(tier_names)} tier. Please upgrade.",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def requires_feature(
    feature_name: Union[str, FeatureFlag],
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator to require a specific feature for an endpoint.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            user = kwargs.get("user") or kwargs.get("current_user")
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Authentication required",
                )

            user_tier = normalize_tier(getattr(user, "tier", PricingTier.FREE))

            if not is_feature_enabled(user_tier, feature_name):
                fn = (
                    feature_name.value
                    if isinstance(feature_name, FeatureFlag)
                    else feature_name
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Feature '{fn}' is not available on your current plan. Please upgrade.",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def get_tenant_tier(
    tenant_id: Union[str, uuid.UUID], db: "AsyncSession"
) -> PricingTier:
    """
    Get the pricing tier for a tenant.

    Uses a per-session cache to avoid repeated tenant lookups within the same
    request/job execution context.
    """
    from sqlalchemy import select

    from app.models.tenant import Tenant

    if isinstance(tenant_id, str):
        try:
            tenant_id = uuid.UUID(tenant_id)
        except (ValueError, AttributeError):
            return PricingTier.FREE

    cache: dict[str, PricingTier] | None = None
    db_info = getattr(db, "info", None)
    if isinstance(db_info, dict):
        raw_cache = db_info.setdefault("_tenant_tier_cache", {})
        if isinstance(raw_cache, dict):
            cache = raw_cache

    tenant_key = str(tenant_id)
    if cache is not None and tenant_key in cache:
        return cache[tenant_key]

    runtime_cached_tier = _runtime_cache_get(tenant_key)
    if runtime_cached_tier is not None:
        if cache is not None:
            cache[tenant_key] = runtime_cached_tier
        return runtime_cached_tier

    try:
        result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        scalar_one_or_none = getattr(result, "scalar_one_or_none", None)
        tenant: Any = None
        if callable(scalar_one_or_none):
            tenant = scalar_one_or_none()
        if tenant is not None and not hasattr(tenant, "plan"):
            logger.error(
                "tenant_lookup_invalid_result_type",
                tenant_id=str(tenant_id),
                result_type=type(tenant).__name__,
            )
            if cache is not None:
                cache[tenant_key] = PricingTier.FREE
            _runtime_cache_set(tenant_key, PricingTier.FREE)
            return PricingTier.FREE

        if not tenant:
            if cache is not None:
                cache[tenant_key] = PricingTier.FREE
            _runtime_cache_set(tenant_key, PricingTier.FREE)
            return PricingTier.FREE
        try:
            resolved = PricingTier(tenant.plan)
            if cache is not None:
                cache[tenant_key] = resolved
            _runtime_cache_set(tenant_key, resolved)
            return resolved
        except ValueError:
            logger.error("invalid_tenant_plan", tenant_id=str(tenant_id), plan=tenant.plan)
            if cache is not None:
                cache[tenant_key] = PricingTier.FREE
            _runtime_cache_set(tenant_key, PricingTier.FREE)
            return PricingTier.FREE
    except TENANT_TIER_LOOKUP_RECOVERABLE_EXCEPTIONS as e:
        logger.error("get_tenant_tier_failed", tenant_id=str(tenant_id), error=str(e))
        if cache is not None:
            cache[tenant_key] = PricingTier.FREE
        return PricingTier.FREE


class TierGuard:
    """
    Context manager and helper for tier-based feature gating.

    Usage:
        async with TierGuard(user, db) as guard:
            if guard.has(FeatureFlag.AI_INSIGHTS):
                ...
    """

    def __init__(self, user: "CurrentUser", db: "AsyncSession"):
        self.user = user
        self.db = db
        self.tier = PricingTier.FREE

    async def __aenter__(self) -> "TierGuard":
        if self.user and self.user.tenant_id:
            self.tier = await get_tenant_tier(self.user.tenant_id, self.db)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        pass

    def has(self, feature: FeatureFlag) -> bool:
        return is_feature_enabled(self.tier, feature)

    def limit(self, limit_name: str) -> Any:
        return get_tier_limit(self.tier, limit_name)

    def require(self, feature: FeatureFlag) -> None:
        if not self.has(feature):
            raise HTTPException(
                status_code=403,
                detail=f"Feature '{feature.value}' requires a plan upgrade.",
            )
