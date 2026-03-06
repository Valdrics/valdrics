# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_api_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_consume_approval_token_conflict_error_paths(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    owner_user = CurrentUser(
        id=uuid4(),
        email="owner@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    _override_user(async_client, owner_user)

    decision = SimpleNamespace(
        id=uuid4(),
        source=SimpleNamespace(value="terraform"),
        environment="prod",
        project_id="default",
        action="terraform.apply",
        resource_reference="module.db.aws_db_instance.main",
        request_fingerprint="fp-123",
        estimated_monthly_delta_usd="100.00",
        token_expires_at=None,
    )

    try:
        approval_missing_expiry = SimpleNamespace(
            id=uuid4(),
            approval_token_expires_at=None,
            approval_token_consumed_at=datetime.now(timezone.utc),
        )
        with patch(
            "app.modules.enforcement.api.v1.approvals.EnforcementService.consume_approval_token",
            new_callable=AsyncMock,
            return_value=(approval_missing_expiry, decision),
        ):
            missing_expiry = await async_client.post(
                "/api/v1/enforcement/approvals/consume",
                json={"approval_token": "x" * 48},
            )
        assert missing_expiry.status_code == 409
        assert "expiry is unavailable" in str(missing_expiry.json()).lower()

        approval_not_consumed = SimpleNamespace(
            id=uuid4(),
            approval_token_expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            approval_token_consumed_at=None,
        )
        with patch(
            "app.modules.enforcement.api.v1.approvals.EnforcementService.consume_approval_token",
            new_callable=AsyncMock,
            return_value=(approval_not_consumed, decision),
        ):
            not_consumed = await async_client.post(
                "/api/v1/enforcement/approvals/consume",
                json={"approval_token": "y" * 48},
            )
        assert not_consumed.status_code == 409
        assert "was not consumed" in str(not_consumed.json()).lower()
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_policy_budget_credit_list_endpoints_with_member_access(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        policy_update = await async_client.post(
            "/api/v1/enforcement/policies",
            json={
                "terraform_mode": "soft",
                "k8s_admission_mode": "hard",
                "require_approval_for_prod": True,
                "require_approval_for_nonprod": True,
                "auto_approve_below_monthly_usd": "10",
                "hard_deny_above_monthly_usd": "3000",
                "default_ttl_seconds": 900,
            },
        )
        assert policy_update.status_code == 200

        budget_create = await async_client.post(
            "/api/v1/enforcement/budgets",
            json={
                "scope_key": "default",
                "monthly_limit_usd": "1200",
                "active": True,
            },
        )
        assert budget_create.status_code == 200

        expires_at = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        credit_create = await async_client.post(
            "/api/v1/enforcement/credits",
            json={
                "scope_key": "default",
                "total_amount_usd": "250",
                "expires_at": expires_at,
                "reason": "integration test credit",
            },
        )
        assert credit_create.status_code == 200

        member_user = CurrentUser(
            id=uuid4(),
            email="member@enforcement.local",
            tenant_id=tenant.id,
            role=UserRole.MEMBER,
        )
        _override_user(async_client, member_user)

        policy_get = await async_client.get("/api/v1/enforcement/policies")
        budgets_get = await async_client.get("/api/v1/enforcement/budgets")
        credits_get = await async_client.get("/api/v1/enforcement/credits")

        assert policy_get.status_code == 200
        assert policy_get.json()["k8s_admission_mode"] == "hard"
        assert budgets_get.status_code == 200
        assert len(budgets_get.json()) == 1
        assert budgets_get.json()[0]["scope_key"] == "default"
        assert credits_get.status_code == 200
        assert len(credits_get.json()) == 1
        assert credits_get.json()[0]["reason"] == "integration test credit"
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_reconcile_overdue_uses_configured_default_sla(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        gate_payload = await _create_pending_approval_via_api(
            async_client,
            idempotency_key="api-reconcile-default-sla-1",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )
        decision_id = gate_payload["decision_id"]
        decision = (
            await db.execute(
                select(EnforcementDecision).where(
                    EnforcementDecision.id == UUID(decision_id)
                )
            )
        ).scalar_one()
        decision.created_at = datetime.now(timezone.utc) - timedelta(hours=3)
        await db.commit()

        with patch(
            "app.modules.enforcement.api.v1.reservations.get_settings",
            return_value=SimpleNamespace(
                ENFORCEMENT_RESERVATION_RECONCILIATION_SLA_SECONDS=7200
            ),
        ):
            reconcile = await async_client.post(
                "/api/v1/enforcement/reservations/reconcile-overdue",
                json={"limit": 50},
            )
        assert reconcile.status_code == 200
        payload = reconcile.json()
        assert payload["released_count"] == 1
        assert payload["older_than_seconds"] == 7200
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_export_parity_validation_branches(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        bad_order = await async_client.get(
            "/api/v1/enforcement/exports/parity"
            "?start_date=2026-02-10&end_date=2026-02-01"
        )
        assert bad_order.status_code == 422
        assert "on or before end_date" in str(bad_order.json()).lower()

        too_wide = await async_client.get(
            "/api/v1/enforcement/exports/parity"
            "?start_date=2024-01-01&end_date=2026-02-01"
        )
        assert too_wide.status_code == 422
        assert "date window exceeds export limit" in str(too_wide.json()).lower()

        bad_max_rows = await async_client.get(
            "/api/v1/enforcement/exports/parity?max_rows=0"
        )
        assert bad_max_rows.status_code == 422
        assert "max_rows must be >= 1" in str(bad_max_rows.json()).lower()

        too_large_max_rows = await async_client.get(
            "/api/v1/enforcement/exports/parity?max_rows=50001"
        )
        assert too_large_max_rows.status_code == 422
        assert "max_rows must be <=" in str(too_large_max_rows.json()).lower()
    finally:
        _clear_user_override(async_client)



def test_export_limit_helper_fallback_branches() -> None:
    from app.modules.enforcement.api.v1.exports import _export_max_days, _export_max_rows

    with patch(
        "app.modules.enforcement.api.v1.exports.get_settings",
        return_value=SimpleNamespace(
            ENFORCEMENT_EXPORT_MAX_DAYS="not-an-int",
            ENFORCEMENT_EXPORT_MAX_ROWS="not-an-int",
        ),
    ):
        assert _export_max_days() == 366
        assert _export_max_rows() == 10000

    with patch(
        "app.modules.enforcement.api.v1.exports.get_settings",
        return_value=SimpleNamespace(
            ENFORCEMENT_EXPORT_MAX_DAYS=0,
            ENFORCEMENT_EXPORT_MAX_ROWS=999999,
        ),
    ):
        assert _export_max_days() == 1
        assert _export_max_rows() == 50000
