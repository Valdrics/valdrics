from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.remediation import (
    RemediationAction,
    RemediationRequest,
    RemediationStatus,
)
from app.models.realized_savings import RealizedSavingsEvent
from app.models.scim_group import ScimGroup, ScimGroupMember
from app.models.sso_domain_mapping import SsoDomainMapping
from app.models.tenant import Tenant, User, UserRole
from app.models.tenant_growth_funnel_snapshot import TenantGrowthFunnelSnapshot
from app.models.tenant_identity_settings import TenantIdentitySettings
from app.modules.governance.api.v1.audit_access import request_data_erasure
from app.modules.governance.domain.security.audit_log import (
    AuditEventType,
    AuditLog,
    SystemAuditLog,
)
from app.shared.core.auth import CurrentUser
from app.shared.core.pricing import PricingTier


@pytest.mark.asyncio
async def test_request_data_erasure_removes_owner_tenant_and_extended_tenant_tables(
    db,
) -> None:
    tenant_id = uuid4()
    owner_id = uuid4()
    member_id = uuid4()
    group_id = uuid4()
    remediation_id = uuid4()
    now = datetime.now(timezone.utc)

    tenant = Tenant(
        id=tenant_id,
        name="Erase Tenant",
        plan=PricingTier.PRO.value,
        is_deleted=False,
    )
    owner = User(
        id=owner_id,
        tenant_id=tenant_id,
        email="owner-erase@example.com",
        role=UserRole.OWNER.value,
    )
    member = User(
        id=member_id,
        tenant_id=tenant_id,
        email="member-erase@example.com",
        role=UserRole.ADMIN.value,
    )
    remediation = RemediationRequest(
        id=remediation_id,
        tenant_id=tenant_id,
        resource_id="i-erase",
        resource_type="ec2_instance",
        provider="aws",
        region="us-east-1",
        action=RemediationAction.STOP_INSTANCE,
        status=RemediationStatus.PENDING,
        requested_by_user_id=owner_id,
    )
    db.add_all([tenant, owner, member, remediation])
    db.add_all(
        [
            TenantIdentitySettings(
                tenant_id=tenant_id,
                sso_enabled=True,
                allowed_email_domains=["example.com"],
                sso_federation_enabled=True,
                sso_federation_mode="domain",
                scim_enabled=True,
                scim_bearer_token="scim-secret",
                scim_group_mappings=[{"group": "Ops", "role": "admin"}],
                scim_last_rotated_at=now,
            ),
            SsoDomainMapping(
                tenant_id=tenant_id,
                domain="example.com",
                federation_mode="domain",
                provider_id=None,
                is_active=True,
            ),
            ScimGroup(
                id=group_id,
                tenant_id=tenant_id,
                display_name="Ops",
                display_name_norm="ops",
                external_id="ops-ext",
                external_id_norm="ops-ext",
            ),
            ScimGroupMember(
                tenant_id=tenant_id,
                group_id=group_id,
                user_id=member_id,
            ),
            TenantGrowthFunnelSnapshot(
                tenant_id=tenant_id,
                current_tier=PricingTier.PRO.value,
                tenant_onboarded_at=now,
                first_touch_at=now,
                last_touch_at=now,
                created_at=now,
                updated_at=now,
            ),
            RealizedSavingsEvent(
                tenant_id=tenant_id,
                remediation_request_id=remediation_id,
                provider="aws",
                account_id=None,
                resource_id="i-erase",
                service="AmazonEC2",
                region="us-east-1",
                method="ledger_delta_avg_daily_v1",
                baseline_start_date=date(2026, 2, 1),
                baseline_end_date=date(2026, 2, 7),
                measurement_start_date=date(2026, 2, 8),
                measurement_end_date=date(2026, 2, 14),
                baseline_total_cost_usd=Decimal("70.00"),
                baseline_observed_days=7,
                measurement_total_cost_usd=Decimal("35.00"),
                measurement_observed_days=7,
                baseline_avg_daily_cost_usd=Decimal("10.00"),
                measurement_avg_daily_cost_usd=Decimal("5.00"),
                realized_avg_daily_savings_usd=Decimal("5.00"),
                realized_monthly_savings_usd=Decimal("150.00"),
                monthly_multiplier_days=30,
                confidence_score=Decimal("0.95"),
                details={"source": "test"},
                computed_at=now,
            ),
            AuditLog(
                tenant_id=tenant_id,
                event_type=AuditEventType.SETTINGS_UPDATED.value,
                event_timestamp=now.replace(tzinfo=None),
                actor_id=owner_id,
                actor_email="owner-erase@example.com",
                request_method="PUT",
                request_path="/api/v1/settings/identity",
                resource_type="settings",
                resource_id="identity",
                details={"changed": True},
                success=True,
            ),
            SystemAuditLog(
                event_type=AuditEventType.SYSTEM_MAINTENANCE.value,
                actor_id=owner_id,
                actor_email="owner-erase@example.com",
                request_method="POST",
                request_path="/system/test",
                resource_type="ops",
                resource_id="system-test",
                details={"tenant_id": str(tenant_id)},
                success=True,
            ),
        ]
    )
    await db.commit()

    current_user = CurrentUser(
        id=owner_id,
        email="owner-erase@example.com",
        tenant_id=tenant_id,
        role=UserRole.OWNER,
        tier=PricingTier.PRO,
    )

    response = await request_data_erasure(
        current_user,
        db,
        confirmation="DELETE ALL MY DATA",
    )

    assert response["status"] == "erasure_complete"
    assert response["deleted_counts"]["users"] == 2
    assert response["deleted_counts"]["tenants"] == 1
    assert response["deleted_counts"]["tenant_identity_settings"] == 1
    assert response["deleted_counts"]["sso_domain_mappings"] == 1
    assert response["deleted_counts"]["scim_groups"] == 1
    assert response["deleted_counts"]["scim_group_members"] == 1
    assert response["deleted_counts"]["tenant_growth_funnel_snapshots"] == 1
    assert response["deleted_counts"]["realized_savings_events"] == 1
    assert response["deleted_counts"]["audit_logs"] == 1
    assert response["deleted_counts"]["system_audit_logs"] == 1

    assert await db.get(Tenant, tenant_id) is None
    assert await db.get(User, owner_id) is None
    assert await db.get(User, member_id) is None
    assert (
        await db.execute(
            select(TenantIdentitySettings).where(
                TenantIdentitySettings.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(
            select(SsoDomainMapping).where(SsoDomainMapping.tenant_id == tenant_id)
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(select(ScimGroup).where(ScimGroup.tenant_id == tenant_id))
    ).scalar_one_or_none() is None
    assert (
        await db.execute(
            select(ScimGroupMember).where(ScimGroupMember.tenant_id == tenant_id)
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(
            select(TenantGrowthFunnelSnapshot).where(
                TenantGrowthFunnelSnapshot.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(
            select(RealizedSavingsEvent).where(RealizedSavingsEvent.tenant_id == tenant_id)
        )
    ).scalar_one_or_none() is None
    assert (
        await db.execute(select(AuditLog).where(AuditLog.tenant_id == tenant_id))
    ).scalar_one_or_none() is None

    system_summary = (
        await db.execute(
            select(SystemAuditLog).where(
                SystemAuditLog.resource_type == "tenant_erasure",
                SystemAuditLog.resource_id == str(tenant_id),
            )
        )
    ).scalar_one_or_none()
    assert system_summary is not None
    assert system_summary.actor_id is None
    assert system_summary.actor_email is None
