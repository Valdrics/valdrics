import inspect
import re
import ssl
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, AsyncGenerator, Dict, Optional, cast
from uuid import UUID

import structlog
from fastapi import Request
from sqlalchemy import event, text
from sqlalchemy.engine import Connection
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool, StaticPool

from app.shared.core.config import get_settings
from app.shared.core.constants import RLS_EXEMPT_TABLES
from app.shared.core.exceptions import ValdricsException
from app.shared.core.ops_metrics import RLS_CONTEXT_MISSING, RLS_ENFORCEMENT_LATENCY
from app.shared.db.session_context_ops import (
    backend_from_url as _backend_from_url_impl,
    clear_session_tenant_context as _clear_session_tenant_context_impl,
    get_db_impl as _get_db_impl_impl,
    mark_session_system_context as _mark_session_system_context_impl,
    resolve_session_backend as _resolve_session_backend_impl,
    set_session_tenant_id as _set_session_tenant_id_impl,
)
from app.shared.db.session_rls_ops import check_rls_policy as _check_rls_policy_impl

logger = structlog.get_logger()
__all__ = ["ValdricsException"]

# Ensure ORM mappings are registered for scripts/workers that import the DB layer
# without importing `app/main.py`.
import app.models  # noqa: F401, E402

settings = get_settings()

_RLS_EXEMPT_TABLE_PATTERN = re.compile(
    r"\b(" + "|".join(re.escape(table.lower()) for table in RLS_EXEMPT_TABLES) + r")\b"
)


@dataclass(slots=True)
class _DBRuntime:
    settings: Any
    engine: AsyncEngine
    session_maker: async_sessionmaker[AsyncSession]
    effective_url: str


_db_runtime: _DBRuntime | None = None
_db_runtime_lock = Lock()
DB_RUNTIME_DISPOSE_ERRORS = (AttributeError, TypeError, RuntimeError)
SESSION_INTROSPECTION_ERRORS = (AttributeError, TypeError, RuntimeError)
DB_OPERATION_RECOVERABLE_ERRORS = (
    SQLAlchemyError,
    RuntimeError,
    TypeError,
    ValueError,
    OSError,
)
RLS_METRIC_RECOVERABLE_ERRORS = (TypeError, ValueError, RuntimeError)


class GuardedAsyncSession(AsyncSession):
    """Async session with fail-safe rollback on commit errors."""

    async def commit(self) -> None:
        try:
            await super().commit()
        except DB_OPERATION_RECOVERABLE_ERRORS as exc:
            try:
                await super().rollback()
            except DB_OPERATION_RECOVERABLE_ERRORS as rollback_exc:
                logger.error(
                    "session_commit_rollback_failed",
                    commit_error=str(exc),
                    rollback_error=str(rollback_exc),
                )
            raise


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _normalize_db_url(raw_url: str) -> str:
    url = (raw_url or "").strip()
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def _resolve_effective_url(settings_obj: Any) -> tuple[str, bool, bool]:
    db_url = _normalize_db_url(str(getattr(settings_obj, "DATABASE_URL", "") or ""))
    allow_test_database_url = _as_bool(
        getattr(settings_obj, "ALLOW_TEST_DATABASE_URL", False)
    )
    use_null_pool = _as_bool(getattr(settings_obj, "DB_USE_NULL_POOL", False))
    external_pooler = _as_bool(getattr(settings_obj, "DB_EXTERNAL_POOLER", False))

    effective_url = db_url
    is_testing = bool(getattr(settings_obj, "TESTING", False))
    if is_testing and not db_url:
        effective_url = "sqlite+aiosqlite:///:memory:"
    elif is_testing and "sqlite" not in db_url and not allow_test_database_url:
        effective_url = "sqlite+aiosqlite:///:memory:"

    return effective_url, use_null_pool, external_pooler


def _build_connect_args(settings_obj: Any, effective_url: str) -> dict[str, Any]:
    connect_args: dict[str, Any] = {}
    ssl_mode = str(getattr(settings_obj, "DB_SSL_MODE", "require")).lower()

    if "postgresql" in effective_url:
        connect_args["statement_cache_size"] = 0  # Required for Supavisor

    if ssl_mode == "disable":
        logger.warning(
            "database_ssl_disabled",
            msg="SSL disabled - INSECURE, do not use in production!",
        )
        if "postgresql" in effective_url:
            connect_args["ssl"] = False
        return connect_args

    if ssl_mode == "require":
        ssl_context = ssl.create_default_context()
        if getattr(settings_obj, "DB_SSL_CA_CERT_PATH", None):
            ssl_context.load_verify_locations(cafile=settings_obj.DB_SSL_CA_CERT_PATH)
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.check_hostname = True
            logger.info(
                "database_ssl_require_verified",
                ca_cert=settings_obj.DB_SSL_CA_CERT_PATH,
            )
        else:
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.check_hostname = True
            logger.info(
                "database_ssl_require_system_trust",
                msg=(
                    "SSL enabled with system trust store verification. "
                    "Set DB_SSL_CA_CERT_PATH to pin an explicit CA bundle."
                ),
            )
        if "postgresql" in effective_url:
            connect_args["ssl"] = ssl_context
        return connect_args

    if ssl_mode in {"verify-ca", "verify-full"}:
        ca_cert = getattr(settings_obj, "DB_SSL_CA_CERT_PATH", None)
        if not ca_cert:
            raise ValueError(f"DB_SSL_CA_CERT_PATH required for ssl_mode={ssl_mode}")
        ssl_context = ssl.create_default_context(cafile=ca_cert)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = ssl_mode == "verify-full"
        if "postgresql" in effective_url:
            connect_args["ssl"] = ssl_context
        logger.info("database_ssl_verified", mode=ssl_mode, ca_cert=ca_cert)
        return connect_args

    raise ValueError(
        f"Invalid DB_SSL_MODE: {ssl_mode}. Use: disable, require, verify-ca, verify-full"
    )


