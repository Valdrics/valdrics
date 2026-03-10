from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.models.tenant import Tenant
from app.models.tenant_growth_funnel_snapshot import TenantGrowthFunnelSnapshot
from app.modules.reporting.domain.tenant_growth_funnel import (
    normalize_growth_funnel_attribution,
    record_tenant_growth_funnel_stage,
)
from app.shared.core.pricing import PricingTier


@pytest_asyncio.fixture
async def growth_db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Tenant.__table__.create)
        await conn.run_sync(TenantGrowthFunnelSnapshot.__table__.create)

    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
    await engine.dispose()


@pytest.mark.asyncio
async def test_record_tenant_growth_funnel_stage_derives_pql_and_preserves_first_seen(
    growth_db_session: AsyncSession,
) -> None:
    tenant = Tenant(id=uuid4(), name="Growth Funnel Tenant", plan=PricingTier.FREE.value)
    growth_db_session.add(tenant)
    await growth_db_session.commit()

    first_touch = datetime.now(timezone.utc) - timedelta(days=2)
    onboarded_at = datetime.now(timezone.utc) - timedelta(days=1)
    connected_at = datetime.now(timezone.utc) - timedelta(hours=6)
    first_value_at = datetime.now(timezone.utc) - timedelta(hours=1)

    await record_tenant_growth_funnel_stage(
        growth_db_session,
        tenant_id=tenant.id,
        stage="tenant_onboarded",
        occurred_at=onboarded_at,
        current_tier=PricingTier.FREE,
        attribution=normalize_growth_funnel_attribution(
            utm_source="Google",
            utm_medium="CPC",
            utm_campaign="Launch",
            persona="Finance",
            intent="roi_assessment",
            page_path="/onboarding?intent=roi_assessment",
            first_touch_at=first_touch,
            last_touch_at=onboarded_at,
        ),
        source="settings_onboard",
        commit=False,
    )
    await record_tenant_growth_funnel_stage(
        growth_db_session,
        tenant_id=tenant.id,
        stage="connection_verified",
        occurred_at=connected_at,
        current_tier=PricingTier.GROWTH,
        provider="aws",
        source="onboarding_verify_success",
        commit=False,
    )
    snapshot = await record_tenant_growth_funnel_stage(
        growth_db_session,
        tenant_id=tenant.id,
        stage="first_value_activated",
        occurred_at=first_value_at,
        current_tier=PricingTier.GROWTH,
        source="dashboard_first_value",
        commit=True,
    )

    assert snapshot.utm_source == "google"
    assert snapshot.utm_medium == "cpc"
    assert snapshot.utm_campaign == "launch"
    assert snapshot.persona == "finance"
    assert snapshot.acquisition_intent == "roi_assessment"
    assert snapshot.first_path == "/onboarding?intent=roi_assessment"
    assert snapshot.first_touch_at == first_touch
    assert snapshot.tenant_onboarded_at == onboarded_at
    assert snapshot.first_connection_verified_at == connected_at
    assert snapshot.first_connection_provider == "aws"
    assert snapshot.first_value_activated_at == first_value_at
    assert snapshot.first_value_source == "dashboard_first_value"
    assert snapshot.pql_qualified_at == first_value_at
    assert snapshot.current_tier == PricingTier.GROWTH.value

    await record_tenant_growth_funnel_stage(
        growth_db_session,
        tenant_id=tenant.id,
        stage="connection_verified",
        occurred_at=datetime.now(timezone.utc),
        current_tier=PricingTier.PRO,
        provider="azure",
        source="duplicate_connection_verified",
        commit=True,
    )
    refreshed = (
        await growth_db_session.execute(
            select(TenantGrowthFunnelSnapshot).where(
                TenantGrowthFunnelSnapshot.tenant_id == tenant.id
            )
        )
    ).scalar_one()
    assert refreshed.first_connection_verified_at == connected_at
    assert refreshed.first_connection_provider == "aws"
    assert refreshed.current_tier == PricingTier.PRO.value


@pytest.mark.asyncio
async def test_paid_activation_sets_paid_milestone_without_duplicate_pql(
    growth_db_session: AsyncSession,
) -> None:
    tenant = Tenant(id=uuid4(), name="Paid Growth Funnel", plan=PricingTier.FREE.value)
    growth_db_session.add(tenant)
    await growth_db_session.commit()

    base_time = datetime.now(timezone.utc) - timedelta(hours=2)
    await record_tenant_growth_funnel_stage(
        growth_db_session,
        tenant_id=tenant.id,
        stage="tenant_onboarded",
        occurred_at=base_time,
        current_tier=PricingTier.FREE,
        commit=False,
    )
    await record_tenant_growth_funnel_stage(
        growth_db_session,
        tenant_id=tenant.id,
        stage="connection_verified",
        occurred_at=base_time + timedelta(minutes=15),
        current_tier=PricingTier.STARTER,
        provider="aws",
        commit=False,
    )
    await record_tenant_growth_funnel_stage(
        growth_db_session,
        tenant_id=tenant.id,
        stage="first_value_activated",
        occurred_at=base_time + timedelta(minutes=30),
        current_tier=PricingTier.STARTER,
        source="dashboard_first_value",
        commit=False,
    )
    paid_snapshot = await record_tenant_growth_funnel_stage(
        growth_db_session,
        tenant_id=tenant.id,
        stage="paid_activated",
        occurred_at=base_time + timedelta(minutes=45),
        current_tier=PricingTier.PRO,
        source="paystack_charge_success",
        commit=True,
    )

    assert paid_snapshot.pql_qualified_at == base_time + timedelta(minutes=30)
    assert paid_snapshot.paid_activated_at == base_time + timedelta(minutes=45)
    assert paid_snapshot.current_tier == PricingTier.PRO.value
