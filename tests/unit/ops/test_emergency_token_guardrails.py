from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from scripts import emergency_token


def _base_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("VALDRICS_EMERGENCY_TOKEN_ENABLED", "true")
    monkeypatch.setenv("VALDRICS_ALLOW_NONINTERACTIVE_EMERGENCY_TOKEN", "true")


def test_validate_request_rejects_missing_operator(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)

    with pytest.raises(RuntimeError, match="operator"):
        emergency_token._validate_request(
            email="owner@example.com",
            force=True,
            phrase="VALDRICS_BREAK_GLASS",
            ttl_hours=1,
            operator="",
            reason="Need to recover platform access after SSO outage.",
            confirm_environment="development",
            no_prompt=True,
        )


def test_validate_request_rejects_short_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)

    with pytest.raises(RuntimeError, match="at least"):
        emergency_token._validate_request(
            email="owner@example.com",
            force=True,
            phrase="VALDRICS_BREAK_GLASS",
            ttl_hours=1,
            operator="ops-admin",
            reason="too short",
            confirm_environment="development",
            no_prompt=True,
        )


def test_validate_request_rejects_protected_env_without_bypass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _base_env(monkeypatch)
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("VALDRICS_ALLOW_PROD_EMERGENCY_TOKEN", raising=False)

    with pytest.raises(RuntimeError, match="protected environment"):
        emergency_token._validate_request(
            email="owner@example.com",
            force=True,
            phrase="VALDRICS_BREAK_GLASS",
            ttl_hours=1,
            operator="ops-admin",
            reason="Need to recover platform access after SSO outage.",
            confirm_environment="production",
            no_prompt=True,
        )


def test_validate_request_accepts_explicit_break_glass(monkeypatch: pytest.MonkeyPatch) -> None:
    _base_env(monkeypatch)

    emergency_token._validate_request(
        email="owner@example.com",
        force=True,
        phrase="VALDRICS_BREAK_GLASS",
        ttl_hours=1,
        operator="ops-admin",
        reason="Need to recover platform access after SSO outage.",
        confirm_environment="development",
        no_prompt=True,
    )


@pytest.mark.parametrize("role", ["member", "viewer", ""])
def test_validate_target_role_rejects_non_admin_targets(role: str) -> None:
    with pytest.raises(RuntimeError, match="owner/admin"):
        emergency_token._validate_target_role(role)


@pytest.mark.parametrize("role", ["owner", "admin", "ADMIN", " Owner "])
def test_validate_target_role_accepts_privileged_targets(role: str) -> None:
    emergency_token._validate_target_role(role)


@pytest.mark.asyncio
async def test_generate_token_falls_back_to_decrypted_privileged_email_match(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Session:
        def __init__(self) -> None:
            self.commit = AsyncMock()

        async def execute(self, statement):
            del statement
            return SimpleNamespace(
                all=lambda: [
                    ("user-1", "enc-owner", "owner", "tenant-1"),
                    ("user-2", "enc-admin", "admin", "tenant-2"),
                ]
            )

    session = Session()

    class SessionFactory:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    class AuditLogger:
        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs

        async def log(self, **kwargs) -> None:
            self.logged = kwargs

    monkeypatch.setattr(emergency_token, "load_dotenv", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        emergency_token,
        "_repo_root",
        lambda: emergency_token.Path("/tmp/fake-repo"),
    )
    class _FakeStatement:
        def where(self, *_args, **_kwargs):
            return self

        def order_by(self, *_args, **_kwargs):
            return self

    monkeypatch.setattr(emergency_token, "select", lambda *_args, **_kwargs: _FakeStatement())
    class _FakeColumn:
        def in_(self, values):
            return values

        def asc(self):
            return self

    monkeypatch.setitem(
        __import__("sys").modules,
        "app.models.tenant",
        SimpleNamespace(
            User=SimpleNamespace(
                id=_FakeColumn(),
                email=_FakeColumn(),
                role=_FakeColumn(),
                tenant_id=_FakeColumn(),
            )
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.shared.core.auth",
        SimpleNamespace(create_access_token=lambda payload, expires_delta: f"token:{payload['email']}"),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.shared.core.security",
        SimpleNamespace(
            decrypt_string=lambda value, context: {
                "enc-owner": "owner@example.com",
                "enc-admin": "admin@example.com",
            }[value],
        ),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.shared.db.session",
        SimpleNamespace(async_session_maker=lambda: SessionFactory()),
    )
    monkeypatch.setitem(
        __import__("sys").modules,
        "app.modules.governance.domain.security.audit_log",
        SimpleNamespace(
            AuditEventType=SimpleNamespace(SECURITY_EMERGENCY_TOKEN_ISSUED="issued"),
            AuditLogger=AuditLogger,
        ),
    )

    token = await emergency_token.generate_token(
        email="ADMIN@example.com",
        ttl_hours=1,
        operator="ops-admin",
        reason="Need to recover platform access after SSO outage.",
    )

    assert token == "token:admin@example.com"
    session.commit.assert_awaited_once()


def test_main_accepts_explicit_argv_without_parsing_pytest_flags(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        emergency_token,
        "_validate_request",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("invalid request")),
    )

    assert emergency_token.main([]) == 2
    assert "invalid request" in capsys.readouterr().err
