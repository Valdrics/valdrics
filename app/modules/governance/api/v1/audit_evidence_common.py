from datetime import datetime, timezone
import inspect
from typing import Annotated, Any

import structlog
from fastapi import Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.core.auth import CurrentUser
from app.shared.core.dependencies import requires_feature
from app.shared.core.pricing import FeatureFlag

logger = structlog.get_logger()
AUDIT_EVIDENCE_PAYLOAD_ERRORS = (ValidationError, TypeError, ValueError)

AdminComplianceUser = Annotated[
    CurrentUser,
    Depends(requires_feature(FeatureFlag.COMPLIANCE_EXPORTS, required_role="admin")),
]


def validate_evidence_payload(
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


def require_tenant_id(user: CurrentUser) -> Any:
    tenant_id = user.tenant_id
    if tenant_id is None:
        raise HTTPException(status_code=403, detail="Tenant context is required")
    return tenant_id


def evidence_item_base(row: Any) -> dict[str, Any]:
    return {
        "event_id": str(row.id),
        "run_id": row.correlation_id,
        "captured_at": row.event_timestamp.isoformat(),
        "actor_id": str(row.actor_id) if row.actor_id else None,
        "actor_email": row.actor_email,
        "success": bool(row.success),
    }


async def capture_evidence_event(
    *,
    user: CurrentUser,
    db: AsyncSession,
    event_type_attr: str,
    resource_type: str,
    resource_id: str,
    payload_key: str,
    payload: Any,
    success: bool,
    request_path: str,
) -> tuple[str, Any]:
    from uuid import uuid4

    from app.modules.governance.domain.security import audit_log as audit_log_module

    tenant_id = require_tenant_id(user)
    run_id = str(uuid4())
    captured_at = datetime.now(timezone.utc).isoformat()

    audit = audit_log_module.AuditLogger(db=db, tenant_id=tenant_id, correlation_id=run_id)
    event = await audit.log(
        event_type=getattr(audit_log_module.AuditEventType, event_type_attr),
        actor_id=user.id,
        actor_email=user.email,
        resource_type=resource_type,
        resource_id=resource_id,
        details={
            "run_id": run_id,
            "captured_at": captured_at,
            payload_key: payload.model_dump(),
        },
        success=bool(success),
        request_method="POST",
        request_path=request_path,
    )
    await db.commit()
    return run_id, event


async def list_evidence_items(
    *,
    user: CurrentUser,
    db: AsyncSession,
    limit: int,
    event_type_attr: str,
    payload_key: str,
    payload_model: Any,
    item_model: Any,
    warning_event: str,
) -> list[Any]:
    from app.modules.governance.domain.security import audit_log as audit_log_module

    tenant_id = require_tenant_id(user)
    event_type = getattr(audit_log_module.AuditEventType, event_type_attr)

    stmt = (
        select(audit_log_module.AuditLog)
        .where(audit_log_module.AuditLog.tenant_id == tenant_id)
        .where(audit_log_module.AuditLog.event_type == event_type.value)
        .order_by(desc(audit_log_module.AuditLog.event_timestamp))
        .limit(int(limit))
    )
    items: list[Any] = []
    scalar_result = (await db.execute(stmt)).scalars()
    rows = scalar_result.all() if hasattr(scalar_result, "all") else scalar_result
    if inspect.isawaitable(rows):
        rows = await rows
    for row in rows:
        details = row.details or {}
        evidence_payload = validate_evidence_payload(
            raw=details.get(payload_key),
            model=payload_model,
            warning_event=warning_event,
            event_id=str(row.id),
            tenant_id=tenant_id,
        )
        if evidence_payload is None:
            continue
        item_payload = evidence_item_base(row)
        item_payload[payload_key] = evidence_payload
        items.append(item_model(**item_payload))

    return items
