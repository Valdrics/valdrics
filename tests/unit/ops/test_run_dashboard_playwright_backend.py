from __future__ import annotations

import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

from scripts.run_dashboard_playwright_backend import (
    PlaywrightE2EFixture,
    _bootstrap_schema,
    _seed_fixture,
)


class _FakeAsyncSessionContext:
    def __init__(self, session: object) -> None:
        self._session = session

    async def __aenter__(self) -> object:
        return self._session

    async def __aexit__(self, exc_type, exc, tb) -> bool:
        return False


def test_bootstrap_schema_restores_environment() -> None:
    fake_engine = SimpleNamespace(dispose=AsyncMock())
    fake_settings = SimpleNamespace(
        DATABASE_URL="sqlite+aiosqlite:////tmp/dashboard-playwright.sqlite3",
        TESTING=False,
    )

    with (
        patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql+asyncpg://prod.example/app",
                "TESTING": "true",
                "LOCAL_SQLITE_BOOTSTRAP": "false",
            },
            clear=True,
        ),
        patch(
            "scripts.run_dashboard_playwright_backend.reload_settings_from_environment",
            return_value=fake_settings,
        ),
        patch("scripts.run_dashboard_playwright_backend.reset_db_runtime"),
        patch("scripts.run_dashboard_playwright_backend.get_engine", return_value=fake_engine),
        patch(
            "scripts.run_dashboard_playwright_backend.bootstrap_local_sqlite_schema",
            new=AsyncMock(),
        ),
        patch(
            "scripts.run_dashboard_playwright_backend.dispose_db_runtime",
            new=AsyncMock(),
        ),
    ):
        asyncio.run(_bootstrap_schema(fake_settings.DATABASE_URL))

        assert dict(os.environ) == {
            "DATABASE_URL": "postgresql+asyncpg://prod.example/app",
            "TESTING": "true",
            "LOCAL_SQLITE_BOOTSTRAP": "false",
        }

    fake_engine.dispose.assert_awaited_once()


def test_seed_fixture_restores_environment() -> None:
    fake_session = SimpleNamespace(add=Mock(), add_all=Mock(), commit=AsyncMock())
    fixture = PlaywrightE2EFixture(
        database_url="sqlite+aiosqlite:////tmp/dashboard-playwright.sqlite3",
        tenant_id=UUID("11111111-1111-4111-8111-111111111111"),
        tenant_name="Playwright Test Tenant",
        user_id=UUID("22222222-2222-4222-8222-222222222222"),
        user_name="E2E Test User",
        email="e2e@valdrics.test",
        role="admin",
        persona="engineering",
        tier="growth",
    )

    with (
        patch.dict(
            os.environ,
            {
                "DATABASE_URL": "postgresql+asyncpg://prod.example/app",
                "TESTING": "false",
                "LOCAL_SQLITE_BOOTSTRAP": "true",
            },
            clear=True,
        ),
        patch("scripts.run_dashboard_playwright_backend.reload_settings_from_environment"),
        patch("scripts.run_dashboard_playwright_backend.reset_db_runtime"),
        patch(
            "scripts.run_dashboard_playwright_backend.mark_session_system_context",
            new=AsyncMock(),
        ),
        patch(
            "scripts.run_dashboard_playwright_backend.async_session_maker",
            return_value=_FakeAsyncSessionContext(fake_session),
        ),
        patch(
            "scripts.run_dashboard_playwright_backend.dispose_db_runtime",
            new=AsyncMock(),
        ),
    ):
        asyncio.run(_seed_fixture(fixture))

        assert dict(os.environ) == {
            "DATABASE_URL": "postgresql+asyncpg://prod.example/app",
            "TESTING": "false",
            "LOCAL_SQLITE_BOOTSTRAP": "true",
        }

    fake_session.commit.assert_awaited_once()
