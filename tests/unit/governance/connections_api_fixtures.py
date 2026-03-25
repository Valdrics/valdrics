import pytest
from uuid import uuid4

from app.models.tenant import UserRole
from app.shared.core.auth import CurrentUser, get_current_user
from app.shared.core.pricing import PricingTier

@pytest.fixture
def auth_user():
    tenant_id = uuid4()
    return CurrentUser(
        id=uuid4(),
        email="test@valdrics.io",
        tenant_id=tenant_id,
        role=UserRole.ADMIN,
        tier=PricingTier.FREE,
    )


@pytest.fixture
def override_auth(app, auth_user):
    app.dependency_overrides[get_current_user] = lambda: auth_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
