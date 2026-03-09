import pytest
from uuid import uuid4
from unittest.mock import patch

from sqlalchemy import select

from app.models.aws_connection import AWSConnection
from app.shared.core.pricing import PricingTier

from app.models.tenant import Tenant

pytest_plugins = ("tests.unit.governance.connections_api_fixtures",)


def test_tier_gates_are_enforced(auth_user):
    from app.modules.governance.api.v1.settings.connections_helpers import (
        check_cloud_plus_tier,
        check_multi_cloud_tier,
    )
    from fastapi import HTTPException

    # Starter+ gates multi-cloud connections (Azure/GCP).
    auth_user.tier = PricingTier.FREE
    with pytest.raises(HTTPException) as exc:
        check_multi_cloud_tier(auth_user)
    assert exc.value.status_code == 403

    auth_user.tier = PricingTier.STARTER
    assert check_multi_cloud_tier(auth_user) == PricingTier.STARTER

    # Pro+ gates Cloud+ connectors (SaaS/License).
    with pytest.raises(HTTPException) as cloud_exc:
        check_cloud_plus_tier(auth_user)
    assert cloud_exc.value.status_code == 403

    auth_user.tier = PricingTier.PRO
    assert check_cloud_plus_tier(auth_user) == PricingTier.PRO


@pytest.mark.asyncio
async def test_aws_setup_templates(ac, override_auth):
    with patch(
        "app.shared.connections.aws.AWSConnectionService.get_setup_templates"
    ) as mock_service:
        mock_service.return_value = {
            "external_id": "vx-123",
            "cloudformation_yaml": "---",
            "terraform_hcl": "resource...",
            "magic_link": "https://...",
            "instructions": "steps...",
            "permissions_summary": ["sts:AssumeRole"],
        }
        resp = await ac.post("/api/v1/settings/connections/aws/setup")
        assert resp.status_code == 200
        data = resp.json()
        assert data["external_id"] == "vx-123"


@pytest.mark.asyncio
async def test_cloud_plus_setup_templates(ac, override_auth):
    saas = await ac.post("/api/v1/settings/connections/saas/setup")
    assert saas.status_code == 200
    saas_data = saas.json()
    assert "snippet" in saas_data
    assert "sample_feed" in saas_data
    assert "native_connectors" in saas_data

    license_res = await ac.post("/api/v1/settings/connections/license/setup")
    assert license_res.status_code == 200
    license_data = license_res.json()
    assert "snippet" in license_data
    assert "sample_feed" in license_data
    assert "native_connectors" in license_data

    platform_res = await ac.post("/api/v1/settings/connections/platform/setup")
    assert platform_res.status_code == 200
    platform_data = platform_res.json()
    assert "snippet" in platform_data
    assert "sample_feed" in platform_data

    hybrid_res = await ac.post("/api/v1/settings/connections/hybrid/setup")
    assert hybrid_res.status_code == 200
    hybrid_data = hybrid_res.json()
    assert "snippet" in hybrid_data
    assert "sample_feed" in hybrid_data


