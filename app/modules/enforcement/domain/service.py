from __future__ import annotations

import asyncio  # noqa: F401
from decimal import Decimal
import hashlib  # noqa: F401
import time  # noqa: F401
from typing import Any, Mapping, cast
from uuid import UUID

import jwt
import structlog
from sqlalchemy.exc import IntegrityError, SQLAlchemyError  # noqa: F401
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enforcement import (
    EnforcementMode,
    EnforcementPolicy,
    EnforcementSource,
)
from app.modules.enforcement.domain.policy_document import (
    POLICY_DOCUMENT_SCHEMA_VERSION,  # noqa: F401
    PolicyDocument,  # noqa: F401
    PolicyDocumentEntitlementMatrix,  # noqa: F401
    canonical_policy_document_payload,  # noqa: F401
    policy_document_sha256,  # noqa: F401
)
from app.modules.enforcement.domain.runtime_query_ops import (
    get_approval_by_decision as _get_approval_by_decision_impl,
    get_decision_by_idempotency as _get_decision_by_idempotency_impl,
    get_effective_budget as _get_effective_budget_impl,
    get_reserved_totals as _get_reserved_totals_impl,
)
from app.modules.enforcement.domain.gate_evaluation_ops import (
    evaluate_gate as _evaluate_gate_impl,
    resolve_fail_safe_gate as _resolve_fail_safe_gate_impl,
)
from app.modules.enforcement.domain.reconciliation_flow_ops import (
    reconcile_overdue_reservations as _reconcile_overdue_reservations_impl,
    reconcile_reservation as _reconcile_reservation_impl,
)
from app.modules.enforcement.domain.policy_contract_ops import (
    get_or_create_policy as _get_or_create_policy_impl,
    update_policy as _update_policy_impl,
)
from app.modules.enforcement.domain.service_approval_ops import (
    EnforcementServiceApprovalOps,
)
from app.modules.enforcement.domain.service_private_ops import (
    EnforcementServicePrivateOps,
)
from app.modules.enforcement.domain.service_runtime_ops import (
    acquire_gate_evaluation_lock as _acquire_gate_evaluation_lock_impl,
    append_decision_ledger_entry as _append_decision_ledger_entry_impl,
    build_export_bundle as _build_export_bundle_impl,
    build_reservation_reconciliation_idempotent_replay as _build_reservation_reconciliation_idempotent_replay_impl,
    build_signed_export_manifest as _build_signed_export_manifest_impl,
    list_active_reservations as _list_active_reservations_impl,
    list_decision_ledger as _list_decision_ledger_impl,
    list_reconciliation_exceptions as _list_reconciliation_exceptions_impl,
    render_approvals_csv as _render_approvals_csv_runtime_impl,
    render_decisions_csv as _render_decisions_csv_runtime_impl,
    resolve_export_manifest_signing_key_id as _resolve_export_manifest_signing_key_id_runtime_impl,
    resolve_export_manifest_signing_secret as _resolve_export_manifest_signing_secret_runtime_impl,
)
from app.modules.enforcement.domain.service_models import (
    GateEvaluationResult,
    GateInput,
    OverdueReservationReconciliationResult,
    ReservationReconciliationResult,
)
from app.modules.enforcement.domain.service_gate_lock_ops import (
    gate_lock_timeout_seconds as _gate_lock_timeout_seconds_impl,
)
from app.modules.enforcement.domain.service_response_ops import (
    gate_result_to_response,  # noqa: F401
)
from app.modules.enforcement.domain.service_utils import (
    _computed_context_snapshot,  # noqa: F401
    _default_required_permission_for_environment,  # noqa: F401
    _is_production_environment,
    _json_default,  # noqa: F401
    _month_bounds,
    _normalize_allowed_reviewer_roles,  # noqa: F401
    _normalize_environment,
    _normalize_policy_document_schema_version,
    _normalize_policy_document_sha256,
    _normalize_string_list,  # noqa: F401
    _parse_iso_datetime,  # noqa: F401
    _payload_sha256,  # noqa: F401
    _quantize,
    _sanitize_csv_cell,  # noqa: F401
    _stable_fingerprint,
    _to_decimal,
    _unique_reason_codes,
    _iso_or_empty,  # noqa: F401
    _utcnow,
)
from app.shared.core.approval_permissions import user_has_approval_permission
from app.shared.core.config import get_settings
from app.shared.core.pricing import PricingTier, get_tenant_tier, get_tier_limit  # noqa: F401
from app.shared.core.ops_metrics import (
    ENFORCEMENT_EXPORT_EVENTS_TOTAL,  # noqa: F401
    ENFORCEMENT_RESERVATION_DRIFT_USD_TOTAL,
    ENFORCEMENT_RESERVATION_RECONCILIATIONS_TOTAL,
)
from app.shared.core.ops_metrics import (  # noqa: F401
    ENFORCEMENT_GATE_LOCK_EVENTS_TOTAL,
    ENFORCEMENT_GATE_LOCK_WAIT_SECONDS,
)


