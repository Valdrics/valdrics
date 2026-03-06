# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_api_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_gate_k8s_admission_review_rejects_invalid_cost_annotation(
    async_client, db
) -> None:
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
            "/api/v1/enforcement/gate/k8s/admission/review",
            json={
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "request": {
                    "uid": "admission-uid-invalid",
                    "kind": {"group": "apps", "version": "v1", "kind": "Deployment"},
                    "resource": {
                        "group": "apps",
                        "version": "v1",
                        "resource": "deployments",
                    },
                    "name": "api",
                    "namespace": "apps",
                    "operation": "CREATE",
                    "object": {
                        "metadata": {
                            "annotations": {
                                "valdrics.io/estimated-monthly-delta-usd": "not-a-number",
                            }
                        }
                    },
                },
            },
        )
        assert response.status_code == 422
        assert "invalid admission annotation" in str(response.json()).lower()
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_cloud_event_uses_event_id_idempotency_and_contract(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        budget = await async_client.post(
            "/api/v1/enforcement/budgets",
            json={
                "scope_key": "default",
                "monthly_limit_usd": "1000",
                "active": True,
            },
        )
        assert budget.status_code == 200

        payload = {
            "cloud_event": {
                "specversion": "1.0",
                "id": "evt-1001",
                "source": "aws.ec2",
                "type": "aws.ec2.instance.created",
                "subject": "i-0123456789abcdef0",
                "time": "2026-02-25T11:20:00Z",
                "data": {"instanceType": "m7i.large", "region": "us-east-1"},
            },
            "project_id": "default",
            "environment": "nonprod",
            "action": "cloud_event.observe",
            "estimated_monthly_delta_usd": "12",
            "estimated_hourly_delta_usd": "0.02",
        }

        first = await async_client.post(
            "/api/v1/enforcement/gate/cloud-event",
            json=payload,
        )
        second = await async_client.post(
            "/api/v1/enforcement/gate/cloud-event",
            json=payload,
        )
        assert first.status_code == 200
        assert second.status_code == 200
        first_payload = first.json()
        second_payload = second.json()
        assert first_payload["decision_id"] == second_payload["decision_id"]
        assert first_payload["request_fingerprint"] == second_payload["request_fingerprint"]
        assert first_payload["approval_token"] is None
        assert first_payload["approval_token_contract"] == "approval_flow_only"
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_cloud_event_rejects_retry_fingerprint_mismatch(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        budget = await async_client.post(
            "/api/v1/enforcement/budgets",
            json={
                "scope_key": "default",
                "monthly_limit_usd": "1000",
                "active": True,
            },
        )
        assert budget.status_code == 200

        base_payload = {
            "cloud_event": {
                "specversion": "1.0",
                "id": "evt-2001",
                "source": "aws.ec2",
                "type": "aws.ec2.instance.modified",
                "subject": "i-0abcdef0123456789",
                "data": {"instanceType": "m7i.2xlarge"},
            },
            "project_id": "default",
            "environment": "nonprod",
            "action": "cloud_event.observe",
            "estimated_monthly_delta_usd": "30",
            "estimated_hourly_delta_usd": "0.04",
            "idempotency_key": "api-cloud-event-fp-1",
        }
        first = await async_client.post(
            "/api/v1/enforcement/gate/cloud-event",
            json=base_payload,
        )
        assert first.status_code == 200
        first_fingerprint = first.json()["request_fingerprint"]

        mismatch = await async_client.post(
            "/api/v1/enforcement/gate/cloud-event",
            json={
                **base_payload,
                "estimated_monthly_delta_usd": "45",
                "expected_request_fingerprint": first_fingerprint,
            },
        )
        assert mismatch.status_code == 409
        assert "fingerprint mismatch" in str(mismatch.json()).lower()

        decision_count = (
            await db.execute(
                select(func.count())
                .select_from(EnforcementDecision)
                .where(EnforcementDecision.tenant_id == tenant.id)
                .where(EnforcementDecision.idempotency_key == "api-cloud-event-fp-1")
            )
        ).scalar_one()
        assert int(decision_count or 0) == 1
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_cloud_event_hard_mode_can_deny_by_budget(async_client, db) -> None:
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
                "k8s_admission_mode": "hard",
                "require_approval_for_prod": False,
                "require_approval_for_nonprod": False,
                "auto_approve_below_monthly_usd": "0",
                "hard_deny_above_monthly_usd": "2500",
                "default_ttl_seconds": 1200,
            },
        )
        assert policy.status_code == 200
        budget = await async_client.post(
            "/api/v1/enforcement/budgets",
            json={
                "scope_key": "finance",
                "monthly_limit_usd": "5",
                "active": True,
            },
        )
        assert budget.status_code == 200

        response = await async_client.post(
            "/api/v1/enforcement/gate/cloud-event",
            json={
                "cloud_event": {
                    "specversion": "1.0",
                    "id": "evt-3001",
                    "source": "aws.rds",
                    "type": "aws.rds.instance.created",
                    "subject": "db-instance-main",
                    "data": {"engine": "postgres"},
                },
                "project_id": "finance",
                "environment": "prod",
                "action": "cloud_event.observe",
                "estimated_monthly_delta_usd": "80",
                "estimated_hourly_delta_usd": "0.11",
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["decision"] == "DENY"
        assert "budget_exceeded" in payload["reason_codes"]
        assert payload["approval_token_contract"] == "approval_flow_only"
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_policy_budget_and_credit_endpoints(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        get_policy = await async_client.get("/api/v1/enforcement/policies")
        assert get_policy.status_code == 200
        assert get_policy.json()["terraform_mode"] in {"shadow", "soft", "hard"}
        assert (
            get_policy.json()["policy_document_schema_version"]
            == "valdrics.enforcement.policy.v1"
        )
        assert len(get_policy.json()["policy_document_sha256"]) == 64
        assert (
            get_policy.json()["policy_document"]["schema_version"]
            == "valdrics.enforcement.policy.v1"
        )

        update_policy = await async_client.post(
            "/api/v1/enforcement/policies",
            json={
                "terraform_mode": "hard",
                "terraform_mode_prod": "hard",
                "terraform_mode_nonprod": "shadow",
                "k8s_admission_mode": "soft",
                "k8s_admission_mode_prod": "hard",
                "k8s_admission_mode_nonprod": "soft",
                "require_approval_for_prod": True,
                "require_approval_for_nonprod": True,
                "plan_monthly_ceiling_usd": "1500",
                "enterprise_monthly_ceiling_usd": "2500",
                "auto_approve_below_monthly_usd": "0",
                "hard_deny_above_monthly_usd": "2500",
                "default_ttl_seconds": 1200,
            },
        )
        assert update_policy.status_code == 200
        assert update_policy.json()["terraform_mode"] == "hard"
        assert update_policy.json()["terraform_mode_prod"] == "hard"
        assert update_policy.json()["terraform_mode_nonprod"] == "shadow"
        assert update_policy.json()["k8s_admission_mode_prod"] == "hard"
        assert update_policy.json()["k8s_admission_mode_nonprod"] == "soft"
        assert update_policy.json()["require_approval_for_nonprod"] is True
        assert update_policy.json()["plan_monthly_ceiling_usd"] == "1500.0000"
        assert update_policy.json()["enterprise_monthly_ceiling_usd"] == "2500.0000"
        assert (
            update_policy.json()["policy_document"]["mode_matrix"]["terraform_default"]
            == "hard"
        )
        assert (
            update_policy.json()["policy_document"]["mode_matrix"]["terraform_nonprod"]
            == "shadow"
        )

        budget = await async_client.post(
            "/api/v1/enforcement/budgets",
            json={
                "scope_key": "default",
                "monthly_limit_usd": "2000",
                "active": True,
            },
        )
        assert budget.status_code == 200
        assert budget.json()["scope_key"] == "default"

        expires_at = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        credit = await async_client.post(
            "/api/v1/enforcement/credits",
            json={
                "pool_type": "emergency",
                "scope_key": "default",
                "total_amount_usd": "150",
                "expires_at": expires_at,
                "reason": "pilot credits",
            },
        )
        assert credit.status_code == 200
        assert credit.json()["pool_type"] == "emergency"
        assert credit.json()["remaining_amount_usd"] == "150.0000"
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_policy_upsert_accepts_policy_document_contract(async_client, db) -> None:
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
            "/api/v1/enforcement/policies",
            json={
                "terraform_mode": "soft",
                "k8s_admission_mode": "soft",
                "require_approval_for_prod": False,
                "require_approval_for_nonprod": False,
                "auto_approve_below_monthly_usd": "0",
                "hard_deny_above_monthly_usd": "10",
                "default_ttl_seconds": 900,
                "policy_document": {
                    "schema_version": "valdrics.enforcement.policy.v1",
                    "mode_matrix": {
                        "terraform_default": "hard",
                        "terraform_prod": "hard",
                        "terraform_nonprod": "shadow",
                        "k8s_admission_default": "shadow",
                        "k8s_admission_prod": "hard",
                        "k8s_admission_nonprod": "soft",
                    },
                    "approval": {
                        "require_approval_prod": True,
                        "require_approval_nonprod": True,
                        "enforce_prod_requester_reviewer_separation": True,
                        "enforce_nonprod_requester_reviewer_separation": False,
                        "routing_rules": [
                            {
                                "rule_id": "prod-route",
                                "enabled": True,
                                "environments": ["PROD"],
                                "required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
                                "allowed_reviewer_roles": ["OWNER", "ADMIN"],
                            }
                        ],
                    },
                    "entitlements": {
                        "plan_monthly_ceiling_usd": "100",
                        "enterprise_monthly_ceiling_usd": "500",
                        "auto_approve_below_monthly_usd": "5",
                        "hard_deny_above_monthly_usd": "5000",
                    },
                    "execution": {"default_ttl_seconds": 1800},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["terraform_mode"] == "hard"
        assert payload["terraform_mode_nonprod"] == "shadow"
        assert payload["k8s_admission_mode"] == "shadow"
        assert payload["k8s_admission_mode_prod"] == "hard"
        assert payload["require_approval_for_prod"] is True
        assert payload["require_approval_for_nonprod"] is True
        assert payload["auto_approve_below_monthly_usd"] == "5.0000"
        assert payload["default_ttl_seconds"] == 1800
        assert payload["approval_routing_rules"][0]["environments"] == ["prod"]
        assert payload["approval_routing_rules"][0]["allowed_reviewer_roles"] == [
            "owner",
            "admin",
        ]
        assert payload["policy_document"]["execution"]["default_ttl_seconds"] == 1800
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_approval_flow_nonprod_can_be_approved_by_admin(async_client, db) -> None:
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
                "require_approval_for_nonprod": True,
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
                "environment": "nonprod",
                "action": "terraform.apply",
                "resource_reference": "module.app.aws_instance.web",
                "estimated_monthly_delta_usd": "75",
                "estimated_hourly_delta_usd": "0.11",
                "metadata": {"resource_type": "aws_instance"},
                "idempotency_key": "api-approval-nonprod-1",
            },
        )
        assert gate.status_code == 200
        gate_payload = gate.json()
        assert gate_payload["decision"] == "REQUIRE_APPROVAL"
        assert gate_payload["approval_request_id"] is not None

        approve = await async_client.post(
            f"/api/v1/enforcement/approvals/{gate_payload['approval_request_id']}/approve",
            json={"notes": "approved by nonprod approver"},
        )
        assert approve.status_code == 200
        assert approve.json()["status"] == "approved"
        assert isinstance(approve.json()["approval_token"], str)
    finally:
        _clear_user_override(async_client)
