from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Awaitable, Callable, Mapping, cast
from uuid import UUID

from sqlalchemy.exc import IntegrityError

from app.models.enforcement import (
    EnforcementApprovalRequest,
    EnforcementApprovalStatus,
    EnforcementDecisionType,
    EnforcementMode,
    EnforcementSource,
)


def resolve_idempotency_key(*, fingerprint: str, idempotency_key: str | None) -> str:
    raw_idempotency_key = (idempotency_key or fingerprint).strip()
    return raw_idempotency_key[:128] if raw_idempotency_key else fingerprint


async def get_existing_gate_result(
    *,
    service: Any,
    tenant_id: UUID,
    source: EnforcementSource,
    idempotency_key: str,
    gate_evaluation_result_cls: type[Any],
    ttl_seconds: int,
) -> Any | None:
    existing = await service._get_decision_by_idempotency(
        tenant_id=tenant_id,
        source=source,
        idempotency_key=idempotency_key,
    )
    if existing is None:
        return None
    existing_approval = await service._get_approval_by_decision(existing.id)
    return gate_evaluation_result_cls(
        decision=existing,
        approval=existing_approval,
        approval_token=None,
        ttl_seconds=ttl_seconds,
    )


async def get_existing_gate_result_with_lock(
    *,
    service: Any,
    tenant_id: UUID,
    source: EnforcementSource,
    idempotency_key: str,
    gate_evaluation_result_cls: type[Any],
    ttl_seconds: int,
    acquire_lock_fn: Callable[[], Awaitable[None]],
) -> Any | None:
    existing_result = await get_existing_gate_result(
        service=service,
        tenant_id=tenant_id,
        source=source,
        idempotency_key=idempotency_key,
        gate_evaluation_result_cls=gate_evaluation_result_cls,
        ttl_seconds=ttl_seconds,
    )
    if existing_result is not None:
        return existing_result
    await acquire_lock_fn()
    return await get_existing_gate_result(
        service=service,
        tenant_id=tenant_id,
        source=source,
        idempotency_key=idempotency_key,
        gate_evaluation_result_cls=gate_evaluation_result_cls,
        ttl_seconds=ttl_seconds,
    )


async def persist_decision_with_optional_approval(
    *,
    service: Any,
    tenant_id: UUID,
    source: EnforcementSource,
    idempotency_key: str,
    decision_row: Any,
    gate_input: Any,
    mode: EnforcementMode,
    decision: EnforcementDecisionType,
    policy: Any,
    actor_id: UUID,
    now: datetime,
    ttl_seconds: int,
    gate_evaluation_result_cls: type[Any],
    reserve_credit_allocations_fn: Callable[[], Awaitable[list[dict[str, str]]]] | None,
) -> Any:
    approval: EnforcementApprovalRequest | None = None
    try:
        await service.db.flush()

        if reserve_credit_allocations_fn is not None:
            credit_allocations_payload = await reserve_credit_allocations_fn()
            if credit_allocations_payload:
                decision_row.response_payload = {
                    **(decision_row.response_payload or {}),
                    "credit_reservation_allocations": credit_allocations_payload,
                }

        if (
            decision == EnforcementDecisionType.REQUIRE_APPROVAL
            and not gate_input.dry_run
            and mode != EnforcementMode.SHADOW
        ):
            approval_routing_trace = service._resolve_approval_routing_trace(
                policy=policy,
                decision=decision_row,
            )
            approval = EnforcementApprovalRequest(
                tenant_id=tenant_id,
                decision_id=decision_row.id,
                status=EnforcementApprovalStatus.PENDING,
                requested_by_user_id=actor_id,
                routing_rule_id=(
                    str(approval_routing_trace.get("rule_id") or "").strip() or None
                ),
                routing_trace=approval_routing_trace,
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            service.db.add(approval)
            await service.db.flush()

        service._append_decision_ledger_entry(
            decision_row=decision_row,
            approval_row=approval,
        )
        await service.db.commit()
    except IntegrityError:
        await service.db.rollback()
        existing = await service._get_decision_by_idempotency(
            tenant_id=tenant_id,
            source=source,
            idempotency_key=idempotency_key,
        )
        if existing is None:
            raise
        existing_approval = await service._get_approval_by_decision(existing.id)
        return gate_evaluation_result_cls(
            decision=existing,
            approval=existing_approval,
            approval_token=None,
            ttl_seconds=ttl_seconds,
        )

    await service.db.refresh(decision_row)
    if approval is not None:
        await service.db.refresh(approval)

    return gate_evaluation_result_cls(
        decision=decision_row,
        approval=approval,
        approval_token=None,
        ttl_seconds=ttl_seconds,
    )


def credit_reservation_callback(
    *,
    service: Any,
    tenant_id: UUID,
    decision_row: Any,
    scope_key: str | None,
    reserve_reserved_credit_usd: Decimal,
    reserve_emergency_credit_usd: Decimal,
    now: datetime,
) -> Callable[[], Awaitable[list[dict[str, str]]]]:
    async def _reserve() -> list[dict[str, str]]:
        if not decision_row.reservation_active:
            return []
        if decision_row.reserved_credit_usd <= Decimal("0"):
            return []
        return cast(
            list[dict[str, str]],
            await service._reserve_credit_for_decision(
                tenant_id=tenant_id,
                decision_id=decision_row.id,
                scope_key=scope_key,
                reserve_reserved_credit_usd=reserve_reserved_credit_usd,
                reserve_emergency_credit_usd=reserve_emergency_credit_usd,
                now=now,
            ),
        )

    return _reserve


def build_metadata_payload(
    *, original_metadata: Mapping[str, Any], risk_class: str, risk_score: int
) -> dict[str, Any]:
    metadata_payload = dict(original_metadata)
    if "risk_level" not in metadata_payload:
        metadata_payload["risk_level"] = risk_class
    metadata_payload["computed_risk_class"] = risk_class
    metadata_payload["computed_risk_score"] = risk_score
    return metadata_payload


def sanitize_failure_metadata(
    failure_metadata: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not failure_metadata:
        return None
    return {
        str(key): value for key, value in failure_metadata.items() if str(key).strip()
    } or None


def build_fail_safe_reasons(
    *,
    mode: EnforcementMode,
    failure_reason_code: str,
    dry_run: bool,
) -> tuple[str, list[str]]:
    normalized_reason = str(failure_reason_code or "").strip().lower()
    if not normalized_reason:
        normalized_reason = "gate_evaluation_error"

    mode_reason = {
        EnforcementMode.SHADOW: "shadow_mode_fail_open",
        EnforcementMode.SOFT: "soft_mode_fail_safe_escalation",
        EnforcementMode.HARD: "hard_mode_fail_closed",
    }[mode]
    reasons = [normalized_reason, mode_reason]
    if dry_run:
        reasons.append("dry_run")
    return normalized_reason, reasons
