# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_update_policy_materializes_policy_document_contract_and_hash(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)

    policy = await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.HARD,
        terraform_mode_prod=EnforcementMode.HARD,
        terraform_mode_nonprod=EnforcementMode.SHADOW,
        k8s_admission_mode=EnforcementMode.SOFT,
        k8s_admission_mode_prod=EnforcementMode.HARD,
        k8s_admission_mode_nonprod=EnforcementMode.SOFT,
        require_approval_for_prod=True,
        require_approval_for_nonprod=True,
        plan_monthly_ceiling_usd=Decimal("1500"),
        enterprise_monthly_ceiling_usd=Decimal("2500"),
        auto_approve_below_monthly_usd=Decimal("10"),
        hard_deny_above_monthly_usd=Decimal("3000"),
        default_ttl_seconds=1200,
        approval_routing_rules=[
            {
                "rule_id": "policy-doc-hash-test",
                "enabled": True,
                "environments": ["prod"],
                "required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
                "allowed_reviewer_roles": ["owner", "admin"],
            }
        ],
    )

    assert policy.policy_document_schema_version == POLICY_DOCUMENT_SCHEMA_VERSION
    assert len(policy.policy_document_sha256) == 64

    parsed = PolicyDocument.model_validate(policy.policy_document)
    canonical = canonical_policy_document_payload(parsed)
    assert policy.policy_document_sha256 == policy_document_sha256(canonical)
    assert parsed.mode_matrix.terraform_default == EnforcementMode.HARD
    assert parsed.mode_matrix.terraform_nonprod == EnforcementMode.SHADOW
    assert parsed.execution.default_ttl_seconds == 1200



@pytest.mark.asyncio
async def test_update_policy_uses_policy_document_as_authoritative_contract(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)

    policy = await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        terraform_mode_prod=EnforcementMode.SOFT,
        terraform_mode_nonprod=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        k8s_admission_mode_prod=EnforcementMode.SOFT,
        k8s_admission_mode_nonprod=EnforcementMode.SOFT,
        require_approval_for_prod=False,
        require_approval_for_nonprod=False,
        plan_monthly_ceiling_usd=Decimal("1"),
        enterprise_monthly_ceiling_usd=Decimal("2"),
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("10"),
        default_ttl_seconds=900,
        policy_document={
            "schema_version": POLICY_DOCUMENT_SCHEMA_VERSION,
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
                        "allowed_reviewer_roles": ["OWNER", "MEMBER"],
                    }
                ],
            },
            "entitlements": {
                "plan_monthly_ceiling_usd": "111.1",
                "enterprise_monthly_ceiling_usd": "222.2",
                "auto_approve_below_monthly_usd": "5",
                "hard_deny_above_monthly_usd": "500",
            },
            "execution": {"default_ttl_seconds": 1800},
        },
    )

    assert policy.terraform_mode == EnforcementMode.HARD
    assert policy.terraform_mode_nonprod == EnforcementMode.SHADOW
    assert policy.k8s_admission_mode == EnforcementMode.SHADOW
    assert policy.k8s_admission_mode_prod == EnforcementMode.HARD
    assert policy.require_approval_for_prod is True
    assert policy.require_approval_for_nonprod is True
    assert policy.plan_monthly_ceiling_usd == Decimal("111.1000")
    assert policy.enterprise_monthly_ceiling_usd == Decimal("222.2000")
    assert policy.auto_approve_below_monthly_usd == Decimal("5.0000")
    assert policy.hard_deny_above_monthly_usd == Decimal("500.0000")
    assert policy.default_ttl_seconds == 1800
    assert policy.approval_routing_rules[0]["allowed_reviewer_roles"] == [
        "owner",
        "member",
    ]
    assert policy.approval_routing_rules[0]["environments"] == ["prod"]



@pytest.mark.asyncio
async def test_evaluate_gate_idempotency_returns_existing_decision(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    payload = GateInput(
        project_id="proj-a",
        environment="nonprod",
        action="terraform.apply",
        resource_reference="module.ec2.aws_instance.web",
        estimated_monthly_delta_usd=Decimal("12.5"),
        estimated_hourly_delta_usd=Decimal("0.018"),
        metadata={"resource_type": "aws_instance"},
        idempotency_key="idem-key-123",
    )

    first = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=payload,
    )
    second = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=payload,
    )

    assert first.decision.id == second.decision.id
    assert first.decision.decision == second.decision.decision
    assert "no_budget_configured" in (first.decision.reason_codes or [])

    count = (
        await db.execute(
            select(func.count())
            .select_from(EnforcementDecision)
            .where(EnforcementDecision.tenant_id == tenant.id)
        )
    ).scalar_one()
    assert count == 1



