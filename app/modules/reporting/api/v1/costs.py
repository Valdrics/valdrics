from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.unit_economics_settings import UnitEconomicsSettings
from app.modules.reporting.api.v1.costs_acceptance_payload import (
    compute_acceptance_kpis_payload as _compute_acceptance_kpis_payload_impl,
)
from app.modules.reporting.api.v1.costs_acceptance_routes import (
    capture_acceptance_kpis_impl,
    get_acceptance_kpis_impl,
    list_acceptance_kpi_evidence_impl,
)
from app.modules.reporting.api.v1.costs_core_routes import (
    analyze_costs_impl,
    get_canonical_quality_impl,
    get_cost_anomalies_impl,
    get_cost_attribution_coverage_impl,
    get_cost_attribution_summary_impl,
    get_cost_breakdown_impl,
    get_cost_forecast_impl,
    get_costs_impl,
    get_ingestion_sla_impl,
    trigger_ingest_impl,
)
from app.modules.reporting.api.v1.costs_helpers import (
    anomaly_to_response_item,
    build_unit_metrics,
    render_acceptance_kpi_csv,
    sanitize_csv_cell,
    validate_anomaly_severity,
)
from app.modules.reporting.api.v1.costs_http_routes_core import router as _core_router
from app.modules.reporting.api.v1.costs_http_routes_extended import (
    router as _extended_router,
)
from app.modules.reporting.api.v1.costs_metrics import (
    build_provider_recency_summary as _build_provider_recency_summary_impl,
    compute_ingestion_sla_metrics as _compute_ingestion_sla_metrics_impl,
    compute_license_governance_kpi as _compute_license_governance_kpi_impl,
    compute_provider_recency_summaries as _compute_provider_recency_summaries_impl,
    get_or_create_unit_settings as _get_or_create_unit_settings_impl,
    is_connection_active_state as _is_connection_active_impl,
    settings_to_response as _settings_to_response_impl,
    window_total_cost as _window_total_cost_impl,
)
from app.modules.reporting.api.v1.costs_models import (
    AcceptanceKpiEvidenceCaptureResponse,
    AcceptanceKpiEvidenceListResponse,
    AcceptanceKpiMetric,
    AcceptanceKpisResponse,
    CostAnomalyItem,
    CostAnomalyResponse,
    IngestionSLAResponse,
    ProviderInvoiceStatusUpdateRequest,
    ProviderInvoiceUpsertRequest,
    ProviderRecencyResponse,
    UnitEconomicsMetric,
    UnitEconomicsResponse,
    UnitEconomicsSettingsResponse,
    UnitEconomicsSettingsUpdate,
)
from app.modules.reporting.api.v1.costs_reconciliation_routes import (
    delete_provider_invoice_impl,
    export_focus_v13_costs_csv_impl,
    get_reconciliation_close_package_impl,
    get_restatement_history_impl,
    get_restatement_runs_impl,
    list_provider_invoices_impl,
    update_provider_invoice_status_impl,
    upsert_provider_invoice_impl,
)
from app.modules.reporting.api.v1.costs_unit_economics_routes import (
    get_unit_economics_impl,
    get_unit_economics_settings_impl,
    update_unit_economics_settings_impl,
)
from app.modules.reporting.domain.aggregator import LARGE_DATASET_THRESHOLD, CostAggregator
from app.modules.reporting.domain.anomaly_detection import (
    CostAnomaly,
    CostAnomalyDetectionService,
    dispatch_cost_anomaly_alerts,
)
from app.shared.analysis.forecaster import SymbolicForecaster
from app.shared.core.auth import CurrentUser, get_current_user
from app.shared.core.config import get_settings
from app.shared.core.notifications import NotificationDispatcher
from app.shared.core.pricing import (
    FeatureFlag,
    PricingTier,
    is_feature_enabled,
    normalize_tier,
)
from app.shared.llm.analyzer import FinOpsAnalyzer
from app.shared.llm.factory import LLMFactory
from app.shared.db.session import get_db

