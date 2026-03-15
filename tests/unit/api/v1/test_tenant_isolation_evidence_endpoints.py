import uuid
from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_capture_and_list_tenant_isolation_evidence(
    async_client, app, db, test_tenant
):
    from app.shared.core.auth import CurrentUser, get_current_user, UserRole
    from app.shared.core.pricing import PricingTier
    from app.models.tenant import User

    admin_user = CurrentUser(
        id=uuid.uuid4(),
        email="admin-tenancy@valdrics.io",
        tenant_id=test_tenant.id,
        role=UserRole.ADMIN,
        tier=PricingTier.PRO,
    )

    db.add(
        User(
            id=admin_user.id,
            tenant_id=test_tenant.id,
            email=admin_user.email,
            role=UserRole.ADMIN,
        )
    )
    await db.commit()

    app.dependency_overrides[get_current_user] = lambda: admin_user
    try:
        payload = {
            "runner": "scripts/verify_tenant_isolation.py",
            "checks": [
                "connections_list_is_tenant_scoped",
                "notification_settings_get_is_tenant_scoped",
            ],
            "passed": True,
            "pytest_exit_code": 0,
            "duration_seconds": 1.234,
            "git_sha": "deadbeef",
            "captured_at": datetime.now(timezone.utc).isoformat(),
            "notes": "unit-test capture",
        }

        resp = await async_client.post(
            "/api/v1/audit/tenancy/isolation/evidence", json=payload
        )
        assert resp.status_code == 410
    finally:
        app.dependency_overrides.pop(get_current_user, None)