logger = structlog.get_logger()


def _gate_lock_timeout_seconds() -> float:
    return _gate_lock_timeout_seconds_impl(get_settings_fn=get_settings)


class EnforcementService(EnforcementServiceApprovalOps, EnforcementServicePrivateOps):
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_runtime_settings(self) -> Any:
        return get_settings()

    async def _check_user_has_approval_permission(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        return await user_has_approval_permission(*args, **kwargs)

    def _jwt_module(self) -> Any:
        return jwt

    def _quantize_value(self, value: Decimal, quantum: str) -> Decimal:
        return _quantize(value, quantum)

    def _to_decimal_value(
        self,
        value: Any,
        default: Decimal = Decimal("0"),
    ) -> Decimal:
        return _to_decimal(value, default=default)

    def compute_request_fingerprint(
        self,
        *,
        source: EnforcementSource,
        gate_input: GateInput,
    ) -> str:
        return _stable_fingerprint(source, gate_input)

    async def get_or_create_policy(self, tenant_id: UUID) -> EnforcementPolicy:
        return await _get_or_create_policy_impl(
            db=self.db,
            tenant_id=tenant_id,
            policy_document_contract_backfill_required_fn=(
                self._policy_document_contract_backfill_required
            ),
            materialize_policy_contract_fn=self._materialize_policy_contract,
            apply_policy_contract_materialization_fn=(
                self._apply_policy_contract_materialization
            ),
            to_decimal_fn=_to_decimal,
        )

    async def update_policy(
        self,
        *,
        tenant_id: UUID,
        terraform_mode: EnforcementMode,
        terraform_mode_prod: EnforcementMode | None = None,
        terraform_mode_nonprod: EnforcementMode | None = None,
        k8s_admission_mode: EnforcementMode,
        k8s_admission_mode_prod: EnforcementMode | None = None,
        k8s_admission_mode_nonprod: EnforcementMode | None = None,
        require_approval_for_prod: bool,
        require_approval_for_nonprod: bool,
        plan_monthly_ceiling_usd: Decimal | None = None,
        enterprise_monthly_ceiling_usd: Decimal | None = None,
        auto_approve_below_monthly_usd: Decimal,
        hard_deny_above_monthly_usd: Decimal,
        default_ttl_seconds: int,
        enforce_prod_requester_reviewer_separation: bool = True,
        enforce_nonprod_requester_reviewer_separation: bool = False,
        approval_routing_rules: list[Mapping[str, Any]] | None = None,
        policy_document: Mapping[str, Any] | None = None,
    ) -> EnforcementPolicy:
        return await _update_policy_impl(
            db=self.db,
            tenant_id=tenant_id,
            terraform_mode=terraform_mode,
            terraform_mode_prod=terraform_mode_prod,
            terraform_mode_nonprod=terraform_mode_nonprod,
            k8s_admission_mode=k8s_admission_mode,
            k8s_admission_mode_prod=k8s_admission_mode_prod,
            k8s_admission_mode_nonprod=k8s_admission_mode_nonprod,
            require_approval_for_prod=require_approval_for_prod,
            require_approval_for_nonprod=require_approval_for_nonprod,
            plan_monthly_ceiling_usd=plan_monthly_ceiling_usd,
            enterprise_monthly_ceiling_usd=enterprise_monthly_ceiling_usd,
            auto_approve_below_monthly_usd=auto_approve_below_monthly_usd,
            hard_deny_above_monthly_usd=hard_deny_above_monthly_usd,
            default_ttl_seconds=default_ttl_seconds,
            enforce_prod_requester_reviewer_separation=(
                enforce_prod_requester_reviewer_separation
            ),
            enforce_nonprod_requester_reviewer_separation=(
                enforce_nonprod_requester_reviewer_separation
            ),
            approval_routing_rules=approval_routing_rules,
            policy_document=policy_document,
            get_or_create_policy_fn=self.get_or_create_policy,
            materialize_policy_contract_fn=self._materialize_policy_contract,
            apply_policy_contract_materialization_fn=(
                self._apply_policy_contract_materialization
            ),
        )

    async def evaluate_gate(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        source: EnforcementSource,
        gate_input: GateInput,
    ) -> GateEvaluationResult:
        return cast(
            GateEvaluationResult,
            await _evaluate_gate_impl(
                service=self,
                tenant_id=tenant_id,
                actor_id=actor_id,
                source=source,
                gate_input=gate_input,
                gate_evaluation_result_cls=GateEvaluationResult,
                stable_fingerprint_fn=_stable_fingerprint,
                normalize_environment_fn=_normalize_environment,
                month_bounds_fn=_month_bounds,
                quantize_fn=_quantize,
                to_decimal_fn=_to_decimal,
                is_production_environment_fn=_is_production_environment,
                unique_reason_codes_fn=_unique_reason_codes,
                normalize_policy_document_schema_version_fn=(
                    _normalize_policy_document_schema_version
                ),
                normalize_policy_document_sha256_fn=_normalize_policy_document_sha256,
                utcnow_fn=_utcnow,
            ),
        )

    async def resolve_fail_safe_gate(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        source: EnforcementSource,
        gate_input: GateInput,
        failure_reason_code: str,
        failure_metadata: Mapping[str, Any] | None = None,
    ) -> GateEvaluationResult:
        return cast(
            GateEvaluationResult,
            await _resolve_fail_safe_gate_impl(
                service=self,
                tenant_id=tenant_id,
                actor_id=actor_id,
                source=source,
                gate_input=gate_input,
                failure_reason_code=failure_reason_code,
                failure_metadata=failure_metadata,
                gate_evaluation_result_cls=GateEvaluationResult,
                stable_fingerprint_fn=_stable_fingerprint,
                normalize_environment_fn=_normalize_environment,
                quantize_fn=_quantize,
                mode_violation_decision_fn=self._mode_violation_decision,
                is_production_environment_fn=_is_production_environment,
                unique_reason_codes_fn=_unique_reason_codes,
                normalize_policy_document_schema_version_fn=(
                    _normalize_policy_document_schema_version
                ),
                normalize_policy_document_sha256_fn=_normalize_policy_document_sha256,
                utcnow_fn=_utcnow,
            ),
        )

    list_active_reservations = _list_active_reservations_impl
    list_decision_ledger = _list_decision_ledger_impl
    list_reconciliation_exceptions = _list_reconciliation_exceptions_impl
    _build_reservation_reconciliation_idempotent_replay = (
        _build_reservation_reconciliation_idempotent_replay_impl
    )

    async def reconcile_reservation(
        self,
        *,
        tenant_id: UUID,
        decision_id: UUID,
        actor_id: UUID,
        actual_monthly_delta_usd: Decimal,
        notes: str | None,
        idempotency_key: str | None = None,
    ) -> ReservationReconciliationResult:
        return cast(
            ReservationReconciliationResult,
            await _reconcile_reservation_impl(
                service=self,
                tenant_id=tenant_id,
                decision_id=decision_id,
                actor_id=actor_id,
                actual_monthly_delta_usd=actual_monthly_delta_usd,
                notes=notes,
                idempotency_key=idempotency_key,
                reservation_reconciliation_result_cls=ReservationReconciliationResult,
                quantize_fn=_quantize,
                to_decimal_fn=_to_decimal,
                unique_reason_codes_fn=_unique_reason_codes,
                utcnow_fn=_utcnow,
                reservation_reconciliations_total_metric=(
                    ENFORCEMENT_RESERVATION_RECONCILIATIONS_TOTAL
                ),
                reservation_drift_usd_total_metric=(
                    ENFORCEMENT_RESERVATION_DRIFT_USD_TOTAL
                ),
            ),
        )

    async def reconcile_overdue_reservations(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        older_than_seconds: int,
        limit: int,
    ) -> OverdueReservationReconciliationResult:
        return cast(
            OverdueReservationReconciliationResult,
            await _reconcile_overdue_reservations_impl(
                service=self,
                tenant_id=tenant_id,
                actor_id=actor_id,
                older_than_seconds=older_than_seconds,
                limit=limit,
                overdue_reservation_reconciliation_result_cls=(
                    OverdueReservationReconciliationResult
                ),
                quantize_fn=_quantize,
                to_decimal_fn=_to_decimal,
                unique_reason_codes_fn=_unique_reason_codes,
                utcnow_fn=_utcnow,
                reservation_reconciliations_total_metric=(
                    ENFORCEMENT_RESERVATION_RECONCILIATIONS_TOTAL
                ),
            ),
        )

    build_export_bundle = _build_export_bundle_impl
    _resolve_export_manifest_signing_secret = (
        _resolve_export_manifest_signing_secret_runtime_impl
    )
    _resolve_export_manifest_signing_key_id = (
        _resolve_export_manifest_signing_key_id_runtime_impl
    )
    build_signed_export_manifest = _build_signed_export_manifest_impl
    _render_decisions_csv = _render_decisions_csv_runtime_impl
    _render_approvals_csv = _render_approvals_csv_runtime_impl
    _append_decision_ledger_entry = _append_decision_ledger_entry_impl

    _get_decision_by_idempotency = _get_decision_by_idempotency_impl
    _get_approval_by_decision = _get_approval_by_decision_impl
    _get_reserved_totals = _get_reserved_totals_impl
    _get_effective_budget = _get_effective_budget_impl

    def _gate_lock_timeout_seconds(self) -> float:
        return _gate_lock_timeout_seconds()

    _acquire_gate_evaluation_lock = _acquire_gate_evaluation_lock_impl
