"""DB session backend/context helper operations extracted from session facade."""

from __future__ import annotations

from typing import Any, AsyncGenerator, Callable
from uuid import UUID

from fastapi import Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_SESSION_BACKEND_CACHE_KEY = "_resolved_session_backend"


def backend_from_url(url: str) -> str | None:
    """Infer backend name from DSN string."""
    value = url.strip().lower()
    if not value:
        return None
    if "postgresql" in value:
        return "postgresql"
    if "sqlite" in value:
        return "sqlite"
    if "mysql" in value:
        return "mysql"
    return None


def resolve_session_backend(
    session: AsyncSession,
    *,
    backend_from_url_fn: Callable[[str], str | None],
    resolve_effective_url_fn: Callable[[Any], tuple[str, bool, bool]],
    get_settings_fn: Callable[[], Any],
    session_introspection_errors: tuple[type[Exception], ...],
    inspect_module: Any,
    logger_obj: Any,
) -> tuple[str, str]:
    """Resolve effective DB backend and attribution source for a session."""
    cached = _read_cached_session_backend(session)
    if cached is not None:
        return cached

    try:
        bind = getattr(session, "bind", None)
        if bind is not None:
            resolved = _resolve_backend_from_bind(
                bind=bind,
                source_prefix="session.bind",
                backend_from_url_fn=backend_from_url_fn,
            )
            if resolved is not None:
                _cache_session_backend(session, resolved)
                return resolved
    except session_introspection_errors as exc:
        logger_obj.debug("session_bind_introspection_failed", error=str(exc), exc_info=True)

    try:
        get_bind = getattr(session, "get_bind", None)
        runtime_bind = None
        if callable(get_bind):
            if inspect_module.iscoroutinefunction(get_bind):
                logger_obj.debug("session_get_bind_is_coroutine_skipped")
            else:
                runtime_bind = get_bind()
        if runtime_bind is not None:
            resolved = _resolve_backend_from_bind(
                bind=runtime_bind,
                source_prefix="session.get_bind()",
                backend_from_url_fn=backend_from_url_fn,
            )
            if resolved is not None:
                _cache_session_backend(session, resolved)
                return resolved
    except session_introspection_errors as exc:
        logger_obj.debug(
            "session_runtime_bind_resolution_failed", error=str(exc), exc_info=True
        )

    fallback_url, _, _ = resolve_effective_url_fn(get_settings_fn())
    fallback_backend = backend_from_url_fn(fallback_url)
    if fallback_backend is not None:
        logger_obj.warning(
            "session_dialect_fallback_used",
            backend=fallback_backend,
            source="configured_effective_url",
        )
        resolved = (fallback_backend, "configured_effective_url")
        _cache_session_backend(session, resolved)
        return resolved

    resolved = ("unknown", "unresolved")
    _cache_session_backend(session, resolved)
    return resolved


def _resolve_backend_from_bind(
    *,
    bind: Any,
    source_prefix: str,
    backend_from_url_fn: Callable[[str], str | None],
) -> tuple[str, str] | None:
    dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
    if isinstance(dialect_name, str) and dialect_name.strip():
        return dialect_name.strip().lower(), f"{source_prefix}.dialect.name"

    bind_url = getattr(bind, "url", None)
    if bind_url is not None:
        backend = backend_from_url_fn(str(bind_url))
        if backend is not None:
            return backend, f"{source_prefix}.url"
    return None


def _read_cached_session_backend(session: AsyncSession) -> tuple[str, str] | None:
    session_info = getattr(session, "info", None)
    if not isinstance(session_info, dict):
        return None
    cached = session_info.get(_SESSION_BACKEND_CACHE_KEY)
    if (
        isinstance(cached, tuple)
        and len(cached) == 2
        and isinstance(cached[0], str)
        and isinstance(cached[1], str)
    ):
        return cached[0], cached[1]
    return None


def _cache_session_backend(session: AsyncSession, resolved: tuple[str, str]) -> None:
    session_info = getattr(session, "info", None)
    if isinstance(session_info, dict):
        session_info[_SESSION_BACKEND_CACHE_KEY] = resolved


