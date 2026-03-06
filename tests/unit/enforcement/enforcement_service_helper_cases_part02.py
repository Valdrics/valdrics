# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_helper_cases_common import *  # noqa: F401,F403



def test_reserve_amount_quantization_invariant_proves_defensive_guard() -> None:
    # In _reserve_credit_from_grants(), once both guards pass:
    #  - remaining > 0 (already quantized to 4dp)
    #  - grant_remaining > 0 (already quantized to 4dp)
    # then reserve_amount = quantize(min(...), 4dp) must be > 0. The line-4210
    # guard is therefore defensive against arithmetic/coercion regressions.
    step = Decimal("0.0001")
    values = [step * Decimal(i) for i in range(1, 51)]  # 0.0001 .. 0.0050
    for remaining in values:
        for grant_remaining in values:
            reserve_amount = enforcement_service_module._quantize(
                min(remaining, grant_remaining),
                "0.0001",
            )
            assert reserve_amount > Decimal("0.0000")



@pytest.mark.asyncio
async def test_resolve_monthly_ceiling_prefers_policy_then_tier_limits(monkeypatch) -> None:
    service = _service()
    tenant_id = uuid4()
    policy_with_configured_plan = EnforcementPolicy(
        tenant_id=tenant_id,
        plan_monthly_ceiling_usd=Decimal("500.12999"),
        enterprise_monthly_ceiling_usd=None,
    )

    plan = await service._resolve_plan_monthly_ceiling_usd(
        policy=policy_with_configured_plan,
        tenant_tier=enforcement_service_module.PricingTier.PRO,
    )
    assert plan == Decimal("500.1300")

    monkeypatch.setattr(
        enforcement_service_module,
        "get_tier_limit",
        lambda _tier, key: Decimal("1200.5555") if key.endswith("enterprise_monthly_ceiling_usd") else Decimal("0"),
    )

    plan_from_limit = await service._resolve_plan_monthly_ceiling_usd(
        policy=EnforcementPolicy(tenant_id=tenant_id, plan_monthly_ceiling_usd=None),
        tenant_tier=enforcement_service_module.PricingTier.PRO,
    )
    assert plan_from_limit is None

    enterprise = await service._resolve_enterprise_monthly_ceiling_usd(
        policy=policy_with_configured_plan,
        tenant_tier=enforcement_service_module.PricingTier.PRO,
    )
    assert enterprise == Decimal("1200.5555")



def test_derive_risk_assessment_covers_high_medium_and_low_scores() -> None:
    service = _service()

    high_gate = enforcement_service_module.GateInput(
        project_id="p1",
        environment="prod",
        action="terraform.destroy",
        resource_reference="cluster/main-postgres",
        estimated_monthly_delta_usd=Decimal("7500"),
        estimated_hourly_delta_usd=Decimal("10"),
        metadata={"criticality": "critical", "resource_type": "database"},
    )
    high_class, high_score, high_factors = service._derive_risk_assessment(
        gate_input=high_gate,
        is_production=True,
        anomaly_signal=True,
    )
    assert high_class == "high"
    assert high_score >= 8
    assert "destructive_action" in high_factors
    assert "anomaly_spike_signal" in high_factors

    medium_gate = enforcement_service_module.GateInput(
        project_id="p2",
        environment="staging",
        action="terraform.apply",
        resource_reference="service/api",
        estimated_monthly_delta_usd=Decimal("1200"),
        estimated_hourly_delta_usd=Decimal("1"),
        metadata={"criticality": "medium", "resource_type": "database"},
    )
    medium_class, _, medium_factors = service._derive_risk_assessment(
        gate_input=medium_gate,
        is_production=False,
        anomaly_signal=False,
    )
    assert medium_class == "medium"
    assert "moderate_monthly_delta" in medium_factors

    low_gate = enforcement_service_module.GateInput(
        project_id="p3",
        environment="dev",
        action="terraform.plan",
        resource_reference="misc/worker",
        estimated_monthly_delta_usd=Decimal("10"),
        estimated_hourly_delta_usd=Decimal("0.1"),
        metadata={"resource_type": "app"},
    )
    low_class, low_score, low_factors = service._derive_risk_assessment(
        gate_input=low_gate,
        is_production=False,
        anomaly_signal=False,
    )
    assert low_class == "low"
    assert low_score == 0
    assert low_factors == tuple()



