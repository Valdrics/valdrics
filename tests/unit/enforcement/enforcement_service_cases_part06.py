# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_approve_request_member_allowed_with_scim_nonprod_permission(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="member-allowed-scim-nonprod-1",
        approval_routing_rules=[
            {
                "rule_id": "allow-member-nonprod-approver",
                "enabled": True,
                "environments": ["nonprod"],
                "allowed_reviewer_roles": ["owner", "admin", "member"],
                "required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_NONPROD,
                "require_requester_reviewer_separation": False,
            }
        ],
    )
    member_id = uuid4()
    await _seed_member_scim_permission(
        db=db,
        tenant_id=tenant.id,
        member_id=member_id,
        permissions=[APPROVAL_PERMISSION_REMEDIATION_APPROVE_NONPROD],
        scim_enabled=True,
    )
    service = EnforcementService(db)
    reviewer = CurrentUser(
        id=member_id,
        email="member@example.com",
        tenant_id=tenant.id,
        role=UserRole.MEMBER,
    )

    approval, _, _, _ = await service.approve_request(
        tenant_id=tenant.id,
        approval_id=gate.approval.id,
        reviewer=reviewer,
        notes="approved via scim nonprod permission",
    )
    assert approval.status == EnforcementApprovalStatus.APPROVED



@pytest.mark.asyncio
async def test_approve_request_member_denied_when_scim_disabled_even_with_mapping(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="prod",
        require_approval_for_prod=True,
        require_approval_for_nonprod=False,
        idempotency_key="member-denied-scim-disabled-1",
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
        scim_enabled=False,
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
            notes="attempt while scim disabled",
        )
    assert exc.value.status_code == 403
    assert APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD in str(exc.value.detail)



@pytest.mark.asyncio
async def test_deny_request_enforces_reviewer_authority(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="deny-request-permission-guard-1",
    )
    service = EnforcementService(db)
    reviewer = CurrentUser(
        id=uuid4(),
        email="member@example.com",
        tenant_id=tenant.id,
        role=UserRole.MEMBER,
    )

    with pytest.raises(HTTPException) as exc:
        await service.deny_request(
            tenant_id=tenant.id,
            approval_id=gate.approval.id,
            reviewer=reviewer,
            notes="member without approval authority",
        )
    assert exc.value.status_code == 403



@pytest.mark.asyncio
async def test_reconcile_reservation_releases_and_records_drift(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-reservation-1",
    )
    service = EnforcementService(db)

    result = await service.reconcile_reservation(
        tenant_id=tenant.id,
        decision_id=gate.decision.id,
        actor_id=actor_id,
        actual_monthly_delta_usd=Decimal("80"),
        notes="monthly close reconciliation",
    )

    assert result.decision.id == gate.decision.id
    assert result.decision.reservation_active is False
    assert result.decision.reserved_allocation_usd == Decimal("0")
    assert result.decision.reserved_credit_usd == Decimal("0")
    assert result.released_reserved_usd == Decimal("75.0000")
    assert result.actual_monthly_delta_usd == Decimal("80.0000")
    assert result.drift_usd == Decimal("5.0000")
    assert result.status == "overage"
    assert "reservation_reconciled" in (result.decision.reason_codes or [])
    assert "reservation_reconciliation_drift" in (result.decision.reason_codes or [])
    ledger_rows = (
        await db.execute(
            select(EnforcementDecisionLedger)
            .where(EnforcementDecisionLedger.decision_id == gate.decision.id)
            .order_by(
                EnforcementDecisionLedger.recorded_at.asc(),
                EnforcementDecisionLedger.id.asc(),
            )
        )
    ).scalars().all()
    assert len(ledger_rows) == 2
    assert ledger_rows[-1].approval_request_id == gate.approval.id
    assert ledger_rows[-1].approval_status == EnforcementApprovalStatus.PENDING
    assert "reservation_reconciled" in (ledger_rows[-1].reason_codes or [])



@pytest.mark.asyncio
async def test_reconcile_reservation_idempotent_replay_with_same_key(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-reservation-idem-seed-1",
    )
    service = EnforcementService(db)

    first = await service.reconcile_reservation(
        tenant_id=tenant.id,
        decision_id=gate.decision.id,
        actor_id=actor_id,
        actual_monthly_delta_usd=Decimal("80"),
        notes="idempotent replay",
        idempotency_key="reconcile-idem-1",
    )
    second = await service.reconcile_reservation(
        tenant_id=tenant.id,
        decision_id=gate.decision.id,
        actor_id=actor_id,
        actual_monthly_delta_usd=Decimal("80"),
        notes="idempotent replay",
        idempotency_key="reconcile-idem-1",
    )

    assert second.decision.id == first.decision.id
    assert second.status == first.status
    assert second.drift_usd == first.drift_usd
    assert second.released_reserved_usd == first.released_reserved_usd
    assert second.reconciled_at == first.reconciled_at
    reconciliation_payload = (second.decision.response_payload or {}).get(
        "reservation_reconciliation",
        {},
    )
    assert reconciliation_payload.get("idempotency_key") == "reconcile-idem-1"
    ledger_rows = (
        await db.execute(
            select(EnforcementDecisionLedger)
            .where(EnforcementDecisionLedger.decision_id == gate.decision.id)
            .order_by(
                EnforcementDecisionLedger.recorded_at.asc(),
                EnforcementDecisionLedger.id.asc(),
            )
        )
    ).scalars().all()
    # Initial gate ledger row + one reconciliation row. Replay must not append.
    assert len(ledger_rows) == 2



