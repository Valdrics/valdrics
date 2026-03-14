# ruff: noqa: F401
from __future__ import annotations

import asyncio
import base64
import csv
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import io
import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

import app.modules.enforcement.domain.service as enforcement_service_module
import app.modules.enforcement.domain.service_runtime_ops as enforcement_service_runtime_ops_module
from app.modules.enforcement.domain.action_errors import EnforcementDomainError as HTTPException
from app.models.enforcement import (
    EnforcementApprovalStatus,
    EnforcementCreditGrant,
    EnforcementCreditPoolType,
    EnforcementCreditReservationAllocation,
    EnforcementDecision,
    EnforcementDecisionLedger,
    EnforcementDecisionType,
    EnforcementMode,
    EnforcementSource,
)
from app.models.cloud import CloudAccount, CostRecord
from app.models.scim_group import ScimGroup, ScimGroupMember
from app.models.tenant import Tenant, User, UserRole
from app.models.tenant_identity_settings import TenantIdentitySettings
from app.modules.enforcement.domain.policy_document import (
    POLICY_DOCUMENT_SCHEMA_VERSION,
    PolicyDocument,
    canonical_policy_document_payload,
    policy_document_sha256,
)
from app.modules.enforcement.domain.service import EnforcementService, GateInput
from app.shared.core.auth import CurrentUser
from app.shared.core.approval_permissions import (
    APPROVAL_PERMISSION_REMEDIATION_APPROVE_NONPROD,
    APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
)


class _FakeCounter:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, str], float]] = []
        self._last_labels: dict[str, str] = {}

    def labels(self, **labels: str) -> "_FakeCounter":
        self._last_labels = dict(labels)
        return self

    def inc(self, amount: float = 1.0) -> None:
        self.calls.append((dict(self._last_labels), float(amount)))


def _approval_token_runtime_settings(
    secret: str,
    fallback: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        ENFORCEMENT_APPROVAL_TOKEN_SECRET=secret,
        API_URL="https://api.valdrics.local",
        JWT_SIGNING_KID="",
        ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS=list(fallback or []),
    )


def _deterministic_token_secret(label: str) -> str:
    normalized = str(label or "approval-secret").strip().replace("_", "-")
    seed = f"valdrics-{normalized}-fixture-"
    value = seed
    while len(value) < 48:
        value += seed
    return value[:48]


def _deterministic_idempotency_key(*parts: object) -> str:
    return "-".join(str(part).strip().replace("_", "-") for part in parts if str(part).strip())


