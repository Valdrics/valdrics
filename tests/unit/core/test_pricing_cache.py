from app.shared.core.pricing_cache import (
    PricingTier,
    _TENANT_TIER_CACHE_MAX_ENTRIES,
    _tenant_tier_runtime_cache,
    clear_tenant_tier_cache,
    runtime_cache_get,
    runtime_cache_set,
)


def setup_function() -> None:
    clear_tenant_tier_cache()


def teardown_function() -> None:
    clear_tenant_tier_cache()


def test_runtime_cache_set_evicts_oldest_cached_timestamp_not_insertion_order() -> None:
    now = 10_000.0
    step = 0.001

    for index in range(_TENANT_TIER_CACHE_MAX_ENTRIES):
        runtime_cache_set(
            f"tenant-{index}",
            PricingTier.FREE,
            now=now + (float(index) * step),
        )

    # Refresh the first inserted key so it becomes the newest by timestamp while
    # retaining its original dict insertion position.
    runtime_cache_set("tenant-0", PricingTier.PRO, now=now + 50.0)

    runtime_cache_set(
        "tenant-overflow",
        PricingTier.ENTERPRISE,
        now=now + 55.0,
    )

    assert runtime_cache_get("tenant-0", now=now + 55.0) == PricingTier.PRO
    assert runtime_cache_get("tenant-overflow", now=now + 55.0) == PricingTier.ENTERPRISE
    assert runtime_cache_get("tenant-1", now=now + 55.0) is None


def test_runtime_cache_set_prunes_expired_entries_before_oldest_eviction() -> None:
    for index in range(_TENANT_TIER_CACHE_MAX_ENTRIES):
        runtime_cache_set(
            f"tenant-{index}",
            PricingTier.STARTER,
            now=float(index),
        )

    runtime_cache_set(
        "tenant-overflow",
        PricingTier.GROWTH,
        now=120.0,
    )

    assert runtime_cache_get("tenant-overflow", now=120.0) == PricingTier.GROWTH
    assert "tenant-0" not in _tenant_tier_runtime_cache