def test_resolve_approval_routing_trace_matches_policy_rules() -> None:
    service = _service()
    tenant_id = uuid4()
    policy = EnforcementPolicy(
        tenant_id=tenant_id,
        enforce_prod_requester_reviewer_separation=True,
        approval_routing_rules=[
            {
                "rule_id": "team-prod-high",
                "enabled": True,
                "environments": ["prod"],
                "action_prefixes": ["terraform.apply"],
                "min_monthly_delta_usd": "100",
                "max_monthly_delta_usd": "1000",
                "risk_levels": ["critical"],
                "required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
                "allowed_reviewer_roles": ["owner", "member"],
                "require_requester_reviewer_separation": True,
            }
        ],
    )

    decision = SimpleNamespace(
        environment="production",
        action="terraform.apply.module",
        estimated_monthly_delta_usd=Decimal("500"),
        request_payload={"metadata": {"risk_level": "critical"}},
    )

    trace = service._resolve_approval_routing_trace(policy=policy, decision=decision)
    assert trace["matched_rule"] == "policy_rule"
    assert trace["rule_id"] == "team-prod-high"
    assert trace["required_permission"] == APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD
    assert trace["allowed_reviewer_roles"] == ["owner", "member"]

    unmatched_decision = SimpleNamespace(
        environment="dev",
        action="terraform.plan",
        estimated_monthly_delta_usd=Decimal("5"),
        request_payload={"metadata": {"risk_level": "low"}},
    )
    default_trace = service._resolve_approval_routing_trace(
        policy=policy,
        decision=unmatched_decision,
    )
    assert default_trace["matched_rule"] == "default"



def test_routing_trace_or_default_uses_fallback_and_sanitizes_valid_trace() -> None:
    service = _service()
    tenant_id = uuid4()
    policy = EnforcementPolicy(
        tenant_id=tenant_id,
        enforce_nonprod_requester_reviewer_separation=False,
        approval_routing_rules=[],
    )
    decision = SimpleNamespace(environment="dev", request_payload={"metadata": {}}, action="terraform.apply", estimated_monthly_delta_usd=Decimal("10"))

    approval_missing = SimpleNamespace(routing_trace={"rule_id": "", "required_permission": None})
    fallback = service._routing_trace_or_default(
        policy=policy,
        decision=decision,
        approval=approval_missing,
    )
    assert fallback["matched_rule"] == "default"

    approval_valid = SimpleNamespace(
        routing_trace={
            "rule_id": "  custom-rule-id ",
            "required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_NONPROD,
            "allowed_reviewer_roles": ["member", "member", "owner"],
            "require_requester_reviewer_separation": True,
        }
    )
    sanitized = service._routing_trace_or_default(
        policy=policy,
        decision=decision,
        approval=approval_valid,
    )
    assert sanitized["rule_id"] == "custom-rule-id"
    assert sanitized["required_permission"] == APPROVAL_PERMISSION_REMEDIATION_APPROVE_NONPROD
    assert sanitized["allowed_reviewer_roles"] == ["member", "owner"]
    assert sanitized["require_requester_reviewer_separation"] is True



