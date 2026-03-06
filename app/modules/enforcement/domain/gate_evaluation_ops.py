from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Mapping
from uuid import UUID

from app.models.enforcement import (
    EnforcementDecision,
    EnforcementDecisionType,
    EnforcementMode,
    EnforcementSource,
)
from app.modules.enforcement.domain.gate_evaluation_persistence_ops import (
    build_fail_safe_reasons,
    build_metadata_payload,
    credit_reservation_callback,
    get_existing_gate_result,
    get_existing_gate_result_with_lock,
    persist_decision_with_optional_approval,
    sanitize_failure_metadata,
)
from app.modules.enforcement.domain.gate_evaluation_context_ops import build_gate_evaluation_context

async def evaluate_gate(
    *,
    service: Any,
    tenant_id: UUID,
    actor_id: UUID,
    source: EnforcementSource,
    gate_input: Any,
    gate_evaluation_result_cls: type[Any],
    stable_fingerprint_fn: Callable[[EnforcementSource, Any], str],
    normalize_environment_fn: Callable[[str], str],
    month_bounds_fn: Callable[[datetime], tuple[datetime, datetime]],
    quantize_fn: Callable[[Decimal, str], Decimal],
    to_decimal_fn: Callable[[Any], Decimal],
    is_production_environment_fn: Callable[[str], bool],
    unique_reason_codes_fn: Callable[[list[str]], list[str]],
    normalize_policy_document_schema_version_fn: Callable[[str | None], str],
    normalize_policy_document_sha256_fn: Callable[[str | None], str],
    utcnow_fn: Callable[[], datetime],
) -> Any:
    context = await build_gate_evaluation_context(
        service=service,
        tenant_id=tenant_id,
        source=source,
        gate_input=gate_input,
        stable_fingerprint_fn=stable_fingerprint_fn,
        normalize_environment_fn=normalize_environment_fn,
    )
    policy = context.policy
    normalized_env = context.normalized_env
    mode = context.mode
    mode_scope = context.mode_scope
    ttl_seconds = context.ttl_seconds
    fingerprint = context.fingerprint
    idempotency_key = context.idempotency_key
    existing_result = await get_existing_gate_result_with_lock(
        service=service,
        tenant_id=tenant_id,
        source=source,
        idempotency_key=idempotency_key,
        gate_evaluation_result_cls=gate_evaluation_result_cls,
        ttl_seconds=ttl_seconds,
        acquire_lock_fn=lambda: service._acquire_gate_evaluation_lock(
            policy=policy, source=source
        ),
    )
    if existing_result is not None:
        return existing_result
    now = utcnow_fn()
    month_start, month_end = month_bounds_fn(now)
    monthly_delta = quantize_fn(gate_input.estimated_monthly_delta_usd, "0.0001")
    hourly_delta = quantize_fn(gate_input.estimated_hourly_delta_usd, "0.000001")
    reasons: list[str] = []
    reserved_alloc_total, reserved_credit_total = await service._get_reserved_totals(
        tenant_id=tenant_id,
        month_start=month_start,
        month_end=month_end,
    )
    reserved_total_monthly = quantize_fn(
        to_decimal_fn(reserved_alloc_total) + to_decimal_fn(reserved_credit_total),
        "0.0001",
    )
    tenant_tier = await service._resolve_tenant_tier(tenant_id)
    plan_ceiling = await service._resolve_plan_monthly_ceiling_usd(
        policy=policy,
        tenant_tier=tenant_tier,
    )
    enterprise_ceiling = await service._resolve_enterprise_monthly_ceiling_usd(
        policy=policy,
        tenant_tier=tenant_tier,
    )
    plan_headroom = (
        quantize_fn(
            max(Decimal("0.0000"), to_decimal_fn(plan_ceiling) - reserved_total_monthly),
            "0.0001",
        )
        if plan_ceiling is not None
        else None
    )
    enterprise_headroom = (
        quantize_fn(
            max(Decimal("0.0000"), to_decimal_fn(enterprise_ceiling) - reserved_total_monthly),
            "0.0001",
        )
        if enterprise_ceiling is not None
        else None
    )
    budget = await service._get_effective_budget(
        tenant_id=tenant_id,
        scope_key=gate_input.project_id,
    )
    reserved_credit_headroom, emergency_credit_headroom = await service._get_credit_headrooms(
        tenant_id=tenant_id,
        scope_key=gate_input.project_id,
        now=now,
    )
    credits_available = quantize_fn(
        reserved_credit_headroom + emergency_credit_headroom,
        "0.0001",
    )

    if budget is None:
        allocation_headroom: Decimal | None = None
        reasons.append("no_budget_configured")
    else:
        allocation_headroom = max(
            Decimal("0"),
            to_decimal_fn(budget.monthly_limit_usd) - reserved_alloc_total,
        )

    is_prod = is_production_environment_fn(normalized_env)
    computed_context = await service._build_decision_computed_context(
        tenant_id=tenant_id,
        policy_version=int(policy.policy_version),
        gate_input=gate_input,
        now=now,
        is_production=is_prod,
    )
    approval_required = (
        policy.require_approval_for_prod
        if is_prod
        else policy.require_approval_for_nonprod
    )
    if monthly_delta <= to_decimal_fn(policy.auto_approve_below_monthly_usd):
        approval_required = False

    reserve_allocation = Decimal("0")
    reserve_reserved_credit = Decimal("0")
    reserve_emergency_credit = Decimal("0")
    reserve_credit = Decimal("0")
    reservation_active = False
    entitlement_result = None

    decision = EnforcementDecisionType.ALLOW
    computed_context_unavailable = (
        computed_context.data_source_mode == "unavailable"
        and monthly_delta > Decimal("0.0000")
    )
    if computed_context_unavailable:
        reasons.append("computed_context_unavailable")
        reasons.append(service._mode_violation_reason_suffix(mode, subject="cost_context"))
        decision = service._mode_violation_decision(mode)
    else:
        hard_deny_threshold = to_decimal_fn(policy.hard_deny_above_monthly_usd)
        if monthly_delta > hard_deny_threshold:
            reasons.append("hard_deny_threshold_exceeded")
            decision = service._mode_violation_decision(mode)
            if mode == EnforcementMode.SOFT:
                reasons.append("soft_mode_escalation")
            if mode == EnforcementMode.SHADOW:
                reasons.append("shadow_mode_override")
        else:
            entitlement_result = service._evaluate_entitlement_waterfall(
                mode=mode,
                monthly_delta=monthly_delta,
                plan_headroom=plan_headroom,
                allocation_headroom=allocation_headroom,
                reserved_credit_headroom=reserved_credit_headroom,
                emergency_credit_headroom=emergency_credit_headroom,
                enterprise_headroom=enterprise_headroom,
            )
            decision = entitlement_result.decision
            reserve_allocation = entitlement_result.reserve_allocation_usd
            reserve_reserved_credit = entitlement_result.reserve_reserved_credit_usd
            reserve_emergency_credit = entitlement_result.reserve_emergency_credit_usd
            reserve_credit = entitlement_result.reserve_credit_usd

            if entitlement_result.reason_code is not None:
                reasons.append(entitlement_result.reason_code)
                reason_subject = {
                    "budget_exceeded": "budget",
                    "plan_limit_exceeded": "plan_limit",
                    "enterprise_ceiling_exceeded": "enterprise_ceiling",
                }.get(entitlement_result.reason_code)
                if reason_subject and mode in {
                    EnforcementMode.SHADOW,
                    EnforcementMode.SOFT,
                }:
                    reasons.append(
                        service._mode_violation_reason_suffix(
                            mode,
                            subject=reason_subject,
                        )
                    )
            if reserve_credit > Decimal("0.0000"):
                reasons.append("credit_waterfall_used")
                if reserve_reserved_credit > Decimal("0.0000"):
                    reasons.append("reserved_credit_waterfall_used")
                if reserve_emergency_credit > Decimal("0.0000"):
                    reasons.append("emergency_credit_waterfall_used")

    if decision in {
        EnforcementDecisionType.ALLOW,
        EnforcementDecisionType.ALLOW_WITH_CREDITS,
    } and approval_required:
        if mode == EnforcementMode.SHADOW:
            reasons.append("shadow_mode_approval_override")
        else:
            decision = EnforcementDecisionType.REQUIRE_APPROVAL
            reasons.append("approval_required")

    if gate_input.dry_run:
        reasons.append("dry_run")
        reserve_allocation = Decimal("0")
        reserve_reserved_credit = Decimal("0")
        reserve_emergency_credit = Decimal("0")
        reserve_credit = Decimal("0")
        reservation_active = False
    elif decision != EnforcementDecisionType.DENY and mode != EnforcementMode.SHADOW:
        reservation_active = (reserve_allocation + reserve_credit) > Decimal("0")

    metadata_payload = build_metadata_payload(
        original_metadata=gate_input.metadata,
        risk_class=computed_context.risk_class,
        risk_score=computed_context.risk_score,
    )

    decision_row = EnforcementDecision(
        tenant_id=tenant_id,
        source=source,
        environment=normalized_env,
        project_id=gate_input.project_id,
        action=gate_input.action,
        resource_reference=gate_input.resource_reference,
        decision=decision,
        reason_codes=unique_reason_codes_fn(reasons),
        policy_version=int(policy.policy_version),
        policy_document_schema_version=normalize_policy_document_schema_version_fn(
            policy.policy_document_schema_version
        ),
        policy_document_sha256=normalize_policy_document_sha256_fn(
            policy.policy_document_sha256
        ),
        request_fingerprint=fingerprint,
        idempotency_key=idempotency_key,
        request_payload={
            "project_id": gate_input.project_id,
            "environment": normalized_env,
            "action": gate_input.action,
            "resource_reference": gate_input.resource_reference,
            "estimated_monthly_delta_usd": str(monthly_delta),
            "estimated_hourly_delta_usd": str(hourly_delta),
            "metadata": metadata_payload,
            "dry_run": gate_input.dry_run,
        },
        response_payload={
            "mode": mode.value,
            "mode_scope": mode_scope,
            "is_production": is_prod,
            "allocation_headroom_usd": (
                str(allocation_headroom) if allocation_headroom is not None else None
            ),
            "credits_headroom_usd": str(credits_available),
            "reserved_credits_headroom_usd": str(reserved_credit_headroom),
            "emergency_credits_headroom_usd": str(emergency_credit_headroom),
            "plan_monthly_ceiling_usd": (
                str(quantize_fn(to_decimal_fn(plan_ceiling), "0.0001"))
                if plan_ceiling is not None
                else None
            ),
            "plan_headroom_usd": (
                str(quantize_fn(to_decimal_fn(plan_headroom), "0.0001"))
                if plan_headroom is not None
                else None
            ),
            "enterprise_monthly_ceiling_usd": (
                str(quantize_fn(to_decimal_fn(enterprise_ceiling), "0.0001"))
                if enterprise_ceiling is not None
                else None
            ),
            "enterprise_headroom_usd": (
                str(quantize_fn(to_decimal_fn(enterprise_headroom), "0.0001"))
                if enterprise_headroom is not None
                else None
            ),
            "tenant_tier": tenant_tier.value,
            "entitlement_reason_code": (
                entitlement_result.reason_code if entitlement_result is not None else None
            ),
            "entitlement_waterfall": (
                entitlement_result.stage_details if entitlement_result is not None else None
            ),
            "reserved_credit_split_usd": {
                "reserved": str(reserve_reserved_credit),
                "emergency": str(reserve_emergency_credit),
            },
            "computed_context": computed_context.to_payload(),
        },
        estimated_monthly_delta_usd=monthly_delta,
        estimated_hourly_delta_usd=hourly_delta,
        burn_rate_daily_usd=computed_context.burn_rate_daily_usd,
        forecast_eom_usd=computed_context.forecast_eom_usd,
        risk_class=computed_context.risk_class,
        risk_score=int(computed_context.risk_score),
        anomaly_signal=bool(computed_context.anomaly_signal),
        allocation_available_usd=allocation_headroom,
        credits_available_usd=credits_available,
        reserved_allocation_usd=reserve_allocation,
        reserved_credit_usd=reserve_credit,
        reservation_active=reservation_active,
        approval_required=decision == EnforcementDecisionType.REQUIRE_APPROVAL,
        approval_token_issued=False,
        token_expires_at=None,
        created_by_user_id=actor_id,
    )
    service.db.add(decision_row)

    reserve_credit_fn = credit_reservation_callback(
        service=service,
        tenant_id=tenant_id,
        decision_row=decision_row,
        scope_key=gate_input.project_id,
        reserve_reserved_credit_usd=reserve_reserved_credit,
        reserve_emergency_credit_usd=reserve_emergency_credit,
        now=now,
    )

    return await persist_decision_with_optional_approval(
        service=service,
        tenant_id=tenant_id,
        source=source,
        idempotency_key=idempotency_key,
        decision_row=decision_row,
        gate_input=gate_input,
        mode=mode,
        decision=decision,
        policy=policy,
        actor_id=actor_id,
        now=now,
        ttl_seconds=ttl_seconds,
        gate_evaluation_result_cls=gate_evaluation_result_cls,
        reserve_credit_allocations_fn=reserve_credit_fn,
    )
