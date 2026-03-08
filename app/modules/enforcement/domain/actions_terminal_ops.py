from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Mapping
from uuid import UUID

from app.modules.enforcement.domain.action_errors import EnforcementDomainError

from app.models.enforcement import (
    EnforcementActionExecution,
    EnforcementActionStatus,
)


async def complete_action_impl(
    *,
    db: Any,
    get_action_fn: Callable[..., Awaitable[EnforcementActionExecution]],
    tenant_id: UUID,
    action_id: UUID,
    worker_id: UUID,
    result_payload: Mapping[str, Any] | None,
    now: datetime | None,
    as_utc_fn: Callable[[datetime], datetime],
    utcnow_fn: Callable[[], datetime],
    json_sha256_fn: Callable[[Mapping[str, Any] | None], str],
) -> EnforcementActionExecution:
    action = await get_action_fn(tenant_id=tenant_id, action_id=action_id)
    if action.status != EnforcementActionStatus.RUNNING:
        raise EnforcementDomainError(
            status_code=409,
            detail="Only running actions can be completed",
        )
    if action.locked_by_worker_id is not None and action.locked_by_worker_id != worker_id:
        raise EnforcementDomainError(
            status_code=409,
            detail="Action lease is owned by another worker",
        )

    completed_at = as_utc_fn(now) if now is not None else utcnow_fn()
    normalized_result_payload = dict(result_payload or {})
    action.status = EnforcementActionStatus.SUCCEEDED
    action.result_payload = normalized_result_payload
    action.result_payload_sha256 = json_sha256_fn(normalized_result_payload)
    action.last_error_code = None
    action.last_error_message = None
    action.locked_by_worker_id = None
    action.lease_expires_at = None
    action.completed_at = completed_at
    action.next_retry_at = completed_at
    await db.commit()
    await db.refresh(action)
    return action


async def fail_action_impl(
    *,
    db: Any,
    get_action_fn: Callable[..., Awaitable[EnforcementActionExecution]],
    tenant_id: UUID,
    action_id: UUID,
    worker_id: UUID,
    error_code: str,
    error_message: str,
    retryable: bool,
    result_payload: Mapping[str, Any] | None,
    now: datetime | None,
    as_utc_fn: Callable[[datetime], datetime],
    utcnow_fn: Callable[[], datetime],
    json_sha256_fn: Callable[[Mapping[str, Any] | None], str],
) -> EnforcementActionExecution:
    action = await get_action_fn(tenant_id=tenant_id, action_id=action_id)
    if action.status != EnforcementActionStatus.RUNNING:
        raise EnforcementDomainError(
            status_code=409,
            detail="Only running actions can be failed",
        )
    if action.locked_by_worker_id is not None and action.locked_by_worker_id != worker_id:
        raise EnforcementDomainError(
            status_code=409,
            detail="Action lease is owned by another worker",
        )

    normalized_error_code = str(error_code or "").strip().lower()
    if not normalized_error_code:
        raise EnforcementDomainError(status_code=422, detail="error_code is required")
    if len(normalized_error_code) > 64:
        raise EnforcementDomainError(
            status_code=422,
            detail="error_code must be <= 64 characters",
        )
    normalized_error_message = str(error_message or "").strip()
    if not normalized_error_message:
        raise EnforcementDomainError(status_code=422, detail="error_message is required")
    if len(normalized_error_message) > 1000:
        raise EnforcementDomainError(
            status_code=422,
            detail="error_message must be <= 1000 characters",
        )

    failed_at = as_utc_fn(now) if now is not None else utcnow_fn()
    normalized_result_payload = dict(result_payload or {})
    if not normalized_result_payload:
        normalized_result_payload = {
            "error_code": normalized_error_code,
            "error_message": normalized_error_message,
            "retryable": bool(retryable),
        }

    should_retry = bool(retryable) and int(action.attempt_count) < int(action.max_attempts)
    action.last_error_code = normalized_error_code
    action.last_error_message = normalized_error_message
    action.result_payload = normalized_result_payload
    action.result_payload_sha256 = json_sha256_fn(normalized_result_payload)
    action.locked_by_worker_id = None
    action.lease_expires_at = None

    if should_retry:
        action.status = EnforcementActionStatus.QUEUED
        action.next_retry_at = failed_at + timedelta(seconds=int(action.retry_backoff_seconds))
        action.completed_at = None
    else:
        action.status = EnforcementActionStatus.FAILED
        action.next_retry_at = failed_at
        action.completed_at = failed_at

    await db.commit()
    await db.refresh(action)
    return action


async def cancel_action_impl(
    *,
    db: Any,
    get_action_fn: Callable[..., Awaitable[EnforcementActionExecution]],
    tenant_id: UUID,
    action_id: UUID,
    actor_id: UUID,
    reason: str | None,
    now: datetime | None,
    as_utc_fn: Callable[[datetime], datetime],
    utcnow_fn: Callable[[], datetime],
    json_sha256_fn: Callable[[Mapping[str, Any] | None], str],
) -> EnforcementActionExecution:
    action = await get_action_fn(tenant_id=tenant_id, action_id=action_id)
    if action.status in {
        EnforcementActionStatus.SUCCEEDED,
        EnforcementActionStatus.FAILED,
        EnforcementActionStatus.CANCELLED,
    }:
        raise EnforcementDomainError(
            status_code=409,
            detail="Terminal action cannot be cancelled",
        )

    cancelled_at = as_utc_fn(now) if now is not None else utcnow_fn()
    action.status = EnforcementActionStatus.CANCELLED
    action.locked_by_worker_id = None
    action.lease_expires_at = None
    action.completed_at = cancelled_at
    action.next_retry_at = cancelled_at
    if reason is not None:
        normalized_reason = str(reason).strip()
        action.last_error_code = "cancelled"
        action.last_error_message = normalized_reason[:1000] or "cancelled"
        action.result_payload = {
            "cancelled_by": str(actor_id),
            "reason": action.last_error_message,
        }
        action.result_payload_sha256 = json_sha256_fn(action.result_payload)

    await db.commit()
    await db.refresh(action)
    return action
