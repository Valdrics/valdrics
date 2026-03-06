# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_api_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_approval_flow_prod_rejects_admin_without_prod_permission(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        policy = await async_client.post(
            "/api/v1/enforcement/policies",
            json={
                "terraform_mode": "soft",
                "k8s_admission_mode": "soft",
                "require_approval_for_prod": True,
                "require_approval_for_nonprod": False,
                "approval_routing_rules": [
                    {
                        "rule_id": "allow-member-prod-approver",
                        "enabled": True,
                        "environments": ["prod"],
                        "required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
                        "allowed_reviewer_roles": ["owner", "admin", "member"],
                        "require_requester_reviewer_separation": True,
                    }
                ],
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
                "environment": "prod",
                "action": "terraform.apply",
                "resource_reference": "module.db.aws_db_instance.main",
                "estimated_monthly_delta_usd": "100",
                "estimated_hourly_delta_usd": "0.14",
                "metadata": {"resource_type": "aws_db_instance"},
                "idempotency_key": "api-approval-prod-1",
            },
        )
        assert gate.status_code == 200
        gate_payload = gate.json()
        assert gate_payload["decision"] == "REQUIRE_APPROVAL"
        assert gate_payload["approval_request_id"] is not None

        approve = await async_client.post(
            f"/api/v1/enforcement/approvals/{gate_payload['approval_request_id']}/approve",
            json={"notes": "attempting prod approval"},
        )
        assert approve.status_code == 403
        response_body = str(approve.json()).lower()
        assert "insufficient approval permission" in response_body
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_approval_flow_prod_allows_member_with_scim_permission(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        policy = await async_client.post(
            "/api/v1/enforcement/policies",
            json={
                "terraform_mode": "soft",
                "k8s_admission_mode": "soft",
                "require_approval_for_prod": True,
                "require_approval_for_nonprod": False,
                "approval_routing_rules": [
                    {
                        "rule_id": "allow-member-prod-approver",
                        "enabled": True,
                        "environments": ["prod"],
                        "required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
                        "allowed_reviewer_roles": ["owner", "admin", "member"],
                        "require_requester_reviewer_separation": True,
                    }
                ],
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
                "environment": "prod",
                "action": "terraform.apply",
                "resource_reference": "module.db.aws_db_instance.main",
                "estimated_monthly_delta_usd": "100",
                "estimated_hourly_delta_usd": "0.14",
                "metadata": {"resource_type": "aws_db_instance"},
                "idempotency_key": "api-member-scim-prod-1",
            },
        )
        assert gate.status_code == 200
        approval_id = gate.json()["approval_request_id"]
        assert approval_id is not None

        member_id = uuid4()
        await _seed_member_scim_prod_permission(
            db,
            tenant.id,
            member_id,
            scim_enabled=True,
        )
        member_user = CurrentUser(
            id=member_id,
            email="member@enforcement.local",
            tenant_id=tenant.id,
            role=UserRole.MEMBER,
        )
        _override_user(async_client, member_user)

        approve = await async_client.post(
            f"/api/v1/enforcement/approvals/{approval_id}/approve",
            json={"notes": "approved by scim member"},
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"
        assert isinstance(approve.json()["approval_token"], str)
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_approval_flow_prod_denies_member_when_scim_disabled(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        policy = await async_client.post(
            "/api/v1/enforcement/policies",
            json={
                "terraform_mode": "soft",
                "k8s_admission_mode": "soft",
                "require_approval_for_prod": True,
                "require_approval_for_nonprod": False,
                "approval_routing_rules": [
                    {
                        "rule_id": "allow-member-prod-approver",
                        "enabled": True,
                        "environments": ["prod"],
                        "required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
                        "allowed_reviewer_roles": ["owner", "admin", "member"],
                        "require_requester_reviewer_separation": True,
                    }
                ],
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
                "environment": "prod",
                "action": "terraform.apply",
                "resource_reference": "module.db.aws_db_instance.main",
                "estimated_monthly_delta_usd": "100",
                "estimated_hourly_delta_usd": "0.14",
                "metadata": {"resource_type": "aws_db_instance"},
                "idempotency_key": "api-member-scim-disabled-prod-1",
            },
        )
        assert gate.status_code == 200
        approval_id = gate.json()["approval_request_id"]
        assert approval_id is not None

        member_id = uuid4()
        await _seed_member_scim_prod_permission(
            db,
            tenant.id,
            member_id,
            scim_enabled=False,
        )
        member_user = CurrentUser(
            id=member_id,
            email="member@enforcement.local",
            tenant_id=tenant.id,
            role=UserRole.MEMBER,
        )
        _override_user(async_client, member_user)

        approve = await async_client.post(
            f"/api/v1/enforcement/approvals/{approval_id}/approve",
            json={"notes": "attempt with disabled scim"},
        )
        assert approve.status_code == 403
        assert "insufficient approval permission" in str(approve.json()).lower()
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_consume_approval_token_endpoint_rejects_replay_and_tamper(
    async_client, db
) -> None:
    tenant = await _seed_tenant(db)
    owner_user = CurrentUser(
        id=uuid4(),
        email="owner@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    _override_user(async_client, owner_user)

    try:
        token, _, _ = await _issue_approved_token_via_api(async_client)

        consume = await async_client.post(
            "/api/v1/enforcement/approvals/consume",
            json={"approval_token": token},
        )
        assert consume.status_code == 200
        consume_payload = consume.json()
        assert consume_payload["status"] == "consumed"
        assert consume_payload["request_fingerprint"]
        assert consume_payload["max_hourly_delta_usd"] == "0.140000"

        replay = await async_client.post(
            "/api/v1/enforcement/approvals/consume",
            json={"approval_token": token},
        )
        assert replay.status_code == 409
        assert "replay" in str(replay.json()).lower()

        header, payload, signature = token.split(".")
        decoded_payload = json.loads(base64.urlsafe_b64decode(payload + "==").decode())
        decoded_payload["resource_reference"] = "module.hijack.aws_iam_role.admin"
        tampered_payload = (
            base64.urlsafe_b64encode(json.dumps(decoded_payload).encode())
            .decode()
            .rstrip("=")
        )
        tampered_token = f"{header}.{tampered_payload}.{signature}"

        tampered = await async_client.post(
            "/api/v1/enforcement/approvals/consume",
            json={"approval_token": tampered_token},
        )
        assert tampered.status_code == 401
        assert "invalid approval token" in str(tampered.json()).lower()
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_consume_approval_token_endpoint_rejects_expected_project_mismatch(
    async_client, db
) -> None:
    tenant = await _seed_tenant(db)
    owner_user = CurrentUser(
        id=uuid4(),
        email="owner@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    _override_user(async_client, owner_user)

    try:
        token, _, _ = await _issue_approved_token_via_api(async_client)
        consume = await async_client.post(
            "/api/v1/enforcement/approvals/consume",
            json={
                "approval_token": token,
                "expected_project_id": "wrong-project",
            },
        )
        assert consume.status_code == 409
        assert "expected project mismatch" in str(consume.json()).lower()
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_request_rejects_unknown_fields(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        response = await async_client.post(
            "/api/v1/enforcement/gate/terraform",
            json={
                "project_id": "default",
                "environment": "nonprod",
                "action": "terraform.apply",
                "resource_reference": "module.vpc.aws_vpc.main",
                "estimated_monthly_delta_usd": "10",
                "estimated_hourly_delta_usd": "0.01",
                "metadata": {"resource_type": "aws_vpc"},
                "unexpected_field": "must_fail",
            },
        )
        assert response.status_code == 422
        assert "extra" in str(response.json()).lower()
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "trigger", "expected_decision", "expected_mode_reason"),
    [
        ("shadow", "timeout", "ALLOW", "shadow_mode_fail_open"),
        ("soft", "timeout", "REQUIRE_APPROVAL", "soft_mode_fail_safe_escalation"),
        ("hard", "timeout", "DENY", "hard_mode_fail_closed"),
        ("shadow", "error", "ALLOW", "shadow_mode_fail_open"),
        ("soft", "error", "REQUIRE_APPROVAL", "soft_mode_fail_safe_escalation"),
        ("hard", "error", "DENY", "hard_mode_fail_closed"),
    ],
)
async def test_gate_failsafe_timeout_and_error_modes(
    async_client,
    db,
    mode: str,
    trigger: str,
    expected_decision: str,
    expected_mode_reason: str,
) -> None:
    tenant = await _seed_tenant(db)
    owner_user = CurrentUser(
        id=uuid4(),
        email="owner@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    _override_user(async_client, owner_user)

    try:
        await _set_terraform_policy_mode(async_client, mode)

        payload = {
            "project_id": "default",
            "environment": "prod",
            "action": "terraform.apply",
            "resource_reference": "module.eks.aws_eks_cluster.main",
            "estimated_monthly_delta_usd": "100",
            "estimated_hourly_delta_usd": "0.10",
            "metadata": {"resource_type": "aws_eks_cluster"},
            "idempotency_key": f"api-failsafe-{mode}-{trigger}",
        }

        async def _slow_gate(*args, **kwargs):
            _ = args, kwargs
            await asyncio.sleep(0.05)

        async def _error_gate(*args, **kwargs):
            _ = args, kwargs
            raise RuntimeError("simulated outage")

        with (
            patch(
                "app.modules.enforcement.api.v1.enforcement._gate_timeout_seconds",
                return_value=0.01 if trigger == "timeout" else 1.0,
            ),
            patch(
                "app.modules.enforcement.api.v1.enforcement.EnforcementService.evaluate_gate",
                side_effect=_slow_gate if trigger == "timeout" else _error_gate,
            ),
        ):
            response = await async_client.post(
                "/api/v1/enforcement/gate/terraform",
                json=payload,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["decision"] == expected_decision
        reasons = body["reason_codes"]
        assert expected_mode_reason in reasons
        if trigger == "timeout":
            assert "gate_timeout" in reasons
        else:
            assert "gate_evaluation_error" in reasons

        if expected_decision == "REQUIRE_APPROVAL":
            assert body["approval_request_id"] is not None
        else:
            assert body["approval_request_id"] is None
    finally:
        _clear_user_override(async_client)
