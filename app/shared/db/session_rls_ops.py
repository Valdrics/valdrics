"""RLS policy enforcement helper operations for DB session facade."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Connection

from app.shared.core.exceptions import ValdricsException


def check_rls_policy(
    *,
    conn: Connection,
    statement: str,
    parameters: Any,
    settings_obj: Any,
    rls_exempt_table_pattern: Any,
    rls_context_missing_metric: Any,
    rls_metric_recoverable_errors: tuple[type[Exception], ...],
    logger_obj: Any,
) -> tuple[str, Any]:
    """Enforce fail-closed RLS posture for tenant-scoped SQL queries."""
    if settings_obj.TESTING and not settings_obj.ENFORCE_RLS_IN_TESTS:
        return statement, parameters

    stmt_lower = statement.lower()
    stmt_stripped = stmt_lower.lstrip()
    if stmt_stripped:
        verb = stmt_stripped.split(None, 1)[0]
        if verb not in {"select", "insert", "update", "delete", "with"}:
            return statement, parameters

    if (
        "select 1" in stmt_lower
        or "select version()" in stmt_lower
        or "select pg_is_in_recovery()" in stmt_lower
    ):
        return statement, parameters

    if rls_exempt_table_pattern.search(stmt_lower):
        return statement, parameters

    rls_status = conn.info.get("rls_context_set")
    rls_status_explicit = "rls_context_set" in conn.info
    rls_system_context = bool(conn.info.get("rls_system_context", False))

    if rls_status is None:
        if rls_system_context:
            return statement, parameters

        if not settings_obj.TESTING:
            try:
                if statement.split():
                    rls_context_missing_metric.labels(
                        statement_type=statement.split()[0].upper()
                    ).inc()
            except rls_metric_recoverable_errors as exc:
                logger_obj.debug("rls_metric_increment_failed", error=str(exc))

            logger_obj.critical(
                "rls_enforcement_ambiguous_context_detected",
                statement=statement[:500],
                rls_status=rls_status,
                rls_status_explicit=rls_status_explicit,
                rls_system_context=rls_system_context,
                error="Query executed with no explicit RLS/session context marker",
            )
            raise ValdricsException(
                message="RLS context unresolved - query execution aborted",
                code="rls_context_unresolved",
                status_code=500,
                details={
                    "reason": "No explicit tenant/system context marker for DB query",
                    "action": "Use get_db()/set_session_tenant_id for tenant flows, or mark_session_system_context for system flows.",
                },
            )

        logger_obj.warning(
            "rls_context_unset_in_testing",
            statement=statement[:120],
            rls_status_explicit=rls_status_explicit,
        )
        return statement, parameters

    if rls_status is False:
        try:
            if statement.split():
                rls_context_missing_metric.labels(
                    statement_type=statement.split()[0].upper()
                ).inc()
        except rls_metric_recoverable_errors as exc:
            logger_obj.debug("rls_metric_increment_failed", error=str(exc))

        logger_obj.critical(
            "rls_enforcement_violation_detected",
            statement=statement[:500],
            rls_status=rls_status,
            error="Query executed WITHOUT tenant insulation set. RLS policy violated!",
        )

        raise ValdricsException(
            message="RLS context missing - query execution aborted",
            code="rls_enforcement_failed",
            status_code=500,
            details={
                "reason": "Multi-tenant isolation enforcement failed",
                "action": "This is a critical security error. Check that all DB sessions are initialized with tenant context.",
            },
        )

    return statement, parameters


__all__ = ["check_rls_policy"]