@pytest.mark.asyncio
async def test_reconcile_reservation_idempotent_replay_rejects_payload_mismatch(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-reservation-idem-seed-2",
    )
    service = EnforcementService(db)

    await service.reconcile_reservation(
        tenant_id=tenant.id,
        decision_id=gate.decision.id,
        actor_id=actor_id,
        actual_monthly_delta_usd=Decimal("80"),
        notes="idempotent replay mismatch",
        idempotency_key="reconcile-idem-2",
    )

    with pytest.raises(HTTPException) as exc:
        await service.reconcile_reservation(
            tenant_id=tenant.id,
            decision_id=gate.decision.id,
            actor_id=actor_id,
            actual_monthly_delta_usd=Decimal("81"),
            notes="idempotent replay mismatch",
            idempotency_key="reconcile-idem-2",
        )
    assert exc.value.status_code == 409
    assert "payload mismatch" in str(exc.value.detail).lower()



@pytest.mark.asyncio
async def test_reconcile_reservation_partially_consumes_reserved_credit(db) -> None:
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
        reason="reconcile partial consume",
    )
    gate = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.credit-reconcile",
            estimated_monthly_delta_usd=Decimal("30"),
            estimated_hourly_delta_usd=Decimal("0.11"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="reconcile-credit-partial-1",
        ),
    )
    assert gate.approval is not None
    assert gate.decision.reserved_allocation_usd == Decimal("10.0000")
    assert gate.decision.reserved_credit_usd == Decimal("20.0000")

    result = await service.reconcile_reservation(
        tenant_id=tenant.id,
        decision_id=gate.decision.id,
        actor_id=actor_id,
        actual_monthly_delta_usd=Decimal("15"),
        notes="partial credit usage",
    )
    assert result.decision.reservation_active is False
    assert result.status == "savings"
    assert result.drift_usd == Decimal("-15.0000")

    refreshed_credit = (
        await db.execute(
            select(EnforcementCreditGrant).where(EnforcementCreditGrant.id == credit.id)
        )
    ).scalar_one()
    # Reserved 20 at gate-time, then reconcile consumes 5 and releases 15.
    assert refreshed_credit.remaining_amount_usd == Decimal("95.0000")

    allocation = (
        await db.execute(
            select(EnforcementCreditReservationAllocation).where(
                EnforcementCreditReservationAllocation.decision_id == gate.decision.id
            )
        )
    ).scalar_one()
    assert allocation.active is False
    assert allocation.consumed_amount_usd == Decimal("5.0000")
    assert allocation.released_amount_usd == Decimal("15.0000")

    reconciliation_payload = (result.decision.response_payload or {}).get(
        "reservation_reconciliation",
        {},
    )
    assert reconciliation_payload.get("credit_consumed_usd") == "5.0000"
    assert reconciliation_payload.get("credit_released_usd") == "15.0000"
    credit_settlement = reconciliation_payload.get("credit_settlement")
    assert isinstance(credit_settlement, list)
    assert len(credit_settlement) == 1



@pytest.mark.asyncio
async def test_reconcile_reservation_records_metrics(db, monkeypatch) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-reservation-metrics-1",
    )
    reconciliations = _FakeCounter()
    drift = _FakeCounter()
    monkeypatch.setattr(
        enforcement_service_module,
        "ENFORCEMENT_RESERVATION_RECONCILIATIONS_TOTAL",
        reconciliations,
    )
    monkeypatch.setattr(
        enforcement_service_module,
        "ENFORCEMENT_RESERVATION_DRIFT_USD_TOTAL",
        drift,
    )

    service = EnforcementService(db)
    await service.reconcile_reservation(
        tenant_id=tenant.id,
        decision_id=gate.decision.id,
        actor_id=actor_id,
        actual_monthly_delta_usd=Decimal("80"),
        notes="metrics check",
    )

    assert ({"trigger": "manual", "status": "overage"}, 1.0) in reconciliations.calls
    assert ({"direction": "overage"}, 5.0) in drift.calls



@pytest.mark.asyncio
async def test_reconcile_reservation_rejects_when_not_active(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-reservation-inactive-1",
    )
    service = EnforcementService(db)
    reviewer = CurrentUser(
        id=uuid4(),
        email="owner@example.com",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    await service.deny_request(
        tenant_id=tenant.id,
        approval_id=gate.approval.id,
        reviewer=reviewer,
        notes="force inactive before reconcile",
    )

    with pytest.raises(HTTPException) as exc:
        await service.reconcile_reservation(
            tenant_id=tenant.id,
            decision_id=gate.decision.id,
            actor_id=actor_id,
            actual_monthly_delta_usd=Decimal("0"),
            notes="should fail",
        )
    assert exc.value.status_code == 409
    assert "not active" in str(exc.value.detail).lower()
