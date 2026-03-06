from __future__ import annotations

from datetime import date
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reporting.api.v1.costs_models import (
    ProviderInvoiceStatusUpdateRequest,
    ProviderInvoiceUpsertRequest,
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
from app.shared.core.auth import CurrentUser
from app.shared.core.dependencies import requires_feature
from app.shared.core.pricing import FeatureFlag
from app.shared.db.session import get_db


async def get_reconciliation_close_package(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = Query(default=None),
    response_format: str = Query(default="json", pattern="^(json|csv)$"),
    enforce_finalized: bool = Query(default=True),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.CLOSE_WORKFLOW)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await get_reconciliation_close_package_impl(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        response_format=response_format,
        enforce_finalized=enforce_finalized,
        user=user,
        db=db,
        require_tenant_id=costs_module._require_tenant_id,
        normalize_provider_filter=costs_module._normalize_provider_filter,
    )


async def get_restatement_history(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = Query(default=None),
    response_format: str = Query(default="json", pattern="^(json|csv)$"),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.RECONCILIATION)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await get_restatement_history_impl(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        response_format=response_format,
        user=user,
        db=db,
        require_tenant_id=costs_module._require_tenant_id,
        normalize_provider_filter=costs_module._normalize_provider_filter,
        get_settings=costs_module.get_settings,
    )


async def get_restatement_runs(
    start_date: date = Query(...),
    end_date: date = Query(...),
    provider: Optional[str] = Query(default=None),
    response_format: str = Query(default="json", pattern="^(json|csv)$"),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.RECONCILIATION)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await get_restatement_runs_impl(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        response_format=response_format,
        user=user,
        db=db,
        require_tenant_id=costs_module._require_tenant_id,
        normalize_provider_filter=costs_module._normalize_provider_filter,
    )


async def list_provider_invoices(
    provider: Optional[str] = Query(default=None),
    start_date: Optional[date] = Query(default=None),
    end_date: Optional[date] = Query(default=None),
    user: CurrentUser = Depends(requires_feature(FeatureFlag.CLOSE_WORKFLOW)),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await list_provider_invoices_impl(
        provider=provider,
        start_date=start_date,
        end_date=end_date,
        user=user,
        db=db,
        require_tenant_id=costs_module._require_tenant_id,
        normalize_provider_filter=costs_module._normalize_provider_filter,
    )


async def upsert_provider_invoice(
    request: Request,
    payload: ProviderInvoiceUpsertRequest,
    user: CurrentUser = Depends(
        requires_feature(FeatureFlag.CLOSE_WORKFLOW, required_role="admin")
    ),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await upsert_provider_invoice_impl(
        request=request,
        payload=payload,
        user=user,
        db=db,
        require_tenant_id=costs_module._require_tenant_id,
    )


async def update_provider_invoice_status(
    request: Request,
    invoice_id: UUID,
    payload: ProviderInvoiceStatusUpdateRequest,
    user: CurrentUser = Depends(
        requires_feature(FeatureFlag.CLOSE_WORKFLOW, required_role="admin")
    ),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await update_provider_invoice_status_impl(
        request=request,
        invoice_id=invoice_id,
        payload=payload,
        user=user,
        db=db,
        require_tenant_id=costs_module._require_tenant_id,
    )


async def delete_provider_invoice(
    request: Request,
    invoice_id: UUID,
    user: CurrentUser = Depends(
        requires_feature(FeatureFlag.CLOSE_WORKFLOW, required_role="admin")
    ),
    db: AsyncSession = Depends(get_db),
) -> Any:
    from app.modules.reporting.api.v1 import costs as costs_module

    return await delete_provider_invoice_impl(
        request=request,
        invoice_id=invoice_id,
        user=user,
        db=db,
        require_tenant_id=costs_module._require_tenant_id,
    )


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
    from app.modules.reporting.api.v1 import costs as costs_module

    return await export_focus_v13_costs_csv_impl(
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        include_preliminary=include_preliminary,
        user=user,
        db=db,
        require_tenant_id=costs_module._require_tenant_id,
        normalize_provider_filter=costs_module._normalize_provider_filter,
        sanitize_csv_cell=costs_module._sanitize_csv_cell,
        get_settings=costs_module.get_settings,
    )


def register_reconciliation_routes(router: APIRouter) -> None:
    router.add_api_route(
        "/reconciliation/close-package",
        get_reconciliation_close_package,
        methods=["GET"],
        response_model=None,
    )
    router.add_api_route(
        "/reconciliation/restatements",
        get_restatement_history,
        methods=["GET"],
        response_model=None,
    )
    router.add_api_route(
        "/reconciliation/restatement-runs",
        get_restatement_runs,
        methods=["GET"],
        response_model=None,
    )
    router.add_api_route(
        "/reconciliation/invoices",
        list_provider_invoices,
        methods=["GET"],
        response_model=None,
    )
    router.add_api_route(
        "/reconciliation/invoices",
        upsert_provider_invoice,
        methods=["POST"],
        response_model=None,
    )
    router.add_api_route(
        "/reconciliation/invoices/{invoice_id}",
        update_provider_invoice_status,
        methods=["PATCH"],
        response_model=None,
    )
    router.add_api_route(
        "/reconciliation/invoices/{invoice_id}",
        delete_provider_invoice,
        methods=["DELETE"],
        response_model=None,
    )
    router.add_api_route(
        "/export/focus",
        export_focus_v13_costs_csv,
        methods=["GET"],
        response_model=None,
    )
