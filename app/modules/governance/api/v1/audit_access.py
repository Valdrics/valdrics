from datetime import datetime
import importlib
import pkgutil
from typing import Annotated, Any, List, Literal, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import asc, delete, desc, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.governance.api.v1.audit_common import _rowcount, _sanitize_csv_cell
from app.modules.governance.api.v1.audit_schemas import AuditLogResponse
from app.modules.governance.domain.security.audit_log import AuditLog
from app.shared.core.auth import CurrentUser, requires_role
from app.shared.core.dependencies import requires_feature
from app.shared.core.pricing import FeatureFlag
from app.shared.db.base import Base
from app.shared.db.session import (
    allow_audit_log_retention_purge,
    allow_system_audit_log_retention_purge,
)
from app.shared.db.session import get_db

logger = structlog.get_logger()
router = APIRouter(tags=["Audit"])
AUDIT_ACCESS_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    AttributeError,
    ImportError,
)
ERASURE_SWEEP_EXCLUDED_TABLES = frozenset(
    {"tenants", "users", "audit_logs", "system_audit_logs"}
)


def _load_all_model_modules() -> None:
    import app.models as app_models

    for module_info in pkgutil.iter_modules(
        app_models.__path__, f"{app_models.__name__}."
    ):
        if module_info.ispkg:
            continue
        importlib.import_module(module_info.name)


def _iter_tenant_scoped_models() -> list[type[Any]]:
    _load_all_model_modules()

    table_to_model: dict[str, type[Any]] = {}
    for mapper in Base.registry.mappers:
        if getattr(mapper.class_, "__table__", None) is None:
            continue
        table_name = str(getattr(mapper.local_table, "name", ""))
        if table_name:
            table_to_model[table_name] = mapper.class_
    models: list[type[Any]] = []
    for table in reversed(Base.metadata.sorted_tables):
        table_name = str(getattr(table, "name", ""))
        table_columns = getattr(table, "c", {})
        if table_name in ERASURE_SWEEP_EXCLUDED_TABLES or "tenant_id" not in table_columns:
            continue
        model = table_to_model.get(table_name)
        if model is not None:
            models.append(model)
    return models

@router.get("/logs", response_model=List[AuditLogResponse])
async def get_audit_logs(
    user: Annotated[
        CurrentUser,
        Depends(requires_feature(FeatureFlag.AUDIT_LOGS, required_role="admin")),
    ],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    sort_by: Literal["event_timestamp", "event_type", "actor_email"] = Query(
        "event_timestamp"
    ),
    order: Literal["asc", "desc"] = Query("desc"),
) -> list[AuditLogResponse]:
    """
    Get paginated audit logs for tenant.

    Admin-only. Sensitive details are masked by default.
    """
    try:
        if sort_by == "actor_email":
            raise HTTPException(
                status_code=400,
                detail="Sorting by actor_email is not supported for encrypted audit data.",
            )

        sort_column = getattr(AuditLog, sort_by)
        order_func = desc if order == "desc" else asc

        query = (
            select(AuditLog)
            .where(AuditLog.tenant_id == user.tenant_id)
            .order_by(order_func(sort_column))
        )

        if event_type:
            query = query.where(AuditLog.event_type == event_type)

        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        logs = result.scalars().all()

        return [
            AuditLogResponse(
                id=log.id,
                event_type=log.event_type,
                event_timestamp=log.event_timestamp,
                actor_email=log.actor_email,
                resource_type=log.resource_type,
                resource_id=log.resource_id,
                success=log.success,
                correlation_id=log.correlation_id,
            )
            for log in logs
        ]

    except HTTPException:
        raise
    except AUDIT_ACCESS_RECOVERABLE_ERRORS as e:
        logger.error("audit_logs_fetch_failed", error=str(e))
        raise HTTPException(500, "Failed to fetch audit logs") from e