def _build_pool_config(
    settings_obj: Any, effective_url: str, use_null_pool: bool, external_pooler: bool
) -> dict[str, Any]:
    is_sqlite = "sqlite" in effective_url
    pool_config: dict[str, Any] = {
        "pool_recycle": getattr(settings_obj, "DB_POOL_RECYCLE", 3600),
        "pool_pre_ping": True,
        "echo": bool(getattr(settings_obj, "DB_ECHO", False)),
    }

    if is_sqlite:
        pool_config["poolclass"] = StaticPool
    elif use_null_pool:
        pool_config["poolclass"] = NullPool
        logger.warning(
            "database_null_pool_enabled",
            msg="NullPool enabled for external DB pooler mode.",
            external_pooler=external_pooler,
        )
    else:
        pool_config.update(
            {
                "pool_size": int(getattr(settings_obj, "DB_POOL_SIZE", 20)),
                "max_overflow": int(getattr(settings_obj, "DB_MAX_OVERFLOW", 10)),
                "pool_timeout": int(getattr(settings_obj, "DB_POOL_TIMEOUT", 30)),
            }
        )

    if bool(getattr(settings_obj, "TESTING", False)):
        if not is_sqlite and not use_null_pool:
            pool_config.update({"pool_size": 2, "max_overflow": 2, "pool_timeout": 5})
        pool_config["pool_recycle"] = 60

    return pool_config


def _register_engine_event_listeners(engine: AsyncEngine) -> None:
    sync_engine = getattr(engine, "sync_engine", None)
    if sync_engine is None or type(sync_engine).__module__.startswith("unittest.mock"):
        logger.debug("db_engine_listener_registration_skipped_non_engine_target")
        return
    event.listen(sync_engine, "before_cursor_execute", check_rls_policy, retval=True)
    event.listen(sync_engine, "before_cursor_execute", before_cursor_execute)
    event.listen(sync_engine, "after_cursor_execute", after_cursor_execute)


def _build_db_runtime() -> _DBRuntime:
    settings_obj = get_settings()
    db_url = str(getattr(settings_obj, "DATABASE_URL", "") or "").strip()
    if not db_url and not bool(getattr(settings_obj, "TESTING", False)):
        raise ValueError("DATABASE_URL is not set. The application cannot start.")
    if not db_url:
        logger.debug("missing_db_url_in_testing_ignoring")

    effective_url, use_null_pool, external_pooler = _resolve_effective_url(settings_obj)
    connect_args = _build_connect_args(settings_obj, effective_url)
    pool_config = _build_pool_config(
        settings_obj, effective_url, use_null_pool, external_pooler
    )
    engine = create_async_engine(
        effective_url,
        **pool_config,
        connect_args=connect_args,
    )
    _register_engine_event_listeners(engine)
    session_maker = async_sessionmaker(
        engine,
        class_=GuardedAsyncSession,
        expire_on_commit=False,
    )
    return _DBRuntime(
        settings=settings_obj,
        engine=engine,
        session_maker=session_maker,
        effective_url=effective_url,
    )


def _get_db_runtime() -> _DBRuntime:
    global _db_runtime
    runtime = _db_runtime
    if runtime is not None:
        return runtime
    with _db_runtime_lock:
        runtime = _db_runtime
        if runtime is None:
            runtime = _build_db_runtime()
            _db_runtime = runtime
    return runtime


def reset_db_runtime() -> None:
    """Test helper for forcing runtime re-initialization on next access."""
    global _db_runtime
    runtime = _db_runtime
    _db_runtime = None

    if runtime is None:
        return

    try:
        runtime.engine.sync_engine.dispose()
    except DB_RUNTIME_DISPOSE_ERRORS as exc:
        logger.debug("db_runtime_dispose_skipped", error=str(exc), exc_info=True)


def get_engine() -> AsyncEngine:
    """Return the active async engine."""
    return _get_db_runtime().engine


def async_session_maker(*args: Any, **kwargs: Any) -> Any:
    """Return a new async session from the active session factory."""
    return _get_db_runtime().session_maker(*args, **kwargs)


def _get_slow_query_threshold_seconds() -> float:
    """Return configurable slow-query threshold with a safe fallback."""
    try:
        threshold = float(getattr(settings, "DB_SLOW_QUERY_THRESHOLD_SECONDS", 0.2))
    except (TypeError, ValueError):
        threshold = 0.2
    return threshold if threshold > 0 else 0.2


