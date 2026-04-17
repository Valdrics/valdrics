from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

import pytest
from app.shared.core.logging import (
    pii_redactor,
    add_managed_runtime_log_fields,
    audit_log,
    audit_log_async,
    _parse_tenant_id,
    setup_logging,
)


def test_pii_redactor_nested():
    """Verify recursive PII redaction for SOC2 compliance."""
    event_dict = {
        "user_id": 123,
        "email": "pii@example.com",
        "nested": {"token": "secret_123", "safe": "data"},
        "list": [{"password": "pass"}, "safe_item"],
    }

    redacted = pii_redactor(None, None, event_dict)

    # Email is regex-redacted in the value, not key-based
    assert redacted["email"] == "[EMAIL_REDACTED]"
    assert redacted["nested"]["token"] == "[REDACTED]"
    assert redacted["nested"]["safe"] == "data"
    assert redacted["list"][0]["password"] == "[REDACTED]"
    assert redacted["list"][1] == "safe_item"


def test_pii_redactor_regex():
    """Verify regex-based PII redaction for unstructured text in logs."""
    event_dict = {
        "event": "User login failed for admin@example.com from +234 803 123 4567",
        "details": "Contact support at help@valdrics.ai",
    }

    redacted = pii_redactor(None, None, event_dict)

    assert "admin@example.com" not in redacted["event"]
    assert "[EMAIL_REDACTED]" in redacted["event"]
    assert "+234 803 123 4567" not in redacted["event"]
    assert "[PHONE_REDACTED]" in redacted["event"]
    assert "help@valdrics.ai" not in redacted["details"]
    assert "[EMAIL_REDACTED]" in redacted["details"]


def test_add_managed_runtime_log_fields_adds_trace_metadata() -> None:
    """Verify trace metadata and severity injection for managed runtimes."""

    class _SpanContext:
        def __init__(self, trace_id: int, span_id: int, is_valid: bool = True) -> None:
            self.trace_id = trace_id
            self.span_id = span_id
            self.is_valid = is_valid

    class _Span:
        def __init__(self, context: _SpanContext) -> None:
            self._context = context

        def get_span_context(self) -> _SpanContext:
            return self._context

    trace_id = 0xABC
    span_id = 0x1234
    expected_trace_id = format(trace_id, "032x")
    expected_span_id = format(span_id, "016x")

    with (
        patch(
            "app.shared.core.logging.trace.get_current_span",
            return_value=_Span(_SpanContext(trace_id, span_id)),
        ),
        patch("app.shared.core.logging.get_settings") as mock_settings,
    ):
        mock_settings.return_value.GCP_PROJECT_ID = "valdrics-prod"
        result = add_managed_runtime_log_fields(
            None, None, {"event": "test", "level": "warning"}
        )

    assert result["severity"] == "WARNING"
    assert result["message"] == "test"
    assert result["trace_id"] == expected_trace_id
    assert (
        result["logging.googleapis.com/trace"]
        == f"projects/valdrics-prod/traces/{expected_trace_id}"
    )
    assert result["logging.googleapis.com/spanId"] == expected_span_id


def test_add_managed_runtime_log_fields_skips_invalid_span() -> None:
    """Verify invalid spans do not emit trace correlation fields."""

    class _SpanContext:
        def __init__(self) -> None:
            self.trace_id = 0
            self.span_id = 0
            self.is_valid = False

    class _Span:
        def __init__(self, context: _SpanContext) -> None:
            self._context = context

        def get_span_context(self) -> _SpanContext:
            return self._context

    with patch(
        "app.shared.core.logging.trace.get_current_span",
        return_value=_Span(_SpanContext()),
    ):
        result = add_managed_runtime_log_fields(
            None, None, {"event": "test", "level": "info"}
        )

    assert result["severity"] == "INFO"
    assert result["message"] == "test"
    assert "trace_id" not in result
    assert "logging.googleapis.com/trace" not in result
    assert "logging.googleapis.com/spanId" not in result


def test_audit_log_schema():
    """Verify audit log helper enforces the SIEM-friendly schema."""
    with patch("structlog.get_logger") as mock_get_logger:
        mock_audit_logger = MagicMock()
        mock_get_logger.return_value = mock_audit_logger

        audit_log("user_login", "u1", "t1", {"ip": "1.1.1.1"})

        mock_audit_logger.info.assert_called_with(
            "user_login", user_id="u1", tenant_id="t1", metadata={"ip": "1.1.1.1"}
        )


def test_parse_tenant_id_normalizes_uuid_strings() -> None:
    tenant_id = "d290f1ee-6c54-4b01-90e6-d701748f0851"

    assert _parse_tenant_id(tenant_id) == UUID(tenant_id)


