import sys
import structlog
import logging
from typing import Any, cast
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.shared.core.config import get_settings
from app.shared.core.log_exporter import configure_otlp_log_export, mirror_event_to_otel
from app.shared.core.async_utils import maybe_await


def pii_redactor(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Recursively redact common PII and sensitive fields from logs.
    Ensures GDPR/SOC2 compliance by preventing leakage into telemetry.
    """
    import re

    email_regex = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
    phone_regex = re.compile(
        r"(?<!\w)(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}(?!\w)"
    )
    pii_fields = {
        "password",
        "token",
        "secret",
        "authorization",
        "auth",
        "api_key",
        "apikey",
        "ssn",
        "credit_card",
        "cc_number",
        "access_token",
        "refresh_token",
        "client_secret",
        "private_key",
        "x_api_key",
    }
    pii_suffixes = ("_token", "_secret", "_password", "_key")
    pii_contains = ("authorization", "secret", "token", "apikey", "api_key")

    def is_sensitive_key(key: Any) -> bool:
        key_str = str(key).lower().strip()
        key_norm = key_str.replace("-", "_")
        if key_norm in pii_fields:
            return True
        if key_norm.endswith(pii_suffixes):
            return True
        tokens = [t for t in re.split(r"[^a-z0-9]+", key_norm) if t]
        if any(t in pii_fields for t in tokens):
            return True
        return any(fragment in key_norm for fragment in pii_contains)

    def redact_text(text: Any) -> Any:
        if not isinstance(text, str):
            return text
        text = email_regex.sub("[EMAIL_REDACTED]", text)

        # Redact only plausible phone numbers (avoid timestamps/UUID fragments).
        def _replace_phone(match: re.Match[str]) -> str:
            candidate = match.group(0)
            digits = re.sub(r"\D", "", candidate)
            looks_like_phone = len(digits) >= 10 and (
                candidate.strip().startswith("+")
                or any(ch in candidate for ch in (" ", "-", ".", "(", ")"))
            )
            return "[PHONE_REDACTED]" if looks_like_phone else candidate

        text = phone_regex.sub(_replace_phone, text)
        return text

    def redact_recursive(data: Any) -> Any:
        if isinstance(data, dict):
            return {
                k: ("[REDACTED]" if is_sensitive_key(k) else redact_recursive(v))
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [redact_recursive(item) for item in data]
        elif isinstance(data, str):
            return redact_text(data)
        return data

    redacted = redact_recursive(event_dict)
    if isinstance(redacted, dict):
        return cast(dict[str, Any], redacted)
    return {}


def add_otel_trace_id(
    _logger: Any, _method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Integrate OTel Trace IDs into structured logs."""
    from app.shared.core.tracing import get_current_trace_id

    trace_id = get_current_trace_id()
    if trace_id:
        event_dict["trace_id"] = trace_id
    return event_dict


def setup_logging() -> None:
    settings = get_settings()
    configure_otlp_log_export(settings)

    # 1. Configure the common processors (Middleware Pipeline for Logs)
    base_processors = [
        structlog.contextvars.merge_contextvars,  # Support async context
        structlog.processors.add_log_level,  # Add "level": "info"
        structlog.processors.TimeStamper(fmt="iso"),  # Add "timestamp": "2026..."
        structlog.processors.StackInfoRenderer(),
        add_otel_trace_id,  # Observability: Add Trace IDs
        pii_redactor,  # Security: Redact PII before rendering
        mirror_event_to_otel,  # Centralized collector export
    ]

    # 2. Choose the renderer based on environment
    if settings.DEBUG:
        renderer: Any = structlog.dev.ConsoleRenderer()
        processors = base_processors + [renderer]
        min_level = logging.DEBUG
    else:
        renderer = structlog.processors.JSONRenderer()
        processors = base_processors + [structlog.processors.dict_tracebacks, renderer]
        min_level = logging.INFO

    # 3. Configure the logger or apply the configuration
    structlog.configure(
        processors=cast(Any, processors),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )

    # 4. Intercept the standard logging (e.g. uvicorn's internal log).
    # This ensure even library logs get formatted as JSON.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        # filename="debug.log",
        level=min_level,
    )
    logging.getLogger("uvicorn.access").propagate = True
    logging.getLogger("uvicorn.error").propagate = True


def audit_log(
    event: str,
    user_id: str,
    tenant_id: str,
    details: dict[str, Any] | None = None,
) -> None:
    """
    Standardized helper for security-critical audit events.
    Enforces a consistent schema for SIEM ingestion.
    """
    logger = structlog.get_logger("audit")
    logger.info(
        event,
        user_id=str(user_id),
        tenant_id=str(tenant_id),
        metadata=details or {},
    )


def _parse_tenant_id(value: str | UUID) -> UUID:
    return UUID(str(value))


async def audit_log_async(
    event: str,
    user_id: str | UUID | None,
    tenant_id: str | UUID | None,
    details: dict[str, Any] | None = None,
    *,
    db: AsyncSession | None,
    actor_email: str | None = None,
    actor_ip: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    success: bool = True,
    error_message: str | None = None,
    correlation_id: str | None = None,
    request_method: str | None = None,
    request_path: str | None = None,
    commit: bool = False,
    isolated: bool = False,
) -> Any:
    """
    Persist an audit event to `audit_logs` while preserving structured log emission.

    `commit=False` lets callers keep the audit row inside the surrounding transaction.
    `isolated=True` writes via an independent tenant-scoped session so the audit row
    survives outer transaction rollbacks for deny/error paths.
    """

    async def _write(session: AsyncSession) -> Any:
        if tenant_id is None:
            from app.modules.governance.domain.security.audit_log import (
                SystemAuditLogger,
            )

            system_entry = await SystemAuditLogger(
                session,
                correlation_id=correlation_id,
            ).log(
                event_type=event,
                actor_id=user_id,
                actor_email=actor_email,
                actor_ip=actor_ip,
                resource_type=resource_type,
                resource_id=resource_id,
                details=details,
                success=success,
                error_message=error_message,
                request_method=request_method,
                request_path=request_path,
            )
            audit_log(event, str(user_id or "system"), "system", details)
            return system_entry

        from app.modules.governance.domain.security.audit_log import AuditLogger

        tenant_entry = await AuditLogger(
            session,
            tenant_id=tenant_id,
            correlation_id=correlation_id,
        ).log(
            event_type=event,
            actor_id=user_id,
            actor_email=actor_email,
            actor_ip=actor_ip,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            success=success,
            error_message=error_message,
            request_method=request_method,
            request_path=request_path,
        )
        audit_log(event, str(user_id or "system"), str(tenant_id), details)
        return tenant_entry

    if isolated and db is not None and not isinstance(db, AsyncSession):
        entry = await _write(db)
        commit_fn = getattr(db, "commit", None)
        if callable(commit_fn):
            await maybe_await(commit_fn())
        return entry

    if isolated:
        from app.shared.db.session import (
            async_session_maker,
            mark_session_system_context,
            set_session_tenant_id,
        )

        async with async_session_maker() as session:
            if tenant_id is None:
                await mark_session_system_context(session)
            else:
                await set_session_tenant_id(session, _parse_tenant_id(tenant_id))
            entry = await _write(session)
            await maybe_await(session.commit())
            return entry

    if db is None:
        raise ValueError("db session is required unless isolated=True")

    entry = await _write(db)
    if commit:
        await maybe_await(db.commit())
    return entry
