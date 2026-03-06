from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional, cast
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reporting.api.v1.costs_models import (
    AcceptanceKpiEvidenceCaptureResponse,
    AcceptanceKpiEvidenceListResponse,
    AcceptanceKpisResponse,
    ProviderInvoiceStatusUpdateRequest,
    ProviderInvoiceUpsertRequest,
    UnitEconomicsResponse,
    UnitEconomicsSettingsResponse,
    UnitEconomicsSettingsUpdate,
)
from app.shared.core.auth import CurrentUser, get_current_user, requires_role
from app.shared.core.dependencies import requires_feature
from app.shared.core.pricing import FeatureFlag
from app.shared.db.session import get_db

router = APIRouter()


def _costs_api() -> Any:
    from app.modules.reporting.api.v1 import costs as costs_api

    return costs_api


@router.get("/acceptance/kpis", response_model=AcceptanceKpisResponse)
async def get_acceptance_kpis(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    ingestion_window_hours: int = Query(default=24 * 7, ge=1, le=24 * 30),
    ingestion_target_success_rate_percent: float = Query(default=95.0, ge=0, le=100),
    recency_target_hours: int = Query(default=48, ge=1, le=24 * 14),
    chargeback_target_percent: float = Query(default=90.0, ge=0, le=100),
    max_unit_anomalies: int = Query(default=0, ge=0, le=100),
    response_format: str = Query(default="json", pattern="^(json|csv)$"),
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.get_acceptance_kpis(
        start_date=start_date,
        end_date=end_date,
        ingestion_window_hours=ingestion_window_hours,
        ingestion_target_success_rate_percent=ingestion_target_success_rate_percent,
        recency_target_hours=recency_target_hours,
        chargeback_target_percent=chargeback_target_percent,
        max_unit_anomalies=max_unit_anomalies,
        response_format=response_format,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/acceptance/kpis/capture", response_model=AcceptanceKpiEvidenceCaptureResponse
)
async def capture_acceptance_kpis(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    ingestion_window_hours: int = Query(default=24 * 7, ge=1, le=24 * 30),
    ingestion_target_success_rate_percent: float = Query(default=95.0, ge=0, le=100),
    recency_target_hours: int = Query(default=48, ge=1, le=24 * 14),
    chargeback_target_percent: float = Query(default=90.0, ge=0, le=100),
    max_unit_anomalies: int = Query(default=0, ge=0, le=100),
    current_user: CurrentUser = Depends(requires_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AcceptanceKpiEvidenceCaptureResponse:
    costs_api = _costs_api()
    return cast(
        AcceptanceKpiEvidenceCaptureResponse,
        await costs_api.capture_acceptance_kpis(
        start_date=start_date,
        end_date=end_date,
        ingestion_window_hours=ingestion_window_hours,
        ingestion_target_success_rate_percent=ingestion_target_success_rate_percent,
        recency_target_hours=recency_target_hours,
        chargeback_target_percent=chargeback_target_percent,
        max_unit_anomalies=max_unit_anomalies,
        current_user=current_user,
        db=db,
        ),
    )


@router.get(
    "/acceptance/kpis/evidence", response_model=AcceptanceKpiEvidenceListResponse
)
async def list_acceptance_kpi_evidence(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: CurrentUser = Depends(requires_role("admin")),
    db: AsyncSession = Depends(get_db),
) -> AcceptanceKpiEvidenceListResponse:
    costs_api = _costs_api()
    return cast(
        AcceptanceKpiEvidenceListResponse,
        await costs_api.list_acceptance_kpi_evidence(
        limit=limit,
        current_user=current_user,
        db=db,
        ),
    )


@router.get("/unit-economics/settings", response_model=UnitEconomicsSettingsResponse)
async def get_unit_economics_settings(
    user: CurrentUser = Depends(requires_feature(FeatureFlag.UNIT_ECONOMICS)),
    db: AsyncSession = Depends(get_db),
) -> UnitEconomicsSettingsResponse:
    costs_api = _costs_api()
    return cast(
        UnitEconomicsSettingsResponse,
        await costs_api.get_unit_economics_settings(
        user=user,
        db=db,
        ),
    )


@router.put("/unit-economics/settings", response_model=UnitEconomicsSettingsResponse)
async def update_unit_economics_settings(
    payload: UnitEconomicsSettingsUpdate,
    user: CurrentUser = Depends(requires_feature(FeatureFlag.UNIT_ECONOMICS, "admin")),
    db: AsyncSession = Depends(get_db),
) -> UnitEconomicsSettingsResponse:
    costs_api = _costs_api()
    return cast(
        UnitEconomicsSettingsResponse,
        await costs_api.update_unit_economics_settings(
        payload=payload,
        user=user,
        db=db,
        ),
    )


@router.get("/unit-economics", response_model=UnitEconomicsResponse)
async def get_unit_economics(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = Query(default=None),
    request_volume: Optional[float] = Query(default=None, gt=0),
    workload_volume: Optional[float] = Query(default=None, gt=0),
    customer_volume: Optional[float] = Query(default=None, gt=0),
    alert_on_anomaly: bool = Query(default=True),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.UNIT_ECONOMICS)),
    db: AsyncSession = Depends(get_db),
) -> UnitEconomicsResponse:
    costs_api = _costs_api()
    return cast(
        UnitEconomicsResponse,
        await costs_api.get_unit_economics(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        request_volume=request_volume,
        workload_volume=workload_volume,
        customer_volume=customer_volume,
        alert_on_anomaly=alert_on_anomaly,
        user=user,
        db=db,
        ),
    )


@router.get("/reconciliation/close-package", response_model=None)
async def get_reconciliation_close_package(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = Query(default=None),
    response_format: str = Query(default="json", pattern="^(json|csv)$"),
    enforce_finalized: bool = Query(default=True),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.CLOSE_WORKFLOW)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.get_reconciliation_close_package(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        response_format=response_format,
        enforce_finalized=enforce_finalized,
        user=user,
        db=db,
    )


@router.get("/reconciliation/restatements", response_model=None)
async def get_restatement_history(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = Query(default=None),
    response_format: str = Query(default="json", pattern="^(json|csv)$"),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.RECONCILIATION)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.get_restatement_history(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        response_format=response_format,
        user=user,
        db=db,
    )


@router.get("/reconciliation/restatement-runs", response_model=None)
async def get_restatement_runs(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = Query(default=None),
    response_format: str = Query(default="json", pattern="^(json|csv)$"),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.RECONCILIATION)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.get_restatement_runs(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        response_format=response_format,
        user=user,
        db=db,
    )


@router.get("/reconciliation/invoices", response_model=None)
async def list_provider_invoices(
    provider: Optional[str] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.CLOSE_WORKFLOW)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.list_provider_invoices(
        provider=provider,
        start_date=start_date,
        end_date=end_date,
        user=user,
        db=db,
    )


@router.post("/reconciliation/invoices", response_model=None)
async def upsert_provider_invoice(
    request: Request,
    payload: ProviderInvoiceUpsertRequest,
    user: CurrentUser = Depends(
        requires_feature(FeatureFlag.CLOSE_WORKFLOW, required_role="admin")
    ),
    db: AsyncSession = Depends(get_db),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.upsert_provider_invoice(
        request=request,
        payload=payload,
        user=user,
        db=db,
    )


@router.patch("/reconciliation/invoices/{invoice_id}", response_model=None)
async def update_provider_invoice_status(
    request: Request,
    invoice_id: UUID,
    payload: ProviderInvoiceStatusUpdateRequest,
    user: CurrentUser = Depends(
        requires_feature(FeatureFlag.CLOSE_WORKFLOW, required_role="admin")
    ),
    db: AsyncSession = Depends(get_db),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.update_provider_invoice_status(
        request=request,
        invoice_id=invoice_id,
        payload=payload,
        user=user,
        db=db,
    )


@router.delete("/reconciliation/invoices/{invoice_id}", response_model=None)
async def delete_provider_invoice(
    request: Request,
    invoice_id: UUID,
    user: CurrentUser = Depends(
        requires_feature(FeatureFlag.CLOSE_WORKFLOW, required_role="admin")
    ),
    db: AsyncSession = Depends(get_db),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.delete_provider_invoice(
        request=request,
        invoice_id=invoice_id,
        user=user,
        db=db,
    )


@router.get("/export/focus", response_model=None)
async def export_focus_v13_costs_csv(
    start_date: date = Query(..., description="Start date (inclusive, YYYY-MM-DD)"),
    end_date: date = Query(..., description="End date (inclusive, YYYY-MM-DD)"),
    provider: Optional[str] = Query(
        default=None, description="Optional provider filter"
    ),
    include_preliminary: bool = Query(
        default=False,
        description="Include PRELIMINARY records (otherwise exports FINAL only).",
    ),
    user: CurrentUser = Depends(
        requires_feature(FeatureFlag.COMPLIANCE_EXPORTS, required_role="admin")
    ),
    db: AsyncSession = Depends(get_db),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.export_focus_v13_costs_csv(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        include_preliminary=include_preliminary,
        user=user,
        db=db,
    )
