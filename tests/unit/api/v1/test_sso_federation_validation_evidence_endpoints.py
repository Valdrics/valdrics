import uuid
from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_capture_and_list_sso_federation_validation_evidence(
    async_client, app, db, test_tenant
):
    from app.shared.core.auth import CurrentUser, get_current_user, UserRole
    from app.shared.core.pricing import PricingTier
    from app.models.tenant import User
    admin_user = CurrentUser(
        id=uuid.uuid4(),
        email="admin-sso@valdrics.io",
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
            "runner": "scripts/smoke_test_sso_federation.py",
            "passed": True,
            "federation_mode": "domain",
            "frontend_url": "https://app.valdrics.example",
            "expected_redirect_url": "https://app.valdrics.example/auth/callback",
            "discovery_endpoint": "https://api.valdrics.example/api/v1/public/sso/discovery",
            "checks": [
                {
                    "name": "admin.sso_validation",
                    "passed": True,
                    "status_code": 200,
                    "detail": None,
                    "duration_ms": 10.0,
                }
            ],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": 0.1,
            "notes": {"unit_test": True},
        }

        resp = await async_client.post(
            "/api/v1/audit/identity/sso-federation/evidence", json=payload
        )
        assert resp.status_code == 410
    finally:
        app.dependency_overrides.pop(get_current_user, None)