def before_cursor_execute(
    conn: Connection,
    _cursor: Any,
    _statement: str,
    _parameters: Any,
    _context: Any,
    _executemany: bool,
) -> None:
    """Record query start time."""
    conn.info.setdefault("query_start_time", []).append(time.perf_counter())


def after_cursor_execute(
    conn: Connection,
    _cursor: Any,
    statement: str,
    parameters: Any,
    _context: Any,
    _executemany: bool,
) -> None:
    """Log slow queries."""
    total = time.perf_counter() - conn.info["query_start_time"].pop(-1)
    threshold = _get_slow_query_threshold_seconds()
    if total > threshold:
        logger.warning(
            "slow_query_detected",
            duration_seconds=round(total, 3),
            threshold_seconds=threshold,
            statement=statement[:200] + "..." if len(statement) > 200 else statement,
            parameters=str(parameters)[:100] if parameters else None,
        )


def _session_uses_postgresql(session: AsyncSession) -> bool:
    backend, source = _resolve_session_backend(session)
    if backend == "unknown":
        logger.warning(
            "session_dialect_unknown",
            source=source,
            fail_safe_default=False,
        )
        return False
    return backend == "postgresql"


def _backend_from_url(url: str) -> Optional[str]:
    return _backend_from_url_impl(url)


def _resolve_session_backend(session: AsyncSession) -> tuple[str, str]:
    return _resolve_session_backend_impl(
        session,
        backend_from_url_fn=_backend_from_url,
        resolve_effective_url_fn=_resolve_effective_url,
        get_settings_fn=get_settings,
        session_introspection_errors=SESSION_INTROSPECTION_ERRORS,
        inspect_module=inspect,
        logger_obj=logger,
    )


async def _get_db_impl(
    request: Request = cast(Request, None),
) -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db_impl_impl(
        request=request,
        session_factory=async_session_maker,
        resolve_session_backend_fn=_resolve_session_backend,
        rls_enforcement_latency_metric=RLS_ENFORCEMENT_LATENCY,
        db_operation_recoverable_errors=DB_OPERATION_RECOVERABLE_ERRORS,
        logger_obj=logger,
        time_module=time,
    ):
        yield session


async def get_db(
    request: Request = cast(Request, None),
) -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_db_impl(request):
        yield session


async def mark_session_system_context(session: AsyncSession) -> None:
    await _mark_session_system_context_impl(
        session=session,
        db_operation_recoverable_errors=DB_OPERATION_RECOVERABLE_ERRORS,
        logger_obj=logger,
    )


async def _get_system_db_impl() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        await mark_session_system_context(session)
        yield session


async def get_system_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in _get_system_db_impl():
        yield session


async def clear_session_tenant_context(session: AsyncSession) -> None:
    await _clear_session_tenant_context_impl(
        session=session,
        resolve_session_backend_fn=_resolve_session_backend,
        db_operation_recoverable_errors=DB_OPERATION_RECOVERABLE_ERRORS,
        logger_obj=logger,
    )


async def set_session_tenant_id(session: AsyncSession, tenant_id: Optional[UUID]) -> None:
    await _set_session_tenant_id_impl(
        session=session,
        tenant_id=tenant_id,
        clear_session_tenant_context_fn=clear_session_tenant_context,
        resolve_session_backend_fn=_resolve_session_backend,
        rls_enforcement_latency_metric=RLS_ENFORCEMENT_LATENCY,
        db_operation_recoverable_errors=DB_OPERATION_RECOVERABLE_ERRORS,
        logger_obj=logger,
        time_module=time,
    )


def check_rls_policy(
    conn: Connection,
    _cursor: Any,
    statement: str,
    parameters: Any,
    _context: Any,
    _executemany: bool,
) -> tuple[str, Any]:
    return _check_rls_policy_impl(
        conn=conn,
        statement=statement,
        parameters=parameters,
        settings_obj=settings,
        rls_exempt_table_pattern=_RLS_EXEMPT_TABLE_PATTERN,
        rls_context_missing_metric=RLS_CONTEXT_MISSING,
        rls_metric_recoverable_errors=RLS_METRIC_RECOVERABLE_ERRORS,
        logger_obj=logger,
    )


async def health_check() -> Dict[str, Any]:
    """Database health check for monitoring."""
    start_time = time.perf_counter()
    try:
        db_engine = get_engine()
        async with async_session_maker() as session:
            await mark_session_system_context(session)
            await session.execute(text("SELECT 1"))

        latency = (time.perf_counter() - start_time) * 1000
        return {
            "status": "up",
            "latency_ms": round(latency, 2),
            "engine": (
                db_engine.dialect.name if hasattr(db_engine, "dialect") else "unknown"
            ),
        }
    except DB_OPERATION_RECOVERABLE_ERRORS as exc:
        logger.error("database_health_check_failed", error=str(exc))
        return {
            "status": "down",
            "error": str(exc),
            "latency_ms": (time.perf_counter() - start_time) * 1000,
        }
