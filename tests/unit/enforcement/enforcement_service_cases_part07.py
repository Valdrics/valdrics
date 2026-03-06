# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_reconcile_overdue_reservations_releases_only_stale(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    stale_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-overdue-stale-1",
    )
    fresh_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-overdue-fresh-1",
    )

    stale_decision = (
        await db.execute(
            select(EnforcementDecision).where(
                EnforcementDecision.id == stale_gate.decision.id
            )
        )
    ).scalar_one()
    stale_decision.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    await db.commit()

    service = EnforcementService(db)
    summary = await service.reconcile_overdue_reservations(
        tenant_id=tenant.id,
        actor_id=actor_id,
        older_than_seconds=3600,
        limit=200,
    )

    assert summary.released_count == 1
    assert stale_gate.decision.id in summary.decision_ids
    assert fresh_gate.decision.id not in summary.decision_ids
    assert summary.total_released_usd == Decimal("75.0000")
    stale_ledger_rows = (
        await db.execute(
            select(EnforcementDecisionLedger)
            .where(EnforcementDecisionLedger.decision_id == stale_gate.decision.id)
            .order_by(
                EnforcementDecisionLedger.recorded_at.asc(),
                EnforcementDecisionLedger.id.asc(),
            )
        )
    ).scalars().all()
    assert len(stale_ledger_rows) == 2
    assert stale_ledger_rows[-1].approval_request_id == stale_gate.approval.id
    assert stale_ledger_rows[-1].approval_status == EnforcementApprovalStatus.PENDING
    assert "reservation_auto_released_sla" in (stale_ledger_rows[-1].reason_codes or [])



