from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.governance.api.v1.audit_evidence_common import (
    AdminComplianceUser,
    capture_evidence_event,
    list_evidence_items,
    require_tenant_id,
)
from app.modules.governance.api.v1.audit_schemas import (
    JobSLOEvidenceCaptureRequest,
    JobSLOEvidenceCaptureResponse,
    JobSLOEvidenceItem,
    JobSLOEvidenceListResponse,
    JobSLOEvidencePayload,
    TenantIsolationEvidenceCaptureResponse,
    TenantIsolationEvidenceItem,
    TenantIsolationEvidenceListResponse,
    TenantIsolationEvidencePayload,
)
from app.shared.db.session import get_db

router = APIRouter(tags=["Audit"])


@router.post("/jobs/slo/evidence", response_model=JobSLOEvidenceCaptureResponse)
async def capture_job_slo_evidence(
    payload: JobSLOEvidenceCaptureRequest,
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
) -> JobSLOEvidenceCaptureResponse:
    from app.modules.governance.domain.jobs import metrics as metrics_module

    tenant_id = require_tenant_id(user)
    computed_slo = await metrics_module.compute_job_slo(
        db,
        tenant_id=tenant_id,
        window_hours=int(payload.window_hours),
        target_success_rate_percent=float(payload.target_success_rate_percent),
    )
    backlog = await metrics_module.compute_job_backlog_snapshot(db, tenant_id=tenant_id)
    evidence = JobSLOEvidencePayload.model_validate({**computed_slo, "backlog": backlog})

    run_id, event = await capture_evidence_event(
        user=user,
        db=db,
        event_type_attr="JOBS_SLO_CAPTURED",
        resource_type="jobs",
        resource_id=f"{payload.window_hours}h",
        payload_key="job_slo",
        payload=evidence,
        success=bool(evidence.overall_meets_slo),
        request_path="/api/v1/audit/jobs/slo/evidence",
    )
    return JobSLOEvidenceCaptureResponse(
        status="captured",
        event_id=str(event.id),
        run_id=run_id,
        captured_at=event.event_timestamp.isoformat(),
        job_slo=evidence,
    )


@router.get("/jobs/slo/evidence", response_model=JobSLOEvidenceListResponse)
async def list_job_slo_evidence(
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=2000),
) -> JobSLOEvidenceListResponse:
    items = await list_evidence_items(
        user=user,
        db=db,
        limit=limit,
        event_type_attr="JOBS_SLO_CAPTURED",
        payload_key="job_slo",
        payload_model=JobSLOEvidencePayload,
        item_model=JobSLOEvidenceItem,
        warning_event="job_slo_evidence_invalid_payload",
    )
    return JobSLOEvidenceListResponse(total=len(items), items=items)


@router.post(
    "/tenancy/isolation/evidence", response_model=TenantIsolationEvidenceCaptureResponse
)
async def capture_tenant_isolation_evidence(
    payload: TenantIsolationEvidencePayload,
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
) -> TenantIsolationEvidenceCaptureResponse:
    run_id, event = await capture_evidence_event(
        user=user,
        db=db,
        event_type_attr="TENANCY_ISOLATION_VERIFICATION_CAPTURED",
        resource_type="tenancy",
        resource_id="tenant_isolation_verification",
        payload_key="tenant_isolation",
        payload=payload,
        success=bool(payload.passed),
        request_path="/api/v1/audit/tenancy/isolation/evidence",
    )
    return TenantIsolationEvidenceCaptureResponse(
        status="captured",
        event_id=str(event.id),
        run_id=run_id,
        captured_at=event.event_timestamp.isoformat(),
        tenant_isolation=payload,
    )


@router.get(
    "/tenancy/isolation/evidence", response_model=TenantIsolationEvidenceListResponse
)
async def list_tenant_isolation_evidence(
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=2000),
) -> TenantIsolationEvidenceListResponse:
    items = await list_evidence_items(
        user=user,
        db=db,
        limit=limit,
        event_type_attr="TENANCY_ISOLATION_VERIFICATION_CAPTURED",
        payload_key="tenant_isolation",
        payload_model=TenantIsolationEvidencePayload,
        item_model=TenantIsolationEvidenceItem,
        warning_event="tenant_isolation_evidence_invalid_payload",
    )
    return TenantIsolationEvidenceListResponse(total=len(items), items=items)

