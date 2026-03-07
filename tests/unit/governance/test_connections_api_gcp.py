import pytest
from uuid import uuid4
from unittest.mock import patch, AsyncMock


from app.models.gcp_connection import GCPConnection
from app.shared.core.pricing import PricingTier

from app.models.tenant import Tenant

pytest_plugins = ("tests.unit.governance.connections_api_fixtures",)


@pytest.mark.asyncio
async def test_create_gcp_connection_success_on_growth(
    ac, db, override_auth, auth_user
):
    # Upgrade tenant
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    payload = {
        "name": "GCP Project",
        "project_id": "test-project-123",
        "service_account_json": "{}",
        "auth_method": "secret",
    }
    resp = await ac.post("/api/v1/settings/connections/gcp", json=payload)
    assert resp.status_code == 201
    assert resp.json()["project_id"] == "test-project-123"


@pytest.mark.asyncio
async def test_create_gcp_connection_requires_json_when_secret(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    payload = {
        "name": "GCP Missing JSON",
        "project_id": "test-project-123",
        "auth_method": "secret",
    }
    resp = await ac.post("/api/v1/settings/connections/gcp", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_gcp_connection_invalid_json(ac, db, override_auth, auth_user):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    payload = {
        "name": "GCP Bad JSON",
        "project_id": "test-project-123",
        "service_account_json": "{bad-json",
        "auth_method": "secret",
    }
    resp = await ac.post("/api/v1/settings/connections/gcp", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_gcp_connection_workload_identity_verification_failure(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    payload = {
        "name": "GCP WIF",
        "project_id": "wif-project-123",
        "auth_method": "workload_identity",
    }
    with patch(
        "app.shared.connections.oidc.OIDCService.verify_gcp_access",
        new_callable=AsyncMock,
    ) as mock_verify:
        mock_verify.return_value = (False, "STS exchange failed")
        resp = await ac.post("/api/v1/settings/connections/gcp", json=payload)
        assert resp.status_code == 400
        assert "Workload Identity verification failed" in (
            resp.json().get("error") or resp.json().get("message") or ""
        )


@pytest.mark.asyncio
async def test_verify_gcp_connection_denied_on_free(ac, db, override_auth, auth_user):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.FREE.value
    await db.commit()

    conn = GCPConnection(tenant_id=auth_user.tenant_id, name="g", project_id="p")
    db.add(conn)
    await db.commit()

    resp = await ac.post(f"/api/v1/settings/connections/gcp/{conn.id}/verify")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_list_gcp_connections(ac, db, override_auth, auth_user):
    resp = await ac.get("/api/v1/settings/connections/gcp")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_gcp_connections_tenant_isolation(ac, db, override_auth, auth_user):
    other_tenant = Tenant(
        id=uuid4(), name="Other Tenant", plan=PricingTier.GROWTH.value
    )
    db.add(other_tenant)
    await db.commit()

    db.add_all(
        [
            GCPConnection(tenant_id=auth_user.tenant_id, name="Mine", project_id="p1"),
            GCPConnection(tenant_id=other_tenant.id, name="Other", project_id="p2"),
        ]
    )
    await db.commit()

    resp = await ac.get("/api/v1/settings/connections/gcp")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["project_id"] == "p1"


@pytest.mark.asyncio
async def test_delete_gcp_connection(ac, db, override_auth, auth_user):
    conn = GCPConnection(tenant_id=auth_user.tenant_id, name="g", project_id="p")
    db.add(conn)
    await db.commit()
    resp = await ac.delete(f"/api/v1/settings/connections/gcp/{conn.id}")
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_delete_gcp_connection_tenant_isolation(ac, db, override_auth, auth_user):
    other_tenant = Tenant(
        id=uuid4(), name="Other Tenant", plan=PricingTier.GROWTH.value
    )
    db.add(other_tenant)
    await db.commit()

    conn = GCPConnection(tenant_id=other_tenant.id, name="g", project_id="p")
    db.add(conn)
    await db.commit()

    resp = await ac.delete(f"/api/v1/settings/connections/gcp/{conn.id}")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_create_gcp_connection_duplicate(ac, db, override_auth, auth_user):
    # Setup Growth tier
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    # Pre-create
    conn = GCPConnection(
        tenant_id=auth_user.tenant_id, name="Existing", project_id="proj-duplicate"
    )
    db.add(conn)
    await db.commit()

    payload = {
        "name": "New",
        "project_id": "proj-duplicate",
        "service_account_json": "{}",
        "auth_method": "secret",
    }
    resp = await ac.post("/api/v1/settings/connections/gcp", json=payload)
    assert resp.status_code == 409