async def get_db_impl(
    *,
    request: Request | None,
    session_factory: Callable[..., Any],
    resolve_session_backend_fn: Callable[[AsyncSession], tuple[str, str]],
    rls_enforcement_latency_metric: Any,
    db_operation_recoverable_errors: tuple[type[Exception], ...],
    logger_obj: Any,
    time_module: Any,
) -> AsyncGenerator[AsyncSession, None]:
    """Internal implementation for FastAPI DB dependency."""
    async with session_factory() as session:
        rls_context_set = False

        if request is not None:
            tenant_id = getattr(request.state, "tenant_id", None)
            tenant_key = str(tenant_id) if isinstance(tenant_id, UUID) else tenant_id
            if tenant_id:
                try:
                    backend, source = resolve_session_backend_fn(session)
                    if backend == "postgresql":
                        rls_start = time_module.perf_counter()
                        await session.execute(
                            text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                            {"tid": str(tenant_id)},
                        )
                        rls_enforcement_latency_metric.observe(
                            time_module.perf_counter() - rls_start
                        )
                        rls_context_set = True
                    elif backend == "unknown":
                        logger_obj.error(
                            "rls_session_backend_unknown_fail_closed",
                            source=source,
                            tenant_id=tenant_key,
                        )
                        rls_context_set = False
                    else:
                        rls_context_set = True
                except db_operation_recoverable_errors as exc:
                    logger_obj.warning("rls_context_set_failed", error=str(exc))
        else:
            rls_context_set = True

        session.info["rls_context_set"] = rls_context_set
        session.info["rls_system_context"] = False

        conn = await session.connection()
        conn.info["rls_context_set"] = rls_context_set
        conn.info["rls_system_context"] = False

        yield session


async def mark_session_system_context(
    *,
    session: AsyncSession,
    db_operation_recoverable_errors: tuple[type[Exception], ...],
    logger_obj: Any,
) -> None:
    """Mark a session as explicit system/public context."""
    session_info = getattr(session, "info", None)
    if not isinstance(session_info, dict):
        logger_obj.debug("mark_session_system_context_missing_session_info_dict")
        return

    session_info["rls_context_set"] = None
    session_info["rls_system_context"] = True
    try:
        conn = await session.connection()
        conn.info["rls_context_set"] = None
        conn.info["rls_system_context"] = True
    except db_operation_recoverable_errors as exc:
        logger_obj.debug(
            "mark_session_system_context_connection_unavailable", error=str(exc)
        )


async def clear_session_tenant_context(
    *,
    session: AsyncSession,
    resolve_session_backend_fn: Callable[[AsyncSession], tuple[str, str]],
    db_operation_recoverable_errors: tuple[type[Exception], ...],
    logger_obj: Any,
) -> None:
    """Clear tenant/session RLS context and mark the session fail-closed."""
    session.info["tenant_id"] = None
    session.info["rls_context_set"] = False
    session.info["rls_system_context"] = False

    conn = await session.connection()
    conn.info["tenant_id"] = None
    conn.info["rls_context_set"] = False
    conn.info["rls_system_context"] = False

    backend, source = resolve_session_backend_fn(session)
    if backend == "postgresql":
        try:
            await session.execute(text("SELECT set_config('app.current_tenant_id', '', true)"))
        except db_operation_recoverable_errors as exc:
            logger_obj.warning("failed_to_clear_rls_config_in_session", error=str(exc))
    elif backend == "unknown":
        logger_obj.error(
            "clear_session_tenant_context_backend_unknown_fail_closed",
            source=source,
        )


async def set_session_tenant_id(
    *,
    session: AsyncSession,
    tenant_id: UUID | None,
    clear_session_tenant_context_fn: Callable[[AsyncSession], Any],
    resolve_session_backend_fn: Callable[[AsyncSession], tuple[str, str]],
    rls_enforcement_latency_metric: Any,
    db_operation_recoverable_errors: tuple[type[Exception], ...],
    logger_obj: Any,
    time_module: Any,
) -> None:
    """Set tenant context for a session. `tenant_id=None` clears context fail-closed."""
    if tenant_id is None:
        await clear_session_tenant_context_fn(session)
        return

    session.info["tenant_id"] = tenant_id

    conn = await session.connection()
    conn.info["tenant_id"] = tenant_id
    backend, source = resolve_session_backend_fn(session)
    if backend == "unknown":
        session.info["rls_context_set"] = False
        session.info["rls_system_context"] = False
        conn.info["rls_context_set"] = False
        conn.info["rls_system_context"] = False
        logger_obj.error(
            "set_session_tenant_id_backend_unknown_fail_closed",
            source=source,
            tenant_id=str(tenant_id),
        )
        return

    session.info["rls_context_set"] = True
    session.info["rls_system_context"] = False
    conn.info["rls_context_set"] = True
    conn.info["rls_system_context"] = False

    if backend == "postgresql":
        try:
            rls_start = time_module.perf_counter()
            await session.execute(
                text("SELECT set_config('app.current_tenant_id', :tid, true)"),
                {"tid": str(tenant_id)},
            )
            rls_enforcement_latency_metric.observe(time_module.perf_counter() - rls_start)
        except db_operation_recoverable_errors as exc:
            session.info["rls_context_set"] = False
            session.info["rls_system_context"] = False
            conn.info["rls_context_set"] = False
            conn.info["rls_system_context"] = False
            logger_obj.warning("failed_to_set_rls_config_in_session", error=str(exc))


__all__ = [
    "backend_from_url",
    "clear_session_tenant_context",
    "get_db_impl",
    "mark_session_system_context",
    "resolve_session_backend",
    "set_session_tenant_id",
]
