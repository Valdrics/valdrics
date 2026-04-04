import pytest
import uuid
from httpx import AsyncClient
from sqlalchemy import select
from app.models.llm import LLMBudget
from app.models.tenant import UserRole
from app.shared.core.auth import (
    CurrentUser,
    get_current_user,
    get_current_user_with_db_context,
)
from unittest.mock import patch
from app.shared.core.pricing import PricingTier


@pytest.mark.asyncio
async def test_get_llm_settings_is_read_only_for_missing_budget(
    async_client: AsyncClient, db, app
):
    """GET /llm should return defaults without creating a budget row."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="member@valdrics.io",
        role=UserRole.MEMBER,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.get("/api/v1/settings/llm")
        assert response.status_code == 200
        assert response.json()["monthly_limit_usd"] == 10.0

        result = await db.execute(
            select(LLMBudget).where(LLMBudget.tenant_id == tenant_id)
        )
        assert result.scalar_one_or_none() is None
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_llm_settings(
    async_client: AsyncClient, db, mock_user_id, mock_tenant_id, app
):
    """PUT /llm should update existing budget and keys."""
    user_id = uuid.UUID(str(mock_user_id))
    tenant_id = uuid.UUID(str(mock_tenant_id))
    mock_user = CurrentUser(
        id=user_id, tenant_id=tenant_id, email="test@valdrics.io", role=UserRole.ADMIN
    )

    budget = LLMBudget(
        tenant_id=tenant_id, monthly_limit_usd=10.0, preferred_provider="groq"
    )
    db.add(budget)
    await db.commit()

    update_data = {
        "monthly_limit_usd": 50.0,
        "preferred_provider": "openai",
        "openai_api_key": "sk-test",
    }
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.put("/api/v1/settings/llm", json=update_data)
        assert response.status_code == 200
        assert response.json()["monthly_limit_usd"] == 50.0
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_llm_settings_preserves_omitted_existing_keys(
    async_client: AsyncClient, db, app
):
    """Partial PUT /llm should preserve stored BYOK keys that were not sent."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id,
        tenant_id=tenant_id,
        email="admin@valdrics.io",
        role=UserRole.ADMIN,
    )

    budget = LLMBudget(
        tenant_id=tenant_id,
        monthly_limit_usd=10.0,
        alert_threshold_percent=80,
        hard_limit=False,
        preferred_provider="openai",
        preferred_model="gpt-4o",
        openai_api_key="sk-existing",
        groq_api_key="gsk-existing",
    )
    db.add(budget)
    await db.commit()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.put(
            "/api/v1/settings/llm",
            json={"preferred_model": "gpt-4o-mini"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["preferred_model"] == "gpt-4o-mini"
        assert data["has_openai_key"] is True
        assert data["has_groq_key"] is True

        refreshed = await db.get(LLMBudget, budget.id)
        assert refreshed is not None
        assert refreshed.preferred_provider == "openai"
        assert float(refreshed.monthly_limit_usd) == 10.0
        assert refreshed.openai_api_key == "sk-existing"
        assert refreshed.groq_api_key == "gsk-existing"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_llm_models(
    async_client: AsyncClient, app, mock_user_id, mock_tenant_id
):
    """GET /llm/models requires auth and returns available models for authenticated users."""
    unauthorized = await async_client.get("/api/v1/settings/llm/models")
    assert unauthorized.status_code == 401

    mock_user = CurrentUser(
        id=uuid.UUID(str(mock_user_id)),
        tenant_id=uuid.UUID(str(mock_tenant_id)),
        email="test@valdrics.io",
        role=UserRole.ADMIN,
    )
    app.dependency_overrides[get_current_user_with_db_context] = lambda: mock_user
    try:
        response = await async_client.get("/api/v1/settings/llm/models")
        assert response.status_code == 200
        assert "groq" in response.json()
    finally:
        app.dependency_overrides.pop(get_current_user_with_db_context, None)

    # Verify pricing data import works (runtime check)
    from app.shared.llm.pricing_data import LLM_PRICING

    assert LLM_PRICING is not None


@pytest.mark.asyncio
async def test_update_llm_settings_creates_with_keys(
    async_client: AsyncClient, db, app
):
    """PUT /llm should create settings when missing and set key flags."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id, tenant_id=tenant_id, email="admin@valdrics.io", role=UserRole.ADMIN
    )

    update_data = {
        "monthly_limit_usd": 25.0,
        "alert_threshold_percent": 80,
        "hard_limit": True,
        "preferred_provider": "openai",
        "preferred_model": "gpt-4o-mini",
        "openai_api_key": "sk-test",
        "groq_api_key": "gsk-test",
    }

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.put("/api/v1/settings/llm", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_limit_usd"] == 25.0
        assert data["has_openai_key"] is True
        assert data["has_groq_key"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_llm_settings_threshold_logging(
    async_client: AsyncClient, db, app
):
    """PUT /llm logs threshold boundary values when settings exist."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id, tenant_id=tenant_id, email="admin@valdrics.io", role=UserRole.ADMIN
    )

    db.add(
        LLMBudget(
            tenant_id=tenant_id, monthly_limit_usd=10.0, preferred_provider="groq"
        )
    )
    await db.commit()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        with (
            patch("app.modules.governance.api.v1.settings.llm.logger") as mock_logger,
            patch("app.modules.governance.api.v1.settings.llm.audit_log") as mock_audit,
        ):
            response = await async_client.put(
                "/api/v1/settings/llm",
                json={
                    "monthly_limit_usd": 10.0,
                    "alert_threshold_percent": 0,
                    "hard_limit": False,
                    "preferred_provider": "groq",
                    "preferred_model": "llama-3.3-70b-versatile",
                },
            )
            assert response.status_code == 200
            assert mock_logger.info.called

            response = await async_client.put(
                "/api/v1/settings/llm",
                json={
                    "monthly_limit_usd": 10.0,
                    "alert_threshold_percent": 100,
                    "hard_limit": False,
                    "preferred_provider": "groq",
                    "preferred_model": "llama-3.3-70b-versatile",
                },
            )
            assert response.status_code == 200
            assert mock_logger.info.called
            assert mock_audit.called
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_llm_settings_flags(async_client: AsyncClient, db, app):
    """GET /llm should return key presence flags."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = CurrentUser(
        id=user_id, tenant_id=tenant_id, email="admin@valdrics.io", role=UserRole.ADMIN
    )

    db.add(
        LLMBudget(
            tenant_id=tenant_id,
            monthly_limit_usd=10.0,
            preferred_provider="groq",
            openai_api_key="sk-test",
            claude_api_key=None,
            google_api_key="gcp-key",
            groq_api_key=None,
        )
    )
    await db.commit()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.get("/api/v1/settings/llm")
        assert response.status_code == 200
        data = response.json()
        assert data["has_openai_key"] is True
        assert data["has_google_key"] is True
        assert data["has_claude_key"] is False
        assert data["has_groq_key"] is False
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_llm_settings_requires_admin(async_client: AsyncClient, app):
    member = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="member@llm.io",
        role=UserRole.MEMBER,
    )
    app.dependency_overrides[get_current_user] = lambda: member
    try:
        response = await async_client.put(
            "/api/v1/settings/llm",
            json={
                "monthly_limit_usd": 10.0,
                "alert_threshold_percent": 80,
                "hard_limit": False,
                "preferred_provider": "groq",
                "preferred_model": "llama-3.3-70b-versatile",
            },
        )
        assert response.status_code == 403
        assert "Insufficient permissions" in response.json()["error"]
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_get_llm_settings_requires_tenant_context(async_client: AsyncClient, app):
    platform_user = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=None,
        email="platform-llm@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.ENTERPRISE,
    )
    app.dependency_overrides[get_current_user] = lambda: platform_user
    try:
        response = await async_client.get("/api/v1/settings/llm")
        assert response.status_code == 403
        assert "tenant context required" in str(response.json()).lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_llm_settings_requires_tenant_context(async_client: AsyncClient, app):
    platform_user = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=None,
        email="platform-llm-write@valdrics.io",
        role=UserRole.ADMIN,
        tier=PricingTier.ENTERPRISE,
    )
    app.dependency_overrides[get_current_user] = lambda: platform_user
    try:
        response = await async_client.put(
            "/api/v1/settings/llm",
            json={
                "monthly_limit_usd": 10.0,
                "alert_threshold_percent": 80,
                "hard_limit": False,
                "preferred_provider": "groq",
                "preferred_model": "llama-3.3-70b-versatile",
            },
        )
        assert response.status_code == 403
        assert "tenant context required" in str(response.json()).lower()
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_llm_settings_validation_failure(async_client: AsyncClient, app):
    admin = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="admin@llm.io",
        role=UserRole.ADMIN,
    )
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        response = await async_client.put(
            "/api/v1/settings/llm",
            json={
                "monthly_limit_usd": 10.0,
                "alert_threshold_percent": 80,
                "hard_limit": False,
                "preferred_provider": "invalid",
                "preferred_model": "gpt-4o-mini",
            },
        )
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_llm_settings_accepts_512_char_api_keys(
    async_client: AsyncClient, db, mock_user_id, mock_tenant_id, app
):
    user_id = uuid.UUID(str(mock_user_id))
    tenant_id = uuid.UUID(str(mock_tenant_id))
    mock_user = CurrentUser(
        id=user_id, tenant_id=tenant_id, email="test@valdrics.io", role=UserRole.ADMIN
    )

    budget = LLMBudget(
        tenant_id=tenant_id, monthly_limit_usd=10.0, preferred_provider="groq"
    )
    db.add(budget)
    await db.commit()

    long_key = "k" * 512
    app.dependency_overrides[get_current_user] = lambda: mock_user
    try:
        response = await async_client.put(
            "/api/v1/settings/llm",
            json={
                "monthly_limit_usd": 50.0,
                "preferred_provider": "openai",
                "openai_api_key": long_key,
            },
        )
        assert response.status_code == 200
        assert response.json()["has_openai_key"] is True
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_update_llm_settings_rejects_keys_longer_than_512(
    async_client: AsyncClient, app
):
    admin = CurrentUser(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="admin@llm.io",
        role=UserRole.ADMIN,
    )
    app.dependency_overrides[get_current_user] = lambda: admin
    try:
        response = await async_client.put(
            "/api/v1/settings/llm",
            json={
                "monthly_limit_usd": 10.0,
                "alert_threshold_percent": 80,
                "hard_limit": False,
                "preferred_provider": "openai",
                "preferred_model": "gpt-4o-mini",
                "openai_api_key": "k" * 513,
            },
        )
        assert response.status_code == 422
        assert response.json()["code"] == "VALIDATION_ERROR"
    finally:
        app.dependency_overrides.pop(get_current_user, None)
