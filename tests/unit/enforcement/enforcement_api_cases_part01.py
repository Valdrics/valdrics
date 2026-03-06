# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_api_cases_common import *  # noqa: F401,F403



def test_enforcement_global_gate_limit_uses_configured_cap() -> None:
    with patch.object(
        enforcement_api,
        "get_settings",
        return_value=SimpleNamespace(
            ENFORCEMENT_GLOBAL_ABUSE_GUARD_ENABLED=True,
            ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP=321,
        ),
    ):
        assert enforcement_api._enforcement_global_gate_limit(SimpleNamespace()) == "321/minute"



def test_enforcement_global_gate_limit_fallback_when_disabled() -> None:
    with patch.object(
        enforcement_api,
        "get_settings",
        return_value=SimpleNamespace(
            ENFORCEMENT_GLOBAL_ABUSE_GUARD_ENABLED=False,
            ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP=1,
        ),
    ):
        assert (
            enforcement_api._enforcement_global_gate_limit(SimpleNamespace())
            == "1000000/minute"
        )



@pytest.mark.asyncio
async def test_gate_terraform_uses_idempotency_key(async_client, db) -> None:
    tenant = await _seed_tenant(db)
    admin_user = CurrentUser(
        id=uuid4(),
        email="admin@enforcement.local",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    _override_user(async_client, admin_user)

    try:
        payload = {
            "project_id": "default",
            "environment": "nonprod",
            "action": "terraform.apply",
            "resource_reference": "module.vpc.aws_vpc.main",
            "estimated_monthly_delta_usd": "15.25",
            "estimated_hourly_delta_usd": "0.02",
            "metadata": {"resource_type": "aws_vpc"},
        }
        headers = {"Idempotency-Key": "api-idem-terraform-1"}

        first = await async_client.post(
            "/api/v1/enforcement/gate/terraform",
            json=payload,
            headers=headers,
        )
        second = await async_client.post(
            "/api/v1/enforcement/gate/terraform",
            json=payload,
            headers=headers,
        )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["decision_id"] == second.json()["decision_id"]
        assert first.json()["approval_token"] is None
        assert first.json()["approval_token_contract"] == "approval_flow_only"
        assert isinstance(first.json().get("computed_context"), dict)
        assert "forecast_eom_usd" in first.json()["computed_context"]
        assert "burn_rate_daily_usd" in first.json()["computed_context"]
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_terraform_preflight_contract_and_retry_binding(async_client, db) -> None:
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
                "scope_key": "platform",
                "monthly_limit_usd": "1000",
                "active": True,
            },
        )
        assert budget.status_code == 200

        payload = {
            "run_id": "run-1001",
            "stage": "pre_plan",
            "workspace_id": "ws-01",
            "workspace_name": "platform-prod",
            "project_id": "platform",
            "environment": "nonprod",
            "action": "terraform.apply",
            "resource_reference": "module.vpc.aws_vpc.main",
            "estimated_monthly_delta_usd": "20",
            "estimated_hourly_delta_usd": "0.03",
            "metadata": {"resource_type": "aws_vpc"},
            "idempotency_key": "api-preflight-idempotency-1",
        }

        first = await async_client.post(
            "/api/v1/enforcement/gate/terraform/preflight",
            json=payload,
        )
        assert first.status_code == 200
        first_payload = first.json()
        assert first_payload["run_id"] == "run-1001"
        assert first_payload["stage"] == "pre_plan"
        assert first_payload["approval_token_contract"] == "approval_flow_only"
        assert first_payload["continuation"]["approval_consume_endpoint"] == (
            "/api/v1/enforcement/approvals/consume"
        )
        binding = first_payload["continuation"]["binding"]
        assert binding["expected_source"] == "terraform"
        assert binding["expected_project_id"] == "platform"
        assert binding["expected_request_fingerprint"] == first_payload["request_fingerprint"]

        retry_payload = {
            **payload,
            "expected_request_fingerprint": first_payload["request_fingerprint"],
        }
        second = await async_client.post(
            "/api/v1/enforcement/gate/terraform/preflight",
            json=retry_payload,
        )
        assert second.status_code == 200
        second_payload = second.json()
        assert first_payload["decision_id"] == second_payload["decision_id"]
        assert first_payload["request_fingerprint"] == second_payload["request_fingerprint"]
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_terraform_preflight_rejects_retry_fingerprint_mismatch(
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
        budget = await async_client.post(
            "/api/v1/enforcement/budgets",
            json={
                "scope_key": "platform",
                "monthly_limit_usd": "1000",
                "active": True,
            },
        )
        assert budget.status_code == 200

        base_payload = {
            "run_id": "run-2001",
            "stage": "pre_apply",
            "project_id": "platform",
            "environment": "nonprod",
            "action": "terraform.apply",
            "resource_reference": "module.eks.aws_eks_cluster.main",
            "estimated_monthly_delta_usd": "60",
            "estimated_hourly_delta_usd": "0.08",
            "metadata": {"resource_type": "aws_eks_cluster"},
            "idempotency_key": "api-preflight-mismatch-1",
        }
        first = await async_client.post(
            "/api/v1/enforcement/gate/terraform/preflight",
            json=base_payload,
        )
        assert first.status_code == 200
        expected_fingerprint = first.json()["request_fingerprint"]

        mismatch = await async_client.post(
            "/api/v1/enforcement/gate/terraform/preflight",
            json={
                **base_payload,
                "estimated_monthly_delta_usd": "75",
                "expected_request_fingerprint": expected_fingerprint,
            },
        )
        assert mismatch.status_code == 409
        assert "fingerprint mismatch" in str(mismatch.json()).lower()

        decision_count = (
            await db.execute(
                select(func.count())
                .select_from(EnforcementDecision)
                .where(EnforcementDecision.tenant_id == tenant.id)
                .where(EnforcementDecision.idempotency_key == "api-preflight-mismatch-1")
            )
        ).scalar_one()
        assert int(decision_count or 0) == 1
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_terraform_preflight_approval_continuation_end_to_end(
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
        policy = await async_client.post(
            "/api/v1/enforcement/policies",
            json={
                "terraform_mode": "soft",
                "k8s_admission_mode": "soft",
                "require_approval_for_prod": False,
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
                "scope_key": "platform",
                "monthly_limit_usd": "1000",
                "active": True,
            },
        )
        assert budget.status_code == 200

        preflight = await async_client.post(
            "/api/v1/enforcement/gate/terraform/preflight",
            json={
                "run_id": "run-3001",
                "stage": "pre_apply",
                "project_id": "platform",
                "environment": "nonprod",
                "action": "terraform.apply",
                "resource_reference": "module.db.aws_db_instance.main",
                "estimated_monthly_delta_usd": "100",
                "estimated_hourly_delta_usd": "0.14",
                "metadata": {"resource_type": "aws_db_instance"},
                "idempotency_key": "api-preflight-approval-1",
            },
        )
        assert preflight.status_code == 200
        preflight_payload = preflight.json()
        assert preflight_payload["decision"] == "REQUIRE_APPROVAL"
        approval_request_id = preflight_payload["approval_request_id"]
        assert approval_request_id is not None

        approve = await async_client.post(
            f"/api/v1/enforcement/approvals/{approval_request_id}/approve",
            json={"notes": "approved via preflight path"},
        )
        assert approve.status_code == 200
        approval_token = approve.json()["approval_token"]
        assert isinstance(approval_token, str) and approval_token

        binding = preflight_payload["continuation"]["binding"]
        consume = await async_client.post(
            "/api/v1/enforcement/approvals/consume",
            json={
                "approval_token": approval_token,
                "expected_source": binding["expected_source"],
                "expected_project_id": binding["expected_project_id"],
                "expected_environment": binding["expected_environment"],
                "expected_request_fingerprint": binding["expected_request_fingerprint"],
                "expected_resource_reference": binding["expected_resource_reference"],
            },
        )
        assert consume.status_code == 200
        consume_payload = consume.json()
        assert consume_payload["status"] == "consumed"
        assert consume_payload["decision_id"] == preflight_payload["decision_id"]
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_k8s_admission_review_contract_allow(async_client, db) -> None:
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
                    "uid": "admission-uid-1",
                    "kind": {"group": "apps", "version": "v1", "kind": "Deployment"},
                    "resource": {
                        "group": "apps",
                        "version": "v1",
                        "resource": "deployments",
                    },
                    "name": "web",
                    "namespace": "apps",
                    "operation": "CREATE",
                    "userInfo": {"username": "system:serviceaccount:apps:deployer"},
                    "object": {
                        "metadata": {
                            "labels": {
                                "valdrics.io/project-id": "platform",
                                "valdrics.io/environment": "nonprod",
                            }
                        }
                    },
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["apiVersion"] == "admission.k8s.io/v1"
        assert payload["kind"] == "AdmissionReview"
        assert payload["response"]["uid"] == "admission-uid-1"
        assert payload["response"]["allowed"] is True
        assert payload["response"]["auditAnnotations"]["valdrics.io/decision-id"]
        assert payload["response"]["auditAnnotations"]["valdrics.io/request-fingerprint"]
    finally:
        _clear_user_override(async_client)



@pytest.mark.asyncio
async def test_gate_k8s_admission_review_uses_annotation_cost_inputs_for_deny(
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
                "scope_key": "payments",
                "monthly_limit_usd": "5",
                "active": True,
            },
        )
        assert budget.status_code == 200

        response = await async_client.post(
            "/api/v1/enforcement/gate/k8s/admission/review",
            json={
                "apiVersion": "admission.k8s.io/v1",
                "kind": "AdmissionReview",
                "request": {
                    "uid": "admission-uid-2",
                    "kind": {"group": "apps", "version": "v1", "kind": "Deployment"},
                    "resource": {
                        "group": "apps",
                        "version": "v1",
                        "resource": "deployments",
                    },
                    "name": "payments-api",
                    "namespace": "payments",
                    "operation": "CREATE",
                    "object": {
                        "metadata": {
                            "annotations": {
                                "valdrics.io/project-id": "payments",
                                "valdrics.io/environment": "prod",
                                "valdrics.io/estimated-monthly-delta-usd": "50",
                                "valdrics.io/estimated-hourly-delta-usd": "0.07",
                            }
                        }
                    },
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["response"]["allowed"] is False
        assert payload["response"]["status"]["code"] == 403
        assert "decision=DENY" in payload["response"]["status"]["message"]
        assert (
            payload["response"]["auditAnnotations"]["valdrics.io/decision"] == "DENY"
        )
    finally:
        _clear_user_override(async_client)
