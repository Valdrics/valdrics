# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_evaluate_gate_computed_context_defaults_when_cost_history_missing(
    db,
    monkeypatch,
) -> None:
    fixed_now = datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(enforcement_service_module, "_utcnow", lambda: fixed_now)

    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.vpc.aws_vpc.main",
            estimated_monthly_delta_usd=Decimal("12"),
            estimated_hourly_delta_usd=Decimal("0.02"),
            metadata={"resource_type": "aws_vpc"},
            idempotency_key="computed-context-no-history-1",
        ),
    )

    assert result.decision.decision == EnforcementDecisionType.ALLOW
    assert result.decision.burn_rate_daily_usd == Decimal("0.0000")
    assert result.decision.forecast_eom_usd == Decimal("0.0000")
    assert result.decision.risk_class == "low"
    assert result.decision.anomaly_signal is False

    payload = result.decision.response_payload or {}
    context = payload.get("computed_context")
    assert isinstance(context, dict)
    assert context.get("data_source_mode") == "none"
    assert context.get("burn_rate_daily_usd") == "0.0000"
    assert context.get("forecast_eom_usd") == "0.0000"
    assert context.get("mtd_spend_usd") == "0.0000"
    assert context.get("observed_cost_days") == 0
    assert context.get("latest_cost_date") is None



@pytest.mark.asyncio
async def test_evaluate_gate_computed_context_detects_new_spend_when_baseline_is_zero(
    db,
    monkeypatch,
) -> None:
    fixed_now = datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(enforcement_service_module, "_utcnow", lambda: fixed_now)

    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await _seed_daily_cost_history(
        db,
        tenant_id=tenant.id,
        provider="aws",
        daily_costs=[(date(2026, 2, 20), Decimal("150"))],
    )

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.lambda.aws_lambda_function.new-service",
            estimated_monthly_delta_usd=Decimal("20"),
            estimated_hourly_delta_usd=Decimal("0.03"),
            metadata={"resource_type": "aws_lambda_function"},
            idempotency_key="computed-context-new-spend-1",
        ),
    )

    context = (result.decision.response_payload or {}).get("computed_context")
    assert isinstance(context, dict)
    assert result.decision.anomaly_signal is True
    assert context.get("anomaly_signal") is True
    assert context.get("anomaly_kind") == "new_spend"
    assert context.get("anomaly_percent") is None
    assert context.get("anomaly_delta_usd") == "150.0000"
    assert context.get("data_source_mode") == "final"



@pytest.mark.asyncio
async def test_evaluate_gate_computed_context_marks_unavailable_on_cost_query_failure(
    db,
    monkeypatch,
) -> None:
    fixed_now = datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(enforcement_service_module, "_utcnow", lambda: fixed_now)

    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()
    warning_calls: list[tuple[str, dict[str, object]]] = []

    async def _raise_cost_query(**_kwargs):
        raise RuntimeError("cost backend unavailable")

    def _capture_warning(event: str, **kwargs):
        warning_calls.append((event, dict(kwargs)))

    monkeypatch.setattr(service, "_load_daily_cost_totals", _raise_cost_query)
    monkeypatch.setattr(enforcement_service_module.logger, "warning", _capture_warning)

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.vpc.aws_vpc.main",
            estimated_monthly_delta_usd=Decimal("12"),
            estimated_hourly_delta_usd=Decimal("0.02"),
            metadata={"resource_type": "aws_vpc"},
            idempotency_key="computed-context-unavailable-1",
        ),
    )

    context = (result.decision.response_payload or {}).get("computed_context")
    assert isinstance(context, dict)
    assert context.get("data_source_mode") == "unavailable"
    assert context.get("anomaly_signal") is False
    assert context.get("anomaly_kind") is None
    assert context.get("burn_rate_daily_usd") == "0.0000"
    assert context.get("forecast_eom_usd") == "0.0000"
    assert warning_calls
    assert warning_calls[0][0] == "enforcement_computed_context_unavailable"
    assert warning_calls[0][1]["tenant_id"] == str(tenant.id)
    assert warning_calls[0][1]["error_type"] == "RuntimeError"
    assert result.decision.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert "computed_context_unavailable" in (result.decision.reason_codes or [])
    assert "soft_mode_cost_context_escalation" in (result.decision.reason_codes or [])



