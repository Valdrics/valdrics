from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException
from fastapi.params import Param

from app.models.carbon_factors import CarbonFactorSet, CarbonFactorUpdateLog
from app.modules.reporting.api.v1.carbon_models import (
    CarbonFactorSetItem,
    CarbonFactorUpdateLogItem,
)
from app.shared.core.auth import CurrentUser
from app.shared.core.connection_state import resolve_connection_region


def factor_set_to_item(row: CarbonFactorSet) -> CarbonFactorSetItem:
    return CarbonFactorSetItem(
        id=str(row.id),
        status=str(row.status),
        is_active=bool(row.is_active),
        factor_source=str(row.factor_source),
        factor_version=str(row.factor_version),
        factor_timestamp=row.factor_timestamp.isoformat(),
        methodology_version=str(row.methodology_version),
        factors_checksum_sha256=str(row.factors_checksum_sha256),
        created_at=row.created_at.isoformat(),
        activated_at=row.activated_at.isoformat() if row.activated_at else None,
    )


def update_log_to_item(row: CarbonFactorUpdateLog) -> CarbonFactorUpdateLogItem:
    return CarbonFactorUpdateLogItem(
        id=str(row.id),
        recorded_at=row.recorded_at.isoformat(),
        action=str(row.action),
        message=row.message,
        old_factor_set_id=str(row.old_factor_set_id) if row.old_factor_set_id else None,
        new_factor_set_id=str(row.new_factor_set_id) if row.new_factor_set_id else None,
        old_checksum_sha256=row.old_checksum_sha256,
        new_checksum_sha256=row.new_checksum_sha256,
        details=row.details if isinstance(row.details, dict) else {},
    )


def require_tenant_id(user: CurrentUser) -> UUID:
    if user.tenant_id is None:
        raise HTTPException(status_code=401, detail="Tenant context required")
    return user.tenant_id


def normalize_provider(provider: str, *, supported_providers: set[str]) -> str:
    normalized = provider.strip().lower()
    if normalized not in supported_providers:
        supported = ", ".join(sorted(supported_providers))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported provider '{provider}'. Use one of: {supported}",
        )
    return normalized


def resolve_region_hint(provider: str, requested_region: str) -> str:
    region = requested_region.strip().lower()
    if not region:
        return "us-east-1" if provider == "aws" else "global"
    if region == "global":
        return "global"
    if provider != "aws" and region == "us-east-1":
        return "global"
    return region


def resolve_calc_region(connection: Any, provider: str, requested_region: str) -> str:
    region = requested_region.strip().lower()
    if (
        region
        and region != "global"
        and not (provider != "aws" and region == "us-east-1")
    ):
        return region
    return resolve_connection_region(connection)


def coerce_query_str(value: Any, *, default: str) -> str:
    if isinstance(value, Param):
        value = value.default
    normalized = str(value or "").strip()
    return normalized or default


def coerce_query_int(
    value: Any,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if isinstance(value, Param):
        value = value.default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    if parsed < minimum:
        return minimum
    if parsed > maximum:
        return maximum
    return parsed
