# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_resolve_fail_safe_gate_integrityerror_replays_existing_decision(db, monkeypatch) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    seed_service = EnforcementService(db)
    payload = GateInput(
        project_id="default",
        environment="prod",
        action="terraform.apply",
        resource_reference="module.rds.aws_db_instance.failsafe-race",
        estimated_monthly_delta_usd=Decimal("70"),
        estimated_hourly_delta_usd=Decimal("0.08"),
        metadata={"resource_type": "aws_db_instance"},
        idempotency_key="failsafe-replay-race-1",
    )

    seeded = await seed_service.resolve_fail_safe_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=payload,
        failure_reason_code="gate_timeout",
        failure_metadata={"timeout_seconds": "0.01"},
    )
    existing_decision_id = seeded.decision.id
    existing_decision_stub = SimpleNamespace(
        id=existing_decision_id,
        decision=seeded.decision.decision,
    )
    existing_approval_stub = (
        SimpleNamespace(id=seeded.approval.id) if seeded.approval is not None else None
    )

    service = EnforcementService(db)
    idem_calls: list[str] = []
    approval_calls: list[object] = []

    async def _fake_get_decision_by_idempotency(**_kwargs):
        idem_calls.append("call")
        if len(idem_calls) == 1:
            return None
        return existing_decision_stub

    async def _fake_get_approval_by_decision(decision_id):
        approval_calls.append(decision_id)
        return existing_approval_stub

    monkeypatch.setattr(service, "_get_decision_by_idempotency", _fake_get_decision_by_idempotency)
    monkeypatch.setattr(service, "_get_approval_by_decision", _fake_get_approval_by_decision)

    result = await service.resolve_fail_safe_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=payload,
        failure_reason_code="gate_timeout",
        failure_metadata={"timeout_seconds": "0.01"},
    )

    assert result.decision.id == existing_decision_id
    assert len(idem_calls) == 2  # pre-check + replay lookup after IntegrityError rollback
    assert approval_calls == [existing_decision_id]



@pytest.mark.asyncio
async def test_resolve_fail_safe_gate_integrityerror_reraises_when_replay_lookup_missing(
    db, monkeypatch
) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    seed_service = EnforcementService(db)
    payload = GateInput(
        project_id="default",
        environment="prod",
        action="terraform.apply",
        resource_reference="module.rds.aws_db_instance.failsafe-race-miss",
        estimated_monthly_delta_usd=Decimal("71"),
        estimated_hourly_delta_usd=Decimal("0.081"),
        metadata={"resource_type": "aws_db_instance"},
        idempotency_key="failsafe-rereraise-race-1",
    )

    await seed_service.resolve_fail_safe_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=payload,
        failure_reason_code="gate_timeout",
        failure_metadata={"timeout_seconds": "0.01"},
    )

    service = EnforcementService(db)
    idem_calls: list[str] = []

    async def _always_miss_idempotency(**_kwargs):
        idem_calls.append("call")
        return None

    monkeypatch.setattr(service, "_get_decision_by_idempotency", _always_miss_idempotency)

    with pytest.raises(enforcement_service_module.IntegrityError):
        await service.resolve_fail_safe_gate(
            tenant_id=tenant.id,
            actor_id=actor_id,
            source=EnforcementSource.TERRAFORM,
            gate_input=payload,
            failure_reason_code="gate_timeout",
            failure_metadata={"timeout_seconds": "0.01"},
        )

    assert len(idem_calls) == 2  # pre-check + replay lookup after rollback