@pytest.mark.asyncio
async def test_evaluate_gate_computed_context_unavailable_hard_mode_denies(
    db,
    monkeypatch,
) -> None:
    fixed_now = datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(enforcement_service_module, "_utcnow", lambda: fixed_now)

    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.HARD,
        k8s_admission_mode=EnforcementMode.HARD,
        require_approval_for_prod=False,
        require_approval_for_nonprod=False,
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("5000"),
        default_ttl_seconds=900,
    )

    async def _raise_cost_query(**_kwargs):
        raise RuntimeError("cost backend unavailable")

    monkeypatch.setattr(service, "_load_daily_cost_totals", _raise_cost_query)

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.eks.aws_eks_cluster.main",
            estimated_monthly_delta_usd=Decimal("42"),
            estimated_hourly_delta_usd=Decimal("0.07"),
            metadata={"resource_type": "aws_eks_cluster"},
            idempotency_key="computed-context-unavailable-hard-1",
        ),
    )

    context = (result.decision.response_payload or {}).get("computed_context")
    assert isinstance(context, dict)
    assert context.get("data_source_mode") == "unavailable"
    assert result.decision.decision == EnforcementDecisionType.DENY
    assert "computed_context_unavailable" in (result.decision.reason_codes or [])
    assert "hard_mode_cost_context_closed" in (result.decision.reason_codes or [])



@pytest.mark.asyncio
async def test_evaluate_gate_computed_context_snapshot_metadata_stable_across_runs(
    db,
    monkeypatch,
) -> None:
    fixed_now = datetime(2026, 2, 20, 10, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(enforcement_service_module, "_utcnow", lambda: fixed_now)

    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    daily_costs = [(date(2026, 2, day), Decimal("50")) for day in range(1, 21)]
    await _seed_daily_cost_history(
        db,
        tenant_id=tenant.id,
        provider="aws",
        daily_costs=daily_costs,
    )

    gate_input = GateInput(
        project_id="default",
        environment="nonprod",
        action="terraform.apply",
        resource_reference="module.vpc.aws_vpc.main",
        estimated_monthly_delta_usd=Decimal("10"),
        estimated_hourly_delta_usd=Decimal("0.01"),
        metadata={"resource_type": "aws_vpc"},
        dry_run=True,
    )

    first = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(**{**gate_input.__dict__, "idempotency_key": "context-stable-1"}),
    )
    second = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(**{**gate_input.__dict__, "idempotency_key": "context-stable-2"}),
    )

    first_context = (first.decision.response_payload or {}).get("computed_context")
    second_context = (second.decision.response_payload or {}).get("computed_context")
    assert isinstance(first_context, dict)
    assert isinstance(second_context, dict)

    stable_keys = [
        "month_start",
        "month_end",
        "month_elapsed_days",
        "month_total_days",
        "observed_cost_days",
        "latest_cost_date",
        "mtd_spend_usd",
        "burn_rate_daily_usd",
        "forecast_eom_usd",
        "data_source_mode",
    ]
    for key in stable_keys:
        assert first_context.get(key) == second_context.get(key), key



@pytest.mark.asyncio
async def test_evaluate_gate_enforces_plan_monthly_ceiling_before_budget_waterfall(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        require_approval_for_prod=False,
        require_approval_for_nonprod=False,
        plan_monthly_ceiling_usd=Decimal("50"),
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("1000"),
        default_ttl_seconds=900,
    )
    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("500"),
        active=True,
    )

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.plan-cap",
            estimated_monthly_delta_usd=Decimal("60"),
            estimated_hourly_delta_usd=Decimal("0.08"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="plan-ceiling-soft-1",
        ),
    )

    reasons = result.decision.reason_codes or []
    assert result.decision.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert "plan_limit_exceeded" in reasons
    assert "soft_mode_plan_limit_escalation" in reasons
    assert result.decision.reservation_active is False
    assert result.decision.reserved_allocation_usd == Decimal("0")
    assert result.decision.reserved_credit_usd == Decimal("0")
    assert result.approval is not None

    payload = result.decision.response_payload or {}
    assert payload.get("entitlement_reason_code") == "plan_limit_exceeded"
    waterfall = payload.get("entitlement_waterfall")
    assert isinstance(waterfall, list) and waterfall
    assert waterfall[0]["stage"] == "plan_limit"
    assert waterfall[0]["status"] == "fail"
    assert payload.get("plan_headroom_usd") == "50.0000"