async def _seed_tenant(db) -> Tenant:
    tenant = Tenant(
        id=uuid4(),
        name="Enforcement Test Tenant",
        plan="enterprise",
        is_deleted=False,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


async def _seed_daily_cost_history(
    db: AsyncSession,
    *,
    tenant_id,
    provider: str,
    daily_costs: list[tuple[date, Decimal]],
) -> CloudAccount:
    account = CloudAccount(
        id=uuid4(),
        tenant_id=tenant_id,
        provider=provider,
        name=f"{provider}-cost-account",
        is_production=True,
        criticality="high",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    for idx, (record_day, cost) in enumerate(daily_costs):
        db.add(
            CostRecord(
                id=uuid4(),
                tenant_id=tenant_id,
                account_id=account.id,
                service="AmazonEC2",
                region="us-east-1",
                usage_type="BoxUsage",
                resource_id=f"seed-{record_day.isoformat()}-{idx}",
                usage_amount=Decimal("1"),
                usage_unit="Hrs",
                canonical_charge_category="compute",
                canonical_charge_subcategory="instance",
                canonical_mapping_version="focus-1.3-v1",
                cost_usd=cost.quantize(Decimal("0.0001")),
                amount_raw=cost.quantize(Decimal("0.0001")),
                currency="USD",
                carbon_kg=None,
                is_preliminary=False,
                cost_status="FINAL",
                reconciliation_run_id=None,
                ingestion_metadata=None,
                tags=None,
                attribution_id=None,
                allocated_to=None,
                recorded_at=record_day,
                timestamp=datetime(
                    record_day.year,
                    record_day.month,
                    record_day.day,
                    12,
                    0,
                    0,
                    tzinfo=timezone.utc,
                ),
            )
        )

    await db.commit()
    return account


async def _issue_approved_token(
    *,
    db,
    tenant_id,
    actor_id,
    project_id: str = "default",
    environment: str = "prod",
    monthly_delta: Decimal = Decimal("120"),
    idempotency_key: str = "token-issue-1",
) -> tuple[str, object, object]:
    service = EnforcementService(db)
    await service.upsert_budget(
        tenant_id=tenant_id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("2000"),
        active=True,
    )

    gate_result = await service.evaluate_gate(
        tenant_id=tenant_id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id=project_id,
            environment=environment,
            action="terraform.apply",
            resource_reference="module.rds.aws_db_instance.main",
            estimated_monthly_delta_usd=monthly_delta,
            estimated_hourly_delta_usd=Decimal("0.160"),
            metadata={"resource_type": "aws_db_instance"},
            idempotency_key=idempotency_key,
        ),
    )
    assert gate_result.approval is not None

    reviewer = CurrentUser(
        id=uuid4(),
        email="owner@example.com",
        tenant_id=tenant_id,
        role=UserRole.OWNER,
    )
    approval, decision, token, _ = await service.approve_request(
        tenant_id=tenant_id,
        approval_id=gate_result.approval.id,
        reviewer=reviewer,
        notes="approved for token tests",
    )
    assert isinstance(token, str) and token
    return token, approval, decision


async def _issue_pending_approval(
    *,
    db,
    tenant_id,
    actor_id,
    environment: str,
    require_approval_for_prod: bool,
    require_approval_for_nonprod: bool,
    idempotency_key: str,
    approval_routing_rules: list[dict[str, object]] | None = None,
    enforce_prod_requester_reviewer_separation: bool = True,
    enforce_nonprod_requester_reviewer_separation: bool = False,
):
    service = EnforcementService(db)
    await service.update_policy(
        tenant_id=tenant_id,
        terraform_mode=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        require_approval_for_prod=require_approval_for_prod,
        require_approval_for_nonprod=require_approval_for_nonprod,
        enforce_prod_requester_reviewer_separation=enforce_prod_requester_reviewer_separation,
        enforce_nonprod_requester_reviewer_separation=enforce_nonprod_requester_reviewer_separation,
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("2500"),
        default_ttl_seconds=900,
        approval_routing_rules=approval_routing_rules,
    )
    await service.upsert_budget(
        tenant_id=tenant_id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("1000"),
        active=True,
    )
    gate = await service.evaluate_gate(
        tenant_id=tenant_id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment=environment,
            action="terraform.apply",
            resource_reference="module.app.aws_instance.web",
            estimated_monthly_delta_usd=Decimal("75"),
            estimated_hourly_delta_usd=Decimal("0.11"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key=idempotency_key,
        ),
    )
    assert gate.approval is not None
    assert gate.decision.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    return gate


async def _seed_member_scim_permission(
    *,
    db,
    tenant_id,
    member_id,
    permissions: list[str],
    scim_enabled: bool,
    group_name: str = "finops-approvers",
) -> None:
    member = (
        await db.execute(select(User).where(User.id == member_id))
    ).scalar_one_or_none()
    if member is None:
        member = User(
            id=member_id,
            tenant_id=tenant_id,
            email=f"{member_id.hex[:12]}@example.com",
            role=UserRole.MEMBER.value,
            persona="engineering",
            is_active=True,
        )
        db.add(member)
        await db.flush()

    settings = (
        await db.execute(
            select(TenantIdentitySettings).where(
                TenantIdentitySettings.tenant_id == tenant_id
            )
        )
    ).scalar_one_or_none()
    if settings is None:
        settings = TenantIdentitySettings(tenant_id=tenant_id)
        db.add(settings)
        await db.flush()

    settings.scim_enabled = bool(scim_enabled)
    settings.scim_group_mappings = [
        {
            "group": group_name,
            "permissions": permissions,
        }
    ]

    group = (
        await db.execute(
            select(ScimGroup).where(
                ScimGroup.tenant_id == tenant_id,
                ScimGroup.display_name_norm == group_name.strip().lower(),
            )
        )
    ).scalar_one_or_none()
    if group is None:
        group = ScimGroup(
            tenant_id=tenant_id,
            display_name=group_name,
            display_name_norm=group_name.strip().lower(),
            external_id=group_name,
            external_id_norm=group_name.strip().lower(),
        )
        db.add(group)
        await db.flush()

    membership = (
        await db.execute(
            select(ScimGroupMember).where(
                ScimGroupMember.tenant_id == tenant_id,
                ScimGroupMember.group_id == group.id,
                ScimGroupMember.user_id == member_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        db.add(
            ScimGroupMember(
                tenant_id=tenant_id,
                group_id=group.id,
                user_id=member_id,
            )
        )

    await db.commit()

# Export underscore-prefixed helper symbols for star-imported test parts.
__all__ = [name for name in globals() if not name.startswith("__")]