@pytest.mark.asyncio
async def test_evaluate_gate_uses_terraform_environment_mode_matrix(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    service = EnforcementService(db)

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        terraform_mode_prod=EnforcementMode.HARD,
        terraform_mode_nonprod=EnforcementMode.SHADOW,
        k8s_admission_mode=EnforcementMode.SOFT,
        k8s_admission_mode_prod=EnforcementMode.SOFT,
        k8s_admission_mode_nonprod=EnforcementMode.SOFT,
        require_approval_for_prod=False,
        require_approval_for_nonprod=False,
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("100"),
        default_ttl_seconds=900,
    )

    prod = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="prod",
            action="terraform.apply",
            resource_reference="module.eks.aws_eks_cluster.prod",
            estimated_monthly_delta_usd=Decimal("250"),
            estimated_hourly_delta_usd=Decimal("0.2"),
            metadata={"resource_type": "aws_eks_cluster"},
            idempotency_key="env-mode-matrix-terraform-prod-1",
        ),
    )
    nonprod = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.eks.aws_eks_cluster.nonprod",
            estimated_monthly_delta_usd=Decimal("250"),
            estimated_hourly_delta_usd=Decimal("0.2"),
            metadata={"resource_type": "aws_eks_cluster"},
            idempotency_key="env-mode-matrix-terraform-nonprod-1",
        ),
    )

    assert prod.decision.decision == EnforcementDecisionType.DENY
    assert "hard_mode_fail_closed" not in (prod.decision.reason_codes or [])
    assert "hard_deny_threshold_exceeded" in (prod.decision.reason_codes or [])
    assert (prod.decision.response_payload or {}).get("mode_scope") == "terraform:prod"

    assert nonprod.decision.decision == EnforcementDecisionType.ALLOW
    assert "shadow_mode_override" in (nonprod.decision.reason_codes or [])
    assert (nonprod.decision.response_payload or {}).get("mode_scope") == "terraform:nonprod"



@pytest.mark.asyncio
async def test_evaluate_gate_uses_k8s_environment_mode_matrix(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    service = EnforcementService(db)

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        terraform_mode_prod=EnforcementMode.SOFT,
        terraform_mode_nonprod=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        k8s_admission_mode_prod=EnforcementMode.HARD,
        k8s_admission_mode_nonprod=EnforcementMode.SOFT,
        require_approval_for_prod=False,
        require_approval_for_nonprod=False,
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("100"),
        default_ttl_seconds=900,
    )

    prod = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.K8S_ADMISSION,
        gate_input=GateInput(
            project_id="default",
            environment="prod",
            action="admission.validate",
            resource_reference="deployments/apps/prod-api",
            estimated_monthly_delta_usd=Decimal("250"),
            estimated_hourly_delta_usd=Decimal("0.2"),
            metadata={"resource_type": "kubernetes_deployment"},
            idempotency_key="env-mode-matrix-k8s-prod-1",
        ),
    )
    nonprod = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.K8S_ADMISSION,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="admission.validate",
            resource_reference="deployments/apps/nonprod-api",
            estimated_monthly_delta_usd=Decimal("250"),
            estimated_hourly_delta_usd=Decimal("0.2"),
            metadata={"resource_type": "kubernetes_deployment"},
            idempotency_key="env-mode-matrix-k8s-nonprod-1",
        ),
    )

    assert prod.decision.decision == EnforcementDecisionType.DENY
    assert (prod.decision.response_payload or {}).get("mode_scope") == "k8s_admission:prod"
    assert nonprod.decision.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert (nonprod.decision.response_payload or {}).get("mode_scope") == "k8s_admission:nonprod"



@pytest.mark.asyncio
async def test_resolve_fail_safe_gate_respects_environment_mode_matrix(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    service = EnforcementService(db)

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        terraform_mode_prod=EnforcementMode.HARD,
        terraform_mode_nonprod=EnforcementMode.SHADOW,
        k8s_admission_mode=EnforcementMode.SOFT,
        k8s_admission_mode_prod=EnforcementMode.SOFT,
        k8s_admission_mode_nonprod=EnforcementMode.SOFT,
        require_approval_for_prod=False,
        require_approval_for_nonprod=False,
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("1000"),
        default_ttl_seconds=900,
    )

    prod = await service.resolve_fail_safe_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="prod",
            action="terraform.apply",
            resource_reference="module.rds.aws_db_instance.prod",
            estimated_monthly_delta_usd=Decimal("80"),
            estimated_hourly_delta_usd=Decimal("0.09"),
            metadata={"resource_type": "aws_db_instance"},
            idempotency_key="failsafe-env-matrix-prod-1",
        ),
        failure_reason_code="gate_timeout",
        failure_metadata={"timeout_seconds": "0.01"},
    )
    nonprod = await service.resolve_fail_safe_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.rds.aws_db_instance.nonprod",
            estimated_monthly_delta_usd=Decimal("80"),
            estimated_hourly_delta_usd=Decimal("0.09"),
            metadata={"resource_type": "aws_db_instance"},
            idempotency_key="failsafe-env-matrix-nonprod-1",
        ),
        failure_reason_code="gate_timeout",
        failure_metadata={"timeout_seconds": "0.01"},
    )

    assert prod.decision.decision == EnforcementDecisionType.DENY
    assert "hard_mode_fail_closed" in (prod.decision.reason_codes or [])
    assert (prod.decision.response_payload or {}).get("mode_scope") == "terraform:prod"

    assert nonprod.decision.decision == EnforcementDecisionType.ALLOW
    assert "shadow_mode_fail_open" in (nonprod.decision.reason_codes or [])
    assert (nonprod.decision.response_payload or {}).get("mode_scope") == "terraform:nonprod"



