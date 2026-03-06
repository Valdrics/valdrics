# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_credit_waterfall_uses_emergency_only_and_preserves_caller_risk_level(
    db,
) -> None:
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
    await service.create_credit_grant(
        tenant_id=tenant.id,
        actor_id=actor_id,
        pool_type=EnforcementCreditPoolType.EMERGENCY,
        scope_key="default",
        total_amount_usd=Decimal("10"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="emergency only pool",
    )

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.K8S_ADMISSION,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="admission.validate",
            resource_reference="deployments/apps/emergency-only-credit",
            estimated_monthly_delta_usd=Decimal("3"),
            estimated_hourly_delta_usd=Decimal("0.01"),
            metadata={"namespace": "apps", "risk_level": "manual"},
            idempotency_key="credit-emergency-only-risk-preserve-1",
        ),
    )

    reasons = result.decision.reason_codes or []
    assert result.decision.decision == EnforcementDecisionType.ALLOW_WITH_CREDITS
    assert "credit_waterfall_used" in reasons
    assert "emergency_credit_waterfall_used" in reasons
    assert "reserved_credit_waterfall_used" not in reasons
    assert result.decision.reserved_credit_usd == Decimal("3.0000")

    request_payload = result.decision.request_payload or {}
    metadata_payload = request_payload.get("metadata") or {}
    assert metadata_payload.get("risk_level") == "manual"
    assert metadata_payload.get("computed_risk_class") == result.decision.risk_class
    assert metadata_payload.get("computed_risk_score") == result.decision.risk_score


@pytest.mark.asyncio
async def test_credit_reservation_debits_grants_and_persists_allocation_mapping(db) -> None:
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
    credit = await service.create_credit_grant(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        total_amount_usd=Decimal("100"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="debit check",
    )

    result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.K8S_ADMISSION,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="admission.validate",
            resource_reference="deployments/apps/credit-check",
            estimated_monthly_delta_usd=Decimal("30"),
            estimated_hourly_delta_usd=Decimal("0.04"),
            metadata={"namespace": "apps"},
            idempotency_key="credit-debit-map-1",
        ),
    )
    assert result.decision.decision == EnforcementDecisionType.ALLOW_WITH_CREDITS
    assert result.decision.reserved_credit_usd == Decimal("20.0000")

    refreshed_credit = (
        await db.execute(
            select(EnforcementCreditGrant).where(EnforcementCreditGrant.id == credit.id)
        )
    ).scalar_one()
    assert refreshed_credit.remaining_amount_usd == Decimal("80.0000")

    allocations = (
        await db.execute(
            select(EnforcementCreditReservationAllocation).where(
                EnforcementCreditReservationAllocation.decision_id
                == result.decision.id
            )
        )
    ).scalars().all()
    assert len(allocations) == 1
    allocation = allocations[0]
    assert allocation.credit_grant_id == credit.id
    assert allocation.reserved_amount_usd == Decimal("20.0000")
    assert allocation.active is True



@pytest.mark.asyncio
async def test_approve_request_issues_token_and_marks_decision(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("500"),
        active=True,
    )

    gate_result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="prod",
            action="terraform.apply",
            resource_reference="module.rds.aws_db_instance.main",
            estimated_monthly_delta_usd=Decimal("120"),
            estimated_hourly_delta_usd=Decimal("0.16"),
            metadata={"resource_type": "aws_db_instance"},
            idempotency_key="approve-token-1",
        ),
    )
    assert gate_result.approval is not None

    reviewer = CurrentUser(
        id=uuid4(),
        email="owner@example.com",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )

    approval, decision, token, expires_at = await service.approve_request(
        tenant_id=tenant.id,
        approval_id=gate_result.approval.id,
        reviewer=reviewer,
        notes="approved for launch",
    )

    assert approval.status == EnforcementApprovalStatus.APPROVED
    assert isinstance(token, str) and token
    assert decision.approval_token_issued is True
    assert decision.token_expires_at is not None
    decision_expiry = decision.token_expires_at
    if decision_expiry.tzinfo is None:
        decision_expiry = decision_expiry.replace(tzinfo=timezone.utc)
    assert decision_expiry == expires_at