@router.get("/logs/{log_id}")
async def get_audit_log_detail(
    log_id: UUID,
    user: Annotated[
        CurrentUser,
        Depends(requires_feature(FeatureFlag.AUDIT_LOGS, required_role="admin")),
    ],
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """Get single audit log entry with full details."""
    try:
        result = await db.execute(
            select(AuditLog).where(
                AuditLog.id == log_id, AuditLog.tenant_id == user.tenant_id
            )
        )
        log = result.scalar_one_or_none()

        if not log:
            raise HTTPException(404, "Audit log not found")

        return {
            "id": str(log.id),
            "event_type": log.event_type,
            "event_timestamp": log.event_timestamp.isoformat(),
            "actor_id": str(log.actor_id) if log.actor_id else None,
            "actor_email": log.actor_email,
            "actor_ip": log.actor_ip,
            "correlation_id": log.correlation_id,
            "request_method": log.request_method,
            "request_path": log.request_path,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "details": log.details,  # Already masked by AuditLogger
            "success": log.success,
            "error_message": log.error_message,
        }

    except HTTPException:
        raise
    except AUDIT_ACCESS_RECOVERABLE_ERRORS as e:
        logger.error("audit_log_detail_failed", error=str(e))
        raise HTTPException(500, "Failed to fetch audit log") from e


@router.get("/event-types")
async def get_event_types(
    _: Annotated[
        CurrentUser,
        Depends(requires_feature(FeatureFlag.AUDIT_LOGS, required_role="admin")),
    ],
) -> dict[str, list[str]]:
    """Get list of available audit event types for filtering."""
    from app.modules.governance.domain.security.audit_log import AuditEventType

    return {"event_types": [e.value for e in AuditEventType]}


@router.get("/export")
async def export_audit_logs(
    user: Annotated[
        CurrentUser,
        Depends(
            requires_feature(FeatureFlag.COMPLIANCE_EXPORTS, required_role="admin")
        ),
    ],
    db: AsyncSession = Depends(get_db),
    start_date: Optional[datetime] = Query(None, description="Start of date range"),
    end_date: Optional[datetime] = Query(None, description="End of date range"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
) -> Any:
    """
    Export audit logs as CSV for the tenant.
    GDPR/SOC2: Provides audit trail export for compliance.
    """
    from fastapi.responses import StreamingResponse
    import csv
    import io

    try:
        query = (
            select(AuditLog)
            .where(AuditLog.tenant_id == user.tenant_id)
            .order_by(desc(AuditLog.event_timestamp))
        )

        if start_date:
            query = query.where(AuditLog.event_timestamp >= start_date)
        if end_date:
            query = query.where(AuditLog.event_timestamp <= end_date)
        if event_type:
            query = query.where(AuditLog.event_type == event_type)

        # Limit export to 10,000 records for performance
        query = query.limit(10000)

        result = await db.execute(query)
        logs = result.scalars().all()

        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "event_type",
                "event_timestamp",
                "actor_email",
                "resource_type",
                "resource_id",
                "success",
                "correlation_id",
            ]
        )

        for log in logs:
            writer.writerow(
                [
                    str(log.id),
                    _sanitize_csv_cell(log.event_type),
                    _sanitize_csv_cell(log.event_timestamp.isoformat()),
                    _sanitize_csv_cell(log.actor_email or ""),
                    _sanitize_csv_cell(log.resource_type or ""),
                    _sanitize_csv_cell(str(log.resource_id) if log.resource_id else ""),
                    _sanitize_csv_cell(str(log.success)),
                    _sanitize_csv_cell(log.correlation_id or ""),
                ]
            )

        output.seek(0)

        logger.info(
            "audit_logs_exported", tenant_id=str(user.tenant_id), record_count=len(logs)
        )

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_logs_{user.tenant_id}.csv"
            },
        )

    except AUDIT_ACCESS_RECOVERABLE_ERRORS + (csv.Error,) as e:
        logger.error("audit_export_failed", error=str(e))
        raise HTTPException(500, "Failed to export audit logs") from e