def test_entitlement_waterfall_and_budget_waterfall_cover_mode_branches() -> None:
    service = _service()

    plan_fail = service._evaluate_entitlement_waterfall(
        mode=EnforcementMode.SHADOW,
        monthly_delta=Decimal("200"),
        plan_headroom=Decimal("100"),
        allocation_headroom=Decimal("100"),
        reserved_credit_headroom=Decimal("0"),
        emergency_credit_headroom=Decimal("0"),
        enterprise_headroom=None,
    )
    assert plan_fail.decision == EnforcementDecisionType.ALLOW
    assert plan_fail.reason_code == "plan_limit_exceeded"

    budget_soft = service._evaluate_entitlement_waterfall(
        mode=EnforcementMode.SOFT,
        monthly_delta=Decimal("300"),
        plan_headroom=None,
        allocation_headroom=Decimal("100"),
        reserved_credit_headroom=Decimal("100"),
        emergency_credit_headroom=Decimal("50"),
        enterprise_headroom=None,
    )
    assert budget_soft.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert budget_soft.reason_code == "budget_exceeded"
    assert budget_soft.reserve_allocation_usd == Decimal("100.0000")
    assert budget_soft.reserve_reserved_credit_usd == Decimal("100.0000")
    assert budget_soft.reserve_emergency_credit_usd == Decimal("50.0000")

    enterprise_soft = service._evaluate_entitlement_waterfall(
        mode=EnforcementMode.SOFT,
        monthly_delta=Decimal("250"),
        plan_headroom=None,
        allocation_headroom=Decimal("200"),
        reserved_credit_headroom=Decimal("100"),
        emergency_credit_headroom=Decimal("0"),
        enterprise_headroom=Decimal("200"),
    )
    assert enterprise_soft.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert enterprise_soft.reason_code == "enterprise_ceiling_exceeded"

    allow_with_credits = service._evaluate_entitlement_waterfall(
        mode=EnforcementMode.HARD,
        monthly_delta=Decimal("150"),
        plan_headroom=None,
        allocation_headroom=Decimal("100"),
        reserved_credit_headroom=Decimal("50"),
        emergency_credit_headroom=Decimal("0"),
        enterprise_headroom=None,
    )
    assert allow_with_credits.decision == EnforcementDecisionType.ALLOW_WITH_CREDITS
    assert allow_with_credits.reason_code is None

    allow = service._evaluate_entitlement_waterfall(
        mode=EnforcementMode.HARD,
        monthly_delta=Decimal("80"),
        plan_headroom=None,
        allocation_headroom=Decimal("100"),
        reserved_credit_headroom=Decimal("0"),
        emergency_credit_headroom=Decimal("0"),
        enterprise_headroom=None,
    )
    assert allow.decision == EnforcementDecisionType.ALLOW
    assert allow.reason_code is None

    reasons: list[str] = []
    decision, reserved_alloc, reserved_credit = service._evaluate_budget_waterfall(
        mode=EnforcementMode.SOFT,
        monthly_delta=Decimal("220"),
        allocation_headroom=Decimal("100"),
        credits_headroom=Decimal("100"),
        reasons=reasons,
    )
    assert decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert reserved_alloc == Decimal("100.0000")
    assert reserved_credit == Decimal("100.0000")
    assert "budget_exceeded" in reasons
    assert "soft_mode_budget_escalation" in reasons
    assert "credit_waterfall_used" in reasons



def test_mode_violation_helpers_and_gate_result_response() -> None:
    service = _service()

    assert service._mode_violation_decision(EnforcementMode.SHADOW) == EnforcementDecisionType.ALLOW
    assert service._mode_violation_decision(EnforcementMode.SOFT) == EnforcementDecisionType.REQUIRE_APPROVAL
    assert service._mode_violation_decision(EnforcementMode.HARD) == EnforcementDecisionType.DENY

    assert service._mode_violation_reason_suffix(EnforcementMode.SHADOW, subject="budget") == "shadow_mode_budget_override"
    assert service._mode_violation_reason_suffix(EnforcementMode.SOFT, subject="budget") == "soft_mode_budget_escalation"
    assert service._mode_violation_reason_suffix(EnforcementMode.HARD, subject="budget") == "hard_mode_budget_closed"

    decision = SimpleNamespace(
        decision=EnforcementDecisionType.REQUIRE_APPROVAL,
        reason_codes=["budget_exceeded"],
        id=uuid4(),
        policy_version=7,
        approval_required=True,
        request_fingerprint="fingerprint-123",
        reservation_active=True,
        response_payload={"computed_context": {"risk_class": "high"}},
    )
    approval = SimpleNamespace(id=uuid4())
    result = GateEvaluationResult(
        decision=decision,
        approval=approval,
        approval_token="signed-token",
        ttl_seconds=600,
    )

    payload = gate_result_to_response(result)
    assert payload["decision"] == EnforcementDecisionType.REQUIRE_APPROVAL.value
    assert payload["approval_request_id"] == approval.id
    assert payload["approval_token"] == "signed-token"
    assert payload["computed_context"] == {"risk_class": "high"}

    decision.response_payload = {"computed_context": "invalid"}
    payload_no_context = gate_result_to_response(result)
    assert payload_no_context["computed_context"] is None



