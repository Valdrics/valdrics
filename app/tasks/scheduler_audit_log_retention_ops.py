from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import inspect
from typing import Any, Callable

from sqlalchemy import tuple_

from app.tasks.scheduler_retention_utils import (
    coerce_positive_int,
    extract_deleted_count,
)


def _row_attr(row: Any, name: str) -> Any:
    return getattr(row, name, None)


async def purge_expired_audit_logs(
    *,
    db: Any,
    sa: Any,
    logger: Any,
    audit_log_model: Any,
    datetime_cls: type[datetime],
    timezone_obj: Any,
    timedelta_cls: Any,
    get_settings_fn: Callable[[], Any],
    set_audit_retention_purge_flag_fn: Callable[[Any, bool], Any] | None = None,
) -> dict[str, Any]:
    settings = get_settings_fn()
    retention_days = coerce_positive_int(
        getattr(settings, "AUDIT_LOG_RETENTION_DAYS", 90),
        default=90,
        minimum=1,
    )
    batch_size = coerce_positive_int(
        getattr(settings, "AUDIT_LOG_RETENTION_PURGE_BATCH_SIZE", 5000),
        default=5000,
        minimum=50,
    )
    max_batches = coerce_positive_int(
        getattr(settings, "AUDIT_LOG_RETENTION_PURGE_MAX_BATCHES", 20),
        default=20,
        minimum=1,
    )

    cutoff = datetime_cls.now(timezone_obj.utc) - timedelta_cls(days=retention_days)
    total_deleted = 0
    deleted_by_tenant: dict[Any, int] = defaultdict(int)
    tenant_id_column = getattr(audit_log_model, "tenant_id", None)

    if callable(set_audit_retention_purge_flag_fn):
        flag_result = set_audit_retention_purge_flag_fn(db, True)
        if inspect.isawaitable(flag_result):
            await flag_result

    try:
        for _ in range(max_batches):
            selection_columns = [
                audit_log_model.id,
                audit_log_model.event_timestamp,
            ]
            if tenant_id_column is not None:
                selection_columns.append(tenant_id_column)

            selection_stmt = (
                sa.select(*selection_columns)
                .where(audit_log_model.event_timestamp < cutoff)
                .order_by(audit_log_model.event_timestamp)
                .limit(batch_size)
            )
            selected_rows = list((await db.execute(selection_stmt)).all())
            if not selected_rows:
                break

            key_pairs = []
            for row in selected_rows:
                log_id = _row_attr(row, "id")
                event_timestamp = _row_attr(row, "event_timestamp")
                tenant_id = (
                    _row_attr(row, "tenant_id") if tenant_id_column is not None else None
                )
                if log_id is None or event_timestamp is None:
                    continue
                key_pairs.append((log_id, event_timestamp))
                if tenant_id is not None:
                    deleted_by_tenant[tenant_id] += 1

            if not key_pairs:
                break

            delete_stmt = sa.delete(audit_log_model).where(
                tuple_(audit_log_model.id, audit_log_model.event_timestamp).in_(key_pairs)
            )
            delete_result = await db.execute(delete_stmt)
            deleted_count = extract_deleted_count(delete_result, fallback=len(key_pairs))
            if deleted_count == 0:
                break
            total_deleted += deleted_count
    finally:
        if callable(set_audit_retention_purge_flag_fn):
            flag_result = set_audit_retention_purge_flag_fn(db, False)
            if inspect.isawaitable(flag_result):
                await flag_result

    if total_deleted:
        logger.info(
            "maintenance_audit_logs_purged",
            deleted=total_deleted,
            retention_days=retention_days,
            batch_size=batch_size,
            max_batches=max_batches,
        )

    tenant_reports = [
        {"tenant_id": tenant_id, "deleted_count": deleted_count}
        for tenant_id, deleted_count in sorted(deleted_by_tenant.items())
        if deleted_count > 0
    ]
    return {
        "total_deleted": total_deleted,
        "retention_days": retention_days,
        "batch_size": batch_size,
        "max_batches": max_batches,
        "cutoff": cutoff.isoformat(),
        "tenant_reports": tenant_reports,
    }
