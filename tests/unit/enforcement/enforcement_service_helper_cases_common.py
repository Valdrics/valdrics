# ruff: noqa: F401
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import app.modules.enforcement.domain.service as enforcement_service_module
from app.models.enforcement import (
    EnforcementApprovalStatus,
    EnforcementCreditPoolType,
    EnforcementDecisionType,
    EnforcementMode,
    EnforcementPolicy,
    EnforcementSource,
)
from app.models.tenant import Tenant
from app.modules.enforcement.domain.service import (
    EnforcementService,
    GateEvaluationResult,
    gate_result_to_response,
)
from app.shared.core.approval_permissions import (
    APPROVAL_PERMISSION_REMEDIATION_APPROVE_NONPROD,
    APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
)


def _service() -> EnforcementService:
    return EnforcementService(db=SimpleNamespace())


class _FakeCounter:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, str], float]] = []
        self._labels: dict[str, str] = {}

    def labels(self, **labels: str) -> "_FakeCounter":
        self._labels = dict(labels)
        return self

    def inc(self, amount: float = 1.0) -> None:
        self.calls.append((dict(self._labels), float(amount)))


class _FakeHistogram:
    def __init__(self) -> None:
        self.calls: list[tuple[dict[str, str], float]] = []
        self._labels: dict[str, str] = {}

    def labels(self, **labels: str) -> "_FakeHistogram":
        self._labels = dict(labels)
        return self

    def observe(self, amount: float) -> None:
        self.calls.append((dict(self._labels), float(amount)))


async def _seed_tenant(db) -> Tenant:
    tenant = Tenant(
        id=uuid4(),
        name="enforcement-helper-tenant",
        plan="pro",
        is_deleted=False,
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


def _base_policy_update_kwargs(*, tenant_id) -> dict[str, object]:
    return {
        "tenant_id": tenant_id,
        "terraform_mode": EnforcementMode.SOFT,
        "k8s_admission_mode": EnforcementMode.SOFT,
        "require_approval_for_prod": True,
        "require_approval_for_nonprod": False,
        "auto_approve_below_monthly_usd": Decimal("10"),
        "hard_deny_above_monthly_usd": Decimal("100"),
        "default_ttl_seconds": 900,
    }

# Export underscore-prefixed helper symbols for star-imported test parts.
__all__ = [name for name in globals() if not name.startswith("__")]
