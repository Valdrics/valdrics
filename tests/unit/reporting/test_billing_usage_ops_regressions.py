from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.modules.billing.api.v1 import billing_ops
from app.shared.core.pricing import PricingTier


@pytest.mark.asyncio
async def test_load_billing_usage_counts_active_connections_across_all_provider_families() -> None:
    db = MagicMock()
    tenant_id = uuid4()
    active_connections = [
        SimpleNamespace(provider="aws"),
        SimpleNamespace(provider="aws"),
        SimpleNamespace(provider="azure"),
        SimpleNamespace(provider="saas"),
        SimpleNamespace(provider="license"),
        SimpleNamespace(provider="platform"),
        SimpleNamespace(provider="hybrid"),
    ]

    with patch.object(
        billing_ops,
        "list_tenant_connections",
        new=AsyncMock(return_value=active_connections),
    ) as list_connections_mock:
        usage = await billing_ops.load_billing_usage(
            db,
            tenant_id=tenant_id,
            tier=PricingTier.PRO,
        )

    list_connections_mock.assert_awaited_once_with(
        db,
        tenant_id,
        active_only=True,
    )
    assert usage["aws"].connected == 2
    assert usage["saas"].connected == 1
    assert usage["license"].connected == 1
    assert usage["platform"].connected == 1
    assert usage["hybrid"].connected == 1
    assert usage["platform"].limit == 10
    assert usage["hybrid"].limit == 10


@pytest.mark.asyncio
async def test_load_billing_usage_returns_zeroes_without_tenant_context() -> None:
    usage = await billing_ops.load_billing_usage(
        MagicMock(),
        tenant_id=None,
        tier=PricingTier.PRO,
    )

    assert usage["aws"].connected == 0
    assert usage["platform"].connected == 0
    assert usage["hybrid"].connected == 0
