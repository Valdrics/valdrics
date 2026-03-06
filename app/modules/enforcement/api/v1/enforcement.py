from __future__ import annotations

import asyncio
from decimal import Decimal
import time

from fastapi import APIRouter, Depends, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.enforcement import EnforcementSource
from app.modules.enforcement.api.v1.actions import router as actions_router
from app.modules.enforcement.api.v1.approvals import router as approvals_router
from app.modules.enforcement.api.v1.common import (
    require_features_or_403,
    tenant_or_403,
)
from app.modules.enforcement.api.v1.enforcement_gate_ops import (
    _annotation_decimal,
    _build_cloud_event_gate_input,
    _build_gate_input,
    _enforcement_global_gate_limit as _enforcement_global_gate_limit_impl,
    _extract_k8s_labels_annotations,
    _gate_timeout_seconds as _gate_timeout_seconds_impl,
    _http_detail_mapping,
    _lock_failure_reason_from_http_exception,
    _metric_reason,
    _run_gate_input_impl,
)
from app.modules.enforcement.api.v1.exports import router as exports_router
from app.modules.enforcement.api.v1.ledger import router as ledger_router
from app.modules.enforcement.api.v1.policy_budget_credit import (
    router as policy_budget_credit_router,
)
from app.modules.enforcement.api.v1.reservations import router as reservations_router
from app.modules.enforcement.api.v1.schemas import (
    CloudEventGateRequest,
    GateDecisionResponse,
    GateRequest,
    K8sAdmissionReviewPayload,
    K8sAdmissionReviewResponse,
    K8sAdmissionReviewResult,
    K8sAdmissionReviewStatus,
    TerraformPreflightBinding,
    TerraformPreflightContinuation,
    TerraformPreflightRequest,
    TerraformPreflightResponse,
)
from app.modules.enforcement.domain.service import EnforcementService, gate_result_to_response
from app.modules.enforcement.domain.service_models import GateInput
from app.shared.core.auth import CurrentUser, requires_role_with_db_context
from app.shared.core.config import get_settings
from app.shared.core.ops_metrics import (
    ENFORCEMENT_GATE_DECISION_REASONS_TOTAL,
    ENFORCEMENT_GATE_DECISIONS_TOTAL,
    ENFORCEMENT_GATE_FAILURES_TOTAL,
    ENFORCEMENT_GATE_LATENCY_SECONDS,
)
from app.shared.core.pricing import FeatureFlag
from app.shared.core.rate_limit import global_rate_limit, rate_limit
from app.shared.db.session import get_db

router = APIRouter(tags=["Enforcement"])
logger = structlog.get_logger()
ENFORCEMENT_GATE_EVALUATION_RECOVERABLE_EXCEPTIONS = (
    SQLAlchemyError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)


def _gate_timeout_seconds() -> float:
    return _gate_timeout_seconds_impl(get_settings_fn=get_settings)


def _enforcement_global_gate_limit(request: Request) -> str:
    return _enforcement_global_gate_limit_impl(request, get_settings_fn=get_settings)


async def _run_gate_input(
    *,
    source: EnforcementSource,
    gate_input: GateInput,
    expected_request_fingerprint: str | None,
    current_user: CurrentUser,
    db: AsyncSession,
) -> GateDecisionResponse:
    return await _run_gate_input_impl(
        source=source,
        gate_input=gate_input,
        expected_request_fingerprint=expected_request_fingerprint,
        current_user=current_user,
        db=db,
        tenant_or_403_fn=tenant_or_403,
        enforcement_service_cls=EnforcementService,
        gate_result_to_response_fn=gate_result_to_response,
        gate_timeout_seconds_fn=_gate_timeout_seconds,
        lock_failure_reason_from_http_exception_fn=_lock_failure_reason_from_http_exception,
        http_detail_mapping_fn=_http_detail_mapping,
        metric_reason_fn=_metric_reason,
        gate_evaluation_recoverable_exceptions=ENFORCEMENT_GATE_EVALUATION_RECOVERABLE_EXCEPTIONS,
        gate_decisions_total_metric=ENFORCEMENT_GATE_DECISIONS_TOTAL,
        gate_decision_reasons_total_metric=ENFORCEMENT_GATE_DECISION_REASONS_TOTAL,
        gate_failures_total_metric=ENFORCEMENT_GATE_FAILURES_TOTAL,
        gate_latency_seconds_metric=ENFORCEMENT_GATE_LATENCY_SECONDS,
        logger_obj=logger,
        wait_for_fn=asyncio.wait_for,
        perf_counter_fn=time.perf_counter,
    )


