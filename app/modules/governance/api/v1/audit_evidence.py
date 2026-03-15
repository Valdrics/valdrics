from dataclasses import dataclass
from typing import Any, Callable, NoReturn, TypeVar

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.governance.api.v1.audit_evidence_common import (
    AUDIT_EVIDENCE_PAYLOAD_ERRORS,
    AdminComplianceUser,
    capture_evidence_event,
    list_evidence_items,
    require_tenant_id,
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
_CaptureResponseT = TypeVar("_CaptureResponseT")
_ItemModelT = TypeVar("_ItemModelT")
_ListResponseT = TypeVar("_ListResponseT")


@dataclass(frozen=True, slots=True)
class _EvidenceEndpointConfig:
    event_type_attr: str
    resource_type: str
    payload_key: str
    request_path: str
    warning_event: str
    response_payload_field: str
    capture_status: str = "recorded"
    verification_status: str = "operator_attested"


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

_RETIRED_OPERATOR_CAPTURE_DETAIL = (
    "Operator-submitted evidence capture is retired. Use a server-verified "
    "evidence workflow instead."
)


def _raise_retired_operator_capture(user: AdminComplianceUser) -> NoReturn:
    require_tenant_id(user)
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail=_RETIRED_OPERATOR_CAPTURE_DETAIL,
    )


async def _capture_evidence_response(
    *,
    payload: object,
    user: AdminComplianceUser,
    db: AsyncSession,
    config: _EvidenceEndpointConfig,
    response_model: Callable[..., _CaptureResponseT],
    resource_id: str,
    success: bool,
) -> _CaptureResponseT:
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
        verification_status=config.verification_status,
    )
    payload_data = {
        "status": config.capture_status,
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
    payload_model: Any,
    item_model: Callable[..., _ItemModelT],
    list_response_model: Callable[..., _ListResponseT],
) -> _ListResponseT:
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
    _ = (payload, db)
    return _raise_retired_operator_capture(user)


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
    _ = (payload, db)
    return _raise_retired_operator_capture(user)


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
    _ = (payload, db)
    return _raise_retired_operator_capture(user)


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
    _ = (payload, db)
    return _raise_retired_operator_capture(user)


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
    _ = (payload, db)
    return _raise_retired_operator_capture(user)


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
