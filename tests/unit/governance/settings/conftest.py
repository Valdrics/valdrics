from __future__ import annotations

import os
import uuid
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextlib import ExitStack
from pathlib import Path
from tempfile import mkstemp
from typing import Any, TYPE_CHECKING

import pytest
import pytest_asyncio

from app.shared.core.auth import CurrentUser, UserRole, get_current_user
from app.shared.core.pricing import PricingTier

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from httpx import AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession

_UNSET = object()


@pytest.fixture
def make_current_user() -> Callable[..., CurrentUser]:
    def _make(
        *,
        role: UserRole = UserRole.ADMIN,
        tier: PricingTier | None = None,
        tenant_id: uuid.UUID | None | object = _UNSET,
        user_id: uuid.UUID | object = _UNSET,
        email: str | None = None,
    ) -> CurrentUser:
        resolved_tenant_id = (
            uuid.uuid4() if tenant_id is _UNSET else tenant_id
        )
        resolved_user_id = uuid.uuid4() if user_id is _UNSET else user_id
        resolved_email = email or (
            "admin@notify.io" if role is UserRole.ADMIN else "member@notify.io"
        )

        kwargs: dict[str, Any] = {
            "id": resolved_user_id,
            "tenant_id": resolved_tenant_id,
            "email": resolved_email,
            "role": role,
        }
        if tier is not None:
            kwargs["tier"] = tier
        return CurrentUser(**kwargs)

    return _make


@pytest.fixture
def override_current_user() -> Callable[[Any, CurrentUser], Iterator[CurrentUser]]:
    @contextmanager
    def _override(app: Any, user: CurrentUser) -> Iterator[CurrentUser]:
        app.dependency_overrides[get_current_user] = lambda: user
        try:
            yield user
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    return _override


@pytest_asyncio.fixture
async def async_engine() -> AsyncGenerator[Any, None]:
    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.shared.db.base import Base
    from tests import conftest as root_test_conftest

    # Mirror the root suite bootstrap so every mapped table exists even when
    # this subtree runs after other modules have already imported part of the ORM.
    root_test_conftest._register_models()

    fd, raw_path = mkstemp(prefix="valdrics-settings-", suffix=".sqlite")
    os.close(fd)
    Path(raw_path).unlink(missing_ok=True)
    path = Path(raw_path)

    sync_engine = create_engine(f"sqlite:///{path}")
    Base.metadata.create_all(sync_engine)
    sync_engine.dispose()

    engine = create_async_engine(f"sqlite+aiosqlite:///{path}")
    try:
        yield engine
    finally:
        await engine.dispose()
        path.unlink(missing_ok=True)


@pytest_asyncio.fixture
async def db_session(async_engine: Any) -> AsyncGenerator["AsyncSession", None]:
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


@pytest_asyncio.fixture
async def db(db_session: "AsyncSession") -> "AsyncSession":
    return db_session


@pytest_asyncio.fixture
async def async_client(
    app: Any, db: "AsyncSession"
) -> AsyncGenerator["AsyncClient", None]:
    from httpx import ASGITransport, AsyncClient

    from app.shared.db.session import get_db, get_system_db
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from unittest.mock import patch

    old_db_override = app.dependency_overrides.get(get_db)
    old_system_db_override = app.dependency_overrides.get(get_system_db)
    session_maker = async_sessionmaker(
        bind=db.bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    modules_to_patch = [
        "app.shared.db.session.async_session_maker",
        "app.shared.connections.oidc.async_session_maker",
        "app.modules.governance.api.v1.jobs.async_session_maker",
        "app.modules.governance.domain.jobs.cur_ingestion.async_session_maker",
        "app.modules.governance.domain.jobs.processor.async_session_maker",
        "app.tasks.scheduler_tasks.async_session_maker",
        "app.shared.llm.pricing_data.async_session_maker",
        "app.main.async_session_maker",
    ]

    with ExitStack() as stack:
        for target in modules_to_patch:
            try:
                stack.enter_context(patch(target, session_maker))
            except (ImportError, AttributeError):
                continue

        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_system_db] = lambda: db

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                setattr(client, "app", app)
                yield client
        finally:
            if old_db_override is not None:
                app.dependency_overrides[get_db] = old_db_override
            else:
                app.dependency_overrides.pop(get_db, None)

            if old_system_db_override is not None:
                app.dependency_overrides[get_system_db] = old_system_db_override
            else:
                app.dependency_overrides.pop(get_system_db, None)


@pytest_asyncio.fixture
async def ac(async_client: "AsyncClient") -> "AsyncClient":
    return async_client


@pytest.fixture
def build_notification_payload() -> Callable[..., dict[str, Any]]:
    def _build(**overrides: Any) -> dict[str, Any]:
        payload = {
            "slack_enabled": True,
            "digest_schedule": "daily",
            "digest_hour": 9,
            "digest_minute": 0,
            "alert_on_budget_warning": True,
            "alert_on_budget_exceeded": True,
            "alert_on_zombie_detected": True,
        }
        payload.update(overrides)
        return payload

    return _build


@pytest.fixture
def build_jira_payload(
    build_notification_payload: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    def _build(**overrides: Any) -> dict[str, Any]:
        payload = build_notification_payload(
            jira_enabled=True,
            jira_base_url="https://example.atlassian.net",
            jira_email="jira@example.com",
            jira_project_key="FINOPS",
            jira_issue_type="Task",
            jira_api_token="jira_token_value_123",
        )
        payload.update(overrides)
        return payload

    return _build


@pytest.fixture
def build_teams_payload(
    build_notification_payload: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    def _build(**overrides: Any) -> dict[str, Any]:
        payload = build_notification_payload(
            teams_enabled=True,
            teams_webhook_url="https://example.webhook.office.com/webhookb2/xxxx",
        )
        payload.update(overrides)
        return payload

    return _build


@pytest.fixture
def build_workflow_payload(
    build_notification_payload: Callable[..., dict[str, Any]],
) -> Callable[..., dict[str, Any]]:
    def _build(**overrides: Any) -> dict[str, Any]:
        payload = build_notification_payload(
            jira_enabled=False,
            workflow_github_enabled=True,
            workflow_github_owner="Valdrics-AI",
            workflow_github_repo="valdrics",
            workflow_github_workflow_id="remediation.yml",
            workflow_github_ref="main",
            workflow_github_token="gh_token_value_123",
            workflow_gitlab_enabled=True,
            workflow_gitlab_base_url="https://gitlab.com",
            workflow_gitlab_project_id="12345",
            workflow_gitlab_ref="main",
            workflow_gitlab_trigger_token="gl_token_value_123",
            workflow_webhook_enabled=True,
            workflow_webhook_url="https://ci.example.com/hooks/valdrics",
            workflow_webhook_bearer_token="webhook_token_value_123",
        )
        payload.update(overrides)
        return payload

    return _build
