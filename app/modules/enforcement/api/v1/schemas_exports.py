from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EnforcementExportParityResponse(BaseModel):
    generated_at: datetime
    window_start: datetime
    window_end: datetime
    decision_count_db: int = Field(..., ge=0)
    decision_count_exported: int = Field(..., ge=0)
    approval_count_db: int = Field(..., ge=0)
    approval_count_exported: int = Field(..., ge=0)
    decisions_sha256: str = Field(..., min_length=64, max_length=64)
    approvals_sha256: str = Field(..., min_length=64, max_length=64)
    policy_lineage_sha256: str = Field(..., min_length=64, max_length=64)
    policy_lineage_entries: int = Field(..., ge=0)
    computed_context_lineage_sha256: str = Field(..., min_length=64, max_length=64)
    computed_context_lineage_entries: int = Field(..., ge=0)
    parity_ok: bool
    manifest_content_sha256: str = Field(..., min_length=64, max_length=64)
    manifest_signature: str = Field(..., min_length=64, max_length=64)
    manifest_signature_algorithm: Literal["hmac-sha256"]
    manifest_signature_key_id: str = Field(..., min_length=1, max_length=64)


class DecisionLedgerItem(BaseModel):
    ledger_id: UUID
    decision_id: UUID
    source: str
    environment: str
    project_id: str
    action: str
    resource_reference: str
    decision: str
    reason_codes: list[str]
    policy_version: int
    policy_document_schema_version: str
    policy_document_sha256: str = Field(..., min_length=64, max_length=64)
    request_fingerprint: str
    idempotency_key: str
    estimated_monthly_delta_usd: Decimal
    estimated_hourly_delta_usd: Decimal
    burn_rate_daily_usd: Decimal | None = None
    forecast_eom_usd: Decimal | None = None
    risk_class: str | None = None
    risk_score: int | None = None
    anomaly_signal: bool | None = None
    reserved_total_usd: Decimal
    approval_required: bool
    approval_request_id: UUID | None = None
    approval_status: str | None = None
    request_payload_sha256: str
    response_payload_sha256: str
    decision_created_at: datetime
    recorded_at: datetime


__all__ = [
    "EnforcementExportParityResponse",
    "DecisionLedgerItem",
]
