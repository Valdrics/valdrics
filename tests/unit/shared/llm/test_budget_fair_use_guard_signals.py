from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.shared.core.exceptions import LLMFairUseExceededError
from app.shared.core.pricing import PricingTier
from app.shared.llm import budget_fair_use
from tests.unit.shared.llm.budget_fair_use_test_helpers import DummyManager, MetricStub


@pytest.mark.asyncio
async def test_enforce_fair_use_guards_disabled_or_unsupported_tier() -> None:
    tenant_id = uuid4()
    db = AsyncMock()

    settings_disabled = SimpleNamespace(LLM_FAIR_USE_GUARDS_ENABLED=False)
    with patch("app.shared.llm.budget_manager.get_settings", return_value=settings_disabled):
        assert (
            await budget_fair_use.enforce_fair_use_guards(
                DummyManager, tenant_id, db, PricingTier.PRO
            )
            is False
        )

    settings_enabled = SimpleNamespace(LLM_FAIR_USE_GUARDS_ENABLED=True)
    with patch("app.shared.llm.budget_manager.get_settings", return_value=settings_enabled):
        assert (
            await budget_fair_use.enforce_fair_use_guards(
                DummyManager, tenant_id, db, PricingTier.FREE
            )
            is False
        )


def test_classify_client_ip_risk_buckets() -> None:
    assert budget_fair_use._classify_client_ip(None) == ("unknown", 50)
    assert budget_fair_use._classify_client_ip("not-an-ip") == ("invalid", 80)
    assert budget_fair_use._classify_client_ip("127.0.0.1")[0] == "loopback"
    assert budget_fair_use._classify_client_ip("10.0.0.5")[0] == "private"
    assert budget_fair_use._classify_client_ip("8.8.8.8")[0] == "public_v4"


def test_classify_ip_additional_buckets() -> None:
    assert budget_fair_use._classify_client_ip("169.254.10.10")[0] == "link_local"
    assert budget_fair_use._classify_client_ip("ff00::1")[0] == "reserved"
    assert budget_fair_use._classify_client_ip("2001:4860:4860::8888")[0] == "public_v6"


@pytest.mark.asyncio
async def test_record_authenticated_abuse_signal_metrics_and_high_risk_audit() -> None:
    tenant_id = uuid4()
    metric = MetricStub()
    with (
        patch("app.shared.llm.budget_manager.LLM_AUTH_ABUSE_SIGNALS", metric),
        patch("app.shared.llm.budget_manager.LLM_AUTH_IP_RISK_SCORE", metric),
        patch("app.shared.llm.budget_manager.audit_log") as mock_audit,
    ):
        await budget_fair_use.record_authenticated_abuse_signal(
            manager_cls=DummyManager,
            tenant_id=tenant_id,
            db=AsyncMock(),
            tier=PricingTier.PRO,
            actor_type="user",
            user_id=uuid4(),
            client_ip="127.0.0.1",
        )
    assert metric.inc_calls == 1
    assert metric.set_calls == 1
    mock_audit.assert_called_once()


@pytest.mark.asyncio
async def test_record_authenticated_abuse_signal_low_risk_and_actor_normalization() -> None:
    tenant_id = uuid4()
    metric = MetricStub()
    with (
        patch("app.shared.llm.budget_manager.LLM_AUTH_ABUSE_SIGNALS", metric),
        patch("app.shared.llm.budget_manager.LLM_AUTH_IP_RISK_SCORE", metric),
        patch("app.shared.llm.budget_manager.audit_log") as mock_audit,
    ):
        await budget_fair_use.record_authenticated_abuse_signal(
            manager_cls=DummyManager,
            tenant_id=tenant_id,
            db=AsyncMock(),
            tier=PricingTier.PRO,
            actor_type="unknown",
            user_id=uuid4(),
            client_ip="10.0.0.8",
        )
    mock_audit.assert_not_called()


@pytest.mark.asyncio
async def test_record_authenticated_abuse_signal_system_actor_with_user_id_normalizes() -> None:
    tenant_id = uuid4()
    metric = MetricStub()
    with (
        patch("app.shared.llm.budget_manager.LLM_AUTH_ABUSE_SIGNALS", metric),
        patch("app.shared.llm.budget_manager.LLM_AUTH_IP_RISK_SCORE", metric),
        patch("app.shared.llm.budget_manager.audit_log") as mock_audit,
    ):
        await budget_fair_use.record_authenticated_abuse_signal(
            manager_cls=DummyManager,
            tenant_id=tenant_id,
            db=AsyncMock(),
            tier=PricingTier.PRO,
            actor_type="system",
            user_id=uuid4(),
            client_ip="10.1.0.1",
        )
    mock_audit.assert_not_called()


