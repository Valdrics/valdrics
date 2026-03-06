# ruff: noqa: F401
from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4
import zipfile

from fastapi import HTTPException
import pytest
from sqlalchemy import func, select

from app.models.enforcement import EnforcementDecision
from app.models.scim_group import ScimGroup, ScimGroupMember
from app.models.tenant import User
from app.models.tenant_identity_settings import TenantIdentitySettings
from app.models.tenant import Tenant, UserRole
from app.modules.enforcement.api.v1 import enforcement as enforcement_api
from app.shared.core.auth import CurrentUser, get_current_user
from app.shared.core.approval_permissions import (
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


class _FakeHistogram:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, str], float]] = []
        self._last_labels: dict[str, str] = {}

    def labels(self, **labels: str) -> "_FakeHistogram":
        self._last_labels = dict(labels)
        return self

    def observe(self, amount: float) -> None:
        self.calls.append((dict(self._last_labels), float(amount)))


class _FakeGauge:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, str], float]] = []
        self._last_labels: dict[str, str] = {}

    def labels(self, **labels: str) -> "_FakeGauge":
        self._last_labels = dict(labels)
        return self

    def set(self, amount: float) -> None:
        self.calls.append((dict(self._last_labels), float(amount)))


async def _seed_tenant(db) -> Tenant:
    tenant = Tenant(
        id=uuid4(),
        name="Enforcement API Tenant",
        plan="enterprise",
        is_deleted=False,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


def _override_user(async_client, user: CurrentUser) -> None:
    async_client.app.dependency_overrides[get_current_user] = lambda: user


def _clear_user_override(async_client) -> None:
    async_client.app.dependency_overrides.pop(get_current_user, None)


async def _issue_approved_token_via_api(async_client) -> tuple[str, str, str]:
    policy = await async_client.post(
        "/api/v1/enforcement/policies",
        json={
            "terraform_mode": "soft",
            "k8s_admission_mode": "soft",
            "require_approval_for_prod": True,
            "require_approval_for_nonprod": False,
            "enforce_prod_requester_reviewer_separation": False,
            "auto_approve_below_monthly_usd": "0",
            "hard_deny_above_monthly_usd": "2500",
            "default_ttl_seconds": 1200,
        },
    )
    assert policy.status_code == 200

    budget = await async_client.post(
        "/api/v1/enforcement/budgets",
        json={
            "scope_key": "default",
            "monthly_limit_usd": "2000",
            "active": True,
        },
    )
    assert budget.status_code == 200

    gate = await async_client.post(
        "/api/v1/enforcement/gate/terraform",
        json={
            "project_id": "default",
            "environment": "prod",
            "action": "terraform.apply",
            "resource_reference": "module.db.aws_db_instance.main",
            "estimated_monthly_delta_usd": "100",
            "estimated_hourly_delta_usd": "0.14",
            "metadata": {"resource_type": "aws_db_instance"},
            "idempotency_key": "api-token-consume-1",
        },
    )
    assert gate.status_code == 200
    gate_payload = gate.json()
    assert gate_payload["approval_request_id"] is not None

    approve = await async_client.post(
        f"/api/v1/enforcement/approvals/{gate_payload['approval_request_id']}/approve",
        json={"notes": "approved for token consume"},
    )
    assert approve.status_code == 200
    approve_payload = approve.json()
    assert isinstance(approve_payload["approval_token"], str)

    return (
        approve_payload["approval_token"],
        gate_payload["approval_request_id"],
        gate_payload["decision_id"],
    )


async def _set_terraform_policy_mode(async_client, mode: str) -> None:
    response = await async_client.post(
        "/api/v1/enforcement/policies",
        json={
            "terraform_mode": mode,
            "k8s_admission_mode": mode,
            "require_approval_for_prod": False,
            "require_approval_for_nonprod": False,
            "auto_approve_below_monthly_usd": "0",
            "hard_deny_above_monthly_usd": "2500",
            "default_ttl_seconds": 1200,
        },
    )
    assert response.status_code == 200


async def _create_pending_approval_via_api(
    async_client,
    *,
    idempotency_key: str,
    environment: str = "nonprod",
    require_approval_for_prod: bool = False,
    require_approval_for_nonprod: bool = True,
) -> dict:
    policy = await async_client.post(
        "/api/v1/enforcement/policies",
        json={
            "terraform_mode": "soft",
            "k8s_admission_mode": "soft",
            "require_approval_for_prod": require_approval_for_prod,
            "require_approval_for_nonprod": require_approval_for_nonprod,
            "auto_approve_below_monthly_usd": "0",
            "hard_deny_above_monthly_usd": "2500",
            "default_ttl_seconds": 1200,
        },
    )
    assert policy.status_code == 200

    budget = await async_client.post(
        "/api/v1/enforcement/budgets",
        json={
            "scope_key": "default",
            "monthly_limit_usd": "1000",
            "active": True,
        },
    )
    assert budget.status_code == 200

    gate = await async_client.post(
        "/api/v1/enforcement/gate/terraform",
        json={
            "project_id": "default",
            "environment": environment,
            "action": "terraform.apply",
            "resource_reference": "module.app.aws_instance.web",
            "estimated_monthly_delta_usd": "75",
            "estimated_hourly_delta_usd": "0.11",
            "metadata": {"resource_type": "aws_instance"},
            "idempotency_key": idempotency_key,
        },
    )
    assert gate.status_code == 200
    payload = gate.json()
    assert payload["decision"] == "REQUIRE_APPROVAL"
    return payload


async def _seed_member_scim_prod_permission(db, tenant_id, member_id, *, scim_enabled: bool) -> None:
    user = User(
        id=member_id,
        tenant_id=tenant_id,
        email=f"{member_id.hex[:12]}@example.com",
        role=UserRole.MEMBER.value,
        persona="engineering",
        is_active=True,
    )
    db.add(user)

    settings = TenantIdentitySettings(
        tenant_id=tenant_id,
        scim_enabled=scim_enabled,
        scim_group_mappings=[
            {
                "group": "finops-approvers",
                "permissions": [APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD],
            }
        ],
    )
    db.add(settings)
    await db.flush()

    group = ScimGroup(
        tenant_id=tenant_id,
        display_name="finops-approvers",
        display_name_norm="finops-approvers",
        external_id="finops-approvers",
        external_id_norm="finops-approvers",
    )
    db.add(group)
    await db.flush()

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
