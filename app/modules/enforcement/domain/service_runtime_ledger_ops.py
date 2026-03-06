from __future__ import annotations

from app.models.enforcement import (
    EnforcementApprovalRequest,
    EnforcementDecision,
    EnforcementDecisionLedger,
)
from app.modules.enforcement.domain.service_utils import (
    _normalize_policy_document_schema_version,
    _normalize_policy_document_sha256,
    _payload_sha256,
    _quantize,
    _to_decimal,
    _utcnow,
)


def append_decision_ledger_entry(
    service: object,
    *,
    decision_row: EnforcementDecision,
    approval_row: EnforcementApprovalRequest | None = None,
) -> None:
    reserved_total = _quantize(
        _to_decimal(decision_row.reserved_allocation_usd)
        + _to_decimal(decision_row.reserved_credit_usd),
        "0.0001",
    )
    ledger_entry = EnforcementDecisionLedger(
        tenant_id=decision_row.tenant_id,
        decision_id=decision_row.id,
        source=decision_row.source,
        environment=decision_row.environment,
        project_id=decision_row.project_id,
        action=decision_row.action,
        resource_reference=decision_row.resource_reference,
        decision=decision_row.decision,
        reason_codes=list(decision_row.reason_codes or []),
        policy_version=int(decision_row.policy_version),
        policy_document_schema_version=_normalize_policy_document_schema_version(
            decision_row.policy_document_schema_version
        ),
        policy_document_sha256=_normalize_policy_document_sha256(
            decision_row.policy_document_sha256
        ),
        request_fingerprint=decision_row.request_fingerprint,
        idempotency_key=decision_row.idempotency_key,
        estimated_monthly_delta_usd=_quantize(
            _to_decimal(decision_row.estimated_monthly_delta_usd),
            "0.0001",
        ),
        estimated_hourly_delta_usd=_quantize(
            _to_decimal(decision_row.estimated_hourly_delta_usd),
            "0.000001",
        ),
        burn_rate_daily_usd=(
            _quantize(_to_decimal(decision_row.burn_rate_daily_usd), "0.0001")
            if decision_row.burn_rate_daily_usd is not None
            else None
        ),
        forecast_eom_usd=(
            _quantize(_to_decimal(decision_row.forecast_eom_usd), "0.0001")
            if decision_row.forecast_eom_usd is not None
            else None
        ),
        risk_class=(
            str(decision_row.risk_class).strip().lower()
            if decision_row.risk_class is not None
            else None
        ),
        risk_score=(
            int(decision_row.risk_score)
            if decision_row.risk_score is not None
            else None
        ),
        anomaly_signal=(
            bool(decision_row.anomaly_signal)
            if decision_row.anomaly_signal is not None
            else None
        ),
        reserved_total_usd=reserved_total,
        approval_required=bool(decision_row.approval_required),
        approval_request_id=approval_row.id if approval_row is not None else None,
        approval_status=approval_row.status if approval_row is not None else None,
        request_payload_sha256=_payload_sha256(decision_row.request_payload or {}),
        response_payload_sha256=_payload_sha256(decision_row.response_payload or {}),
        created_by_user_id=decision_row.created_by_user_id,
        decision_created_at=decision_row.created_at or _utcnow(),
    )
    service.db.add(ledger_entry)
