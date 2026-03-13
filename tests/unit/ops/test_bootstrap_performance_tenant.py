from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

import scripts.bootstrap_performance_tenant as bootstrap_performance_tenant
from app.shared.core.pricing_types import PricingTier


@pytest.mark.asyncio
async def test_onboard_tenant_accepts_success(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 200
        text = "ok"

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            assert headers["Authorization"] == "Bearer token-123"
            assert json["tenant_name"] == "Perf Tenant"
            return Response()

    monkeypatch.setattr(bootstrap_performance_tenant.httpx, "AsyncClient", Client)

    await bootstrap_performance_tenant._onboard_tenant(
        base_url="http://127.0.0.1:8000",
        token="token-123",
        tenant_name="Perf Tenant",
        email="owner@example.com",
    )


@pytest.mark.asyncio
async def test_onboard_tenant_accepts_already_onboarded(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 400
        text = "Already onboarded"

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            return Response()

    monkeypatch.setattr(bootstrap_performance_tenant.httpx, "AsyncClient", Client)

    await bootstrap_performance_tenant._onboard_tenant(
        base_url="http://127.0.0.1:8000",
        token="token-123",
        tenant_name="Perf Tenant",
        email="owner@example.com",
    )


@pytest.mark.asyncio
async def test_onboard_tenant_raises_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        status_code = 503
        text = "upstream failure"

    class Client:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def post(self, url, headers, json):
            return Response()

    monkeypatch.setattr(bootstrap_performance_tenant.httpx, "AsyncClient", Client)

    with pytest.raises(SystemExit, match="Tenant bootstrap failed \\(503\\)"):
        await bootstrap_performance_tenant._onboard_tenant(
            base_url="http://127.0.0.1:8000",
            token="token-123",
            tenant_name="Perf Tenant",
            email="owner@example.com",
        )


def test_is_local_target_only_allows_loopback_hosts() -> None:
    assert bootstrap_performance_tenant._is_local_target("http://127.0.0.1:8000")
    assert bootstrap_performance_tenant._is_local_target("http://localhost:8000")
    assert not bootstrap_performance_tenant._is_local_target("https://staging.valdrics.ai")


@pytest.mark.asyncio
async def test_apply_local_tenant_tier_updates_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant = SimpleNamespace(plan=PricingTier.FREE.value)
    session = SimpleNamespace()
    session.commit = AsyncMock()

    class Result:
        @staticmethod
        def scalar_one_or_none():
            return tenant

    async def _execute(_statement):
        return Result()

    session.execute = _execute

    class SessionFactory:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    mark_calls: list[object] = []

    async def _mark_session_system_context(db_session):
        mark_calls.append(db_session)

    monkeypatch.setattr(
        bootstrap_performance_tenant, "async_session_maker", lambda: SessionFactory()
    )
    monkeypatch.setattr(
        bootstrap_performance_tenant,
        "mark_session_system_context",
        _mark_session_system_context,
    )

    await bootstrap_performance_tenant._apply_local_tenant_tier(
        user_id=uuid4(),
        tier=PricingTier.STARTER,
    )

    assert tenant.plan == PricingTier.STARTER.value
    assert mark_calls == [session]
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_apply_local_tenant_tier_rejects_missing_tenant(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = SimpleNamespace()
    session.commit = AsyncMock()

    class Result:
        @staticmethod
        def scalar_one_or_none():
            return None

    async def _execute(_statement):
        return Result()

    session.execute = _execute

    class SessionFactory:
        async def __aenter__(self):
            return session

        async def __aexit__(self, exc_type, exc, tb):
            return None

    monkeypatch.setattr(
        bootstrap_performance_tenant, "async_session_maker", lambda: SessionFactory()
    )
    monkeypatch.setattr(
        bootstrap_performance_tenant,
        "mark_session_system_context",
        AsyncMock(),
    )

    with pytest.raises(SystemExit, match="Unable to locate bootstrapped tenant"):
        await bootstrap_performance_tenant._apply_local_tenant_tier(
            user_id=uuid4(),
            tier=PricingTier.STARTER,
        )
