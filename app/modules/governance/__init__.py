from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["AuditLogger", "AuditEventType", "SchedulerService"]


if TYPE_CHECKING:
    from .domain.scheduler import SchedulerService
    from .domain.security.audit_log import AuditEventType, AuditLogger


def __getattr__(name: str) -> Any:
    if name in {"AuditLogger", "AuditEventType"}:
        from .domain.security.audit_log import AuditEventType, AuditLogger

        exports = {
            "AuditLogger": AuditLogger,
            "AuditEventType": AuditEventType,
        }
        return exports[name]
    if name == "SchedulerService":
        from .domain.scheduler import SchedulerService

        return SchedulerService
    raise AttributeError(name)
