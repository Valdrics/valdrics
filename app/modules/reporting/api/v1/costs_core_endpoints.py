from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reporting.api.v1.costs_models import CostAnomalyResponse, IngestionSLAResponse
from app.shared.core.auth import CurrentUser, get_current_user, requires_role
from app.shared.core.dependencies import requires_feature
from app.shared.core.pricing import FeatureFlag
from app.shared.core.rate_limit import analysis_limit
from app.shared.db.session import get_db


async def get_costs(
    response: Response,
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await costs_module.get_costs_impl(
        response=response,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        db=db,
        current_user=current_user,
        require_tenant_id=costs_module._require_tenant_id,
        cost_aggregator_cls=costs_module.CostAggregator,
    )


async def get_cost_breakdown(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await costs_module.get_cost_breakdown_impl(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        limit=limit,
        offset=offset,
        db=db,
        current_user=current_user,
        require_tenant_id=costs_module._require_tenant_id,
        cost_aggregator_cls=costs_module.CostAggregator,
    )


async def get_cost_attribution_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    bucket: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(requires_feature(FeatureFlag.CHARGEBACK)),
) -> Dict[str, Any]:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await costs_module.get_cost_attribution_summary_impl(
        start_date=start_date,
        end_date=end_date,
        bucket=bucket,
        limit=limit,
        offset=offset,
        db=db,
        current_user=current_user,
        require_tenant_id=costs_module._require_tenant_id,
    )


async def get_cost_attribution_coverage(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(requires_feature(FeatureFlag.CHARGEBACK)),
) -> Dict[str, Any]:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await costs_module.get_cost_attribution_coverage_impl(
        start_date=start_date,
        end_date=end_date,
        db=db,
        current_user=current_user,
        require_tenant_id=costs_module._require_tenant_id,
    )


async def get_canonical_quality(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = Query(default=None),
    notify_on_breach: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await costs_module.get_canonical_quality_impl(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        notify_on_breach=notify_on_breach,
        db=db,
        current_user=current_user,
        require_tenant_id=costs_module._require_tenant_id,
        normalize_provider_filter=costs_module._normalize_provider_filter,
        cost_aggregator_cls=costs_module.CostAggregator,
        notification_dispatcher_cls=costs_module.NotificationDispatcher,
    )


async def get_cost_forecast(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await costs_module.get_cost_forecast_impl(
        days=days,
        db=db,
        current_user=current_user,
        require_tenant_id=costs_module._require_tenant_id,
        cost_aggregator_cls=costs_module.CostAggregator,
        symbolic_forecaster_cls=costs_module.SymbolicForecaster,
    )


async def get_cost_anomalies(
    target_date: date = Query(default_factory=date.today),
    lookback_days: int = Query(default=28, ge=7, le=120),
    provider: Optional[str] = Query(default=None),
    min_abs_usd: float = Query(default=25.0, ge=0.0),
    min_percent: float = Query(default=30.0, gt=0.0),
    min_severity: str = Query(default="medium"),
    alert: bool = Query(default=False),
    suppression_hours: int = Query(default=24, ge=1, le=24 * 30),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.ANOMALY_DETECTION)),
    db: AsyncSession = Depends(get_db),
) -> CostAnomalyResponse:
    from app.modules.reporting.api.v1 import costs as costs_module

    payload = await costs_module.get_cost_anomalies_impl(
        target_date=target_date,
        lookback_days=lookback_days,
        provider=provider,
        min_abs_usd=min_abs_usd,
        min_percent=min_percent,
        min_severity=min_severity,
        alert=alert,
        suppression_hours=suppression_hours,
        user=user,
        db=db,
        require_tenant_id=costs_module._require_tenant_id,
        normalize_provider_filter=costs_module._normalize_provider_filter,
        validate_anomaly_severity=costs_module._validate_anomaly_severity,
        anomaly_to_response_item=costs_module._anomaly_to_response_item,
        anomaly_detection_service_cls=costs_module.CostAnomalyDetectionService,
        dispatch_cost_anomaly_alerts_fn=costs_module.dispatch_cost_anomaly_alerts,
    )
    return CostAnomalyResponse(**payload)


@analysis_limit
async def analyze_costs(
    request: Request,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    provider: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(requires_feature(FeatureFlag.LLM_ANALYSIS)),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await costs_module.analyze_costs_impl(
        request=request,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        db=db,
        current_user=current_user,
        require_tenant_id=costs_module._require_tenant_id,
        cost_aggregator_cls=costs_module.CostAggregator,
        llm_factory_cls=costs_module.LLMFactory,
        finops_analyzer_cls=costs_module.FinOpsAnalyzer,
    )


async def trigger_ingest(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(requires_role("admin")),
) -> Dict[str, str]:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await costs_module.trigger_ingest_impl(
        start_date=start_date,
        end_date=end_date,
        db=db,
        current_user=current_user,
        resolve_user_tier=costs_module._resolve_user_tier,
        require_tenant_id=costs_module._require_tenant_id,
    )


async def get_ingestion_sla(
    window_hours: int = Query(default=24, ge=1, le=24 * 30),
    target_success_rate_percent: float = Query(default=95.0, ge=0, le=100),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.INGESTION_SLA)),
    db: AsyncSession = Depends(get_db),
) -> IngestionSLAResponse:
    from app.modules.reporting.api.v1 import costs as costs_module

    payload = await costs_module.get_ingestion_sla_impl(
        window_hours=window_hours,
        target_success_rate_percent=target_success_rate_percent,
        user=user,
        db=db,
        require_tenant_id=costs_module._require_tenant_id,
        compute_ingestion_sla_metrics=costs_module._compute_ingestion_sla_metrics,
    )
    if isinstance(payload, IngestionSLAResponse):
        return payload
    return IngestionSLAResponse.model_validate(payload)


def register_core_routes(router: APIRouter) -> None:
    router.add_api_route("", get_costs, methods=["GET"])
    router.add_api_route("/breakdown", get_cost_breakdown, methods=["GET"])
    router.add_api_route(
        "/attribution/summary",
        get_cost_attribution_summary,
        methods=["GET"],
    )
    router.add_api_route(
        "/attribution/coverage",
        get_cost_attribution_coverage,
        methods=["GET"],
    )
    router.add_api_route("/canonical/quality", get_canonical_quality, methods=["GET"])
    router.add_api_route("/forecast", get_cost_forecast, methods=["GET"])
    router.add_api_route(
        "/anomalies",
        get_cost_anomalies,
        methods=["GET"],
        response_model=CostAnomalyResponse,
    )
    router.add_api_route("/analyze", analyze_costs, methods=["POST"])
    router.add_api_route("/ingest", trigger_ingest, methods=["POST"])
    router.add_api_route(
        "/ingestion/sla",
        get_ingestion_sla,
        methods=["GET"],
        response_model=IngestionSLAResponse,
    )
