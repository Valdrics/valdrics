from datetime import datetime, timezone
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.governance.api.v1.audit_schemas import (
    CarbonAssuranceEvidenceCaptureRequest,
    CarbonAssuranceEvidenceCaptureResponse,
    CarbonAssuranceEvidenceItem,
    CarbonAssuranceEvidenceListResponse,
    CarbonAssuranceEvidencePayload,
)
from app.shared.core.auth import CurrentUser
from app.shared.core.dependencies import requires_feature
from app.shared.core.pricing import FeatureFlag
from app.shared.db.session import get_db

logger = structlog.get_logger()
router = APIRouter(tags=["Audit"])
AUDIT_EVIDENCE_PAYLOAD_ERRORS = (ValidationError, TypeError, ValueError)
CARBON_FACTOR_FALLBACK_ERRORS = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    ImportError,
    AttributeError,
    TypeError,
    ValueError,
)


def _validate_evidence_payload(
    *,
    raw: Any,
    model: Any,
    warning_event: str,
    event_id: str,
    tenant_id: Any,
) -> Any | None:
    if not isinstance(raw, dict):
        return None
    try:
        return model.model_validate(raw)
    except AUDIT_EVIDENCE_PAYLOAD_ERRORS:
        logger.warning(
            warning_event,
            event_id=event_id,
            tenant_id=str(tenant_id),
        )
        return None


@router.post(
    "/carbon/assurance/evidence", response_model=CarbonAssuranceEvidenceCaptureResponse
)
async def capture_carbon_assurance_evidence(
    request: CarbonAssuranceEvidenceCaptureRequest,
    user: Annotated[
        CurrentUser,
        Depends(
            requires_feature(FeatureFlag.COMPLIANCE_EXPORTS, required_role="admin")
        ),
    ],
    db: AsyncSession = Depends(get_db),
) -> CarbonAssuranceEvidenceCaptureResponse:
    """Capture an auditable carbon methodology + factor snapshot into the tenant audit log."""
    from uuid import uuid4

    from app.modules.governance.domain.security.audit_log import (
        AuditEventType,
        AuditLogger,
    )
    from app.modules.reporting.domain.calculator import carbon_assurance_snapshot
    from app.modules.reporting.domain.carbon_factors import CarbonFactorService

    tenant_id = user.tenant_id
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context is required")

    run_id = str(uuid4())
    active_factor_set_id: str | None = None
    active_factor_set_status: str | None = None
    factor_payload: dict[str, Any] | None = None
    try:
        factor_service = CarbonFactorService(db)
        active_factor_set = await factor_service.ensure_active()
        factor_payload = await factor_service.get_active_payload()
        active_factor_set_id = str(active_factor_set.id)
        active_factor_set_status = str(active_factor_set.status)
    except CARBON_FACTOR_FALLBACK_ERRORS as exc:
        logger.warning(
            "carbon_assurance_factor_payload_fallback",
            tenant_id=str(tenant_id),
            error=str(exc),
        )

    snapshot = carbon_assurance_snapshot(factor_payload)
    payload = CarbonAssuranceEvidencePayload(
        runner=str(request.runner or "api"),
        notes=str(request.notes) if request.notes else None,
        captured_at=datetime.now(timezone.utc).isoformat(),
        snapshot=snapshot,
        factor_set_id=active_factor_set_id,
        factor_set_status=active_factor_set_status,
    )

    audit = AuditLogger(db=db, tenant_id=tenant_id, correlation_id=run_id)
    event = await audit.log(
        event_type=AuditEventType.CARBON_ASSURANCE_SNAPSHOT_CAPTURED,
        actor_id=user.id,
        actor_email=user.email,
        resource_type="carbon",
        resource_id="carbon_assurance_snapshot",
        details={
            "run_id": run_id,
            "captured_at": payload.captured_at,
            "carbon_assurance": payload.model_dump(),
        },
        success=True,
        request_method="POST",
        request_path="/api/v1/audit/carbon/assurance/evidence",
    )
    await db.commit()

    return CarbonAssuranceEvidenceCaptureResponse(
        status="captured",
        event_id=str(event.id),
        run_id=run_id,
        captured_at=event.event_timestamp.isoformat(),
        carbon_assurance=payload,
    )


@router.get(
    "/carbon/assurance/evidence", response_model=CarbonAssuranceEvidenceListResponse
)
async def list_carbon_assurance_evidence(
    user: Annotated[
        CurrentUser,
        Depends(
            requires_feature(FeatureFlag.COMPLIANCE_EXPORTS, required_role="admin")
        ),
    ],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=2000),
) -> CarbonAssuranceEvidenceListResponse:
    """List persisted carbon assurance evidence snapshots for this tenant (latest first)."""
    from app.modules.governance.domain.security.audit_log import (
        AuditEventType,
        AuditLog,
    )

    tenant_id = user.tenant_id
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context is required")

    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == tenant_id)
        .where(
            AuditLog.event_type
            == AuditEventType.CARBON_ASSURANCE_SNAPSHOT_CAPTURED.value
        )
        .order_by(desc(AuditLog.event_timestamp))
        .limit(int(limit))
    )
    items: list[CarbonAssuranceEvidenceItem] = []
    for row in (await db.execute(stmt)).scalars():
        details = row.details or {}
        carbon_assurance = _validate_evidence_payload(
            raw=details.get("carbon_assurance"),
            model=CarbonAssuranceEvidencePayload,
            warning_event="carbon_assurance_evidence_invalid_payload",
            event_id=str(row.id),
            tenant_id=tenant_id,
        )
        if carbon_assurance is None:
            continue

        items.append(
            CarbonAssuranceEvidenceItem(
                event_id=str(row.id),
                run_id=row.correlation_id,
                captured_at=row.event_timestamp.isoformat(),
                actor_id=str(row.actor_id) if row.actor_id else None,
                actor_email=row.actor_email,
                success=bool(row.success),
                carbon_assurance=carbon_assurance,
            )
        )

    return CarbonAssuranceEvidenceListResponse(total=len(items), items=items)