@pytest.mark.asyncio
async def test_evaluate_gate_integrityerror_replays_existing_idempotent_decision(db, monkeypatch) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    seed_service = EnforcementService(db)
    payload = GateInput(
        project_id="proj-race",
        environment="nonprod",
        action="terraform.apply",
        resource_reference="module.ec2.aws_instance.race",
        estimated_monthly_delta_usd=Decimal("15"),
        estimated_hourly_delta_usd=Decimal("0.02"),
        metadata={"resource_type": "aws_instance"},
        idempotency_key="idem-race-replay-1",
    )

    seeded = await seed_service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=payload,
    )
    existing_decision_id = seeded.decision.id
    existing_decision_stub = SimpleNamespace(
        id=existing_decision_id,
        decision=seeded.decision.decision,
    )

    service = EnforcementService(db)
    idem_calls: list[str] = []
    approval_calls: list[object] = []

    async def _fake_get_decision_by_idempotency(**_kwargs):
        idem_calls.append("call")
        if len(idem_calls) < 3:
            return None
        return existing_decision_stub

    async def _fake_get_approval_by_decision(decision_id):
        approval_calls.append(decision_id)
        return None

    async def _noop_lock(**_kwargs):
        return None

    monkeypatch.setattr(service, "_get_decision_by_idempotency", _fake_get_decision_by_idempotency)
    monkeypatch.setattr(service, "_get_approval_by_decision", _fake_get_approval_by_decision)
    monkeypatch.setattr(service, "_acquire_gate_evaluation_lock", _noop_lock)

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=payload,
    )

    assert result.decision.id == existing_decision_id
    assert result.approval is None
    assert len(idem_calls) == 3  # pre-check, post-lock recheck, IntegrityError replay fallback
    assert approval_calls == [existing_decision_id]



@pytest.mark.asyncio
async def test_evaluate_gate_integrityerror_reraises_when_replay_lookup_missing(db, monkeypatch) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    seed_service = EnforcementService(db)
    payload = GateInput(
        project_id="proj-race-miss",
        environment="nonprod",
        action="terraform.apply",
        resource_reference="module.ec2.aws_instance.race-miss",
        estimated_monthly_delta_usd=Decimal("16"),
        estimated_hourly_delta_usd=Decimal("0.021"),
        metadata={"resource_type": "aws_instance"},
        idempotency_key="idem-race-reraise-1",
    )

    # Seed a real decision so the duplicate insert triggers a database IntegrityError.
    await seed_service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=payload,
    )

    service = EnforcementService(db)
    idem_calls: list[str] = []

    async def _always_miss_idempotency(**_kwargs):
        idem_calls.append("call")
        return None

    async def _noop_lock(**_kwargs):
        return None

    monkeypatch.setattr(service, "_get_decision_by_idempotency", _always_miss_idempotency)
    monkeypatch.setattr(service, "_acquire_gate_evaluation_lock", _noop_lock)

    with pytest.raises(enforcement_service_module.IntegrityError):
        await service.evaluate_gate(
            tenant_id=tenant.id,
            actor_id=actor_id,
            source=EnforcementSource.TERRAFORM,
            gate_input=payload,
        )

    assert len(idem_calls) == 3  # pre-check, post-lock recheck, replay lookup after rollback



@pytest.mark.asyncio
async def test_evaluate_gate_prod_requires_approval_and_creates_pending_request(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("5000"),
        active=True,
    )

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="prod",
            action="terraform.apply",
            resource_reference="module.eks.aws_eks_cluster.main",
            estimated_monthly_delta_usd=Decimal("250"),
            estimated_hourly_delta_usd=Decimal("0.34"),
            metadata={"resource_type": "aws_eks_cluster"},
            idempotency_key="prod-approval-1",
        ),
    )

    assert result.decision.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert result.decision.approval_required is True
    assert result.approval is not None
    assert result.approval.status == EnforcementApprovalStatus.PENDING