@pytest.mark.asyncio
async def test_create_aws_connection(ac, override_auth, auth_user, db):
    payload = {
        "aws_account_id": "123456789012",
        "role_arn": "arn:aws:iam::123456789012:role/Valdrics",
        "external_id": "vx-12345678901234567890123456789012",
        "region": "us-east-1",
        "is_management_account": True,
        "organization_id": "o-123",
    }
    resp = await ac.post("/api/v1/settings/connections/aws", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["aws_account_id"] == "123456789012"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_aws_connection_defaults_region_global(
    ac, override_auth, auth_user, db
):
    payload = {
        "aws_account_id": "210987654321",
        "role_arn": "arn:aws:iam::210987654321:role/Valdrics",
        "external_id": "vx-21098765432121098765432121098765",
    }
    resp = await ac.post("/api/v1/settings/connections/aws", json=payload)
    assert resp.status_code == 201
    data = resp.json()
    assert data["region"] == "global"


@pytest.mark.asyncio
async def test_duplicate_aws_connection(ac, db, override_auth, auth_user):
    # Pre-create a connection
    conn = AWSConnection(
        tenant_id=auth_user.tenant_id,
        aws_account_id="999999999999",
        role_arn="arn:aws:iam::999999999999:role/Valdrics",
        external_id="vx-99999999999999999999999999999999",
        status="pending",
    )
    db.add(conn)
    await db.commit()

    payload = {
        "aws_account_id": "999999999999",
        "role_arn": "arn:aws:iam::999999999999:role/Valdrics",
        "external_id": "vx-99999999999999999999999999999999",
        "region": "us-east-1",
    }
    resp = await ac.post("/api/v1/settings/connections/aws", json=payload)
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_sync_aws_org(ac, db, override_auth, auth_user):
    # Create management account
    conn = AWSConnection(
        tenant_id=auth_user.tenant_id,
        aws_account_id="112233445566",
        role_arn="arn:aws:iam::112233445566:role/Valdrics",
        external_id="vx-11223344556611223344556611223344",
        is_management_account=True,
        status="active",
    )
    db.add(conn)
    await db.commit()

    with patch(
        "app.shared.connections.organizations.OrganizationsDiscoveryService.sync_accounts"
    ) as mock_sync:
        mock_sync.return_value = 5
        resp = await ac.post(f"/api/v1/settings/connections/aws/{conn.id}/sync-org")
        assert resp.status_code == 200
        assert resp.json()["count"] == 5


@pytest.mark.asyncio
async def test_sync_aws_org_not_management(ac, db, override_auth, auth_user):
    # Standard connection (not management)
    conn = AWSConnection(
        tenant_id=auth_user.tenant_id,
        aws_account_id="998877665544",
        role_arn="arn:aws:iam::998877665544:role/Valdrics",
        external_id="vx-998877665544",
        is_management_account=False,
        status="active",
    )
    db.add(conn)
    await db.commit()

    resp = await ac.post(f"/api/v1/settings/connections/aws/{conn.id}/sync-org")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_aws_connections(ac, db, override_auth, auth_user):
    conn = AWSConnection(
        tenant_id=auth_user.tenant_id,
        aws_account_id="123",
        role_arn="arn",
        external_id="vx-123",
        status="active",
    )
    db.add(conn)
    await db.commit()
    resp = await ac.get("/api/v1/settings/connections/aws")
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_verify_aws_connection(ac, db, override_auth, auth_user):
    conn = AWSConnection(
        tenant_id=auth_user.tenant_id,
        aws_account_id="123",
        role_arn="arn",
        external_id="vx-123",
        status="active",
    )
    db.add(conn)
    await db.commit()
    with patch(
        "app.shared.connections.aws.AWSConnectionService.verify_connection"
    ) as mock_verify:
        mock_verify.return_value = {"status": "verified"}
        resp = await ac.post(f"/api/v1/settings/connections/aws/{conn.id}/verify")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_aws_connection(ac, db, override_auth, auth_user):
    conn = AWSConnection(
        tenant_id=auth_user.tenant_id,
        aws_account_id="delete-me",
        role_arn="arn",
        external_id="vx-123",
        status="active",
    )
    db.add(conn)
    await db.commit()
    resp = await ac.delete(f"/api/v1/settings/connections/aws/{conn.id}")
    assert resp.status_code == 204
    # Verify gone
    stmt = select(AWSConnection).where(AWSConnection.id == conn.id)
    res = await db.execute(stmt)
    assert res.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_delete_aws_connection_tenant_isolation(ac, db, override_auth, auth_user):
    other_tenant = Tenant(
        id=uuid4(), name="Other Tenant", plan=PricingTier.GROWTH.value
    )
    db.add(other_tenant)
    await db.commit()

    conn = AWSConnection(
        tenant_id=other_tenant.id,
        aws_account_id="123456789012",
        role_arn="arn:aws:iam::123456789012:role/Valdrics",
        external_id="vx-12345678901234567890123456789012",
        status="pending",
    )
    db.add(conn)
    await db.commit()

    resp = await ac.delete(f"/api/v1/settings/connections/aws/{conn.id}")
    assert resp.status_code == 404
