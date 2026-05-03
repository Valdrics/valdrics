"""Async cost export artifact construction."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
from datetime import date
from typing import Any, Dict
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_job import BackgroundJob
from app.modules.governance.domain.jobs.errors import PermanentJobError

logger = structlog.get_logger()
COST_EXPORT_PROVIDER_FILTERS = {
    "ai",
    "aws",
    "azure",
    "gcp",
    "saas",
    "license",
    "platform",
    "hybrid",
}
COST_EXPORT_INLINE_DEFAULT_MAX_BYTES = 1_000_000
COST_EXPORT_INLINE_HARD_MAX_BYTES = 5_000_000


def require_tenant_id(job: BackgroundJob) -> UUID:
    if job.tenant_id is None:
        raise PermanentJobError("tenant_id required")
    return job.tenant_id


def require_iso_date(payload: dict[str, Any], key: str) -> date:
    raw_value = payload.get(key)
    if not isinstance(raw_value, str):
        raise PermanentJobError(f"{key} must be an ISO date string")
    try:
        return date.fromisoformat(raw_value)
    except ValueError as exc:
        raise PermanentJobError(f"{key} must be an ISO date string") from exc


def normalize_cost_export_format(value: Any) -> str:
    normalized = str(value or "focus_v13_csv").strip().lower()
    if normalized in {"csv", "focus_csv", "focus_v13", "focus_v13_csv"}:
        return "focus_v13_csv"
    raise PermanentJobError("format must be one of: focus_v13_csv")


def normalize_cost_export_provider(value: Any) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip().lower()
    if not normalized:
        return None
    if normalized not in COST_EXPORT_PROVIDER_FILTERS:
        supported = ", ".join(sorted(COST_EXPORT_PROVIDER_FILTERS))
        raise PermanentJobError(f"provider must be one of: {supported}")
    return normalized


def payload_bool(payload: dict[str, Any], key: str, *, default: bool = False) -> bool:
    value = payload.get(key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    raise PermanentJobError(f"{key} must be a boolean")


def payload_positive_int(
    payload: dict[str, Any],
    key: str,
    *,
    default: int,
    maximum: int,
) -> int:
    raw_value = payload.get(key, default)
    try:
        value = int(raw_value)
    except (TypeError, ValueError) as exc:
        raise PermanentJobError(f"{key} must be a positive integer") from exc
    if value <= 0 or value > maximum:
        raise PermanentJobError(f"{key} must be between 1 and {maximum}")
    return value


async def build_cost_export_result(
    job: BackgroundJob,
    db: AsyncSession,
) -> Dict[str, Any]:
    from app.modules.reporting.api.v1.costs_helpers import sanitize_csv_cell
    from app.modules.reporting.domain.focus_export import (
        FOCUS_V13_CORE_COLUMNS,
        FocusV13ExportService,
    )

    payload = job.payload or {}
    tenant_id = require_tenant_id(job)
    start_date = require_iso_date(payload, "start_date")
    end_date = require_iso_date(payload, "end_date")
    if start_date > end_date:
        raise PermanentJobError("start_date must be <= end_date")
    export_format = normalize_cost_export_format(payload.get("format"))
    provider = normalize_cost_export_provider(payload.get("provider"))
    include_preliminary = payload_bool(payload, "include_preliminary", default=False)
    max_inline_bytes = payload_positive_int(
        payload,
        "max_inline_bytes",
        default=COST_EXPORT_INLINE_DEFAULT_MAX_BYTES,
        maximum=COST_EXPORT_INLINE_HARD_MAX_BYTES,
    )

    logger.info(
        "cost_export_started",
        tenant_id=str(tenant_id),
        start_date=str(start_date),
        end_date=str(end_date),
        provider=provider,
        format=export_format,
    )

    service = FocusV13ExportService(db)
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(FOCUS_V13_CORE_COLUMNS)
    record_count = 0

    async for row in service.export_rows(
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
        provider=provider,
        include_preliminary=include_preliminary,
    ):
        writer.writerow(
            [sanitize_csv_cell(row.get(col, "")) for col in FOCUS_V13_CORE_COLUMNS]
        )
        record_count += 1
        if out.tell() > max_inline_bytes:
            raise PermanentJobError(
                "Cost export exceeded max_inline_bytes; configure durable object "
                "storage before queuing larger async exports."
            )

    content = out.getvalue().encode("utf-8")
    if len(content) > max_inline_bytes:
        raise PermanentJobError(
            "Cost export exceeded max_inline_bytes; configure durable object "
            "storage before queuing larger async exports."
        )
    digest = hashlib.sha256(content).hexdigest()
    filename = (
        f"focus-v1.3-core-{start_date.isoformat()}-{end_date.isoformat()}"
        f"-{provider or 'all'}.csv"
    )

    logger.info(
        "cost_export_completed",
        tenant_id=str(tenant_id),
        records_exported=record_count,
        byte_size=len(content),
        sha256=digest,
    )
    return {
        "status": "completed",
        "export_format": export_format,
        "artifact": {
            "storage": "background_job.result.inline_base64",
            "filename": filename,
            "content_type": "text/csv",
            "sha256": digest,
            "byte_size": len(content),
            "content_base64": base64.b64encode(content).decode("ascii"),
        },
        "records_exported": record_count,
        "provider": provider,
        "include_preliminary": include_preliminary,
    }