async def _run_gate(
    *,
    request: Request,
    payload: GateRequest,
    source: EnforcementSource,
    current_user: CurrentUser,
    db: AsyncSession,
) -> GateDecisionResponse:
    idempotency_header = request.headers.get("Idempotency-Key")
    gate_input = _build_gate_input(
        payload=payload,
        idempotency_key=(idempotency_header or payload.idempotency_key),
    )
    return await _run_gate_input(
        source=source,
        gate_input=gate_input,
        expected_request_fingerprint=None,
        current_user=current_user,
        db=db,
    )


@router.post("/gate/terraform", response_model=GateDecisionResponse)
@global_rate_limit(_enforcement_global_gate_limit, namespace="enforcement_gate")
@rate_limit("120/minute")
async def gate_terraform(
    request: Request,
    payload: GateRequest,
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
    db: AsyncSession = Depends(get_db),
) -> GateDecisionResponse:
    await require_features_or_403(
        user=current_user,
        db=db,
        features=(FeatureFlag.API_ACCESS, FeatureFlag.POLICY_CONFIGURATION),
    )
    return await _run_gate(
        request=request,
        payload=payload,
        source=EnforcementSource.TERRAFORM,
        current_user=current_user,
        db=db,
    )


@router.post("/gate/k8s/admission", response_model=GateDecisionResponse)
@global_rate_limit(_enforcement_global_gate_limit, namespace="enforcement_gate")
@rate_limit("120/minute")
async def gate_k8s_admission(
    request: Request,
    payload: GateRequest,
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
    db: AsyncSession = Depends(get_db),
) -> GateDecisionResponse:
    await require_features_or_403(
        user=current_user,
        db=db,
        features=(FeatureFlag.API_ACCESS, FeatureFlag.POLICY_CONFIGURATION),
    )
    return await _run_gate(
        request=request,
        payload=payload,
        source=EnforcementSource.K8S_ADMISSION,
        current_user=current_user,
        db=db,
    )


