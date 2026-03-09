from typing import Any, Mapping

from app.modules.enforcement.domain.service_models import GateEvaluationResult

APPROVAL_TOKEN_CONTRACT = (
    "approval_flow_only"  # nosec B105 - public API contract label
)


def gate_result_to_response(
    result: GateEvaluationResult,
) -> Mapping[str, Any]:
    decision = result.decision
    approval = result.approval
    response_payload = (
        decision.response_payload
        if isinstance(decision.response_payload, dict)
        else {}
    )
    computed_context = response_payload.get("computed_context")

    return {
        "decision": decision.decision.value,
        "reason_codes": list(decision.reason_codes or []),
        "decision_id": decision.id,
        "policy_version": int(decision.policy_version),
        "approval_required": bool(decision.approval_required),
        "approval_request_id": approval.id if approval is not None else None,
        "approval_token": result.approval_token,
        "approval_token_contract": APPROVAL_TOKEN_CONTRACT,
        "ttl_seconds": int(result.ttl_seconds),
        "request_fingerprint": decision.request_fingerprint,
        "reservation_active": bool(decision.reservation_active),
        "computed_context": (
            computed_context if isinstance(computed_context, dict) else None
        ),
    }