@pytest.mark.asyncio
async def test_audit_log_async_isolated_parses_tenant_uuid_before_session_context() -> (
    None
):
    session = AsyncMock()
    parsed_tenant = UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")

    async def _log(**_: object) -> dict[str, str]:
        return {"status": "ok"}

    audit_logger_instance = MagicMock()
    audit_logger_instance.log = AsyncMock(side_effect=_log)

    class _SessionContext:
        async def __aenter__(self) -> AsyncMock:
            return session

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    with (
        patch(
            "app.shared.db.session.async_session_maker", return_value=_SessionContext()
        ),
        patch(
            "app.shared.db.session.set_session_tenant_id", new=AsyncMock()
        ) as set_tenant_id,
        patch(
            "app.modules.governance.domain.security.audit_log.AuditLogger",
            return_value=audit_logger_instance,
        ),
        patch("app.shared.core.logging.audit_log"),
    ):
        result = await audit_log_async(
            "user_login",
            "u1",
            str(parsed_tenant),
            {"ip": "1.1.1.1"},
            db=None,  # type: ignore[arg-type]
            isolated=True,
        )

    assert result == {"status": "ok"}
    set_tenant_id.assert_awaited_once_with(session, parsed_tenant)
    session.commit.assert_awaited_once()
    session.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_audit_log_async_isolated_uses_independent_session_for_duck_typed_db() -> (
    None
):
    caller_db = AsyncMock()
    session = AsyncMock()
    parsed_tenant = UUID("d290f1ee-6c54-4b01-90e6-d701748f0851")

    async def _log(**_: object) -> dict[str, str]:
        return {"status": "ok"}

    audit_logger_instance = MagicMock()
    audit_logger_instance.log = AsyncMock(side_effect=_log)

    class _SessionContext:
        async def __aenter__(self) -> AsyncMock:
            return session

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    with (
        patch(
            "app.shared.db.session.async_session_maker", return_value=_SessionContext()
        ),
        patch(
            "app.shared.db.session.set_session_tenant_id", new=AsyncMock()
        ) as set_tenant_id,
        patch(
            "app.modules.governance.domain.security.audit_log.AuditLogger",
            return_value=audit_logger_instance,
        ),
        patch("app.shared.core.logging.audit_log"),
    ):
        result = await audit_log_async(
            "user_login",
            "u1",
            str(parsed_tenant),
            {"ip": "1.1.1.1"},
            db=caller_db,  # type: ignore[arg-type]
            isolated=True,
        )

    assert result == {"status": "ok"}
    set_tenant_id.assert_awaited_once_with(session, parsed_tenant)
    session.commit.assert_awaited_once()
    caller_db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_audit_log_async_isolated_without_tenant_uses_system_audit_logger() -> (
    None
):
    session = AsyncMock()

    async def _log(**_: object) -> dict[str, str]:
        return {"status": "ok"}

    audit_logger_instance = MagicMock()
    audit_logger_instance.log = AsyncMock(side_effect=_log)

    class _SessionContext:
        async def __aenter__(self) -> AsyncMock:
            return session

        async def __aexit__(self, exc_type, exc, tb) -> bool:
            return False

    with (
        patch(
            "app.shared.db.session.async_session_maker", return_value=_SessionContext()
        ),
        patch(
            "app.shared.db.session.mark_session_system_context",
            new=AsyncMock(),
        ) as mark_system_context,
        patch(
            "app.modules.governance.domain.security.audit_log.SystemAuditLogger",
            return_value=audit_logger_instance,
        ),
        patch("app.shared.core.logging.audit_log"),
    ):
        result = await audit_log_async(
            "admin_auth_failed",
            "admin_portal",
            None,
            {"path": "/admin"},
            db=None,
            isolated=True,
        )

    assert result == {"status": "ok"}
    mark_system_context.assert_awaited_once_with(session)
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_audit_log_async_requires_db_when_not_isolated() -> None:
    with pytest.raises(ValueError, match="db session is required unless isolated=True"):
        await audit_log_async(
            "user_login",
            "u1",
            "d290f1ee-6c54-4b01-90e6-d701748f0851",
            {"ip": "1.1.1.1"},
            db=None,
            isolated=False,
        )


def test_setup_logging_no_crash():
    """Verify logging setup runs for both Debug and Prod modes."""
    with (
        patch("app.shared.core.logging.get_settings") as mock_settings,
        patch("app.shared.core.logging.structlog.configure") as mock_structlog,
        patch("app.shared.core.logging.logging.basicConfig") as mock_basic_config,
    ):
        # 1. Debug (Console)
        mock_settings.return_value.DEBUG = True
        mock_settings.return_value.TESTING = False
        mock_settings.return_value.GCP_PROJECT_ID = ""
        setup_logging()

        # 2. Prod (JSON)
        mock_settings.return_value.DEBUG = False
        mock_settings.return_value.GCP_PROJECT_ID = "valdrics-prod"
        setup_logging()
        assert mock_structlog.call_count == 2
        assert mock_basic_config.call_count == 2
