from typing import Annotated, Dict, Any, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import NO_VALUE
import structlog

from app.shared.core.auth import CurrentUser, requires_role, require_tenant_access
from app.shared.db.session import get_db
from app.models.remediation import (
    RemediationRequest,
)
from app.modules.optimization.domain import ZombieService, RemediationService
from app.modules.optimization.api.v1.zombies_route_helpers import (
    DEFAULT_REGION_HINT as _DEFAULT_REGION_HINT,
    coerce_query_bool as _coerce_query_bool_impl,
    coerce_query_int as _coerce_query_int_impl,
    coerce_region_hint as _coerce_region_hint_impl,
    enforce_growth_nonprod_auto_remediation as _enforce_growth_nonprod_auto_remediation_impl,
    load_remediation_request_for_authorization as _load_remediation_request_for_authorization_impl,
    parse_remediation_action as _parse_remediation_action_impl,
    raise_if_failed_execution as _raise_if_failed_execution_impl,
    required_approval_permission as _required_approval_permission_impl,
)
from app.shared.core.dependencies import requires_feature
from app.shared.core.pricing import FeatureFlag
from app.shared.core.rate_limit import rate_limit
from app.shared.core.exceptions import ResourceNotFoundError, ValdricsException
from app.shared.core.provider import normalize_provider
from app.models.background_job import JobType
from app.modules.governance.domain.jobs.processor import enqueue_job
from app.shared.core.approval_permissions import (
    user_has_approval_permission,
)

router = APIRouter(tags=["Cloud Hygiene (Zombies)"])
logger = structlog.get_logger()
DEFAULT_REGION_HINT = _DEFAULT_REGION_HINT
REMEDIATION_EXECUTION_RECOVERABLE_EXCEPTIONS = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    ConnectionError,
    TypeError,
)

_coerce_region_hint = _coerce_region_hint_impl
_coerce_query_bool = _coerce_query_bool_impl
_coerce_query_int = _coerce_query_int_impl
_parse_remediation_action = _parse_remediation_action_impl
_raise_if_failed_execution = _raise_if_failed_execution_impl
_load_remediation_request_for_authorization = (
    _load_remediation_request_for_authorization_impl
)
_required_approval_permission = _required_approval_permission_impl


def _request_finding_status(request_row: RemediationRequest) -> str | None:
    finding = _request_loaded_finding(request_row)
    if finding is not None:
        return getattr(getattr(finding, "status", None), "value", None)
    snapshot = getattr(request_row, "finding_snapshot", None)
    if isinstance(snapshot, dict):
        value = str(snapshot.get("status") or "").strip()
        return value or None
    return None


def _request_finding_category(request_row: RemediationRequest) -> str | None:
    finding = _request_loaded_finding(request_row)
    if finding is not None:
        value = str(getattr(finding, "category", "") or "").strip()
        return value or None
    snapshot = getattr(request_row, "finding_snapshot", None)
    if isinstance(snapshot, dict):
        value = str(snapshot.get("category") or "").strip()
        return value or None
    return None


def _request_loaded_finding(request_row: RemediationRequest) -> Any | None:
    state = sa_inspect(request_row)
    attr_state = state.attrs.finding
    loaded_value = attr_state.loaded_value
    if loaded_value is NO_VALUE:
        return None
    return loaded_value


def _serialize_request_row(
    request_row: RemediationRequest,
    *,
    default_region: str,
    include_execution_fields: bool = False,
) -> dict[str, Any]:
    created_at = request_row.created_at
    payload: dict[str, Any] = {
        "id": str(request_row.id),
        "status": request_row.status.value,
        "resource_id": request_row.resource_id,
        "resource_type": request_row.resource_type,
        "action": request_row.action.value,
        "provider": normalize_provider(getattr(request_row, "provider", None))
        or "unknown",
        "region": getattr(request_row, "region", default_region),
        "connection_id": str(request_row.connection_id)
        if getattr(request_row, "connection_id", None)
        else None,
        "finding_id": str(request_row.finding_id)
        if getattr(request_row, "finding_id", None)
        else None,
        "finding_status": _request_finding_status(request_row),
        "finding_category": _request_finding_category(request_row),
        "estimated_savings": float(request_row.estimated_monthly_savings or 0),
        "created_at": created_at.isoformat() if created_at else None,
    }
    if include_execution_fields:
        executed_at = getattr(request_row, "executed_at", None)
        payload["executed_at"] = (
            executed_at.isoformat() if executed_at is not None else None
        )
        payload["execution_error"] = getattr(request_row, "execution_error", None)
    else:
        scheduled_execution_at = request_row.scheduled_execution_at
        payload["scheduled_execution_at"] = (
            scheduled_execution_at.isoformat()
            if scheduled_execution_at is not None
            else None
        )
        payload["escalation_required"] = bool(
            getattr(request_row, "escalation_required", False)
        )
        payload["escalation_reason"] = getattr(request_row, "escalation_reason", None)
        payload["escalated_at"] = (
            escalated_at.isoformat()
            if (escalated_at := getattr(request_row, "escalated_at", None))
            else None
        )
    return payload