@pytest.mark.asyncio
async def test_reconcile_overdue_reservations_records_processed_count_metric(
    db,
    monkeypatch,
) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    stale_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-overdue-metric-stale-1",
    )
    _fresh_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-overdue-metric-fresh-1",
    )
    stale_decision = (
        await db.execute(
            select(EnforcementDecision)
            .where(EnforcementDecision.id == stale_gate.decision.id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    stale_decision.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    await db.commit()

    reconciliations = _FakeCounter()
    monkeypatch.setattr(
        enforcement_service_module,
        "ENFORCEMENT_RESERVATION_RECONCILIATIONS_TOTAL",
        reconciliations,
    )
    service = EnforcementService(db)
    summary = await service.reconcile_overdue_reservations(
        tenant_id=tenant.id,
        actor_id=actor_id,
        older_than_seconds=3600,
        limit=200,
    )
    assert summary.released_count == 1
    assert ({"trigger": "auto", "status": "auto_release"}, 1.0) in reconciliations.calls



@pytest.mark.asyncio
async def test_reconcile_reservation_rolls_back_on_credit_settlement_failure(db) -> None:
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
    await service.create_credit_grant(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        total_amount_usd=Decimal("100"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="rollback test",
    )
    gate = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.rollback-reconcile",
            estimated_monthly_delta_usd=Decimal("30"),
            estimated_hourly_delta_usd=Decimal("0.11"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="rollback-reconcile-seed-1",
        ),
    )
    assert gate.approval is not None
    decision_id = gate.decision.id
    await db.execute(
        delete(EnforcementCreditReservationAllocation).where(
            EnforcementCreditReservationAllocation.decision_id == decision_id
        )
    )
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await service.reconcile_reservation(
            tenant_id=tenant.id,
            decision_id=decision_id,
            actor_id=actor_id,
            actual_monthly_delta_usd=Decimal("15"),
            notes="should rollback",
            idempotency_key="rollback-reconcile-key-1",
        )
    assert exc.value.status_code == 409
    assert "missing credit reservation allocation" in str(exc.value.detail).lower()

    decision = (
        await db.execute(
            select(EnforcementDecision)
            .where(EnforcementDecision.id == decision_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert decision.reservation_active is True
    assert decision.reserved_allocation_usd == Decimal("10.0000")
    assert decision.reserved_credit_usd == Decimal("20.0000")
    response_payload = decision.response_payload or {}
    assert "reservation_reconciliation" not in response_payload



@pytest.mark.asyncio
async def test_reconcile_overdue_rolls_back_on_credit_settlement_failure(db) -> None:
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
    await service.create_credit_grant(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        total_amount_usd=Decimal("100"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="rollback overdue test",
    )
    gate = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.rollback-overdue",
            estimated_monthly_delta_usd=Decimal("30"),
            estimated_hourly_delta_usd=Decimal("0.11"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="rollback-overdue-seed-1",
        ),
    )
    assert gate.approval is not None
    decision_id = gate.decision.id
    stale_decision = (
        await db.execute(
            select(EnforcementDecision)
            .where(EnforcementDecision.id == decision_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    stale_decision.created_at = datetime.now(timezone.utc) - timedelta(hours=2)
    await db.execute(
        delete(EnforcementCreditReservationAllocation).where(
            EnforcementCreditReservationAllocation.decision_id == decision_id
        )
    )
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await service.reconcile_overdue_reservations(
            tenant_id=tenant.id,
            actor_id=actor_id,
            older_than_seconds=3600,
            limit=50,
        )
    assert exc.value.status_code == 409
    assert "missing credit reservation allocation" in str(exc.value.detail).lower()

    refreshed = (
        await db.execute(
            select(EnforcementDecision)
            .where(EnforcementDecision.id == decision_id)
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert refreshed.reservation_active is True
    assert refreshed.reserved_allocation_usd == Decimal("10.0000")
    assert refreshed.reserved_credit_usd == Decimal("20.0000")
    response_payload = refreshed.response_payload or {}
    assert "auto_reconciliation" not in response_payload



@pytest.mark.asyncio
async def test_list_reconciliation_exceptions_returns_only_drift(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    drift_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-exception-drift-1",
    )
    matched_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="reconcile-exception-matched-1",
    )

    service = EnforcementService(db)
    await service.reconcile_reservation(
        tenant_id=tenant.id,
        decision_id=drift_gate.decision.id,
        actor_id=actor_id,
        actual_monthly_delta_usd=Decimal("80"),
        notes="drift case",
    )
    await service.reconcile_reservation(
        tenant_id=tenant.id,
        decision_id=matched_gate.decision.id,
        actor_id=actor_id,
        actual_monthly_delta_usd=Decimal("75"),
        notes="matched case",
    )

    exceptions = await service.list_reconciliation_exceptions(
        tenant_id=tenant.id,
        limit=50,
    )

    assert len(exceptions) == 1
    assert exceptions[0].decision.id == drift_gate.decision.id
    assert exceptions[0].status == "overage"
    assert exceptions[0].drift_usd == Decimal("5.0000")



@pytest.mark.asyncio
async def test_reconciliation_exceptions_include_credit_settlement_diagnostics(db) -> None:
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
    await service.create_credit_grant(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        total_amount_usd=Decimal("100"),
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        reason="exceptions diagnostics",
    )
    gate = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.exceptions-credit",
            estimated_monthly_delta_usd=Decimal("30"),
            estimated_hourly_delta_usd=Decimal("0.11"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="exceptions-credit-1",
        ),
    )
    assert gate.approval is not None

    await service.reconcile_reservation(
        tenant_id=tenant.id,
        decision_id=gate.decision.id,
        actor_id=actor_id,
        actual_monthly_delta_usd=Decimal("15"),
        notes="credit diagnostics case",
    )

    exceptions = await service.list_reconciliation_exceptions(
        tenant_id=tenant.id,
        limit=20,
    )
    assert len(exceptions) == 1
    entry = exceptions[0]
    assert entry.decision.id == gate.decision.id
    assert entry.credit_settlement
    settlement = entry.credit_settlement[0]
    assert settlement["consumed_amount_usd"] == "5.0000"
    assert settlement["released_amount_usd"] == "15.0000"