@pytest.mark.asyncio
async def test_approve_request_member_denied_without_scim_permission(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="prod",
        require_approval_for_prod=True,
        require_approval_for_nonprod=False,
        idempotency_key="member-denied-no-scim-1",
    )
    service = EnforcementService(db)
    reviewer = CurrentUser(
        id=uuid4(),
        email="member@example.com",
        tenant_id=tenant.id,
        role=UserRole.MEMBER,
    )

    with pytest.raises(HTTPException) as exc:
        await service.approve_request(
            tenant_id=tenant.id,
            approval_id=gate.approval.id,
            reviewer=reviewer,
            notes="attempt without permission",
        )
    assert exc.value.status_code == 403
    assert "reviewer role" in str(exc.value.detail).lower()



@pytest.mark.asyncio
async def test_approve_request_member_with_scim_permission_requires_explicit_member_route(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="prod",
        require_approval_for_prod=True,
        require_approval_for_nonprod=False,
        idempotency_key="member-scim-needs-route-1",
    )
    member_id = uuid4()
    await _seed_member_scim_permission(
        db=db,
        tenant_id=tenant.id,
        member_id=member_id,
        permissions=[APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD],
        scim_enabled=True,
    )
    service = EnforcementService(db)
    reviewer = CurrentUser(
        id=member_id,
        email="member@example.com",
        tenant_id=tenant.id,
        role=UserRole.MEMBER,
    )

    with pytest.raises(HTTPException) as exc:
        await service.approve_request(
            tenant_id=tenant.id,
            approval_id=gate.approval.id,
            reviewer=reviewer,
            notes="member without explicit routing allow-list",
        )
    assert exc.value.status_code == 403
    assert "reviewer role" in str(exc.value.detail).lower()



@pytest.mark.asyncio
async def test_approve_request_member_allowed_with_scim_prod_permission(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="prod",
        require_approval_for_prod=True,
        require_approval_for_nonprod=False,
        idempotency_key="member-allowed-scim-prod-1",
        approval_routing_rules=[
            {
                "rule_id": "allow-member-prod-approver",
                "enabled": True,
                "environments": ["prod"],
                "allowed_reviewer_roles": ["owner", "admin", "member"],
                "required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
                "require_requester_reviewer_separation": True,
            }
        ],
    )
    member_id = uuid4()
    await _seed_member_scim_permission(
        db=db,
        tenant_id=tenant.id,
        member_id=member_id,
        permissions=[APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD],
        scim_enabled=True,
    )
    service = EnforcementService(db)
    reviewer = CurrentUser(
        id=member_id,
        email="member@example.com",
        tenant_id=tenant.id,
        role=UserRole.MEMBER,
    )

    approval, decision, token, _ = await service.approve_request(
        tenant_id=tenant.id,
        approval_id=gate.approval.id,
        reviewer=reviewer,
        notes="approved via scim prod permission",
    )
    assert approval.status == EnforcementApprovalStatus.APPROVED
    assert isinstance(token, str) and token
    assert decision.approval_token_issued is True



@pytest.mark.asyncio
async def test_approve_request_rejects_requester_reviewer_self_approval_for_prod(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="prod",
        require_approval_for_prod=True,
        require_approval_for_nonprod=False,
        idempotency_key="requester-reviewer-self-approval-1",
    )
    service = EnforcementService(db)
    reviewer = CurrentUser(
        id=actor_id,
        email="owner@example.com",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )

    with pytest.raises(HTTPException) as exc:
        await service.approve_request(
            tenant_id=tenant.id,
            approval_id=gate.approval.id,
            reviewer=reviewer,
            notes="self approval should be blocked",
        )
    assert exc.value.status_code == 403
    assert "requester/reviewer separation" in str(exc.value.detail).lower()
