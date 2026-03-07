from __future__ import annotations

from decimal import Decimal
from typing import Any, Callable


def build_gate_request_payload(
    *,
    gate_input: Any,
    normalized_env: str,
    monthly_delta: Decimal,
    hourly_delta: Decimal,
    metadata_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "project_id": gate_input.project_id,
        "environment": normalized_env,
        "action": gate_input.action,
        "resource_reference": gate_input.resource_reference,
        "estimated_monthly_delta_usd": str(monthly_delta),
        "estimated_hourly_delta_usd": str(hourly_delta),
        "metadata": metadata_payload,
        "dry_run": gate_input.dry_run,
    }


def build_gate_response_payload(
    *,
    mode: Any,
    mode_scope: str,
    is_prod: bool,
    allocation_headroom: Decimal | None,
    credits_available: Decimal,
    reserved_credit_headroom: Decimal,
    emergency_credit_headroom: Decimal,
    plan_ceiling: Decimal | None,
    plan_headroom: Decimal | None,
    enterprise_ceiling: Decimal | None,
    enterprise_headroom: Decimal | None,
    tenant_tier: Any,
    entitlement_result: Any,
    reserve_reserved_credit: Decimal,
    reserve_emergency_credit: Decimal,
    computed_context: Any,
    quantize_fn: Callable[[Decimal, str], Decimal],
    to_decimal_fn: Callable[[Any], Decimal],
) -> dict[str, Any]:
    return {
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
    }


def build_fail_safe_response_payload(
    *,
    mode: Any,
    mode_scope: str,
    is_prod: bool,
    normalized_reason: str,
    fail_safe_details: dict[str, Any] | None,
    computed_context: Any,
) -> dict[str, Any]:
    return {
        "mode": mode.value,
        "mode_scope": mode_scope,
        "is_production": is_prod,
        "fail_safe_trigger": normalized_reason,
        "fail_safe_details": fail_safe_details,
        "computed_context": computed_context.to_payload(),
    }
