import time
import asyncio
from collections import OrderedDict
from enum import Enum
from dataclasses import dataclass
from typing import Any, Dict, Optional, cast
from datetime import datetime, timezone
import structlog

from app.shared.core.config import get_settings

logger = structlog.get_logger()


def _monotonic_time() -> float:
    return time.monotonic()


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreakerConfig:
    failure_threshold: int = 3
    recovery_timeout_seconds: int = 300
    max_daily_savings_usd: float = 1000.0

    @classmethod
    def from_settings(cls) -> "CircuitBreakerConfig":
        s = get_settings()
        return cls(
            failure_threshold=s.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            recovery_timeout_seconds=s.CIRCUIT_BREAKER_RECOVERY_SECONDS,
            max_daily_savings_usd=s.CIRCUIT_BREAKER_MAX_DAILY_SAVINGS,
        )


class CircuitBreakerState:
    """
    Handles circuit-breaker state with process-local memory only.
    """

    def __init__(self, tenant_id: str) -> None:
        self.tenant_id = tenant_id
        self._memory_state: Dict[str, Any] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        return self._memory_state.get(key, default)

    async def set(self, key: str, value: Any, expire: int | None = None) -> None:
        del expire
        self._memory_state[key] = value

    async def incr(self, key: str) -> int:
        current = cast(int, self._memory_state.get(key, 0))
        new_val = current + 1
        self._memory_state[key] = new_val
        return new_val

    async def incr_float(self, key: str, amount: float) -> float:
        current = float(self._memory_state.get(key, 0.0))
        new_val = current + float(amount)
        self._memory_state[key] = new_val
        return new_val

    async def delete(self, key: str) -> None:
        self._memory_state.pop(key, None)


class CircuitBreaker:
    """
    Advanced circuit breaker with tenant isolation and process-local state.
    """

    def __init__(
        self,
        tenant_id: str,
        config: Optional[CircuitBreakerConfig] = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.config = config or CircuitBreakerConfig.from_settings()
        self.state = CircuitBreakerState(tenant_id)

    async def _reset_daily_budget_if_needed(self) -> None:
        """Reset daily savings counter when UTC date changes."""
        today = datetime.now(timezone.utc).date().isoformat()
        last_reset_day = await self.state.get("daily_savings_date")
        if last_reset_day != today:
            await self.state.set("daily_savings_usd", 0.0)
            await self.state.set("daily_savings_date", today)

    async def get_state(self) -> CircuitState:
        s = await self.state.get("state", CircuitState.CLOSED.value)
        return CircuitState(s)

    async def can_execute(self, estimated_savings: float = 0.0) -> bool:
        state = await self.get_state()

        if state == CircuitState.OPEN.value or state == CircuitState.OPEN:
            last_fail_monotonic = await self.state.get("last_failure_monotonic")
            if (
                last_fail_monotonic
                and (_monotonic_time() - float(last_fail_monotonic))
                > self.config.recovery_timeout_seconds
            ):
                await self.state.set("state", CircuitState.HALF_OPEN.value)
                logger.info("circuit_breaker_half_open", tenant_id=self.tenant_id)
                return True
            last_fail = await self.state.get("last_failure_at")
            if (
                last_fail
                and (time.time() - last_fail) > self.config.recovery_timeout_seconds
            ):
                # Transition to HALF_OPEN
                await self.state.set("state", CircuitState.HALF_OPEN.value)
                logger.info("circuit_breaker_half_open", tenant_id=self.tenant_id)
                return True
            return False

        # Check daily budget
        await self._reset_daily_budget_if_needed()
        daily_savings = await self.state.get("daily_savings_usd", 0.0)
        if (daily_savings + estimated_savings) > self.config.max_daily_savings_usd:
            logger.warning(
                "circuit_breaker_budget_exceeded",
                tenant_id=self.tenant_id,
                current=daily_savings,
                limit=self.config.max_daily_savings_usd,
            )
            return False

        return True

    async def record_success(self, savings: float = 0.0) -> None:
        state = await self.get_state()
        if state == CircuitState.HALF_OPEN:
            await self.reset()
            logger.info("circuit_breaker_recovered", tenant_id=self.tenant_id)

        # Reset failure count
        await self.state.set("failure_count", 0)

        # Track savings (daily budget)
        await self._reset_daily_budget_if_needed()
        await self.state.incr_float("daily_savings_usd", savings)

    async def record_failure(self, error: str) -> None:
        count = await self.state.incr("failure_count")
        await self.state.set("last_failure_at", time.time())
        await self.state.set("last_failure_monotonic", _monotonic_time())
        await self.state.set("last_error", error)

        if count >= self.config.failure_threshold:
            await self.state.set("state", CircuitState.OPEN.value)
            logger.error(
                "circuit_breaker_opened",
                tenant_id=self.tenant_id,
                failure_count=count,
                error=error,
            )

    async def reset(self) -> None:
        """Manually reset the circuit breaker."""
        await self.state.set("state", CircuitState.CLOSED.value)
        await self.state.set("failure_count", 0)
        await self.state.delete("last_failure_at")
        await self.state.delete("last_failure_monotonic")
        await self.state.delete("last_error")

    async def get_status(self) -> Dict[str, Any]:
        return {
            "tenant_id": self.tenant_id,
            "state": (await self.get_state()).value,
            "failure_count": await self.state.get("failure_count", 0),
            "daily_savings_usd": await self.state.get("daily_savings_usd", 0.0),
            "can_execute": await self.can_execute(),
            "last_error": await self.state.get("last_error"),
        }


# Multi-tenant cache
_tenant_breakers: "OrderedDict[str, CircuitBreaker]" = OrderedDict()
_tenant_breakers_lock = asyncio.Lock()

async def get_circuit_breaker(tenant_id: str) -> CircuitBreaker:
    """Get or create a circuit breaker for a tenant."""
    async with _tenant_breakers_lock:
        runtime_settings = get_settings()
        current_config = CircuitBreakerConfig.from_settings()
        existing_breaker = _tenant_breakers.get(tenant_id)
        if existing_breaker is not None and existing_breaker.config == current_config:
            _tenant_breakers.move_to_end(tenant_id)
            return existing_breaker

        _tenant_breakers[tenant_id] = CircuitBreaker(
            tenant_id,
            config=current_config,
        )

        max_cache_size = max(
            1,
            int(getattr(runtime_settings, "CIRCUIT_BREAKER_CACHE_SIZE", 100)),
        )
        while len(_tenant_breakers) > max_cache_size:
            evicted_tenant_id, _ = _tenant_breakers.popitem(last=False)
            logger.info("circuit_breaker_cache_evicted", tenant_id=evicted_tenant_id)

        return _tenant_breakers[tenant_id]