@pytest.mark.asyncio
async def test_acquire_gate_evaluation_lock_emits_contention_metrics(monkeypatch) -> None:
    class _Db:
        async def execute(self, _stmt):
            return SimpleNamespace(rowcount=1)

        async def rollback(self) -> None:
            raise AssertionError("rollback should not be called on successful lock acquisition")

    service = EnforcementService(db=_Db())
    policy = EnforcementPolicy(tenant_id=uuid4())
    policy.id = uuid4()
    lock_events = _FakeCounter()
    lock_wait = _FakeHistogram()
    perf_values = iter([100.0, 100.2])

    monkeypatch.setattr(
        enforcement_service_module,
        "ENFORCEMENT_GATE_LOCK_EVENTS_TOTAL",
        lock_events,
    )
    monkeypatch.setattr(
        enforcement_service_module,
        "ENFORCEMENT_GATE_LOCK_WAIT_SECONDS",
        lock_wait,
    )
    monkeypatch.setattr(
        enforcement_service_module,
        "_gate_lock_timeout_seconds",
        lambda: 1.0,
    )
    monkeypatch.setattr(
        enforcement_service_module.time,
        "perf_counter",
        lambda: next(perf_values),
    )

    await service._acquire_gate_evaluation_lock(
        policy=policy,
        source=EnforcementSource.TERRAFORM,
    )

    assert any(
        call[0]["event"] == "acquired" and call[0]["source"] == "terraform"
        for call in lock_events.calls
    )
    assert any(
        call[0]["event"] == "contended" and call[0]["source"] == "terraform"
        for call in lock_events.calls
    )
    assert len(lock_wait.calls) == 1
    assert lock_wait.calls[0][0]["source"] == "terraform"
    assert lock_wait.calls[0][0]["outcome"] == "acquired"
    assert lock_wait.calls[0][1] >= 0.19



@pytest.mark.asyncio
async def test_acquire_gate_evaluation_lock_rowcount_zero_raises_contended_reason(
    monkeypatch,
) -> None:
    class _Db:
        async def execute(self, _stmt):
            return SimpleNamespace(rowcount=0)

        async def rollback(self) -> None:
            raise AssertionError("rollback should not run for rowcount=0 path")

    service = EnforcementService(db=_Db())
    policy = EnforcementPolicy(tenant_id=uuid4())
    policy.id = uuid4()
    lock_events = _FakeCounter()
    lock_wait = _FakeHistogram()
    perf_values = iter([200.0, 200.01])

    monkeypatch.setattr(
        enforcement_service_module,
        "ENFORCEMENT_GATE_LOCK_EVENTS_TOTAL",
        lock_events,
    )
    monkeypatch.setattr(
        enforcement_service_module,
        "ENFORCEMENT_GATE_LOCK_WAIT_SECONDS",
        lock_wait,
    )
    monkeypatch.setattr(
        enforcement_service_module.time,
        "perf_counter",
        lambda: next(perf_values),
    )

    with pytest.raises(HTTPException) as exc:
        await service._acquire_gate_evaluation_lock(
            policy=policy,
            source=EnforcementSource.TERRAFORM,
        )

    assert exc.value.status_code == 409
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "gate_lock_contended"
    assert detail["lock_wait_seconds"] == "0.010"
    assert any(
        call[0]["event"] == "acquired" and call[0]["source"] == "terraform"
        for call in lock_events.calls
    )
    assert any(
        call[0]["event"] == "not_acquired" and call[0]["source"] == "terraform"
        for call in lock_events.calls
    )
    assert len(lock_wait.calls) == 1
    assert lock_wait.calls[0][0]["outcome"] == "acquired"
