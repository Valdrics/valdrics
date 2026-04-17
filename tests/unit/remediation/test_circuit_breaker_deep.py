import pytest
import time
from types import SimpleNamespace
from unittest.mock import patch
from app.shared.remediation.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    get_circuit_breaker,
)
from app.shared.remediation import circuit_breaker as cb_module


class TestCircuitBreakerDeep:
    @pytest.mark.asyncio
    async def test_circuit_breaker_initial_state(self):
        cb = CircuitBreaker("tenant-1")
        assert await cb.get_state() == CircuitState.CLOSED
        assert await cb.can_execute() is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_failure_threshold(self):
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout_seconds=60)
        cb = CircuitBreaker("tenant-1", config=config)

        await cb.record_failure("error 1")
        assert await cb.get_state() == CircuitState.CLOSED

        await cb.record_failure("error 2")
        assert await cb.get_state() == CircuitState.OPEN
        assert await cb.can_execute() is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_recovery_timeout(self):
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_seconds=0.1)
        cb = CircuitBreaker("tenant-1", config=config)

        await cb.record_failure("trip")
        assert await cb.get_state() == CircuitState.OPEN
        assert await cb.can_execute() is False

        # Wait for recovery timeout
        time.sleep(0.15)

        assert await cb.can_execute() is True
        assert await cb.get_state() == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_memory_recovery_uses_monotonic_time(self):
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout_seconds=30)
        cb = CircuitBreaker("tenant-monotonic", config=config)

        with (
            patch.object(cb_module.time, "time", return_value=100.0),
            patch.object(cb_module, "_monotonic_time", return_value=10.0),
        ):
            await cb.record_failure("trip")

        assert await cb.get_state() == CircuitState.OPEN

        with (
            patch.object(cb_module.time, "time", return_value=100.0),
            patch.object(cb_module, "_monotonic_time", return_value=45.0),
        ):
            assert await cb.can_execute() is True

        assert await cb.get_state() == CircuitState.HALF_OPEN

    @pytest.mark.asyncio
    async def test_circuit_breaker_half_open_success_reset(self):
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("tenant-1", config=config)

        await cb.record_failure("trip")
        await cb.state.set("state", CircuitState.HALF_OPEN.value)

        await cb.record_success(savings=10.0)
        assert await cb.get_state() == CircuitState.CLOSED
        status = await cb.get_status()
        assert status["daily_savings_usd"] == 10.0

    @pytest.mark.asyncio
    async def test_circuit_breaker_budget_exceeded(self):
        config = CircuitBreakerConfig(max_daily_savings_usd=50.0)
        cb = CircuitBreaker("tenant-1", config=config)

        await cb.record_success(savings=40.0)
        assert await cb.can_execute(estimated_savings=20.0) is False
        assert await cb.can_execute(estimated_savings=5.0) is True

    @pytest.mark.asyncio
    async def test_circuit_breaker_reset(self):
        cb = CircuitBreaker("tenant-1")
        await cb.record_failure("fail")
        await cb.reset()
        assert await cb.get_state() == CircuitState.CLOSED
        assert await cb.state.get("failure_count") == 0

    @pytest.mark.asyncio
    async def test_get_circuit_breaker_factory(self):
        cb1 = await get_circuit_breaker("t1")
        cb2 = await get_circuit_breaker("t1")
        assert cb1 is cb2
        assert cb1.tenant_id == "t1"

    @pytest.mark.asyncio
    async def test_daily_savings_resets_when_day_changes(self):
        config = CircuitBreakerConfig(max_daily_savings_usd=50.0)
        cb = CircuitBreaker("tenant-1", config=config)

        await cb.state.set("daily_savings_usd", 40.0)
        await cb.state.set("daily_savings_date", "2000-01-01")

        # Should reset old day usage, otherwise this would exceed 50.0
        assert await cb.can_execute(estimated_savings=20.0) is True

    @pytest.mark.asyncio
    async def test_get_circuit_breaker_eviction_bound(self):
        cb_module._tenant_breakers.clear()
        runtime_settings = SimpleNamespace(
            CIRCUIT_BREAKER_CACHE_SIZE=2,
            CIRCUIT_BREAKER_FAILURE_THRESHOLD=3,
            CIRCUIT_BREAKER_RECOVERY_SECONDS=120,
            CIRCUIT_BREAKER_MAX_DAILY_SAVINGS=1000.0,
        )
        with patch.object(cb_module, "get_settings", return_value=runtime_settings):
            await get_circuit_breaker("tenant-1")
            await get_circuit_breaker("tenant-2")
            await get_circuit_breaker("tenant-3")

            assert len(cb_module._tenant_breakers) == 2
            assert "tenant-1" not in cb_module._tenant_breakers

    @pytest.mark.asyncio
    async def test_get_circuit_breaker_rebuilds_when_runtime_threshold_changes(self):
        cb_module._tenant_breakers.clear()
        runtime_settings = SimpleNamespace(
            CIRCUIT_BREAKER_CACHE_SIZE=100,
            CIRCUIT_BREAKER_FAILURE_THRESHOLD=3,
            CIRCUIT_BREAKER_RECOVERY_SECONDS=120,
            CIRCUIT_BREAKER_MAX_DAILY_SAVINGS=1000.0,
        )

        with patch.object(cb_module, "get_settings", return_value=runtime_settings):
            first = await get_circuit_breaker("tenant-runtime-refresh")
            runtime_settings.CIRCUIT_BREAKER_FAILURE_THRESHOLD = 7
            second = await get_circuit_breaker("tenant-runtime-refresh")

        assert first is not second
        assert second.config.failure_threshold == 7