@pytest.mark.asyncio
async def test_budget_waterfall_allocates_credit_headroom(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("10"),
        active=True,
    )
    await service.create_credit_grant(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        total_amount_usd=Decimal("100"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="pilot safety credit",
    )

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.K8S_ADMISSION,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="admission.validate",
            resource_reference="deployments/apps/web",
            estimated_monthly_delta_usd=Decimal("30"),
            estimated_hourly_delta_usd=Decimal("0.04"),
            metadata={"namespace": "apps"},
            idempotency_key="credits-waterfall-1",
        ),
    )

    assert result.decision.decision == EnforcementDecisionType.ALLOW_WITH_CREDITS
    assert result.decision.reserved_allocation_usd == Decimal("10.0000")
    assert result.decision.reserved_credit_usd == Decimal("20.0000")
    assert "credit_waterfall_used" in (result.decision.reason_codes or [])



@pytest.mark.asyncio
async def test_evaluate_gate_computed_context_populates_decision_and_ledger(
    db,
    monkeypatch,
) -> None:
    fixed_now = datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(enforcement_service_module, "_utcnow", lambda: fixed_now)

    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    daily_costs = [(date(2026, 2, day), Decimal("100")) for day in range(1, 20)]
    daily_costs.append((date(2026, 2, 20), Decimal("300")))
    await _seed_daily_cost_history(
        db,
        tenant_id=tenant.id,
        provider="aws",
        daily_costs=daily_costs,
    )

    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("10000"),
        active=True,
    )

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="prod",
            action="terraform.destroy",
            resource_reference="module.db.aws_db_instance.main",
            estimated_monthly_delta_usd=Decimal("1500"),
            estimated_hourly_delta_usd=Decimal("2.08"),
            metadata={"resource_type": "aws_db_instance", "criticality": "critical"},
            idempotency_key="computed-context-1",
        ),
    )

    assert result.decision.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert result.approval is not None
    assert result.decision.burn_rate_daily_usd == Decimal("110.0000")
    assert result.decision.forecast_eom_usd == Decimal("3080.0000")
    assert result.decision.risk_class == "high"
    assert int(result.decision.risk_score or 0) >= 6
    assert result.decision.anomaly_signal is True
    assert result.decision.policy_document_schema_version == "valdrics.enforcement.policy.v1"
    assert len(result.decision.policy_document_sha256) == 64

    payload = result.decision.response_payload or {}
    context = payload.get("computed_context")
    assert isinstance(context, dict)
    assert context.get("burn_rate_daily_usd") == "110.0000"
    assert context.get("forecast_eom_usd") == "3080.0000"
    assert context.get("mtd_spend_usd") == "2200.0000"
    assert context.get("anomaly_signal") is True
    assert context.get("anomaly_kind") == "spike"
    assert context.get("anomaly_delta_usd") == "200.0000"
    assert context.get("anomaly_percent") == "200.00"
    assert context.get("risk_class") == "high"
    assert context.get("month_elapsed_days") == 20
    assert context.get("month_total_days") == 28
    assert context.get("observed_cost_days") == 20
    assert context.get("data_source_mode") == "final"

    metadata = (result.decision.request_payload or {}).get("metadata") or {}
    assert metadata.get("risk_level") == "high"
    assert metadata.get("computed_risk_class") == "high"
    assert int(metadata.get("computed_risk_score", 0)) >= 6

    ledger_row = (
        await db.execute(
            select(EnforcementDecisionLedger).where(
                EnforcementDecisionLedger.decision_id == result.decision.id
            )
        )
    ).scalar_one()
    assert ledger_row.burn_rate_daily_usd == Decimal("110.0000")
    assert ledger_row.forecast_eom_usd == Decimal("3080.0000")
    assert ledger_row.risk_class == "high"
    assert int(ledger_row.risk_score or 0) >= 6
    assert ledger_row.anomaly_signal is True
    assert ledger_row.policy_document_schema_version == "valdrics.enforcement.policy.v1"
    assert len(ledger_row.policy_document_sha256) == 64
    assert ledger_row.policy_document_sha256 == result.decision.policy_document_sha256