@router.post("/gate/terraform/preflight", response_model=TerraformPreflightResponse)
@global_rate_limit(_enforcement_global_gate_limit, namespace="enforcement_gate")
@rate_limit("120/minute")
async def gate_terraform_preflight(
    request: Request,
    payload: TerraformPreflightRequest,
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
    db: AsyncSession = Depends(get_db),
) -> TerraformPreflightResponse:
    await require_features_or_403(
        user=current_user,
        db=db,
        features=(FeatureFlag.API_ACCESS, FeatureFlag.POLICY_CONFIGURATION),
    )
    idempotency_header = request.headers.get("Idempotency-Key")
    default_idempotency_key = f"terraform:{payload.run_id}:{payload.stage}"[:128]
    gate_metadata = {
        **dict(payload.metadata or {}),
        "terraform_run_id": payload.run_id,
        "terraform_stage": payload.stage,
    }
    if payload.workspace_id:
        gate_metadata["terraform_workspace_id"] = payload.workspace_id
    if payload.workspace_name:
        gate_metadata["terraform_workspace_name"] = payload.workspace_name
    if payload.callback_url:
        gate_metadata["terraform_callback_url"] = payload.callback_url
    if payload.run_url:
        gate_metadata["terraform_run_url"] = payload.run_url

    gate_input = GateInput(
        project_id=str(payload.project_id).strip().lower() or "default",
        environment=payload.environment,
        action=str(payload.action).strip().lower(),
        resource_reference=str(payload.resource_reference).strip(),
        estimated_monthly_delta_usd=payload.estimated_monthly_delta_usd,
        estimated_hourly_delta_usd=payload.estimated_hourly_delta_usd,
        metadata=gate_metadata,
        idempotency_key=(
            idempotency_header or payload.idempotency_key or default_idempotency_key
        ),
        dry_run=bool(payload.dry_run),
    )

    gate_response = await _run_gate_input(
        source=EnforcementSource.TERRAFORM,
        gate_input=gate_input,
        expected_request_fingerprint=payload.expected_request_fingerprint,
        current_user=current_user,
        db=db,
    )
    binding = TerraformPreflightBinding(
        expected_source=EnforcementSource.TERRAFORM,
        expected_project_id=gate_input.project_id,
        expected_environment=gate_input.environment,
        expected_request_fingerprint=gate_response.request_fingerprint,
        expected_resource_reference=gate_input.resource_reference,
    )
    continuation = TerraformPreflightContinuation(
        approval_consume_endpoint="/api/v1/enforcement/approvals/consume",
        binding=binding,
    )
    return TerraformPreflightResponse(
        run_id=payload.run_id,
        stage=payload.stage,
        decision=gate_response.decision,
        reason_codes=list(gate_response.reason_codes or []),
        decision_id=gate_response.decision_id,
        policy_version=gate_response.policy_version,
        approval_required=gate_response.approval_required,
        approval_request_id=gate_response.approval_request_id,
        approval_token_contract=gate_response.approval_token_contract,
        ttl_seconds=gate_response.ttl_seconds,
        request_fingerprint=gate_response.request_fingerprint,
        reservation_active=gate_response.reservation_active,
        computed_context=gate_response.computed_context,
        continuation=continuation,
    )