@pytest.mark.asyncio
async def test_evaluate_gate_enforces_enterprise_ceiling_after_waterfall_stages(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        require_approval_for_prod=False,
        require_approval_for_nonprod=False,
        enterprise_monthly_ceiling_usd=Decimal("25"),
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("1000"),
        default_ttl_seconds=900,
    )
    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("100"),
        active=True,
    )

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.enterprise-cap",
            estimated_monthly_delta_usd=Decimal("30"),
            estimated_hourly_delta_usd=Decimal("0.09"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="enterprise-ceiling-soft-1",
        ),
    )

    reasons = result.decision.reason_codes or []
    assert result.decision.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert "enterprise_ceiling_exceeded" in reasons
    assert "soft_mode_enterprise_ceiling_escalation" in reasons
    assert result.decision.reservation_active is True
    assert result.decision.reserved_allocation_usd == Decimal("25.0000")
    assert result.decision.reserved_credit_usd == Decimal("0.0000")
    assert result.approval is not None

    payload = result.decision.response_payload or {}
    assert payload.get("entitlement_reason_code") == "enterprise_ceiling_exceeded"
    waterfall = payload.get("entitlement_waterfall")
    assert isinstance(waterfall, list)
    assert any(
        stage.get("stage") == "enterprise_ceiling" and stage.get("status") == "fail"
        for stage in waterfall
    )
    assert payload.get("enterprise_headroom_usd") == "25.0000"



@pytest.mark.asyncio
async def test_credit_waterfall_uses_reserved_before_emergency_credit_pools(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("0"),
        active=True,
    )
    reserved_credit = await service.create_credit_grant(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        total_amount_usd=Decimal("5"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="reserved pool",
    )
    emergency_credit = await service.create_credit_grant(
        tenant_id=tenant.id,
        actor_id=actor_id,
        pool_type=EnforcementCreditPoolType.EMERGENCY,
        scope_key="org",
        total_amount_usd=Decimal("10"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="emergency pool",
    )

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.K8S_ADMISSION,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="admission.validate",
            resource_reference="deployments/apps/credit-pool-order",
            estimated_monthly_delta_usd=Decimal("12"),
            estimated_hourly_delta_usd=Decimal("0.02"),
            metadata={"namespace": "apps"},
            idempotency_key="credit-pool-order-1",
        ),
    )

    reasons = result.decision.reason_codes or []
    assert result.decision.decision == EnforcementDecisionType.ALLOW_WITH_CREDITS
    assert result.decision.reserved_allocation_usd == Decimal("0.0000")
    assert result.decision.reserved_credit_usd == Decimal("12.0000")
    assert "credit_waterfall_used" in reasons
    assert "reserved_credit_waterfall_used" in reasons
    assert "emergency_credit_waterfall_used" in reasons

    response_payload = result.decision.response_payload or {}
    assert response_payload.get("reserved_credit_split_usd") == {
        "reserved": "5.0000",
        "emergency": "7.0000",
    }

    refreshed_reserved = (
        await db.execute(
            select(EnforcementCreditGrant).where(
                EnforcementCreditGrant.id == reserved_credit.id
            )
        )
    ).scalar_one()
    refreshed_emergency = (
        await db.execute(
            select(EnforcementCreditGrant).where(
                EnforcementCreditGrant.id == emergency_credit.id
            )
        )
    ).scalar_one()
    assert refreshed_reserved.remaining_amount_usd == Decimal("0.0000")
    assert refreshed_emergency.remaining_amount_usd == Decimal("3.0000")

    allocations = (
        await db.execute(
            select(EnforcementCreditReservationAllocation).where(
                EnforcementCreditReservationAllocation.decision_id == result.decision.id
            )
        )
    ).scalars().all()
    assert len(allocations) == 2
