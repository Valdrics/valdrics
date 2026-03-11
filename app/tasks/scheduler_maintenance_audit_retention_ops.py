from __future__ import annotations

from typing import Any


async def _await_if_needed(result: Any, inspect_module: Any) -> Any:
    if inspect_module.isawaitable(result):
        return await result
    return result


async def _commit(db: Any, inspect_module: Any) -> None:
    await _await_if_needed(db.commit(), inspect_module)


async def _rollback(db: Any, inspect_module: Any) -> None:
    await _await_if_needed(db.rollback(), inspect_module)


def _empty_audit_retention_summary() -> dict[str, Any]:
    return {
        "total_deleted": 0,
        "retention_days": None,
        "batch_size": None,
        "max_batches": None,
        "cutoff": None,
        "tenant_reports": [],
    }


async def _purge_tenant_audit_logs(
    *,
    db: Any,
    sa: Any,
    inspect_module: Any,
    datetime_cls: Any,
    timezone_obj: Any,
    timedelta_cls: Any,
    logger: Any,
    recoverable_errors: tuple[type[Exception], ...],
) -> tuple[dict[str, Any], bool]:
    from uuid import uuid4

    from app.modules.governance.domain.security.audit_log import AuditEventType, AuditLog
    from app.shared.core.config import get_settings
    from app.shared.core.logging import audit_log_async
    from app.shared.core.ops_metrics import record_audit_log_retention_failure
    from app.shared.db.session import allow_audit_log_retention_purge
    from app.tasks.scheduler_audit_log_retention_ops import purge_expired_audit_logs

    summary = _empty_audit_retention_summary()
    try:
        summary = await purge_expired_audit_logs(
            db=db,
            sa=sa,
            logger=logger,
            audit_log_model=AuditLog,
            datetime_cls=datetime_cls,
            timezone_obj=timezone_obj,
            timedelta_cls=timedelta_cls,
            get_settings_fn=get_settings,
            set_audit_retention_purge_flag_fn=allow_audit_log_retention_purge,
        )
        if summary["total_deleted"] > 0:
            await _commit(db, inspect_module)
            retention_run_id = str(uuid4())
            for tenant_report in summary["tenant_reports"]:
                tenant_id = tenant_report.get("tenant_id")
                if not tenant_id:
                    continue
                await audit_log_async(
                    AuditEventType.SYSTEM_MAINTENANCE.value,
                    None,
                    str(tenant_id),
                    {
                        "run_id": retention_run_id,
                        "captured_at": datetime_cls.now(timezone_obj.utc).isoformat(),
                        "retention_days": summary["retention_days"],
                        "batch_size": summary["batch_size"],
                        "max_batches": summary["max_batches"],
                        "cutoff": summary["cutoff"],
                        "tenant_deleted_count": tenant_report.get("deleted_count", 0),
                        "total_deleted": summary["total_deleted"],
                    },
                    db=db,
                    resource_type="audit_logs_retention",
                    resource_id=str(summary["retention_days"]),
                    success=True,
                    correlation_id=retention_run_id,
                    request_method="SCHEDULER",
                    request_path="/scheduler/maintenance_sweep/audit_logs_retention",
                    isolated=True,
                )
        logger.info("maintenance_tenant_audit_logs_retention_success", **summary)
        return summary, False
    except recoverable_errors as exc:
        await _rollback(db, inspect_module)
        record_audit_log_retention_failure("audit_logs_retention")
        logger.warning("maintenance_audit_logs_retention_failed", error=str(exc))
        return summary, True