@router.post("/gate/k8s/admission/review", response_model=K8sAdmissionReviewResponse)
@global_rate_limit(_enforcement_global_gate_limit, namespace="enforcement_gate")
@rate_limit("120/minute")
async def gate_k8s_admission_review(
    request: Request,
    payload: K8sAdmissionReviewPayload,
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
    db: AsyncSession = Depends(get_db),
) -> K8sAdmissionReviewResponse:
    await require_features_or_403(
        user=current_user,
        db=db,
        features=(FeatureFlag.API_ACCESS, FeatureFlag.POLICY_CONFIGURATION),
    )
    review_request = payload.request
    labels, annotations, metadata_name, metadata_namespace = _extract_k8s_labels_annotations(
        review_request.obj
    )
    namespace = (
        str(review_request.namespace or "").strip()
        or metadata_namespace
        or "default"
    )
    name = str(review_request.name or "").strip() or metadata_name or "unnamed"
    project_id = (
        str(
            annotations.get("valdrics.io/project-id")
            or labels.get("valdrics.io/project-id")
            or namespace
        )
        .strip()
        .lower()
        or "default"
    )
    environment = (
        str(
            annotations.get("valdrics.io/environment")
            or labels.get("valdrics.io/environment")
            or "nonprod"
        )
        .strip()
        .lower()
        or "nonprod"
    )
    resource_type = str(review_request.resource.resource).strip().lower()
    action = f"admission.{review_request.operation.lower()}"
    resource_reference = f"{resource_type}/{namespace}/{name}"
    estimated_monthly_delta_usd = _annotation_decimal(
        annotations,
        key="valdrics.io/estimated-monthly-delta-usd",
        default=Decimal("0"),
    )
    estimated_hourly_delta_usd = _annotation_decimal(
        annotations,
        key="valdrics.io/estimated-hourly-delta-usd",
        default=Decimal("0"),
    )
    gate_input = GateInput(
        project_id=project_id,
        environment=environment,
        action=action,
        resource_reference=resource_reference,
        estimated_monthly_delta_usd=estimated_monthly_delta_usd,
        estimated_hourly_delta_usd=estimated_hourly_delta_usd,
        metadata={
            "resource_type": str(review_request.kind.kind).strip().lower(),
            "admission_operation": review_request.operation,
            "admission_namespace": namespace,
            "admission_name": name,
            "admission_labels": labels,
            "admission_annotations": annotations,
            "admission_kind": review_request.kind.kind,
            "admission_resource": review_request.resource.resource,
            "admission_user": str(review_request.user_info.get("username") or ""),
        },
        idempotency_key=(request.headers.get("Idempotency-Key") or review_request.uid),
        dry_run=bool(review_request.dry_run),
    )
    gate_response = await _run_gate_input(
        source=EnforcementSource.K8S_ADMISSION,
        gate_input=gate_input,
        expected_request_fingerprint=None,
        current_user=current_user,
        db=db,
    )
    decision = str(gate_response.decision).strip().upper()
    allowed = decision in {"ALLOW", "ALLOW_WITH_CREDITS"}
    reason_codes = [
        str(reason).strip().lower() for reason in gate_response.reason_codes or []
    ]

    status: K8sAdmissionReviewStatus | None = None
    if not allowed:
        status = K8sAdmissionReviewStatus(
            code=403,
            reason="Forbidden",
            message=(
                f"Valdrics admission decision={decision}; "
                f"reason_codes={','.join(reason_codes) or 'none'}"
            ),
        )

    response = K8sAdmissionReviewResult(
        uid=review_request.uid,
        allowed=allowed,
        status=status,
        warnings=[f"valdrics:{reason}" for reason in reason_codes[:8]],
        audit_annotations={
            "valdrics.io/decision-id": str(gate_response.decision_id),
            "valdrics.io/decision": decision,
            "valdrics.io/policy-version": str(gate_response.policy_version),
            "valdrics.io/request-fingerprint": gate_response.request_fingerprint,
            "valdrics.io/approval-required": str(
                bool(gate_response.approval_required)
            ).lower(),
            "valdrics.io/approval-request-id": (
                str(gate_response.approval_request_id)
                if gate_response.approval_request_id is not None
                else ""
            ),
        },
    )
    return K8sAdmissionReviewResponse(
        api_version=payload.api_version,
        kind="AdmissionReview",
        response=response,
    )


@router.post("/gate/cloud-event", response_model=GateDecisionResponse)
@global_rate_limit(_enforcement_global_gate_limit, namespace="enforcement_gate")
@rate_limit("120/minute")
async def gate_cloud_event(
    request: Request,
    payload: CloudEventGateRequest,
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
    db: AsyncSession = Depends(get_db),
) -> GateDecisionResponse:
    await require_features_or_403(
        user=current_user,
        db=db,
        features=(FeatureFlag.API_ACCESS, FeatureFlag.POLICY_CONFIGURATION),
    )
    idempotency_header = request.headers.get("Idempotency-Key")
    cloud_event_default_idempotency = f"cloudevent:{payload.cloud_event.id}"[:128]
    gate_input = _build_cloud_event_gate_input(
        payload=payload,
        idempotency_key=(
            idempotency_header
            or payload.idempotency_key
            or cloud_event_default_idempotency
        ),
    )
    return await _run_gate_input(
        source=EnforcementSource.CLOUD_EVENT,
        gate_input=gate_input,
        expected_request_fingerprint=payload.expected_request_fingerprint,
        current_user=current_user,
        db=db,
    )


router.include_router(policy_budget_credit_router)
router.include_router(approvals_router)
router.include_router(reservations_router)
router.include_router(actions_router)
router.include_router(exports_router)
router.include_router(ledger_router)
