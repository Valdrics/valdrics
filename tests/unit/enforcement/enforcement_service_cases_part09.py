# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_evaluate_gate_appends_immutable_decision_ledger_entry(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("250"),
        active=True,
    )

    payload = GateInput(
        project_id="default",
        environment="nonprod",
        action="terraform.apply",
        resource_reference="module.vpc.aws_vpc.main",
        estimated_monthly_delta_usd=Decimal("50"),
        estimated_hourly_delta_usd=Decimal("0.07"),
        metadata={"resource_type": "aws_vpc"},
        idempotency_key="ledger-idempotency-1",
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

    rows = await db.execute(
        select(EnforcementDecisionLedger)
        .where(EnforcementDecisionLedger.tenant_id == tenant.id)
        .order_by(EnforcementDecisionLedger.recorded_at.asc())
    )
    ledger_entries = list(rows.scalars().all())
    assert len(ledger_entries) == 1
    entry = ledger_entries[0]
    assert entry.decision_id == first.decision.id
    assert entry.decision == first.decision.decision
    assert entry.request_fingerprint == first.decision.request_fingerprint
    assert entry.burn_rate_daily_usd is not None
    assert entry.forecast_eom_usd is not None
    assert entry.risk_class in {"low", "medium", "high"}
    assert entry.anomaly_signal in {True, False}
    assert len(entry.request_payload_sha256) == 64
    assert len(entry.response_payload_sha256) == 64
    entry_id = entry.id

    entry.reason_codes = ["tamper_attempt"]
    with pytest.raises(Exception) as update_exc:
        await db.commit()
    assert "append-only" in str(update_exc.value).lower()
    await db.rollback()

    persisted = (
        await db.execute(
            select(EnforcementDecisionLedger).where(
                EnforcementDecisionLedger.id == entry_id
            )
        )
    ).scalar_one()
    assert "tamper_attempt" not in (persisted.reason_codes or [])

    await db.delete(persisted)
    with pytest.raises(Exception) as delete_exc:
        await db.commit()
    assert "append-only" in str(delete_exc.value).lower()
    await db.rollback()



@pytest.mark.asyncio
async def test_ledger_captures_approval_linkage_and_status_transitions(db) -> None:
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
        hard_deny_above_monthly_usd=Decimal("2500"),
        default_ttl_seconds=900,
    )
    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("1000"),
        active=True,
    )

    gate = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.web",
            estimated_monthly_delta_usd=Decimal("80"),
            estimated_hourly_delta_usd=Decimal("0.10"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="ledger-approval-linkage-1",
        ),
    )
    assert gate.approval is not None
    assert gate.decision.decision == EnforcementDecisionType.REQUIRE_APPROVAL

    pending_rows = (
        await db.execute(
            select(EnforcementDecisionLedger)
            .where(EnforcementDecisionLedger.decision_id == gate.decision.id)
            .order_by(
                EnforcementDecisionLedger.recorded_at.asc(),
                EnforcementDecisionLedger.id.asc(),
            )
        )
    ).scalars().all()
    assert len(pending_rows) == 1
    assert pending_rows[0].approval_request_id == gate.approval.id
    assert pending_rows[0].approval_status == EnforcementApprovalStatus.PENDING

    reviewer = CurrentUser(
        id=uuid4(),
        email="owner@example.com",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    approval, _, _, _ = await service.approve_request(
        tenant_id=tenant.id,
        approval_id=gate.approval.id,
        reviewer=reviewer,
        notes="approve for ledger linkage",
    )
    assert approval.status == EnforcementApprovalStatus.APPROVED

    rows_after_approve = (
        await db.execute(
            select(EnforcementDecisionLedger)
            .where(EnforcementDecisionLedger.decision_id == gate.decision.id)
            .order_by(
                EnforcementDecisionLedger.recorded_at.asc(),
                EnforcementDecisionLedger.id.asc(),
            )
        )
    ).scalars().all()
    assert len(rows_after_approve) == 2
    assert rows_after_approve[-1].approval_request_id == gate.approval.id
    assert rows_after_approve[-1].approval_status == EnforcementApprovalStatus.APPROVED



@pytest.mark.asyncio
async def test_create_approval_request_appends_ledger_linkage_for_existing_decision(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        require_approval_for_prod=True,
        require_approval_for_nonprod=False,
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("2500"),
        default_ttl_seconds=900,
    )
    await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("1000"),
        active=True,
    )

    gate = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="prod",
            action="terraform.apply",
            resource_reference="module.db.aws_db_instance.main",
            estimated_monthly_delta_usd=Decimal("100"),
            estimated_hourly_delta_usd=Decimal("0.14"),
            metadata={"resource_type": "aws_db_instance"},
            idempotency_key="ledger-create-approval-linkage-1",
            dry_run=True,
        ),
    )
    assert gate.decision.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert gate.approval is None

    initial_rows = (
        await db.execute(
            select(EnforcementDecisionLedger)
            .where(EnforcementDecisionLedger.decision_id == gate.decision.id)
            .order_by(
                EnforcementDecisionLedger.recorded_at.asc(),
                EnforcementDecisionLedger.id.asc(),
            )
        )
    ).scalars().all()
    assert len(initial_rows) == 1
    assert initial_rows[0].approval_request_id is None
    assert initial_rows[0].approval_status is None

    created = await service.create_or_get_approval_request(
        tenant_id=tenant.id,
        actor_id=actor_id,
        decision_id=gate.decision.id,
        notes="create approval linkage snapshot",
    )
    assert created.status == EnforcementApprovalStatus.PENDING

    rows_after_create = (
        await db.execute(
            select(EnforcementDecisionLedger)
            .where(EnforcementDecisionLedger.decision_id == gate.decision.id)
            .order_by(
                EnforcementDecisionLedger.recorded_at.asc(),
                EnforcementDecisionLedger.id.asc(),
            )
        )
    ).scalars().all()
    assert len(rows_after_create) == 2
    assert rows_after_create[-1].approval_request_id == created.id
    assert rows_after_create[-1].approval_status == EnforcementApprovalStatus.PENDING