__all__ = [
    "CostAggregator",
    "CostAnomalyDetectionService",
    "FinOpsAnalyzer",
    "LARGE_DATASET_THRESHOLD",
    "LLMFactory",
    "NotificationDispatcher",
    "SymbolicForecaster",
    "UnitEconomicsSettingsUpdate",
    "analyze_costs_impl",
    "dispatch_cost_anomaly_alerts",
    "get_canonical_quality_impl",
    "get_cost_anomalies_impl",
    "get_cost_attribution_coverage_impl",
    "get_cost_attribution_summary_impl",
    "get_cost_breakdown_impl",
    "get_cost_forecast_impl",
    "get_costs_impl",
    "get_ingestion_sla_impl",
    "get_settings",
    "trigger_ingest_impl",
]

router = APIRouter(tags=["Costs"])
# Include prebuilt route fragments without applying an additional prefix layer.
router.routes.extend(_core_router.routes)
router.routes.extend(_extended_router.routes)

@router.get("")
async def get_costs_root(
    response: Response,
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    return await get_costs(
        response=response,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        db=db,
        current_user=current_user,
    )

_PATCHABLE_TEST_SEAMS = (
    NotificationDispatcher,
    CostAggregator,
    FeatureFlag,
    CostAnomaly,
    CostAnomalyDetectionService,
    dispatch_cost_anomaly_alerts,
    UnitEconomicsSettings,
    FinOpsAnalyzer,
    LLMFactory,
    AcceptanceKpiEvidenceCaptureResponse,
    AcceptanceKpiEvidenceListResponse,
    AcceptanceKpiMetric,
    AcceptanceKpisResponse,
    CostAnomalyItem,
    CostAnomalyResponse,
    IngestionSLAResponse,
    ProviderInvoiceStatusUpdateRequest,
    ProviderInvoiceUpsertRequest,
    ProviderRecencyResponse,
    UnitEconomicsMetric,
    UnitEconomicsResponse,
    UnitEconomicsSettingsResponse,
    UnitEconomicsSettingsUpdate,
)
SUPPORTED_PROVIDER_FILTERS = {"aws", "azure", "gcp", "saas", "license", "platform", "hybrid"}
SUPPORTED_ANOMALY_SEVERITIES = {"low", "medium", "high", "critical"}

def _require_tenant_id(user: CurrentUser) -> UUID:
    if user.tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context is required")
    return user.tenant_id


def _resolve_user_tier(user: CurrentUser) -> PricingTier:
    return normalize_tier(getattr(user, "tier", PricingTier.FREE))


def _normalize_provider_filter(provider: str | None) -> str | None:
    if provider is None:
        return None
    normalized = provider.strip().lower()
    if not normalized:
        return None
    if normalized not in SUPPORTED_PROVIDER_FILTERS:
        supported = ", ".join(sorted(SUPPORTED_PROVIDER_FILTERS))
        raise HTTPException(status_code=400, detail=f"Unsupported provider '{provider}'. Use one of: {supported}")
    return normalized


_sanitize_csv_cell = sanitize_csv_cell
_get_or_create_unit_settings = _get_or_create_unit_settings_impl
_settings_to_response = _settings_to_response_impl
_window_total_cost = _window_total_cost_impl
_anomaly_to_response_item = anomaly_to_response_item
_build_unit_metrics = build_unit_metrics
_render_acceptance_kpi_csv = render_acceptance_kpi_csv


def _validate_anomaly_severity(value: str) -> str:
    return validate_anomaly_severity(value, SUPPORTED_ANOMALY_SEVERITIES)


def _is_connection_active(connection: Any) -> bool:
    return _is_connection_active_impl(connection)


def _build_provider_recency_summary(
    provider: str,
    connections: list[Any],
    *,
    now: Any,
    recency_target_hours: int,
) -> ProviderRecencyResponse:
    return _build_provider_recency_summary_impl(
        provider,
        connections,
        now=now,
        recency_target_hours=recency_target_hours,
    )


async def _compute_provider_recency_summaries(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    recency_target_hours: int,
) -> list[ProviderRecencyResponse]:
    return await _compute_provider_recency_summaries_impl(
        db,
        tenant_id,
        recency_target_hours=recency_target_hours,
    )


async def _compute_ingestion_sla_metrics(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    window_hours: int,
    target_success_rate_percent: float,
) -> IngestionSLAResponse:
    return await _compute_ingestion_sla_metrics_impl(
        db,
        tenant_id,
        window_hours=window_hours,
        target_success_rate_percent=target_success_rate_percent,
    )


async def _compute_license_governance_kpi(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    start_date: date,
    end_date: date,
) -> AcceptanceKpiMetric:
    return await _compute_license_governance_kpi_impl(
        db=db,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )


async def get_costs(**kwargs: Any) -> Any:
    return await get_costs_impl(
        require_tenant_id=_require_tenant_id,
        cost_aggregator_cls=CostAggregator,
        **kwargs,
    )


async def get_cost_breakdown(**kwargs: Any) -> Any:
    return await get_cost_breakdown_impl(
        require_tenant_id=_require_tenant_id,
        cost_aggregator_cls=CostAggregator,
        **kwargs,
    )


async def get_cost_attribution_summary(**kwargs: Any) -> dict[str, Any]:
    return await get_cost_attribution_summary_impl(
        require_tenant_id=_require_tenant_id,
        **kwargs,
    )


async def get_cost_attribution_coverage(**kwargs: Any) -> dict[str, Any]:
    return await get_cost_attribution_coverage_impl(
        require_tenant_id=_require_tenant_id,
        **kwargs,
    )


async def get_canonical_quality(**kwargs: Any) -> Any:
    return await get_canonical_quality_impl(
        require_tenant_id=_require_tenant_id,
        normalize_provider_filter=_normalize_provider_filter,
        cost_aggregator_cls=CostAggregator,
        notification_dispatcher_cls=NotificationDispatcher,
        **kwargs,
    )


async def get_cost_forecast(**kwargs: Any) -> Any:
    return await get_cost_forecast_impl(
        require_tenant_id=_require_tenant_id,
        cost_aggregator_cls=CostAggregator,
        symbolic_forecaster_cls=SymbolicForecaster,
        **kwargs,
    )


async def get_cost_anomalies(**kwargs: Any) -> CostAnomalyResponse:
    payload = await get_cost_anomalies_impl(
        require_tenant_id=_require_tenant_id,
        normalize_provider_filter=_normalize_provider_filter,
        validate_anomaly_severity=_validate_anomaly_severity,
        anomaly_to_response_item=_anomaly_to_response_item,
        anomaly_detection_service_cls=CostAnomalyDetectionService,
        dispatch_cost_anomaly_alerts_fn=dispatch_cost_anomaly_alerts,
        **kwargs,
    )
    if isinstance(payload, CostAnomalyResponse):
        return payload
    return CostAnomalyResponse(**payload)


async def analyze_costs(**kwargs: Any) -> Any:
    return await analyze_costs_impl(
        require_tenant_id=_require_tenant_id,
        cost_aggregator_cls=CostAggregator,
        llm_factory_cls=LLMFactory,
        finops_analyzer_cls=FinOpsAnalyzer,
        **kwargs,
    )


async def trigger_ingest(**kwargs: Any) -> dict[str, str]:
    return await trigger_ingest_impl(
        resolve_user_tier=_resolve_user_tier,
        require_tenant_id=_require_tenant_id,
        **kwargs,
    )


async def get_ingestion_sla(**kwargs: Any) -> IngestionSLAResponse:
    payload = await get_ingestion_sla_impl(
        require_tenant_id=_require_tenant_id,
        compute_ingestion_sla_metrics=_compute_ingestion_sla_metrics,
        **kwargs,
    )
    if isinstance(payload, IngestionSLAResponse):
        return payload
    return IngestionSLAResponse.model_validate(payload)


async def _compute_acceptance_kpis_payload(**kwargs: Any) -> AcceptanceKpisResponse:
    return await _compute_acceptance_kpis_payload_impl(
        compute_ingestion_sla_metrics_fn=_compute_ingestion_sla_metrics,
        compute_provider_recency_summaries_fn=_compute_provider_recency_summaries,
        compute_license_governance_kpi_fn=_compute_license_governance_kpi,
        get_or_create_unit_settings_fn=_get_or_create_unit_settings,
        window_total_cost_fn=_window_total_cost,
        get_settings_fn=get_settings,
        is_feature_enabled_fn=is_feature_enabled,
        **kwargs,
    )


async def get_acceptance_kpis(**kwargs: Any) -> Any:
    return await get_acceptance_kpis_impl(
        compute_acceptance_kpis_payload=_compute_acceptance_kpis_payload,
        render_acceptance_kpi_csv=_render_acceptance_kpi_csv,
        **kwargs,
    )


async def capture_acceptance_kpis(**kwargs: Any) -> Any:
    return await capture_acceptance_kpis_impl(
        compute_acceptance_kpis_payload=_compute_acceptance_kpis_payload,
        require_tenant_id=_require_tenant_id,
        **kwargs,
    )


async def list_acceptance_kpi_evidence(**kwargs: Any) -> Any:
    return await list_acceptance_kpi_evidence_impl(
        require_tenant_id=_require_tenant_id,
        **kwargs,
    )


async def get_unit_economics_settings(**kwargs: Any) -> Any:
    return await get_unit_economics_settings_impl(
        require_tenant_id=_require_tenant_id,
        get_or_create_unit_settings=_get_or_create_unit_settings,
        settings_to_response=_settings_to_response,
        **kwargs,
    )


async def update_unit_economics_settings(**kwargs: Any) -> Any:
    return await update_unit_economics_settings_impl(
        require_tenant_id=_require_tenant_id,
        get_or_create_unit_settings=_get_or_create_unit_settings,
        settings_to_response=_settings_to_response,
        **kwargs,
    )


async def get_unit_economics(**kwargs: Any) -> Any:
    return await get_unit_economics_impl(
        require_tenant_id=_require_tenant_id,
        get_or_create_unit_settings=_get_or_create_unit_settings,
        window_total_cost=_window_total_cost,
        build_unit_metrics=_build_unit_metrics,
        **kwargs,
    )


async def get_reconciliation_close_package(**kwargs: Any) -> Any:
    return await get_reconciliation_close_package_impl(
        require_tenant_id=_require_tenant_id,
        normalize_provider_filter=_normalize_provider_filter,
        **kwargs,
    )


async def get_restatement_history(**kwargs: Any) -> Any:
    return await get_restatement_history_impl(
        require_tenant_id=_require_tenant_id,
        normalize_provider_filter=_normalize_provider_filter,
        get_settings=get_settings,
        **kwargs,
    )


async def get_restatement_runs(**kwargs: Any) -> Any:
    return await get_restatement_runs_impl(
        require_tenant_id=_require_tenant_id,
        normalize_provider_filter=_normalize_provider_filter,
        **kwargs,
    )


async def list_provider_invoices(**kwargs: Any) -> Any:
    return await list_provider_invoices_impl(
        require_tenant_id=_require_tenant_id,
        normalize_provider_filter=_normalize_provider_filter,
        **kwargs,
    )


async def upsert_provider_invoice(**kwargs: Any) -> Any:
    return await upsert_provider_invoice_impl(
        require_tenant_id=_require_tenant_id,
        **kwargs,
    )


async def update_provider_invoice_status(**kwargs: Any) -> Any:
    return await update_provider_invoice_status_impl(
        require_tenant_id=_require_tenant_id,
        **kwargs,
    )


async def delete_provider_invoice(**kwargs: Any) -> Any:
    return await delete_provider_invoice_impl(
        require_tenant_id=_require_tenant_id,
        **kwargs,
    )


async def export_focus_v13_costs_csv(**kwargs: Any) -> Any:
    return await export_focus_v13_costs_csv_impl(
        require_tenant_id=_require_tenant_id,
        normalize_provider_filter=_normalize_provider_filter,
        sanitize_csv_cell=_sanitize_csv_cell,
        get_settings=get_settings,
        **kwargs,
    )
