import pytest
from uuid import uuid4
from unittest.mock import patch


from app.models.azure_connection import AzureConnection
from app.shared.core.pricing import PricingTier

from app.models.tenant import Tenant

pytest_plugins = ("tests.unit.governance.connections_api_fixtures",)


@pytest.mark.asyncio
async def test_create_azure_connection_success_on_starter(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.STARTER.value
    await db.commit()
    auth_user.tier = PricingTier.STARTER

    payload = {
        "name": "Azure Test",
        "azure_tenant_id": str(uuid4()),
        "client_id": str(uuid4()),
        "subscription_id": str(uuid4()),
        "client_secret": "secret",
    }
    resp = await ac.post("/api/v1/settings/connections/azure", json=payload)
    assert resp.status_code == 201
    assert resp.json()["subscription_id"] == payload["subscription_id"]


@pytest.mark.asyncio
async def test_create_azure_connection_success_on_growth(
    ac, db, override_auth, auth_user
):
    # Upgrade tenant
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    payload = {
        "name": "Azure Growth",
        "azure_tenant_id": str(uuid4()),
        "client_id": str(uuid4()),
        "subscription_id": str(uuid4()),
        "client_secret": "secret",
    }
    resp = await ac.post("/api/v1/settings/connections/azure", json=payload)
    assert resp.status_code == 201
    assert resp.json()["subscription_id"] == payload["subscription_id"]


@pytest.mark.asyncio
async def test_create_azure_connection_requires_secret_when_auth_secret(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    payload = {
        "name": "Azure Missing Secret",
        "azure_tenant_id": str(uuid4()),
        "client_id": str(uuid4()),
        "subscription_id": str(uuid4()),
        "auth_method": "secret",
    }
    resp = await ac.post("/api/v1/settings/connections/azure", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_azure_connection_invalid_auth_method(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    payload = {
        "name": "Azure Bad Auth",
        "azure_tenant_id": str(uuid4()),
        "client_id": str(uuid4()),
        "subscription_id": str(uuid4()),
        "client_secret": "secret",
        "auth_method": "token",
    }
    resp = await ac.post("/api/v1/settings/connections/azure", json=payload)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_verify_azure_connection(ac, db, override_auth, auth_user):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    conn = AzureConnection(
        tenant_id=auth_user.tenant_id,
        name="Az",
        azure_tenant_id="t",
        client_id="c",
        subscription_id="s",
    )
    db.add(conn)
    await db.commit()
    with patch(
        "app.shared.connections.azure.AzureConnectionService.verify_connection"
    ) as mock_verify:
        mock_verify.return_value = {"status": "verified"}
        resp = await ac.post(f"/api/v1/settings/connections/azure/{conn.id}/verify")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_verify_azure_connection_tenant_isolation(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    other_tenant = Tenant(
        id=uuid4(), name="Other Tenant", plan=PricingTier.GROWTH.value
    )
    db.add(other_tenant)
    await db.commit()

    conn = AzureConnection(
        tenant_id=other_tenant.id,
        name="Other Az",
        azure_tenant_id="t",
        client_id="c",
        subscription_id="s",
    )
    db.add(conn)
    await db.commit()

    resp = await ac.post(f"/api/v1/settings/connections/azure/{conn.id}/verify")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_verify_azure_connection_success_on_starter(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.STARTER.value
    await db.commit()
    auth_user.tier = PricingTier.STARTER

    conn = AzureConnection(
        tenant_id=auth_user.tenant_id,
        name="Az",
        azure_tenant_id="t",
        client_id="c",
        subscription_id="s",
        client_secret="secret",
    )
    db.add(conn)
    await db.commit()

    with patch(
        "app.shared.connections.azure.AzureConnectionService.verify_connection"
    ) as mock_verify:
        mock_verify.return_value = {"status": "verified"}
        resp = await ac.post(f"/api/v1/settings/connections/azure/{conn.id}/verify")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_azure_connections(ac, db, override_auth, auth_user):
    # Retrieve regardless of tier
    resp = await ac.get("/api/v1/settings/connections/azure")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_azure_connections_tenant_isolation(
    ac, db, override_auth, auth_user
):
    other_tenant = Tenant(
        id=uuid4(), name="Other Tenant", plan=PricingTier.GROWTH.value
    )
    db.add(other_tenant)
    await db.commit()

    db.add_all(
        [
            AzureConnection(
                tenant_id=auth_user.tenant_id,
                name="Mine",
                azure_tenant_id="t1",
                client_id="c1",
                subscription_id="s1",
            ),
            AzureConnection(
                tenant_id=other_tenant.id,
                name="Other",
                azure_tenant_id="t2",
                client_id="c2",
                subscription_id="s2",
            ),
        ]
    )
    await db.commit()

    resp = await ac.get("/api/v1/settings/connections/azure")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["subscription_id"] == "s1"


@pytest.mark.asyncio
async def test_create_azure_connection_duplicate(ac, db, override_auth, auth_user):
    # Setup Growth tier
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    # Pre-create
    conn = AzureConnection(
        tenant_id=auth_user.tenant_id,
        name="Existing",
        azure_tenant_id="t-1",
        client_id="c-1",
        subscription_id="sub-duplicate",
    )
    db.add(conn)
    await db.commit()

    payload = {
        "name": "New",
        "azure_tenant_id": "t-2",
        "client_id": "c-2",
        "subscription_id": "sub-duplicate",
        "client_secret": "s",
    }
    resp = await ac.post("/api/v1/settings/connections/azure", json=payload)
    assert resp.status_code == 409