async def _purge_system_audit_logs(
    *,
    db: Any,
    sa: Any,
    inspect_module: Any,
    datetime_cls: Any,
    timezone_obj: Any,
    timedelta_cls: Any,
    logger: Any,
    recoverable_errors: tuple[type[Exception], ...],
) -> tuple[dict[str, Any], bool]:
    from uuid import uuid4

    from app.modules.governance.domain.security.audit_log import (
        AuditEventType,
        SystemAuditLog,
    )
    from app.shared.core.config import get_settings
    from app.shared.core.logging import audit_log_async
    from app.shared.core.ops_metrics import record_audit_log_retention_failure
    from app.shared.db.session import allow_system_audit_log_retention_purge
    from app.tasks.scheduler_audit_log_retention_ops import purge_expired_audit_logs

    summary = _empty_audit_retention_summary()
    try:
        summary = await purge_expired_audit_logs(
            db=db,
            sa=sa,
            logger=logger,
            audit_log_model=SystemAuditLog,
            datetime_cls=datetime_cls,
            timezone_obj=timezone_obj,
            timedelta_cls=timedelta_cls,
            get_settings_fn=get_settings,
            set_audit_retention_purge_flag_fn=allow_system_audit_log_retention_purge,
        )
        if summary["total_deleted"] > 0:
            await _commit(db, inspect_module)
            retention_run_id = str(uuid4())
            await audit_log_async(
                AuditEventType.SYSTEM_MAINTENANCE.value,
                None,
                None,
                {
                    "run_id": retention_run_id,
                    "captured_at": datetime_cls.now(timezone_obj.utc).isoformat(),
                    "retention_days": summary["retention_days"],
                    "batch_size": summary["batch_size"],
                    "max_batches": summary["max_batches"],
                    "cutoff": summary["cutoff"],
                    "total_deleted": summary["total_deleted"],
                },
                db=db,
                resource_type="system_audit_logs_retention",
                resource_id=str(summary["retention_days"]),
                success=True,
                correlation_id=retention_run_id,
                request_method="SCHEDULER",
                request_path="/scheduler/maintenance_sweep/system_audit_logs_retention",
                isolated=True,
            )
        logger.info("maintenance_system_audit_logs_retention_success", **summary)
        return summary, False
    except recoverable_errors as exc:
        await _rollback(db, inspect_module)
        record_audit_log_retention_failure("system_audit_logs_retention")
        logger.warning("maintenance_system_audit_logs_retention_failed", error=str(exc))
        return summary, True


async def run_audit_log_retention(
    *,
    db: Any,
    sa: Any,
    inspect_module: Any,
    datetime_cls: Any,
    timezone_obj: Any,
    timedelta_cls: Any,
    logger: Any,
    recoverable_errors: tuple[type[Exception], ...],
) -> None:
    try:
        from app.shared.core.ops_metrics import (
            record_audit_log_retention_failure,
            record_audit_log_retention_purge,
        )

        tenant_summary, tenant_failed = await _purge_tenant_audit_logs(
            db=db,
            sa=sa,
            inspect_module=inspect_module,
            datetime_cls=datetime_cls,
            timezone_obj=timezone_obj,
            timedelta_cls=timedelta_cls,
            logger=logger,
            recoverable_errors=recoverable_errors,
        )
        system_summary, system_failed = await _purge_system_audit_logs(
            db=db,
            sa=sa,
            inspect_module=inspect_module,
            datetime_cls=datetime_cls,
            timezone_obj=timezone_obj,
            timedelta_cls=timedelta_cls,
            logger=logger,
            recoverable_errors=recoverable_errors,
        )

        failed_operations = [
            name
            for name, failed in (
                ("audit_logs_retention", tenant_failed),
                ("system_audit_logs_retention", system_failed),
            )
            if failed
        ]
        total_deleted = int(tenant_summary["total_deleted"] or 0) + int(
            system_summary["total_deleted"] or 0
        )
        record_audit_log_retention_purge(total_deleted)

        summary_event = (
            "maintenance_audit_logs_retention_success"
            if not failed_operations
            else "maintenance_audit_logs_retention_partial_failure"
        )
        log_method = logger.info if not failed_operations else logger.warning
        log_method(
            summary_event,
            total_deleted=total_deleted,
            tenant_total_deleted=int(tenant_summary["total_deleted"] or 0),
            system_total_deleted=int(system_summary["total_deleted"] or 0),
            retention_days=tenant_summary["retention_days"] or system_summary["retention_days"],
            batch_size=tenant_summary["batch_size"] or system_summary["batch_size"],
            max_batches=tenant_summary["max_batches"] or system_summary["max_batches"],
            cutoff=tenant_summary["cutoff"] or system_summary["cutoff"],
            failed_operations=failed_operations,
        )
    except recoverable_errors as exc:
        await _rollback(db, inspect_module)
        from app.shared.core.ops_metrics import record_audit_log_retention_failure

        record_audit_log_retention_failure("audit_logs_retention_orchestration")
        logger.warning(
            "maintenance_audit_logs_retention_orchestration_failed",
            error=str(exc),
        )
