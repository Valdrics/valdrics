from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Optional, cast

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reporting.api.v1.costs_models import CostAnomalyResponse, IngestionSLAResponse
from app.shared.core.auth import CurrentUser, get_current_user, requires_role
from app.shared.core.dependencies import requires_feature
from app.shared.core.pricing import FeatureFlag
from app.shared.core.rate_limit import analysis_limit
from app.shared.db.session import get_db

router = APIRouter()


def _costs_api() -> Any:
    from app.modules.reporting.api.v1 import costs as costs_api

    return costs_api


@router.get("")
async def get_costs(
    response: Response,
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.get_costs(
        response=response,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        db=db,
        current_user=current_user,
    )


@router.get("/breakdown")
async def get_cost_breakdown(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.get_cost_breakdown(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        limit=limit,
        offset=offset,
        db=db,
        current_user=current_user,
    )


@router.get("/attribution/summary")
async def get_cost_attribution_summary(
    start_date: date = Query(...),
    end_date: date = Query(...),
    bucket: Optional[str] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(requires_feature(FeatureFlag.CHARGEBACK)),
) -> dict[str, Any]:
    costs_api = _costs_api()
    return cast(
        dict[str, Any],
        await costs_api.get_cost_attribution_summary(
        start_date=start_date,
        end_date=end_date,
        bucket=bucket,
        limit=limit,
        offset=offset,
        db=db,
        current_user=current_user,
        ),
    )


@router.get("/attribution/coverage")
async def get_cost_attribution_coverage(
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(requires_feature(FeatureFlag.CHARGEBACK)),
) -> dict[str, Any]:
    costs_api = _costs_api()
    return cast(
        dict[str, Any],
        await costs_api.get_cost_attribution_coverage(
        start_date=start_date,
        end_date=end_date,
        db=db,
        current_user=current_user,
        ),
    )


@router.get("/canonical/quality")
async def get_canonical_quality(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = Query(default=None),
    notify_on_breach: bool = Query(default=False),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.get_canonical_quality(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        notify_on_breach=notify_on_breach,
        db=db,
        current_user=current_user,
    )


@router.get("/forecast")
async def get_cost_forecast(
    days: int = Query(30, ge=7, le=90),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.get_cost_forecast(
        days=days,
        db=db,
        current_user=current_user,
    )


@router.get("/anomalies", response_model=CostAnomalyResponse)
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
    costs_api = _costs_api()
    return cast(
        CostAnomalyResponse,
        await costs_api.get_cost_anomalies(
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
        ),
    )


@router.post("/analyze")
@analysis_limit
async def analyze_costs(
    request: Request,
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    provider: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(requires_feature(FeatureFlag.LLM_ANALYSIS)),
) -> Any:
    costs_api = _costs_api()
    return await costs_api.analyze_costs(
        request=request,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        db=db,
        current_user=current_user,
    )


@router.post("/ingest")
async def trigger_ingest(
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = Depends(requires_role("admin")),
) -> dict[str, str]:
    costs_api = _costs_api()
    return cast(
        dict[str, str],
        await costs_api.trigger_ingest(
        start_date=start_date,
        end_date=end_date,
        db=db,
        current_user=current_user,
        ),
    )


@router.get("/ingestion/sla", response_model=IngestionSLAResponse)
async def get_ingestion_sla(
    window_hours: int = Query(default=24, ge=1, le=24 * 30),
    target_success_rate_percent: float = Query(default=95.0, ge=0, le=100),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.INGESTION_SLA)),
    db: AsyncSession = Depends(get_db),
) -> IngestionSLAResponse:
    costs_api = _costs_api()
    return cast(
        IngestionSLAResponse,
        await costs_api.get_ingestion_sla(
        window_hours=window_hours,
        target_success_rate_percent=target_success_rate_percent,
        user=user,
        db=db,
        ),
    )
