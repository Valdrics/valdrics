from dataclasses import dataclass
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.governance.api.v1.audit_evidence_common import (
    AUDIT_EVIDENCE_PAYLOAD_ERRORS,
    AdminComplianceUser,
    capture_evidence_event,
    list_evidence_items,
    validate_evidence_payload,
)
from app.modules.governance.api.v1.audit_schemas import (
    IdentityIdpSmokeEvidenceCaptureResponse,
    IdentityIdpSmokeEvidenceItem,
    IdentityIdpSmokeEvidenceListResponse,
    IdentityIdpSmokeEvidencePayload,
    IngestionPersistenceEvidenceCaptureResponse,
    IngestionPersistenceEvidenceItem,
    IngestionPersistenceEvidenceListResponse,
    IngestionPersistenceEvidencePayload,
    IngestionSoakEvidenceCaptureResponse,
    IngestionSoakEvidenceItem,
    IngestionSoakEvidenceListResponse,
    IngestionSoakEvidencePayload,
    LoadTestEvidenceCaptureResponse,
    LoadTestEvidenceItem,
    LoadTestEvidenceListResponse,
    LoadTestEvidencePayload,
    SsoFederationValidationEvidenceCaptureResponse,
    SsoFederationValidationEvidenceItem,
    SsoFederationValidationEvidenceListResponse,
    SsoFederationValidationEvidencePayload,
)
from app.shared.db.session import get_db

router = APIRouter(tags=["Audit"])
_validate_evidence_payload = validate_evidence_payload


@dataclass(frozen=True, slots=True)
class _EvidenceEndpointConfig:
    event_type_attr: str
    resource_type: str
    payload_key: str
    request_path: str
    warning_event: str
    response_payload_field: str


_LOAD_TEST_CONFIG = _EvidenceEndpointConfig(
    event_type_attr="PERFORMANCE_LOAD_TEST_CAPTURED",
    resource_type="load_test",
    payload_key="load_test",
    request_path="/api/v1/audit/performance/load-test/evidence",
    warning_event="load_test_evidence_invalid_payload",
    response_payload_field="load_test",
)
_INGESTION_PERSISTENCE_CONFIG = _EvidenceEndpointConfig(
    event_type_attr="PERFORMANCE_INGESTION_PERSISTENCE_CAPTURED",
    resource_type="ingestion_persistence",
    payload_key="benchmark",
    request_path="/api/v1/audit/performance/ingestion/persistence/evidence",
    warning_event="ingestion_persistence_evidence_invalid_payload",
    response_payload_field="benchmark",
)
_INGESTION_SOAK_CONFIG = _EvidenceEndpointConfig(
    event_type_attr="PERFORMANCE_INGESTION_SOAK_CAPTURED",
    resource_type="ingestion_soak",
    payload_key="ingestion_soak",
    request_path="/api/v1/audit/performance/ingestion/soak/evidence",
    warning_event="ingestion_soak_evidence_invalid_payload",
    response_payload_field="ingestion_soak",
)
_IDENTITY_IDP_SMOKE_CONFIG = _EvidenceEndpointConfig(
    event_type_attr="IDENTITY_IDP_SMOKE_CAPTURED",
    resource_type="identity_idp_smoke",
    payload_key="identity_smoke",
    request_path="/api/v1/audit/identity/idp-smoke/evidence",
    warning_event="identity_idp_smoke_evidence_invalid_payload",
    response_payload_field="identity_smoke",
)
_SSO_FEDERATION_CONFIG = _EvidenceEndpointConfig(
    event_type_attr="IDENTITY_SSO_FEDERATION_VALIDATION_CAPTURED",
    resource_type="identity_sso_federation_validation",
    payload_key="sso_federation_validation",
    request_path="/api/v1/audit/identity/sso-federation/evidence",
    warning_event="sso_federation_validation_evidence_invalid_payload",
    response_payload_field="sso_federation_validation",
)