async def resolve_fail_safe_gate(
    *,
    service: Any,
    tenant_id: UUID,
    actor_id: UUID,
    source: EnforcementSource,
    gate_input: Any,
    failure_reason_code: str,
    failure_metadata: Mapping[str, Any] | None,
    gate_evaluation_result_cls: type[Any],
    stable_fingerprint_fn: Callable[[EnforcementSource, Any], str],
    normalize_environment_fn: Callable[[str], str],
    quantize_fn: Callable[[Decimal, str], Decimal],
    mode_violation_decision_fn: Callable[[EnforcementMode], EnforcementDecisionType],
    is_production_environment_fn: Callable[[str], bool],
    unique_reason_codes_fn: Callable[[list[str]], list[str]],
    normalize_policy_document_schema_version_fn: Callable[[str | None], str],
    normalize_policy_document_sha256_fn: Callable[[str | None], str],
    utcnow_fn: Callable[[], datetime],
) -> Any:
    now = utcnow_fn()
    context = await build_gate_evaluation_context(
        service=service,
        tenant_id=tenant_id,
        source=source,
        gate_input=gate_input,
        stable_fingerprint_fn=stable_fingerprint_fn,
        normalize_environment_fn=normalize_environment_fn,
    )
    policy = context.policy
    normalized_env = context.normalized_env
    mode = context.mode
    mode_scope = context.mode_scope
    ttl_seconds = context.ttl_seconds
    fingerprint = context.fingerprint
    idempotency_key = context.idempotency_key
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

    normalized_reason, reasons = build_fail_safe_reasons(
        mode=mode,
        failure_reason_code=failure_reason_code,
        dry_run=gate_input.dry_run,
    )
    monthly_delta = quantize_fn(gate_input.estimated_monthly_delta_usd, "0.0001")
    hourly_delta = quantize_fn(gate_input.estimated_hourly_delta_usd, "0.000001")
    decision = mode_violation_decision_fn(mode)
    is_prod = is_production_environment_fn(normalized_env)
    computed_context = await service._build_decision_computed_context(
        tenant_id=tenant_id,
        policy_version=int(policy.policy_version),
        gate_input=gate_input,
        now=now,
        is_production=is_prod,
    )

    fail_safe_details = sanitize_failure_metadata(failure_metadata)
    metadata_payload = build_metadata_payload(
        original_metadata=gate_input.metadata,
        risk_class=computed_context.risk_class,
        risk_score=computed_context.risk_score,
    )

    decision_row = EnforcementDecision(
        tenant_id=tenant_id,
        source=source,
        environment=normalized_env,
        project_id=gate_input.project_id,
        action=gate_input.action,
        resource_reference=gate_input.resource_reference,
        decision=decision,
        reason_codes=unique_reason_codes_fn(reasons),
        policy_version=int(policy.policy_version),
        policy_document_schema_version=normalize_policy_document_schema_version_fn(
            policy.policy_document_schema_version
        ),
        policy_document_sha256=normalize_policy_document_sha256_fn(
            policy.policy_document_sha256
        ),
        request_fingerprint=fingerprint,
        idempotency_key=idempotency_key,
        request_payload={
            "project_id": gate_input.project_id,
            "environment": normalized_env,
            "action": gate_input.action,
            "resource_reference": gate_input.resource_reference,
            "estimated_monthly_delta_usd": str(monthly_delta),
            "estimated_hourly_delta_usd": str(hourly_delta),
            "metadata": metadata_payload,
            "dry_run": gate_input.dry_run,
        },
        response_payload={
            "mode": mode.value,
            "mode_scope": mode_scope,
            "is_production": is_prod,
            "fail_safe_trigger": normalized_reason,
            "fail_safe_details": fail_safe_details,
            "computed_context": computed_context.to_payload(),
        },
        estimated_monthly_delta_usd=monthly_delta,
        estimated_hourly_delta_usd=hourly_delta,
        burn_rate_daily_usd=computed_context.burn_rate_daily_usd,
        forecast_eom_usd=computed_context.forecast_eom_usd,
        risk_class=computed_context.risk_class,
        risk_score=int(computed_context.risk_score),
        anomaly_signal=bool(computed_context.anomaly_signal),
        allocation_available_usd=None,
        credits_available_usd=None,
        reserved_allocation_usd=Decimal("0"),
        reserved_credit_usd=Decimal("0"),
        reservation_active=False,
        approval_required=decision == EnforcementDecisionType.REQUIRE_APPROVAL,
        approval_token_issued=False,
        token_expires_at=None,
        created_by_user_id=actor_id,
    )
    service.db.add(decision_row)

    return await persist_decision_with_optional_approval(
        service=service,
        tenant_id=tenant_id,
        source=source,
        idempotency_key=idempotency_key,
        decision_row=decision_row,
        gate_input=gate_input,
        mode=mode,
        decision=decision,
        policy=policy,
        actor_id=actor_id,
        now=now,
        ttl_seconds=ttl_seconds,
        gate_evaluation_result_cls=gate_evaluation_result_cls,
        reserve_credit_allocations_fn=None,
    )
