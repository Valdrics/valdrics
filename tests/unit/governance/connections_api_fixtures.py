import pytest_asyncio
from uuid import uuid4

from app.models.tenant import Tenant, User, UserRole
from app.shared.core.auth import CurrentUser, get_current_user
from app.shared.core.pricing import PricingTier


@pytest_asyncio.fixture
async def test_tenant(db):
    tenant = Tenant(id=uuid4(), name="Test Tenant", plan=PricingTier.FREE)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def test_user(db, test_tenant):
    user = User(
        id=uuid4(),
        email="test@valdrics.io",
        tenant_id=test_tenant.id,
        role=UserRole.ADMIN,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
def auth_user(test_user, test_tenant):
    return CurrentUser(
        id=test_user.id,
        email=test_user.email,
        tenant_id=test_tenant.id,
        role=test_user.role,
        tier=test_tenant.plan,
    )


@pytest_asyncio.fixture
def override_auth(app, auth_user):
    app.dependency_overrides[get_current_user] = lambda: auth_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
