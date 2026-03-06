from __future__ import annotations

import copy
from datetime import date, datetime, timedelta
from typing import Any, Callable
from uuid import UUID


async def check_cache_and_delta(
    *,
    tenant_id: UUID | None,
    force_refresh: bool,
    usage_summary: Any,
    get_cache_service_fn: Callable[[], Any],
    get_settings_fn: Callable[[], Any],
    cost_record_cls: type[Any],
    logger_obj: Any,
) -> tuple[dict[str, Any] | None, bool]:
    """Check analysis cache and compute delta-mode records override when enabled."""
    if not tenant_id:
        return None, False

    cache = get_cache_service_fn()
    cached_analysis = await cache.get_analysis(tenant_id) if not force_refresh else None

    settings = get_settings_fn()
    if cached_analysis and not settings.ENABLE_DELTA_ANALYSIS:
        logger_obj.info("analysis_cache_hit_full", tenant_id=str(tenant_id))
        return cached_analysis, False

    is_delta = False
    if cached_analysis and settings.ENABLE_DELTA_ANALYSIS:
        is_delta = True
        logger_obj.info("analysis_delta_mode_enabled", tenant_id=str(tenant_id))
        delta_cutoff = date.today() - timedelta(days=settings.DELTA_ANALYSIS_DAYS)

        raw_records = (
            cached_analysis.get("records", [])
            if isinstance(cached_analysis, dict)
            else usage_summary.records
        )
        records_to_analyze = []
        for record in raw_records:
            record_dt = record.get("date") if isinstance(record, dict) else record.date

            if isinstance(record_dt, datetime):
                record_date = record_dt.date()
            elif isinstance(record_dt, date):
                record_date = record_dt
            elif isinstance(record_dt, str):
                try:
                    record_date = date.fromisoformat(record_dt[:10])
                except ValueError:
                    continue
            else:
                continue

            if record_date >= delta_cutoff:
                if isinstance(record, dict):
                    records_to_analyze.append(cost_record_cls(**record))
                else:
                    records_to_analyze.append(copy.deepcopy(record))

        if not records_to_analyze:
            logger_obj.info("analysis_delta_no_new_data", tenant_id=str(tenant_id))
            return cached_analysis, False

        usage_summary._analysis_records_override = records_to_analyze

    return cached_analysis, is_delta