@router.delete("/data-erasure-request")
async def request_data_erasure(
    user: Annotated[CurrentUser, Depends(requires_role("owner"))],
    db: AsyncSession = Depends(get_db),
    confirmation: str = Query(..., description="Type 'DELETE ALL MY DATA' to confirm"),
) -> dict[str, Any]:
    """
    GDPR Article 17 - Right to Erasure (Right to be Forgotten).

    Initiates a data erasure request for the tenant.
    Owner role required. Irreversible action.
    """
    if confirmation != "DELETE ALL MY DATA":
        raise HTTPException(
            status_code=400,
            detail="Confirmation text must exactly match 'DELETE ALL MY DATA'",
        )

    try:
        from app.models.tenant import User
        from app.models.tenant import Tenant
        from app.models.aws_connection import AWSConnection
        from app.models.cloud import CostRecord
        from app.models.discovered_account import DiscoveredAccount
        from app.models.attribution import CostAllocation
        from app.models.cost_audit import CostAuditLog
        from app.modules.governance.domain.security.audit_log import (
            AuditEventType,
            SystemAuditLog,
            SystemAuditLogger,
        )

        tenant_id = user.tenant_id
        if tenant_id is None:
            raise HTTPException(status_code=403, detail="Tenant context is required")

        tenant_row = await db.execute(
            select(Tenant).where(Tenant.id == tenant_id).with_for_update()
        )
        if tenant_row.scalar_one_or_none() is None:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Log the request before execution
        logger.critical(
            "gdpr_data_erasure_initiated",
            tenant_id=str(tenant_id),
            requested_by=user.email,
        )

        # Delete in order of dependencies
        deleted_counts: dict[str, int] = {}
        tenant_user_ids = select(User.id).where(User.tenant_id == tenant_id)

        # 1. Delete dependent cost evidence with no direct tenant_id.
        result = await db.execute(
            delete(CostAuditLog).where(
                CostAuditLog.cost_record_id.in_(
                    select(CostRecord.id).where(CostRecord.tenant_id == tenant_id)
                )
            )
        )
        deleted_counts["cost_audit_logs"] = _rowcount(result)

        # 2. Delete derived allocations before cost records.
        result = await db.execute(
            delete(CostAllocation).where(
                CostAllocation.cost_record_id.in_(
                    select(CostRecord.id).where(CostRecord.tenant_id == tenant_id)
                )
            )
        )
        deleted_counts["cost_allocations"] = _rowcount(result)

        # 3. Delete child discovery rows with indirect tenant ownership.
        result = await db.execute(
            delete(DiscoveredAccount).where(
                DiscoveredAccount.management_connection_id.in_(
                    select(AWSConnection.id).where(AWSConnection.tenant_id == tenant_id)
                )
            )
        )
        deleted_counts["discovered_accounts"] = _rowcount(result)

        # 4. Remove tenant-scoped audit logs before deleting tenant users.
        await allow_audit_log_retention_purge(db, True)
        try:
            result = await db.execute(delete(AuditLog).where(AuditLog.tenant_id == tenant_id))
        finally:
            await allow_audit_log_retention_purge(db, False)
        deleted_counts["audit_logs"] = _rowcount(result)

        # 5. Remove system-scope audit rows that directly reference tenant users so
        # user deletion cannot be blocked by immutable cross-scope audit history.
        await allow_system_audit_log_retention_purge(db, True)
        try:
            result = await db.execute(
                delete(SystemAuditLog).where(SystemAuditLog.actor_id.in_(tenant_user_ids))
            )
        finally:
            await allow_system_audit_log_retention_purge(db, False)
        deleted_counts["system_audit_logs"] = _rowcount(result)

        # 6. Sweep all tenant-scoped tables registered in metadata, including
        # identity/SSO/SCIM/growth/finance evidence tables that were previously omitted.
        for model in _iter_tenant_scoped_models():
            result = await db.execute(
                delete(model).where(getattr(model, "tenant_id") == tenant_id)
            )
            deleted_counts[model.__table__.name] = _rowcount(result)

        # 7. Delete all tenant users, including the requesting owner principal.
        result = await db.execute(delete(User).where(User.tenant_id == tenant_id))
        deleted_counts["users"] = _rowcount(result)

        # 8. Delete the tenant container itself.
        result = await db.execute(delete(Tenant).where(Tenant.id == tenant_id))
        deleted_counts["tenants"] = _rowcount(result)
        if deleted_counts["tenants"] != 1:
            raise HTTPException(status_code=404, detail="Tenant not found")

        # Preserve a system-scope, non-tenant-linked audit summary for compliance.
        erasure_audit = SystemAuditLogger(db=db)
        await erasure_audit.log(
            event_type=AuditEventType.TENANT_DELETED,
            actor_id=None,
            actor_email=None,
            resource_type="tenant_erasure",
            resource_id=str(tenant_id),
            details={
                "erasure": {
                    "tenant_id": str(tenant_id),
                    "requested_by_email_redacted": True,
                    "deleted_counts": deleted_counts,
                }
            },
            success=True,
            request_method="DELETE",
            request_path="/api/v1/audit/data-erasure-request",
        )

        await db.commit()

        logger.critical(
            "gdpr_data_erasure_complete",
            tenant_id=str(tenant_id),
            deleted_counts=deleted_counts,
        )

        return {
            "status": "erasure_complete",
            "message": (
                "Tenant data erasure completed. The tenant record, all tenant users, "
                "and tenant-scoped data have been deleted."
            ),
            "deleted_counts": deleted_counts,
            "retained_records": {
                "system_audit_summary": True,
            },
        }

    except HTTPException:
        raise
    except AUDIT_ACCESS_RECOVERABLE_ERRORS as e:
        await db.rollback()
        logger.error("gdpr_erasure_failed", error=str(e), tenant_id=str(user.tenant_id))
        raise HTTPException(500, "Data erasure failed. Please contact support.") from e