async def _capture_evidence_response(
    *,
    payload: object,
    user: AdminComplianceUser,
    db: AsyncSession,
    config: _EvidenceEndpointConfig,
    response_model: object,
    resource_id: str,
    success: bool,
) -> object:
    run_id, event = await capture_evidence_event(
        user=user,
        db=db,
        event_type_attr=config.event_type_attr,
        resource_type=config.resource_type,
        resource_id=resource_id,
        payload_key=config.payload_key,
        payload=payload,
        success=bool(success),
        request_path=config.request_path,
    )
    payload_data = {
        "status": "captured",
        "event_id": str(event.id),
        "run_id": run_id,
        "captured_at": event.event_timestamp.isoformat(),
        config.response_payload_field: payload,
    }
    return response_model(**payload_data)


async def _list_evidence_response(
    *,
    user: AdminComplianceUser,
    db: AsyncSession,
    limit: int,
    config: _EvidenceEndpointConfig,
    payload_model: object,
    item_model: object,
    list_response_model: object,
) -> object:
    items = await list_evidence_items(
        user=user,
        db=db,
        limit=limit,
        event_type_attr=config.event_type_attr,
        payload_key=config.payload_key,
        payload_model=payload_model,
        item_model=item_model,
        warning_event=config.warning_event,
    )
    return list_response_model(total=len(items), items=items)


@router.post(
    "/performance/load-test/evidence", response_model=LoadTestEvidenceCaptureResponse
)
async def capture_load_test_evidence(
    payload: LoadTestEvidencePayload,
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
) -> LoadTestEvidenceCaptureResponse:
    return await _capture_evidence_response(
        payload=payload,
        user=user,
        db=db,
        config=_LOAD_TEST_CONFIG,
        response_model=LoadTestEvidenceCaptureResponse,
        resource_id=str(payload.profile or "custom"),
        success=True,
    )


@router.get(
    "/performance/load-test/evidence", response_model=LoadTestEvidenceListResponse
)
async def list_load_test_evidence(
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=2000),
) -> LoadTestEvidenceListResponse:
    return await _list_evidence_response(
        user=user,
        db=db,
        limit=limit,
        config=_LOAD_TEST_CONFIG,
        payload_model=LoadTestEvidencePayload,
        item_model=LoadTestEvidenceItem,
        list_response_model=LoadTestEvidenceListResponse,
    )


@router.post(
    "/performance/ingestion/persistence/evidence",
    response_model=IngestionPersistenceEvidenceCaptureResponse,
)
async def capture_ingestion_persistence_evidence(
    payload: IngestionPersistenceEvidencePayload,
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
) -> IngestionPersistenceEvidenceCaptureResponse:
    return await _capture_evidence_response(
        payload=payload,
        user=user,
        db=db,
        config=_INGESTION_PERSISTENCE_CONFIG,
        response_model=IngestionPersistenceEvidenceCaptureResponse,
        resource_id=str(payload.provider or "unknown"),
        success=bool(payload.meets_targets) if payload.meets_targets is not None else True,
    )


@router.get(
    "/performance/ingestion/persistence/evidence",
    response_model=IngestionPersistenceEvidenceListResponse,
)
async def list_ingestion_persistence_evidence(
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=2000),
) -> IngestionPersistenceEvidenceListResponse:
    return await _list_evidence_response(
        user=user,
        db=db,
        limit=limit,
        config=_INGESTION_PERSISTENCE_CONFIG,
        payload_model=IngestionPersistenceEvidencePayload,
        item_model=IngestionPersistenceEvidenceItem,
        list_response_model=IngestionPersistenceEvidenceListResponse,
    )


@router.post(
    "/performance/ingestion/soak/evidence",
    response_model=IngestionSoakEvidenceCaptureResponse,
)
async def capture_ingestion_soak_evidence(
    payload: IngestionSoakEvidencePayload,
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
) -> IngestionSoakEvidenceCaptureResponse:
    return await _capture_evidence_response(
        payload=payload,
        user=user,
        db=db,
        config=_INGESTION_SOAK_CONFIG,
        response_model=IngestionSoakEvidenceCaptureResponse,
        resource_id=str(payload.jobs_enqueued),
        success=(
            bool(payload.meets_targets)
            if payload.meets_targets is not None
            else bool(payload.results.jobs_failed == 0)
        ),
    )