class RemediationRequestCreate(BaseModel):
    finding_id: UUID
    action: str
    create_backup: bool = False
    backup_retention_days: int = 30
    backup_cost_estimate: float = 0
    parameters: Optional[Dict[str, Any]] = None


class ReviewRequest(BaseModel):
    notes: Optional[str] = None


class PolicyPreviewResponse(BaseModel):
    decision: str
    summary: str
    tier: str
    rule_hits: list[dict[str, Any]]
    config: dict[str, Any]


class PolicyPreviewCreate(BaseModel):
    finding_id: UUID
    action: str
    review_notes: str | None = None
    parameters: Optional[Dict[str, Any]] = None


async def _enforce_approval_permission(
    db: AsyncSession,
    *,
    user: CurrentUser,
    required_permission: str,
) -> None:
    if await user_has_approval_permission(db, user, required_permission):
        return
    raise HTTPException(
        status_code=403,
        detail=(
            "Insufficient permissions. "
            f"Required approval permission: {required_permission}"
        ),
    )


_enforce_growth_nonprod_auto_remediation = (
    _enforce_growth_nonprod_auto_remediation_impl
)

@router.get("")
@rate_limit("10/minute")
async def scan_zombies(
    request: Request,
    tenant_id: Annotated[UUID, Depends(require_tenant_access)],
    user: Annotated[CurrentUser, Depends(requires_role("member"))],
    db: AsyncSession = Depends(get_db),
    region: str = Query(default=DEFAULT_REGION_HINT),
    analyze: bool = Query(
        default=False, description="Enable AI-powered analysis of detected zombies"
    ),
    background: bool = Query(default=False, description="Run scan as a background job"),
) -> Any:
    region_hint = _coerce_region_hint(region)
    analyze_enabled = _coerce_query_bool(analyze, default=False)
    run_in_background = _coerce_query_bool(background, default=False)
    if run_in_background:
        logger.info(
            "enqueuing_zombie_scan",
            tenant_id=str(tenant_id),
            region=region_hint,
        )
        job = await enqueue_job(
            db=db,
            job_type=JobType.ZOMBIE_SCAN,
            tenant_id=tenant_id,
            payload={
                "region": region_hint,
                "analyze": analyze_enabled,
                "requested_by_user_id": str(user.id),
                "requested_client_ip": request.client.host if request.client else None,
            },
        )
        return {"status": "pending", "job_id": str(job.id)}

    service = ZombieService(db=db)
    return await service.scan_for_tenant(
        tenant_id=tenant_id,
        region=region_hint,
        analyze=analyze_enabled,
        requested_by_user_id=user.id,
        requested_client_ip=request.client.host if request.client else None,
    )


@router.post("/request")
async def create_remediation_request(
    request: RemediationRequestCreate,
    tenant_id: Annotated[UUID, Depends(require_tenant_access)],
    user: Annotated[
        CurrentUser, Depends(requires_feature(FeatureFlag.AUTO_REMEDIATION))
    ],
    db: AsyncSession = Depends(get_db),
    region: str = Query(default=DEFAULT_REGION_HINT),
) -> Dict[str, str]:
    """Create a remediation request. Requires Pro tier or higher."""
    region_hint = _coerce_region_hint(region)
    action_enum = _parse_remediation_action(request.action)

    service = RemediationService(db=db, region=region_hint)
    try:
        result = await service.create_request_from_finding(
            tenant_id=tenant_id,
            user_id=user.id,
            finding_id=request.finding_id,
            action=action_enum,
            create_backup=request.create_backup,
            backup_retention_days=request.backup_retention_days,
            backup_cost_estimate=request.backup_cost_estimate,
            parameters=request.parameters,
        )
    except ResourceNotFoundError:
        raise
    except ValdricsException:
        raise
    except ValueError as exc:
        raise ValdricsException(
            message=str(exc),
            code="remediation_request_invalid",
            status_code=400,
        ) from exc
    return {"status": "pending", "request_id": str(result.id)}


