from __future__ import annotations

from typing import Any, Dict

from pydantic import BaseModel, Field


class CarbonFactorStageRequest(BaseModel):
    payload: Dict[str, Any] = Field(
        ..., description="Full canonical carbon factor payload."
    )
    message: str | None = Field(default=None, description="Optional operator notes.")


class CarbonFactorSetItem(BaseModel):
    id: str
    status: str
    is_active: bool
    factor_source: str
    factor_version: str
    factor_timestamp: str
    methodology_version: str
    factors_checksum_sha256: str
    created_at: str
    activated_at: str | None


class CarbonFactorSetListResponse(BaseModel):
    total: int
    items: list[CarbonFactorSetItem]


class CarbonFactorUpdateLogItem(BaseModel):
    id: str
    recorded_at: str
    action: str
    message: str | None
    old_factor_set_id: str | None
    new_factor_set_id: str | None
    old_checksum_sha256: str | None
    new_checksum_sha256: str | None
    details: Dict[str, Any]


class CarbonFactorUpdateLogListResponse(BaseModel):
    total: int
    items: list[CarbonFactorUpdateLogItem]
