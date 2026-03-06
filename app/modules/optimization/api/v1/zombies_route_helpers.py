from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from fastapi.params import Param
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.remediation import RemediationAction, RemediationRequest, RemediationStatus
from app.modules.governance.domain.security.remediation_policy import (
    is_production_destructive_remediation,
    is_production_remediation_target,
)
from app.shared.core.approval_permissions import (
    APPROVAL_PERMISSION_REMEDIATION_APPROVE_NONPROD,
    APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
)
from app.shared.core.auth import CurrentUser
from app.shared.core.exceptions import ResourceNotFoundError, ValdricsException
from app.shared.core.pricing import PricingTier, normalize_tier
from app.shared.core.remediation_results import (
    normalize_remediation_status,
    parse_remediation_execution_error,
)

DEFAULT_REGION_HINT = "global"


def coerce_region_hint(value: Any) -> str:
    if isinstance(value, Param):
        value = value.default
    normalized = str(value or "").strip().lower()
    return normalized or DEFAULT_REGION_HINT


def coerce_query_bool(value: Any, *, default: bool = False) -> bool:
    if isinstance(value, Param):
        value = value.default
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return bool(value)


def coerce_query_int(
    value: Any,
    *,
    default: int,
    minimum: int | None = None,
) -> int:
    if isinstance(value, Param):
        value = value.default
    if value is None:
        coerced = default
    else:
        try:
            coerced = int(value)
        except (TypeError, ValueError):
            coerced = default
    if minimum is not None and coerced < minimum:
        return minimum
    return coerced


def parse_remediation_action(action: str) -> RemediationAction:
    try:
        return RemediationAction(action)
    except ValueError as exc:
        raise ValdricsException(
            message=f"Invalid action: {action}",
            code="invalid_remediation_action",
            status_code=400,
        ) from exc


def raise_if_failed_execution(executed_request: RemediationRequest) -> None:
    status_value = normalize_remediation_status(getattr(executed_request, "status", None))
    if status_value != RemediationStatus.FAILED.value:
        return

    failure = parse_remediation_execution_error(
        getattr(executed_request, "execution_error", None)
    )

    raise ValdricsException(
        message=failure.message,
        code=failure.reason,
        status_code=failure.status_code or 400,
    )


async def load_remediation_request_for_authorization(
    db: AsyncSession,
    *,
    request_id: UUID,
    tenant_id: UUID,
) -> RemediationRequest:
    result = await db.execute(
        select(RemediationRequest)
        .where(RemediationRequest.id == request_id)
        .where(RemediationRequest.tenant_id == tenant_id)
    )
    remediation_request = result.scalar_one_or_none()
    if remediation_request is None:
        raise ResourceNotFoundError(f"Remediation request {request_id} not found")
    return remediation_request


def required_approval_permission(remediation_request: RemediationRequest) -> str:
    if is_production_destructive_remediation(remediation_request):
        return APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD
    return APPROVAL_PERMISSION_REMEDIATION_APPROVE_NONPROD


def enforce_growth_nonprod_auto_remediation(
    *, user: CurrentUser, remediation_request: RemediationRequest
) -> None:
    if normalize_tier(user.tier) != PricingTier.GROWTH:
        return
    if not is_production_remediation_target(remediation_request):
        return
    raise HTTPException(
        status_code=403,
        detail=(
            "Growth tier allows auto-remediation for non-production resources only. "
            "Upgrade to Pro for production remediation."
        ),
    )
