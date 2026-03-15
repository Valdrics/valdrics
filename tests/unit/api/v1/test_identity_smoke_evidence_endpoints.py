import uuid
from datetime import datetime, timezone

import pytest


@pytest.mark.asyncio
async def test_capture_and_list_identity_idp_smoke_evidence(
    async_client, app, db, test_tenant
):
    from app.shared.core.auth import CurrentUser, get_current_user, UserRole
    from app.shared.core.pricing import PricingTier
    from app.models.tenant import User
    admin_user = CurrentUser(
        id=uuid.uuid4(),
        email="admin-identity@valdrics.io",
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
            "runner": "scripts/smoke_test_scim_idp.py",
            "idp": "okta",
            "scim_base_url": "https://example.valdrics.io/scim/v2",
            "write_mode": False,
            "passed": True,
            "checks": [
                {
                    "name": "scim.service_provider_config",
                    "passed": True,
                    "status_code": 200,
                    "detail": None,
                    "duration_ms": 12.3,
                }
            ],
            "started_at": datetime.now(timezone.utc).isoformat(),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": 0.123,
            "notes": {"unit_test": True},
        }

        resp = await async_client.post(
            "/api/v1/audit/identity/idp-smoke/evidence", json=payload
        )
        assert resp.status_code == 410
    finally:
        app.dependency_overrides.pop(get_current_user, None)
