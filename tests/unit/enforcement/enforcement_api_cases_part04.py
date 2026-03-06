# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_api_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_gate_timeout_failsafe_remains_idempotent(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    owner_user = CurrentUser(
        id=uuid4(),
        email="owner@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    _override_user(async_client, owner_user)

    try:
        await _set_terraform_policy_mode(async_client, "hard")

        payload = {
            "project_id": "default",
            "environment": "prod",
            "action": "terraform.apply",
            "resource_reference": "module.rds.aws_db_instance.main",
            "estimated_monthly_delta_usd": "80",
            "estimated_hourly_delta_usd": "0.09",
            "metadata": {"resource_type": "aws_db_instance"},
            "idempotency_key": "api-timeout-idempotent-1",
        }

        async def _slow_gate(*args, **kwargs):
            _ = args, kwargs
            await asyncio.sleep(0.05)

        with (
            patch(
                "app.modules.enforcement.api.v1.enforcement._gate_timeout_seconds",
                return_value=0.01,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.EnforcementService.evaluate_gate",
                side_effect=_slow_gate,
            ),
        ):
            first = await async_client.post(
                "/api/v1/enforcement/gate/terraform",
                json=payload,
            )
            second = await async_client.post(
                "/api/v1/enforcement/gate/terraform",
                json=payload,
            )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["decision"] == "DENY"
        assert first.json()["decision_id"] == second.json()["decision_id"]
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("lock_code", "http_status", "expected_failure_type"),
    [
        ("gate_lock_timeout", 503, "lock_timeout"),
        ("gate_lock_contended", 409, "lock_contended"),
    ],
)
async def test_gate_lock_failures_route_to_failsafe_with_lock_reason_codes(
    async_client,
    db,
    lock_code: str,
    http_status: int,
    expected_failure_type: str,
) -> None:
    tenant = await _seed_tenant(db)
    owner_user = CurrentUser(
        id=uuid4(),
        email="owner@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    _override_user(async_client, owner_user)

    decisions_counter = _FakeCounter()
    reasons_counter = _FakeCounter()
    failures_counter = _FakeCounter()
    latency_hist = _FakeHistogram()

    try:
        await _set_terraform_policy_mode(async_client, "hard")
        with (
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_DECISIONS_TOTAL",
                decisions_counter,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_DECISION_REASONS_TOTAL",
                reasons_counter,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_FAILURES_TOTAL",
                failures_counter,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_LATENCY_SECONDS",
                latency_hist,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.EnforcementService.evaluate_gate",
                side_effect=HTTPException(
                    status_code=http_status,
                    detail={
                        "code": lock_code,
                        "lock_wait_seconds": "0.120",
                        "lock_timeout_seconds": "0.200",
                    },
                ),
            ),
        ):
            response = await async_client.post(
                "/api/v1/enforcement/gate/terraform",
                json={
                    "project_id": "default",
                    "environment": "prod",
                    "action": "terraform.apply",
                    "resource_reference": "module.eks.aws_eks_cluster.main",
                    "estimated_monthly_delta_usd": "100",
                    "estimated_hourly_delta_usd": "0.10",
                    "metadata": {"resource_type": "aws_eks_cluster"},
                    "idempotency_key": f"api-lock-failsafe-{lock_code}",
                },
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["decision"] == "DENY"
        assert lock_code in payload["reason_codes"]
        assert "hard_mode_fail_closed" in payload["reason_codes"]
        assert len(failures_counter.calls) == 1
        assert failures_counter.calls[0][0]["source"] == "terraform"
        assert failures_counter.calls[0][0]["failure_type"] == expected_failure_type
        assert any(call[0]["reason"] == lock_code for call in reasons_counter.calls)
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_metrics_emitted_for_normal_decision(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    owner_user = CurrentUser(
        id=uuid4(),
        email="owner@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    _override_user(async_client, owner_user)

    decisions_counter = _FakeCounter()
    reasons_counter = _FakeCounter()
    failures_counter = _FakeCounter()
    latency_hist = _FakeHistogram()

    try:
        with (
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_DECISIONS_TOTAL",
                decisions_counter,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_DECISION_REASONS_TOTAL",
                reasons_counter,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_FAILURES_TOTAL",
                failures_counter,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_LATENCY_SECONDS",
                latency_hist,
            ),
        ):
            response = await async_client.post(
                "/api/v1/enforcement/gate/terraform",
                json={
                    "project_id": "default",
                    "environment": "nonprod",
                    "action": "terraform.apply",
                    "resource_reference": "module.ec2.aws_instance.app",
                    "estimated_monthly_delta_usd": "10",
                    "estimated_hourly_delta_usd": "0.01",
                    "metadata": {"resource_type": "aws_instance"},
                    "idempotency_key": "api-metrics-normal-1",
                },
            )

        assert response.status_code == 200
        assert len(decisions_counter.calls) >= 1
        assert decisions_counter.calls[0][0]["source"] == "terraform"
        assert decisions_counter.calls[0][0]["path"] == "normal"
        assert len(latency_hist.calls) >= 1
        assert latency_hist.calls[0][0]["source"] == "terraform"
        assert latency_hist.calls[0][0]["path"] == "normal"
        assert failures_counter.calls == []
        assert len(reasons_counter.calls) >= 1
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_metrics_emitted_for_timeout_failsafe(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    owner_user = CurrentUser(
        id=uuid4(),
        email="owner@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    _override_user(async_client, owner_user)

    decisions_counter = _FakeCounter()
    reasons_counter = _FakeCounter()
    failures_counter = _FakeCounter()
    latency_hist = _FakeHistogram()

    async def _slow_gate(*args, **kwargs):
        _ = args, kwargs
        await asyncio.sleep(0.05)

    try:
        await _set_terraform_policy_mode(async_client, "hard")
        with (
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_DECISIONS_TOTAL",
                decisions_counter,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_DECISION_REASONS_TOTAL",
                reasons_counter,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_FAILURES_TOTAL",
                failures_counter,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.ENFORCEMENT_GATE_LATENCY_SECONDS",
                latency_hist,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement._gate_timeout_seconds",
                return_value=0.01,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.EnforcementService.evaluate_gate",
                side_effect=_slow_gate,
            ),
        ):
            response = await async_client.post(
                "/api/v1/enforcement/gate/terraform",
                json={
                    "project_id": "default",
                    "environment": "prod",
                    "action": "terraform.apply",
                    "resource_reference": "module.eks.aws_eks_cluster.main",
                    "estimated_monthly_delta_usd": "100",
                    "estimated_hourly_delta_usd": "0.10",
                    "metadata": {"resource_type": "aws_eks_cluster"},
                    "idempotency_key": "api-metrics-timeout-1",
                },
            )

        assert response.status_code == 200
        assert len(failures_counter.calls) == 1
        assert failures_counter.calls[0][0]["source"] == "terraform"
        assert failures_counter.calls[0][0]["failure_type"] == "timeout"
        assert len(decisions_counter.calls) >= 1
        assert decisions_counter.calls[0][0]["path"] == "failsafe"
        assert len(latency_hist.calls) >= 1
        assert latency_hist.calls[0][0]["path"] == "failsafe"
        assert any(
            call[0]["reason"] == "gate_timeout" for call in reasons_counter.calls
        )
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_reconcile_reservation_endpoint_admin(async_client, db) -> None:
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
            idempotency_key="api-reconcile-reservation-1",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )
        decision_id = gate_payload["decision_id"]

        reconcile = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            json={
                "actual_monthly_delta_usd": "80",
                "notes": "monthly close",
            },
        )
        assert reconcile.status_code == 200
        body = reconcile.json()
        assert body["decision_id"] == decision_id
        assert body["status"] == "overage"
        assert body["released_reserved_usd"] == "75.0000"
        assert body["drift_usd"] == "5.0000"
        assert body["reservation_active"] is False

        second = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            json={
                "actual_monthly_delta_usd": "80",
            },
        )
        assert second.status_code == 409

        active = await async_client.get("/api/v1/enforcement/reservations/active")
        assert active.status_code == 200
        ids = {item["decision_id"] for item in active.json()}
        assert decision_id not in ids
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_reconcile_reservation_endpoint_idempotent_replay_header(async_client, db) -> None:
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
            idempotency_key="api-reconcile-reservation-idem-1",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )
        decision_id = gate_payload["decision_id"]

        first = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            headers={"Idempotency-Key": "api-reconcile-idempotency-1"},
            json={
                "actual_monthly_delta_usd": "80",
                "notes": "monthly close idempotent",
            },
        )
        assert first.status_code == 200
        first_body = first.json()
        assert first_body["status"] == "overage"

        replay = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            headers={"Idempotency-Key": "api-reconcile-idempotency-1"},
            json={
                "actual_monthly_delta_usd": "80",
                "notes": "monthly close idempotent",
            },
        )
        assert replay.status_code == 200
        replay_body = replay.json()
        assert replay_body == first_body

        mismatch = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            headers={"Idempotency-Key": "api-reconcile-idempotency-1"},
            json={
                "actual_monthly_delta_usd": "81",
                "notes": "monthly close idempotent",
            },
        )
        assert mismatch.status_code == 409
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_reconcile_reservation_rejects_invalid_idempotency_key_header(async_client, db) -> None:
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
            idempotency_key="api-reconcile-reservation-idem-2",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )
        decision_id = gate_payload["decision_id"]

        response = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            headers={"Idempotency-Key": "x"},
            json={"actual_monthly_delta_usd": "80"},
        )
        assert response.status_code == 422
        body = response.json()
        assert "idempotency_key" in str(body.get("error", "")).lower()
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_reconcile_reservation_endpoint_idempotent_replay_body_key(async_client, db) -> None:
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
            idempotency_key="api-reconcile-reservation-idem-3",
            environment="nonprod",
            require_approval_for_prod=False,
            require_approval_for_nonprod=True,
        )
        decision_id = gate_payload["decision_id"]

        first = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            json={
                "actual_monthly_delta_usd": "80",
                "notes": "body-idem",
                "idempotency_key": "api-reconcile-body-idem-1",
            },
        )
        assert first.status_code == 200
        first_body = first.json()

        replay = await async_client.post(
            f"/api/v1/enforcement/reservations/{decision_id}/reconcile",
            json={
                "actual_monthly_delta_usd": "80",
                "notes": "body-idem",
                "idempotency_key": "api-reconcile-body-idem-1",
            },
        )
        assert replay.status_code == 200
        assert replay.json() == first_body
    finally:
        _clear_user_override(async_client)
