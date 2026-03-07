import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.models.aws_connection import AWSConnection
from app.models.discovered_account import DiscoveredAccount
from app.shared.core.pricing import PricingTier

from app.models.tenant import Tenant

pytest_plugins = ("tests.unit.governance.connections_api_fixtures",)


@pytest.mark.asyncio
async def test_link_discovered_account(ac, db, override_auth, auth_user):
    # Free tier only allows 1 AWS account; org discovery + link needs a higher tier.
    auth_user.tier = PricingTier.STARTER
    # 1. Create management connection
    mgmt = AWSConnection(
        tenant_id=auth_user.tenant_id,
        aws_account_id="111122223333",
        role_arn="arn:aws:iam::111122223333:role/Valdrics",
        external_id="vx-11112222333311112222333311112222",
        is_management_account=True,
        status="active",
    )
    db.add(mgmt)
    await db.commit()

    # 2. Create discovered account
    disc = DiscoveredAccount(
        management_connection_id=mgmt.id,
        account_id="444455556666",
        name="Member Account",
        status="discovered",
    )
    db.add(disc)
    await db.commit()

    # 3. Link it
    resp = await ac.post(f"/api/v1/settings/connections/aws/discovered/{disc.id}/link")
    assert resp.status_code == 200
    assert resp.json()["message"] == "Account linked successfully"

    # Verify connection created
    stmt = select(AWSConnection).where(AWSConnection.aws_account_id == "444455556666")
    res = await db.execute(stmt)
    new_conn = res.scalar_one()
    assert new_conn.tenant_id == auth_user.tenant_id
    assert new_conn.external_id == mgmt.external_id
    assert new_conn.region == "global"


@pytest.mark.asyncio
async def test_link_discovered_account_idempotent(ac, db, override_auth, auth_user):
    # 1. Management connection
    mgmt = AWSConnection(
        tenant_id=auth_user.tenant_id,
        aws_account_id="888888888888",
        role_arn="arn",
        external_id="vx-unique-test-id-888",
        is_management_account=True,
        status="active",
    )
    db.add(mgmt)
    await db.commit()
    await db.refresh(mgmt)

    # 2. Discovered account
    disc = DiscoveredAccount(
        management_connection_id=mgmt.id,
        account_id="777777777777",
        name="Linked Member",
        status="linked",
    )
    db.add(disc)
    await db.commit()
    await db.refresh(disc)

    # 3. Existing connection
    conn = AWSConnection(
        tenant_id=auth_user.tenant_id,
        aws_account_id="777777777777",
        role_arn="arn",
        external_id=mgmt.external_id,  # Sharing external ID
        status="active",
    )
    db.add(conn)
    await db.commit()

    # 4. Try to link again (should return existing)
    resp = await ac.post(f"/api/v1/settings/connections/aws/discovered/{disc.id}/link")
    assert resp.status_code == 200
    assert resp.json()["status"] == "existing"


@pytest.mark.asyncio
async def test_link_discovered_account_not_authorized(ac, db, override_auth, auth_user):
    other_tenant = Tenant(id=uuid4(), name="Other", plan=PricingTier.GROWTH.value)
    db.add(other_tenant)
    await db.commit()

    mgmt = AWSConnection(
        tenant_id=other_tenant.id,
        aws_account_id="101010101010",
        role_arn="arn",
        external_id="vx-1010",
        is_management_account=True,
        status="active",
    )
    db.add(mgmt)
    await db.commit()

    disc = DiscoveredAccount(
        management_connection_id=mgmt.id,
        account_id="999999999998",
        name="Foreign Account",
        status="discovered",
    )
    db.add(disc)
    await db.commit()

    resp = await ac.post(f"/api/v1/settings/connections/aws/discovered/{disc.id}/link")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_discovered_accounts_empty(ac, override_auth):
    resp = await ac.get("/api/v1/settings/connections/aws/discovered")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_discovered_accounts_sorted(ac, db, override_auth, auth_user):
    mgmt = AWSConnection(
        tenant_id=auth_user.tenant_id,
        aws_account_id="222233334444",
        role_arn="arn",
        external_id="vx-2222",
        is_management_account=True,
        status="active",
    )
    db.add(mgmt)
    await db.commit()

    older = DiscoveredAccount(
        management_connection_id=mgmt.id,
        account_id="111100001111",
        name="Old",
        status="discovered",
        last_discovered_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    newer = DiscoveredAccount(
        management_connection_id=mgmt.id,
        account_id="222200002222",
        name="New",
        status="discovered",
        last_discovered_at=datetime.now(timezone.utc),
    )
    db.add_all([older, newer])
    await db.commit()

    resp = await ac.get("/api/v1/settings/connections/aws/discovered")
    assert resp.status_code == 200
    data = resp.json()
    assert data[0]["account_id"] == "222200002222"
