from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, cast
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.llm.budget_execution_helpers import (
    coerce_bool as _coerce_bool_impl,
    coerce_decimal as _coerce_decimal_impl,
    coerce_threshold_percent as _coerce_threshold_percent_impl,
    compose_request_type as _compose_request_type_impl,
    normalize_actor_type as _normalize_actor_type_impl,
)
from app.shared.llm.budget_execution_runtime_ops import (
    check_and_reserve_budget as _check_and_reserve_budget_impl,
    check_budget_and_alert as _check_budget_and_alert_impl,
    check_budget_state as _check_budget_state_impl,
    record_usage_entry as _record_usage_entry_impl,
)
from app.shared.llm.budget_fair_use import (
    enforce_fair_use_guards,
    enforce_global_abuse_guard,
    record_authenticated_abuse_signal,
)

if TYPE_CHECKING:
    from app.shared.llm.budget_manager import BudgetStatus


BUDGET_EXECUTION_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    AttributeError,
    KeyError,
)
BUDGET_METRIC_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    AttributeError,
)
BUDGET_ROLLBACK_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    AttributeError,
)
BUDGET_CACHE_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    AttributeError,
    KeyError,
    LookupError,
)
BUDGET_ALERT_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    RuntimeError,
    OSError,
    TimeoutError,
    ImportError,
    AttributeError,
    TypeError,
    ValueError,
)


def _coerce_decimal(value: Any) -> Decimal | None:
    return _coerce_decimal_impl(value)


def _coerce_bool(value: Any, *, default: bool = False) -> bool:
    return _coerce_bool_impl(value, default=default)


def _coerce_threshold_percent(value: Any) -> Decimal:
    return _coerce_threshold_percent_impl(value)


def _normalize_actor_type(value: Any) -> str:
    return _normalize_actor_type_impl(value)


def _compose_request_type(actor_type: str, request_type: str) -> str:
    return _compose_request_type_impl(actor_type, request_type)


async def check_and_reserve_budget(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    *,
    provider: str = "openai",
    model: str = "gpt-4o",
    prompt_tokens: int,
    completion_tokens: int,
    operation_id: str | None = None,
    user_id: UUID | None = None,
    actor_type: str = "system",
    client_ip: str | None = None,
) -> Decimal:
    """Check budget and atomically reserve funds."""
    return await _check_and_reserve_budget_impl(
        manager_cls=manager_cls,
        tenant_id=tenant_id,
        db=db,
        provider=provider,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        operation_id=operation_id,
        user_id=user_id,
        actor_type=actor_type,
        client_ip=client_ip,
        normalize_actor_type_fn=_normalize_actor_type,
        record_authenticated_abuse_signal_fn=record_authenticated_abuse_signal,
        enforce_global_abuse_guard_fn=enforce_global_abuse_guard,
        enforce_fair_use_guards_fn=enforce_fair_use_guards,
        execution_recoverable_errors=BUDGET_EXECUTION_RECOVERABLE_ERRORS,
    )


async def record_usage_entry(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    provider: str = "openai",
    actual_cost_usd: Decimal | None = None,
    is_byok: bool = False,
    operation_id: str | None = None,
    request_type: str = "unknown",
    user_id: UUID | None = None,
    actor_type: str = "system",
    client_ip: str | None = None,
) -> None:
    """Record actual LLM usage and handle metrics/alerts."""
    del client_ip
    await _record_usage_entry_impl(
        manager_cls=manager_cls,
        tenant_id=tenant_id,
        db=db,
        model=model,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        provider=provider,
        actual_cost_usd=actual_cost_usd,
        is_byok=is_byok,
        operation_id=operation_id,
        request_type=request_type,
        user_id=user_id,
        actor_type=actor_type,
        normalize_actor_type_fn=_normalize_actor_type,
        compose_request_type_fn=_compose_request_type,
        coerce_decimal_fn=_coerce_decimal,
        metric_recoverable_errors=BUDGET_METRIC_RECOVERABLE_ERRORS,
        rollback_recoverable_errors=BUDGET_ROLLBACK_RECOVERABLE_ERRORS,
        execution_recoverable_errors=BUDGET_EXECUTION_RECOVERABLE_ERRORS,
    )


async def check_budget_state(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
) -> BudgetStatus:
    """Unified budget check for tenants."""
    return cast(
        "BudgetStatus",
        await _check_budget_state_impl(
            manager_cls=manager_cls,
            tenant_id=tenant_id,
            db=db,
            coerce_decimal_fn=_coerce_decimal,
            coerce_threshold_percent_fn=_coerce_threshold_percent,
            coerce_bool_fn=lambda value: _coerce_bool(value, default=False),
            cache_recoverable_errors=BUDGET_CACHE_RECOVERABLE_ERRORS,
        ),
    )


async def check_budget_and_alert(
    manager_cls: Any,
    tenant_id: UUID,
    db: AsyncSession,
    last_cost: Decimal,
) -> None:
    """Checks budget threshold and sends Slack alerts if needed."""
    await _check_budget_and_alert_impl(
        manager_cls=manager_cls,
        tenant_id=tenant_id,
        db=db,
        last_cost=last_cost,
        coerce_decimal_fn=_coerce_decimal,
        coerce_threshold_percent_fn=_coerce_threshold_percent,
        alert_recoverable_errors=BUDGET_ALERT_RECOVERABLE_ERRORS,
    )