@pytest.mark.asyncio
async def test_enforce_fair_use_guards_soft_daily_and_concurrency_paths() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()
    settings = SimpleNamespace(
        LLM_FAIR_USE_GUARDS_ENABLED=True,
        LLM_FAIR_USE_PRO_DAILY_SOFT_CAP=2,
        LLM_FAIR_USE_ENTERPRISE_DAILY_SOFT_CAP=5,
        LLM_FAIR_USE_PER_MINUTE_CAP=0,
        LLM_FAIR_USE_PER_TENANT_CONCURRENCY_CAP=1,
        LLM_FAIR_USE_CONCURRENCY_LEASE_TTL_SECONDS=45,
    )

    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
        patch("app.shared.llm.budget_manager.audit_log"),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=2),
        ),
    ):
        with pytest.raises(LLMFairUseExceededError) as daily_exc:
            await budget_fair_use.enforce_fair_use_guards(
                DummyManager, tenant_id, db, PricingTier.PRO
            )
    assert daily_exc.value.details.get("gate") == "soft_daily"

    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
        patch("app.shared.llm.budget_manager.audit_log"),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.shared.llm.budget_fair_use.acquire_fair_use_inflight_slot",
            new=AsyncMock(return_value=(False, 3)),
        ),
    ):
        with pytest.raises(LLMFairUseExceededError) as conc_exc:
            await budget_fair_use.enforce_fair_use_guards(
                DummyManager, tenant_id, db, PricingTier.PRO
            )
    assert conc_exc.value.details.get("gate") == "concurrency"


@pytest.mark.asyncio
async def test_enforce_fair_use_guards_allow_path_with_invalid_per_minute_cap() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()
    settings = SimpleNamespace(
        LLM_FAIR_USE_GUARDS_ENABLED=True,
        LLM_FAIR_USE_PRO_DAILY_SOFT_CAP=100,
        LLM_FAIR_USE_ENTERPRISE_DAILY_SOFT_CAP=100,
        LLM_FAIR_USE_PER_MINUTE_CAP="invalid",
        LLM_FAIR_USE_PER_TENANT_CONCURRENCY_CAP=0,
        LLM_FAIR_USE_CONCURRENCY_LEASE_TTL_SECONDS="invalid",
    )

    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=settings),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
        patch("app.shared.llm.budget_manager.audit_log"),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=0),
        ),
    ):
        acquired = await budget_fair_use.enforce_fair_use_guards(
            DummyManager, tenant_id, db, PricingTier.PRO
        )

    assert acquired is False


@pytest.mark.asyncio
async def test_enforce_fair_use_guards_per_minute_and_concurrency_edges() -> None:
    tenant_id = uuid4()
    db = AsyncMock()
    metric = MetricStub()

    per_minute_settings = SimpleNamespace(
        LLM_FAIR_USE_GUARDS_ENABLED=True,
        LLM_FAIR_USE_PRO_DAILY_SOFT_CAP="invalid",
        LLM_FAIR_USE_ENTERPRISE_DAILY_SOFT_CAP="invalid",
        LLM_FAIR_USE_PER_MINUTE_CAP=1,
        LLM_FAIR_USE_PER_TENANT_CONCURRENCY_CAP=2,
        LLM_FAIR_USE_CONCURRENCY_LEASE_TTL_SECONDS=45,
    )
    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=per_minute_settings),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_PRE_AUTH_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_DENIALS", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
        patch("app.shared.llm.budget_manager.audit_log"),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=1),
        ),
    ):
        with pytest.raises(LLMFairUseExceededError) as exc:
            await budget_fair_use.enforce_fair_use_guards(
                DummyManager, tenant_id, db, PricingTier.PRO
            )
    assert exc.value.details.get("gate") == "per_minute"

    invalid_concurrency_settings = SimpleNamespace(
        LLM_FAIR_USE_GUARDS_ENABLED=True,
        LLM_FAIR_USE_PRO_DAILY_SOFT_CAP=100,
        LLM_FAIR_USE_ENTERPRISE_DAILY_SOFT_CAP=100,
        LLM_FAIR_USE_PER_MINUTE_CAP=0,
        LLM_FAIR_USE_PER_TENANT_CONCURRENCY_CAP="bad",
        LLM_FAIR_USE_CONCURRENCY_LEASE_TTL_SECONDS=45,
    )
    with (
        patch(
            "app.shared.llm.budget_manager.get_settings",
            return_value=invalid_concurrency_settings,
        ),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=0),
        ),
    ):
        assert (
            await budget_fair_use.enforce_fair_use_guards(
                DummyManager, tenant_id, db, PricingTier.PRO
            )
            is False
        )

    invalid_ttl_settings = SimpleNamespace(
        LLM_FAIR_USE_GUARDS_ENABLED=True,
        LLM_FAIR_USE_PRO_DAILY_SOFT_CAP=100,
        LLM_FAIR_USE_ENTERPRISE_DAILY_SOFT_CAP=100,
        LLM_FAIR_USE_PER_MINUTE_CAP=0,
        LLM_FAIR_USE_PER_TENANT_CONCURRENCY_CAP=2,
        LLM_FAIR_USE_CONCURRENCY_LEASE_TTL_SECONDS="bad",
    )
    with (
        patch("app.shared.llm.budget_manager.get_settings", return_value=invalid_ttl_settings),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_OBSERVED", metric),
        patch("app.shared.llm.budget_manager.LLM_FAIR_USE_EVALUATIONS", metric),
        patch(
            "app.shared.llm.budget_fair_use.count_requests_in_window",
            new=AsyncMock(return_value=0),
        ),
        patch(
            "app.shared.llm.budget_fair_use.acquire_fair_use_inflight_slot",
            new=AsyncMock(return_value=(True, 1)),
        ),
    ):
        assert (
            await budget_fair_use.enforce_fair_use_guards(
                DummyManager, tenant_id, db, PricingTier.PRO
            )
            is True
        )