@pytest.mark.asyncio
async def test_resolve_fail_safe_gate_appends_decision_ledger_entry(db) -> None:
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
        hard_deny_above_monthly_usd=Decimal("1000"),
        default_ttl_seconds=900,
    )

    result = await service.resolve_fail_safe_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="prod",
            action="terraform.apply",
            resource_reference="module.eks.aws_eks_cluster.main",
            estimated_monthly_delta_usd=Decimal("80"),
            estimated_hourly_delta_usd=Decimal("0.11"),
            metadata={"resource_type": "aws_eks_cluster"},
            idempotency_key="ledger-failsafe-1",
        ),
        failure_reason_code="gate_timeout",
        failure_metadata={"timeout_seconds": "0.100"},
    )

    ledger_row = (
        await db.execute(
            select(EnforcementDecisionLedger).where(
                EnforcementDecisionLedger.decision_id == result.decision.id
            )
        )
    ).scalar_one()
    assert ledger_row.decision_id == result.decision.id
    assert ledger_row.decision == EnforcementDecisionType.DENY
    assert "gate_timeout" in (ledger_row.reason_codes or [])



@pytest.mark.asyncio
async def test_budget_and_credit_list_and_validation_branches(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    assert await service.list_budgets(tenant.id) == []
    with pytest.raises(HTTPException, match="monthly_limit_usd must be >= 0"):
        await service.upsert_budget(
            tenant_id=tenant.id,
            actor_id=actor_id,
            scope_key="default",
            monthly_limit_usd=Decimal("-1"),
            active=True,
        )

    budget = await service.upsert_budget(
        tenant_id=tenant.id,
        actor_id=actor_id,
        scope_key="default",
        monthly_limit_usd=Decimal("1000"),
        active=True,
    )
    budgets = await service.list_budgets(tenant.id)
    assert [item.id for item in budgets] == [budget.id]

    assert await service.list_credits(tenant.id) == []
    with pytest.raises(HTTPException, match="total_amount_usd must be > 0"):
        await service.create_credit_grant(
            tenant_id=tenant.id,
            actor_id=actor_id,
            scope_key="default",
            total_amount_usd=Decimal("0"),
            expires_at=None,
            reason="invalid",
        )



@pytest.mark.asyncio
async def test_create_or_get_approval_request_branch_paths(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    with pytest.raises(HTTPException, match="Decision not found"):
        await service.create_or_get_approval_request(
            tenant_id=tenant.id,
            actor_id=actor_id,
            decision_id=uuid4(),
            notes="missing",
        )

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        require_approval_for_prod=False,
        require_approval_for_nonprod=False,
        auto_approve_below_monthly_usd=Decimal("100"),
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
    gate_without_approval = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.no-approval",
            estimated_monthly_delta_usd=Decimal("20"),
            estimated_hourly_delta_usd=Decimal("0.03"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="approval-create-branch-no-approval",
        ),
    )
    assert gate_without_approval.decision.decision == EnforcementDecisionType.ALLOW

    with pytest.raises(HTTPException, match="can only be created"):
        await service.create_or_get_approval_request(
            tenant_id=tenant.id,
            actor_id=actor_id,
            decision_id=gate_without_approval.decision.id,
            notes="not allowed",
        )

    pending_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="approval-create-branch-existing",
    )
    existing = await service.create_or_get_approval_request(
        tenant_id=tenant.id,
        actor_id=actor_id,
        decision_id=pending_gate.decision.id,
        notes="reuse",
    )
    assert existing.id == pending_gate.approval.id



@pytest.mark.asyncio
async def test_list_pending_approvals_reviewer_filtering_branch_paths(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="approval-list-branch-1",
    )
    service = EnforcementService(db)

    pending = await service.list_pending_approvals(
        tenant_id=tenant.id,
        reviewer=None,
        limit=50,
    )
    assert len(pending) == 1
    assert pending[0][0].id == gate.approval.id

    reviewer = CurrentUser(
        id=uuid4(),
        email="member@example.com",
        tenant_id=tenant.id,
        role=UserRole.MEMBER,
    )

    async def _reject_authority(**_kwargs):
        raise HTTPException(status_code=403, detail="forbidden")

    service._enforce_reviewer_authority = _reject_authority  # type: ignore[method-assign]
    filtered = await service.list_pending_approvals(
        tenant_id=tenant.id,
        reviewer=reviewer,
        limit=50,
    )
    assert filtered == []