@pytest.mark.asyncio
async def test_deny_request_releases_existing_reservation(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        require_approval_for_prod=True,
        require_approval_for_nonprod=True,
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("1000"),
        default_ttl_seconds=900,
    )
    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("1000"),
        active=True,
    )

    gate_result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.ec2.aws_instance.worker",
            estimated_monthly_delta_usd=Decimal("75"),
            estimated_hourly_delta_usd=Decimal("0.1"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="deny-release-1",
        ),
    )
    assert gate_result.approval is not None
    assert gate_result.decision.reservation_active is True
    assert gate_result.decision.reserved_allocation_usd == Decimal("75.0000")

    reviewer = CurrentUser(
        id=uuid4(),
        email="owner@example.com",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    approval, decision = await service.deny_request(
        tenant_id=tenant.id,
        approval_id=gate_result.approval.id,
        reviewer=reviewer,
        notes="denied by policy review",
    )

    assert approval.status == EnforcementApprovalStatus.DENIED
    assert decision.reservation_active is False
    assert decision.reserved_allocation_usd == Decimal("0")
    assert decision.reserved_credit_usd == Decimal("0")



@pytest.mark.asyncio
async def test_deny_request_refunds_reserved_credit_grants(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("2500"),
        default_ttl_seconds=900,
    )
    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("10"),
        active=True,
    )
    credit = await service.create_credit_grant(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        total_amount_usd=Decimal("100"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="deny refund",
    )
    gate_result = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.credit-deny",
            estimated_monthly_delta_usd=Decimal("30"),
            estimated_hourly_delta_usd=Decimal("0.11"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="deny-credit-refund-1",
        ),
    )
    assert gate_result.approval is not None
    assert gate_result.decision.reserved_credit_usd == Decimal("20.0000")

    reviewer = CurrentUser(
        id=uuid4(),
        email="owner@example.com",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    approval, decision = await service.deny_request(
        tenant_id=tenant.id,
        approval_id=gate_result.approval.id,
        reviewer=reviewer,
        notes="blocked",
    )
    assert approval.status == EnforcementApprovalStatus.DENIED
    assert decision.reservation_active is False
    assert decision.reserved_credit_usd == Decimal("0")

    refreshed_credit = (
        await db.execute(
            select(EnforcementCreditGrant).where(EnforcementCreditGrant.id == credit.id)
        )
    ).scalar_one()
    assert refreshed_credit.remaining_amount_usd == Decimal("100.0000")
    assert refreshed_credit.active is True

    allocation_rows = (
        await db.execute(
            select(EnforcementCreditReservationAllocation).where(
                EnforcementCreditReservationAllocation.decision_id == decision.id
            )
        )
    ).scalars().all()
    assert len(allocation_rows) == 1
    allocation = allocation_rows[0]
    assert allocation.active is False
    assert allocation.consumed_amount_usd == Decimal("0.0000")
    assert allocation.released_amount_usd == Decimal("20.0000")



@pytest.mark.asyncio
async def test_create_credit_grant_rejects_past_expiry(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)

    with pytest.raises(HTTPException) as exc:
        await service.create_credit_grant(
            tenant_id=tenant.id,
            actor_id=uuid4(),
            scope_key="default",
            total_amount_usd=Decimal("10"),
            expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            reason="expired fixture",
        )
    assert exc.value.status_code == 422



@pytest.mark.asyncio
async def test_consume_approval_token_rejects_replay(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    token, approval, decision = await _issue_approved_token(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        idempotency_key="consume-replay-1",
    )

    service = EnforcementService(db)
    consumed_approval, consumed_decision = await service.consume_approval_token(
        tenant_id=tenant.id,
        approval_token=token,
        actor_id=actor_id,
        expected_source=EnforcementSource.TERRAFORM,
        expected_environment="prod",
        expected_request_fingerprint=decision.request_fingerprint,
        expected_resource_reference=decision.resource_reference,
    )
    assert consumed_approval.id == approval.id
    assert consumed_decision.id == decision.id
    assert consumed_approval.approval_token_consumed_at is not None

    with pytest.raises(HTTPException) as replay_exc:
        await service.consume_approval_token(
            tenant_id=tenant.id,
            approval_token=token,
            actor_id=actor_id,
        )
    assert replay_exc.value.status_code == 409
    assert "replay" in str(replay_exc.value.detail).lower()



@pytest.mark.asyncio
async def test_consume_approval_token_replay_records_metrics(db, monkeypatch) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    token, _, _ = await _issue_approved_token(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        idempotency_key="consume-replay-metrics-1",
    )
    token_events = _FakeCounter()
    monkeypatch.setattr(
        enforcement_service_module,
        "ENFORCEMENT_APPROVAL_TOKEN_EVENTS_TOTAL",
        token_events,
    )

    service = EnforcementService(db)
    await service.consume_approval_token(
        tenant_id=tenant.id,
        approval_token=token,
        actor_id=actor_id,
    )
    with pytest.raises(HTTPException):
        await service.consume_approval_token(
            tenant_id=tenant.id,
            approval_token=token,
            actor_id=actor_id,
        )

    event_calls = [labels.get("event") for labels, _ in token_events.calls]
    assert "consumed" in event_calls
    assert "replay_detected" in event_calls



@pytest.mark.asyncio
async def test_consume_approval_token_accepts_rotated_fallback_secret(
    db, monkeypatch
) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    old_secret = "old-approval-signing-secret-12345678901234567890"
    new_secret = "new-approval-signing-secret-12345678901234567890"

    def _settings(
        secret: str,
        fallback: list[str] | None = None,
    ) -> SimpleNamespace:
        return SimpleNamespace(
            SUPABASE_JWT_SECRET=secret,
            API_URL="https://api.valdrics.local",
            JWT_SIGNING_KID="",
            ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS=list(fallback or []),
        )

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: _settings(old_secret),
    )
    token, approval, _ = await _issue_approved_token(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        idempotency_key="consume-rotation-fallback-1",
    )

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: _settings(new_secret, [old_secret]),
    )
    service = EnforcementService(db)
    consumed_approval, _ = await service.consume_approval_token(
        tenant_id=tenant.id,
        approval_token=token,
        actor_id=actor_id,
    )
    assert consumed_approval.id == approval.id
    assert consumed_approval.approval_token_consumed_at is not None