@router.get(
    "/performance/ingestion/soak/evidence",
    response_model=IngestionSoakEvidenceListResponse,
)
async def list_ingestion_soak_evidence(
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=2000),
) -> IngestionSoakEvidenceListResponse:
    return await _list_evidence_response(
        user=user,
        db=db,
        limit=limit,
        config=_INGESTION_SOAK_CONFIG,
        payload_model=IngestionSoakEvidencePayload,
        item_model=IngestionSoakEvidenceItem,
        list_response_model=IngestionSoakEvidenceListResponse,
    )


@router.post(
    "/identity/idp-smoke/evidence",
    response_model=IdentityIdpSmokeEvidenceCaptureResponse,
)
async def capture_identity_idp_smoke_evidence(
    payload: IdentityIdpSmokeEvidencePayload,
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
) -> IdentityIdpSmokeEvidenceCaptureResponse:
    return await _capture_evidence_response(
        payload=payload,
        user=user,
        db=db,
        config=_IDENTITY_IDP_SMOKE_CONFIG,
        response_model=IdentityIdpSmokeEvidenceCaptureResponse,
        resource_id=str(payload.idp or ""),
        success=bool(payload.passed),
    )


@router.get(
    "/identity/idp-smoke/evidence",
    response_model=IdentityIdpSmokeEvidenceListResponse,
)
async def list_identity_idp_smoke_evidence(
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=2000),
) -> IdentityIdpSmokeEvidenceListResponse:
    return await _list_evidence_response(
        user=user,
        db=db,
        limit=limit,
        config=_IDENTITY_IDP_SMOKE_CONFIG,
        payload_model=IdentityIdpSmokeEvidencePayload,
        item_model=IdentityIdpSmokeEvidenceItem,
        list_response_model=IdentityIdpSmokeEvidenceListResponse,
    )


@router.post(
    "/identity/sso-federation/evidence",
    response_model=SsoFederationValidationEvidenceCaptureResponse,
)
async def capture_sso_federation_validation_evidence(
    payload: SsoFederationValidationEvidencePayload,
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
) -> SsoFederationValidationEvidenceCaptureResponse:
    return await _capture_evidence_response(
        payload=payload,
        user=user,
        db=db,
        config=_SSO_FEDERATION_CONFIG,
        response_model=SsoFederationValidationEvidenceCaptureResponse,
        resource_id=str(payload.federation_mode or ""),
        success=bool(payload.passed),
    )


@router.get(
    "/identity/sso-federation/evidence",
    response_model=SsoFederationValidationEvidenceListResponse,
)
async def list_sso_federation_validation_evidence(
    user: AdminComplianceUser,
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=200, ge=1, le=2000),
) -> SsoFederationValidationEvidenceListResponse:
    return await _list_evidence_response(
        user=user,
        db=db,
        limit=limit,
        config=_SSO_FEDERATION_CONFIG,
        payload_model=SsoFederationValidationEvidencePayload,
        item_model=SsoFederationValidationEvidenceItem,
        list_response_model=SsoFederationValidationEvidenceListResponse,
    )


__all__ = [
    "AUDIT_EVIDENCE_PAYLOAD_ERRORS",
    "capture_identity_idp_smoke_evidence",
    "capture_ingestion_persistence_evidence",
    "capture_ingestion_soak_evidence",
    "capture_load_test_evidence",
    "capture_sso_federation_validation_evidence",
    "list_identity_idp_smoke_evidence",
    "list_ingestion_persistence_evidence",
    "list_ingestion_soak_evidence",
    "list_load_test_evidence",
    "list_sso_federation_validation_evidence",
    "router",
]
