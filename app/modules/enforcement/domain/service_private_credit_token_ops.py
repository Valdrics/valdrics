from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping, cast
from uuid import UUID

from app.models.enforcement import (
    EnforcementApprovalRequest,
    EnforcementCreditPoolType,
    EnforcementDecision,
    EnforcementDecisionType,
    EnforcementMode,
    EnforcementSource,
)
from app.modules.enforcement.domain.approval_token_ops import (
    build_approval_token as _build_approval_token_impl,
    decode_approval_token as _decode_approval_token_impl,
    extract_token_context_payload as _extract_token_context_payload_impl,
)
from app.modules.enforcement.domain.credit_ops import (
    get_credit_headrooms as _get_credit_headrooms_impl,
    reserve_credit_for_decision as _reserve_credit_for_decision_impl,
    reserve_credit_from_grants as _reserve_credit_from_grants_impl,
    settle_credit_reservations_for_decision as _settle_credit_reservations_for_decision_impl,
)
from app.modules.enforcement.domain.runtime_query_ops import (
    assert_pending as _assert_pending_impl,
    load_approval_with_decision as _load_approval_with_decision_impl,
)
from app.modules.enforcement.domain.service_models import (
    ApprovalTokenContext,
    EntitlementWaterfallResult,
)
from app.modules.enforcement.domain.service_utils import (
    _as_utc,
    _quantize,
    _to_decimal,
    _utcnow,
)
from app.modules.enforcement.domain.waterfall_ops import (
    evaluate_budget_waterfall as _evaluate_budget_waterfall_impl,
    evaluate_entitlement_waterfall as _evaluate_entitlement_waterfall_impl,
    mode_violation_decision as _mode_violation_decision_impl,
    mode_violation_reason_suffix as _mode_violation_reason_suffix_impl,
)