@router.get("/pending")
async def list_pending_requests(
    tenant_id: Annotated[UUID, Depends(require_tenant_access)],
    user: Annotated[CurrentUser, Depends(requires_role("member"))],
    db: AsyncSession = Depends(get_db),
    region: str = Query(default=DEFAULT_REGION_HINT),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    """List open remediation requests (approval + execution queue)."""
    region_hint = _coerce_region_hint(region)
    page_limit = _coerce_query_int(limit, default=50, minimum=1)
    page_offset = _coerce_query_int(offset, default=0, minimum=0)
    service = RemediationService(db=db, region=region_hint)
    pending = await service.list_pending(
        tenant_id,
        limit=page_limit,
        offset=page_offset,
    )
    return {
        "pending_count": len(pending),
        "requests": [
            _serialize_request_row(r, default_region=region_hint) for r in pending
        ],
    }


@router.get("/history")
async def list_remediation_history(
    tenant_id: Annotated[UUID, Depends(require_tenant_access)],
    user: Annotated[CurrentUser, Depends(requires_role("member"))],
    db: AsyncSession = Depends(get_db),
    region: str = Query(default=DEFAULT_REGION_HINT),
    status: str = Query(
        default="completed", pattern="^(completed|failed|rejected|cancelled|all)$"
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Dict[str, Any]:
    """List recent non-open remediation requests for an operator-facing history view."""
    region_hint = _coerce_region_hint(region)
    normalized_status = str(status or "completed").strip().lower()
    page_limit = _coerce_query_int(limit, default=20, minimum=1)
    page_offset = _coerce_query_int(offset, default=0, minimum=0)
    service = RemediationService(db=db, region=region_hint)
    try:
        history = await service.list_history(
            tenant_id,
            status=normalized_status,
            limit=page_limit,
            offset=page_offset,
        )
    except ValueError as exc:
        raise ValdricsException(
            message=str(exc),
            code="remediation_history_invalid_status",
            status_code=400,
        ) from exc

    return {
        "history_count": len(history),
        "status": normalized_status,
        "requests": [
            _serialize_request_row(
                request_row,
                default_region=region_hint,
                include_execution_fields=True,
            )
            for request_row in history
        ],
    }


@router.post("/approve/{request_id}")
async def approve_remediation(
    request_id: UUID,
    review: ReviewRequest,
    tenant_id: Annotated[UUID, Depends(require_tenant_access)],
    user: Annotated[CurrentUser, Depends(requires_role("member"))],
    db: AsyncSession = Depends(get_db),
    region: str = Query(default=DEFAULT_REGION_HINT),
) -> Dict[str, str]:
    """Approve a request with explicit remediation approval permission."""
    region_hint = _coerce_region_hint(region)
    remediation_request = await _load_remediation_request_for_authorization(
        db,
        request_id=request_id,
        tenant_id=tenant_id,
    )
    _enforce_growth_nonprod_auto_remediation(
        user=user,
        remediation_request=remediation_request,
    )
    required_permission = _required_approval_permission(remediation_request)
    await _enforce_approval_permission(
        db,
        user=user,
        required_permission=required_permission,
    )

    service = RemediationService(db=db, region=region_hint)
    try:
        result = await service.approve(
            request_id,
            tenant_id,
            user.id,
            notes=review.notes,
            reviewer_role=user.role.value
            if hasattr(user.role, "value")
            else str(user.role),
        )
        return {"status": "approved", "request_id": str(result.id)}
    except ValueError as e:
        raise ResourceNotFoundError(str(e), code="remediation_request_not_found")


@router.get(
    "/policy-preview/{request_id}",
    response_model=PolicyPreviewResponse,
)
async def preview_remediation_policy(
    request_id: UUID,
    tenant_id: Annotated[UUID, Depends(require_tenant_access)],
    user: Annotated[CurrentUser, Depends(requires_feature(FeatureFlag.POLICY_PREVIEW))],
    db: AsyncSession = Depends(get_db),
    region: str = Query(default=DEFAULT_REGION_HINT),
) -> PolicyPreviewResponse:
    """Preview deterministic remediation policy outcome before execution."""
    region_hint = _coerce_region_hint(region)
    service = RemediationService(db=db, region=region_hint)
    remediation_request = await service.get_by_id(
        RemediationRequest, request_id, tenant_id
    )
    if not remediation_request:
        raise ResourceNotFoundError(f"Remediation request {request_id} not found")
    preview = await service.preview_policy(remediation_request, tenant_id)
    return PolicyPreviewResponse(**preview)


@router.post(
    "/policy-preview",
    response_model=PolicyPreviewResponse,
)
async def preview_remediation_policy_payload(
    payload: PolicyPreviewCreate,
    tenant_id: Annotated[UUID, Depends(require_tenant_access)],
    user: Annotated[CurrentUser, Depends(requires_feature(FeatureFlag.POLICY_PREVIEW))],
    db: AsyncSession = Depends(get_db),
    region: str = Query(default=DEFAULT_REGION_HINT),
) -> PolicyPreviewResponse:
    """Preview deterministic policy outcome before a remediation request is created."""
    region_hint = _coerce_region_hint(region)
    action_enum = _parse_remediation_action(payload.action)

    service = RemediationService(db=db, region=region_hint)
    try:
        preview = await service.preview_policy_for_finding(
            tenant_id=tenant_id,
            user_id=user.id,
            finding_id=payload.finding_id,
            action=action_enum,
            review_notes=payload.review_notes,
            parameters=payload.parameters,
        )
    except ResourceNotFoundError:
        raise
    except ValdricsException:
        raise
    except ValueError as exc:
        raise ValdricsException(
            message=str(exc),
            code="remediation_policy_preview_invalid",
            status_code=400,
        ) from exc
    return PolicyPreviewResponse(**preview)


@router.post("/execute/{request_id}")
@rate_limit("50/hour")
async def execute_remediation(
    request: Request,
    request_id: UUID,
    tenant_id: Annotated[UUID, Depends(require_tenant_access)],
    user: Annotated[
        CurrentUser,
        Depends(requires_feature(FeatureFlag.AUTO_REMEDIATION, required_role="member")),
    ],
    db: AsyncSession = Depends(get_db),
    region: str = Query(default=DEFAULT_REGION_HINT),
    bypass_grace_period: bool = Query(
        default=False, description="Bypass 24h grace period (emergency use)"
    ),
) -> Dict[str, str]:
    """Execute a remediation request with explicit remediation approval permission."""
    region_hint = _coerce_region_hint(region)
    bypass_grace = _coerce_query_bool(bypass_grace_period, default=False)
    remediation_request = await _load_remediation_request_for_authorization(
        db,
        request_id=request_id,
        tenant_id=tenant_id,
    )
    _enforce_growth_nonprod_auto_remediation(
        user=user,
        remediation_request=remediation_request,
    )
    required_permission = _required_approval_permission(remediation_request)
    await _enforce_approval_permission(
        db,
        user=user,
        required_permission=required_permission,
    )

    service = RemediationService(db=db, region=region_hint)

    try:
        executed_request = await service.execute(
            request_id,
            tenant_id,
            bypass_grace_period=bypass_grace,
        )
        _raise_if_failed_execution(executed_request)
        return {
            "status": executed_request.status.value,
            "request_id": str(executed_request.id),
        }
    except ResourceNotFoundError:
        raise
    except ValdricsException:
        raise
    except ValueError as exc:
        raise ValdricsException(
            message=str(exc),
            code="remediation_execution_failed",
            status_code=400,
        ) from exc
    except REMEDIATION_EXECUTION_RECOVERABLE_EXCEPTIONS:
        logger.exception("remediation_api_execution_failed", request_id=str(request_id))
        raise ValdricsException(
            message="Failed to execute remediation request.",
            code="remediation_execution_failed",
            status_code=500,
        ) from None


@router.get("/plan/{request_id}")
async def get_remediation_plan(
    request_id: UUID,
    tenant_id: Annotated[UUID, Depends(require_tenant_access)],
    user: Annotated[
        CurrentUser, Depends(requires_feature(FeatureFlag.GITOPS_REMEDIATION))
    ],
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    service = RemediationService(db=db)
    remediation_request = await service.get_by_id(
        RemediationRequest, request_id, tenant_id
    )

    if not remediation_request:
        raise ResourceNotFoundError(f"Remediation request {request_id} not found")

    plan = await service.generate_iac_plan(remediation_request, tenant_id)

    return {
        "status": "success",
        "plan": plan,
        "resource_id": remediation_request.resource_id,
        "provider": remediation_request.provider,
    }
