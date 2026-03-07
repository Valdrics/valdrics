import pytest
from uuid import uuid4
from unittest.mock import patch


from app.models.hybrid_connection import HybridConnection
from app.models.license_connection import LicenseConnection
from app.models.platform_connection import PlatformConnection
from app.models.saas_connection import SaaSConnection
from app.models.tenant import Tenant
from app.shared.core.pricing import PricingTier

pytest_plugins = ("tests.unit.governance.connections_api_fixtures",)


@pytest.mark.asyncio
async def test_create_saas_connection_denied_on_growth(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.GROWTH.value
    await db.commit()
    auth_user.tier = PricingTier.GROWTH

    payload = {
        "name": "Salesforce Feed",
        "vendor": "salesforce",
        "auth_method": "manual",
        "spend_feed": [],
    }
    resp = await ac.post("/api/v1/settings/connections/saas", json=payload)
    assert resp.status_code == 403
    assert "Cloud+ connectors require 'Pro' plan or higher" in resp.json().get(
        "error", ""
    )


@pytest.mark.asyncio
async def test_create_saas_connection_success_on_pro(ac, db, override_auth, auth_user):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.PRO.value
    await db.commit()
    auth_user.tier = PricingTier.PRO

    payload = {
        "name": "Salesforce Feed",
        "vendor": "salesforce",
        "auth_method": "manual",
        "spend_feed": [
            {"service": "Sales Cloud", "cost_usd": 12.5, "timestamp": "2026-02-11"}
        ],
    }
    resp = await ac.post("/api/v1/settings/connections/saas", json=payload)
    assert resp.status_code == 201
    assert resp.json()["vendor"] == "salesforce"


@pytest.mark.asyncio
async def test_verify_saas_connection(ac, db, override_auth, auth_user):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.PRO.value
    await db.commit()
    auth_user.tier = PricingTier.PRO

    conn = SaaSConnection(
        tenant_id=auth_user.tenant_id,
        name="Salesforce Feed",
        vendor="salesforce",
        spend_feed=[],
        auth_method="manual",
    )
    db.add(conn)
    await db.commit()

    with patch(
        "app.shared.connections.saas.SaaSConnectionService.verify_connection"
    ) as mock_verify:
        mock_verify.return_value = {"status": "verified"}
        resp = await ac.post(f"/api/v1/settings/connections/saas/{conn.id}/verify")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_license_connection_success_on_pro(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.PRO.value
    await db.commit()
    auth_user.tier = PricingTier.PRO

    payload = {
        "name": "MS365 Seats",
        "vendor": "microsoft",
        "auth_method": "manual",
        "license_feed": [
            {"service": "M365 E5", "cost_usd": 100.0, "timestamp": "2026-02-11"}
        ],
    }
    resp = await ac.post("/api/v1/settings/connections/license", json=payload)
    assert resp.status_code == 201
    assert resp.json()["vendor"] == "microsoft"


@pytest.mark.asyncio
async def test_list_license_connections_tenant_isolation(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.PRO.value
    await db.commit()
    auth_user.tier = PricingTier.PRO

    other_tenant = Tenant(id=uuid4(), name="Other", plan=PricingTier.PRO.value)
    db.add(other_tenant)
    await db.commit()

    db.add_all(
        [
            LicenseConnection(
                tenant_id=auth_user.tenant_id,
                name="Mine",
                vendor="microsoft",
                auth_method="manual",
                license_feed=[],
            ),
            LicenseConnection(
                tenant_id=other_tenant.id,
                name="Other",
                vendor="google",
                auth_method="manual",
                license_feed=[],
            ),
        ]
    )
    await db.commit()

    resp = await ac.get("/api/v1/settings/connections/license")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Mine"


@pytest.mark.asyncio
async def test_create_platform_connection_success_on_pro(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.PRO.value
    await db.commit()
    auth_user.tier = PricingTier.PRO

    payload = {
        "name": "Platform Ledger",
        "vendor": "internal_platform",
        "auth_method": "manual",
        "spend_feed": [
            {"service": "Shared Cluster", "cost_usd": 50.0, "timestamp": "2026-02-11"}
        ],
    }
    resp = await ac.post("/api/v1/settings/connections/platform", json=payload)
    assert resp.status_code == 201
    assert resp.json()["vendor"] == "internal_platform"


@pytest.mark.asyncio
async def test_verify_platform_connection(ac, db, override_auth, auth_user):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.PRO.value
    await db.commit()
    auth_user.tier = PricingTier.PRO

    conn = PlatformConnection(
        tenant_id=auth_user.tenant_id,
        name="Platform Ledger",
        vendor="internal_platform",
        spend_feed=[],
        auth_method="manual",
    )
    db.add(conn)
    await db.commit()

    with patch(
        "app.shared.connections.platform.PlatformConnectionService.verify_connection"
    ) as mock_verify:
        mock_verify.return_value = {"status": "verified"}
        resp = await ac.post(f"/api/v1/settings/connections/platform/{conn.id}/verify")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_create_hybrid_connection_success_on_pro(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.PRO.value
    await db.commit()
    auth_user.tier = PricingTier.PRO

    payload = {
        "name": "Datacenter Ledger",
        "vendor": "datacenter",
        "auth_method": "manual",
        "spend_feed": [
            {"service": "DC Core", "cost_usd": 500.0, "timestamp": "2026-02-11"}
        ],
    }
    resp = await ac.post("/api/v1/settings/connections/hybrid", json=payload)
    assert resp.status_code == 201
    assert resp.json()["vendor"] == "datacenter"


@pytest.mark.asyncio
async def test_list_hybrid_connections_tenant_isolation(
    ac, db, override_auth, auth_user
):
    tenant = await db.get(Tenant, auth_user.tenant_id)
    tenant.plan = PricingTier.PRO.value
    await db.commit()
    auth_user.tier = PricingTier.PRO

    other_tenant = Tenant(id=uuid4(), name="Other-Hybrid", plan=PricingTier.PRO.value)
    db.add(other_tenant)
    await db.commit()

    db.add_all(
        [
            HybridConnection(
                tenant_id=auth_user.tenant_id,
                name="Mine-Hybrid",
                vendor="datacenter",
                auth_method="manual",
                spend_feed=[],
            ),
            HybridConnection(
                tenant_id=other_tenant.id,
                name="Other-Hybrid",
                vendor="colo",
                auth_method="manual",
                spend_feed=[],
            ),
        ]
    )
    await db.commit()

    resp = await ac.get("/api/v1/settings/connections/hybrid")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Mine-Hybrid"