class EnforcementServicePrivateCreditTokenOps:
    db: Any

    async def _get_credit_headrooms(
        self,
        *,
        tenant_id: UUID,
        scope_key: str,
        now: datetime,
    ) -> tuple[Decimal, Decimal]:
        return await _get_credit_headrooms_impl(
            db=self.db,
            tenant_id=tenant_id,
            scope_key=scope_key,
            now=now,
            quantize_fn=self._quantize_value,
            to_decimal_fn=self._to_decimal_value,
            as_utc_fn=_as_utc,
        )

    async def _get_active_credit_headroom(
        self,
        *,
        tenant_id: UUID,
        scope_key: str,
        now: datetime,
    ) -> Decimal:
        reserved_headroom, emergency_headroom = await self._get_credit_headrooms(
            tenant_id=tenant_id,
            scope_key=scope_key,
            now=now,
        )
        return self._quantize_value(reserved_headroom + emergency_headroom, "0.0001")

    async def _reserve_credit_for_decision(
        self,
        *,
        tenant_id: UUID,
        decision_id: UUID,
        scope_key: str,
        reserve_reserved_credit_usd: Decimal,
        reserve_emergency_credit_usd: Decimal,
        now: datetime,
    ) -> list[dict[str, str]]:
        return await _reserve_credit_for_decision_impl(
            tenant_id=tenant_id,
            decision_id=decision_id,
            scope_key=scope_key,
            reserve_reserved_credit_usd=reserve_reserved_credit_usd,
            reserve_emergency_credit_usd=reserve_emergency_credit_usd,
            now=now,
            reserve_credit_from_grants_fn=self._reserve_credit_from_grants,
            quantize_fn=self._quantize_value,
            to_decimal_fn=self._to_decimal_value,
        )

    async def _reserve_credit_from_grants(
        self,
        *,
        tenant_id: UUID,
        decision_id: UUID,
        scope_key: str,
        pool_type: EnforcementCreditPoolType,
        reserve_target_usd: Decimal,
        now: datetime,
    ) -> list[dict[str, str]]:
        return await _reserve_credit_from_grants_impl(
            db=self.db,
            tenant_id=tenant_id,
            decision_id=decision_id,
            scope_key=scope_key,
            pool_type=pool_type,
            reserve_target_usd=reserve_target_usd,
            now=now,
            quantize_fn=self._quantize_value,
            to_decimal_fn=self._to_decimal_value,
        )

    async def _settle_credit_reservations_for_decision(
        self,
        *,
        tenant_id: UUID,
        decision: EnforcementDecision,
        consumed_credit_usd: Decimal,
        now: datetime,
    ) -> list[dict[str, str]]:
        return await _settle_credit_reservations_for_decision_impl(
            db=self.db,
            tenant_id=tenant_id,
            decision=decision,
            consumed_credit_usd=consumed_credit_usd,
            now=now,
            quantize_fn=self._quantize_value,
            to_decimal_fn=self._to_decimal_value,
            as_utc_fn=_as_utc,
        )

    def _mode_violation_decision(self, mode: EnforcementMode) -> EnforcementDecisionType:
        return cast(
            EnforcementDecisionType,
            _mode_violation_decision_impl(
                mode=mode,
                shadow_mode=EnforcementMode.SHADOW,
                soft_mode=EnforcementMode.SOFT,
                shadow_decision=EnforcementDecisionType.ALLOW,
                soft_decision=EnforcementDecisionType.REQUIRE_APPROVAL,
                hard_decision=EnforcementDecisionType.DENY,
            ),
        )

    def _mode_violation_reason_suffix(self, mode: EnforcementMode, *, subject: str) -> str:
        return _mode_violation_reason_suffix_impl(
            mode=mode,
            subject=subject,
            shadow_mode=EnforcementMode.SHADOW,
            soft_mode=EnforcementMode.SOFT,
        )

    def _evaluate_entitlement_waterfall(
        self,
        *,
        mode: EnforcementMode,
        monthly_delta: Decimal,
        plan_headroom: Decimal | None,
        allocation_headroom: Decimal | None,
        reserved_credit_headroom: Decimal,
        emergency_credit_headroom: Decimal,
        enterprise_headroom: Decimal | None,
    ) -> EntitlementWaterfallResult:
        payload = _evaluate_entitlement_waterfall_impl(
            mode=mode,
            monthly_delta=monthly_delta,
            plan_headroom=plan_headroom,
            allocation_headroom=allocation_headroom,
            reserved_credit_headroom=reserved_credit_headroom,
            emergency_credit_headroom=emergency_credit_headroom,
            enterprise_headroom=enterprise_headroom,
            quantize_fn=self._quantize_value,
            to_decimal_fn=self._to_decimal_value,
            mode_violation_decision_fn=self._mode_violation_decision,
            allow_decision=EnforcementDecisionType.ALLOW,
            allow_with_credits_decision=EnforcementDecisionType.ALLOW_WITH_CREDITS,
            soft_mode=EnforcementMode.SOFT,
        )
        return EntitlementWaterfallResult(**payload)

    def _evaluate_budget_waterfall(
        self,
        *,
        mode: EnforcementMode,
        monthly_delta: Decimal,
        allocation_headroom: Decimal | None,
        credits_headroom: Decimal,
        reasons: list[str],
    ) -> tuple[EnforcementDecisionType, Decimal, Decimal]:
        return _evaluate_budget_waterfall_impl(
            mode=mode,
            monthly_delta=monthly_delta,
            allocation_headroom=allocation_headroom,
            credits_headroom=credits_headroom,
            reasons=reasons,
            evaluate_entitlement_waterfall_fn=self._evaluate_entitlement_waterfall,
            shadow_mode=EnforcementMode.SHADOW,
            soft_mode=EnforcementMode.SOFT,
        )

    _load_approval_with_decision = _load_approval_with_decision_impl
    _assert_pending = _assert_pending_impl

    def _decode_approval_token(self, approval_token: str) -> Mapping[str, Any]:
        service = cast(Any, self)
        return _decode_approval_token_impl(
            approval_token,
            get_settings_fn=service._get_runtime_settings,
            jwt_module=service._jwt_module(),
        )

    def _extract_token_context(
        self,
        payload: Mapping[str, Any],
    ) -> ApprovalTokenContext:
        context_payload = _extract_token_context_payload_impl(
            payload,
            source_enum=EnforcementSource,
            quantize_fn=self._quantize_value,
            to_decimal_fn=self._to_decimal_value,
        )
        return ApprovalTokenContext(**context_payload)

    def _build_approval_token(
        self,
        *,
        decision: EnforcementDecision,
        approval: EnforcementApprovalRequest,
        expires_at: datetime,
    ) -> str:
        service = cast(Any, self)
        return _build_approval_token_impl(
            decision=decision,
            approval=approval,
            expires_at=expires_at,
            get_settings_fn=service._get_runtime_settings,
            utcnow_fn=_utcnow,
            to_decimal_fn=self._to_decimal_value,
            jwt_module=service._jwt_module(),
        )

    def _quantize_value(self, value: Decimal, quantum: str) -> Decimal:
        return _quantize(value, quantum)

    def _to_decimal_value(
        self,
        value: Any,
        default: Decimal = Decimal("0"),
    ) -> Decimal:
        return _to_decimal(value, default=default)
