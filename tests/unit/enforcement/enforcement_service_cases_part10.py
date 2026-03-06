# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_list_pending_approvals_reviewer_filtering_includes_authorized_rows(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="approval-list-branch-allow-1",
    )
    service = EnforcementService(db)
    reviewer = CurrentUser(
        id=uuid4(),
        email="admin@example.com",
        tenant_id=tenant.id,
        role=UserRole.ADMIN,
    )
    authority_calls: list[tuple[str, str]] = []

    async def _allow_authority(*, approval, decision, **_kwargs):
        authority_calls.append((str(approval.id), str(decision.id)))
        return {"required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_NONPROD}

    service._enforce_reviewer_authority = _allow_authority  # type: ignore[method-assign]
    filtered = await service.list_pending_approvals(
        tenant_id=tenant.id,
        reviewer=reviewer,
        limit=50,
    )

    assert len(filtered) == 1
    assert filtered[0][0].id == gate.approval.id
    assert filtered[0][1].id == gate.decision.id
    assert authority_calls == [(str(gate.approval.id), str(gate.decision.id))]



@pytest.mark.asyncio
async def test_approve_request_marks_expired_approval_branch(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="prod",
        require_approval_for_prod=True,
        require_approval_for_nonprod=False,
        idempotency_key="approve-expired-branch-1",
    )
    assert gate.approval is not None
    gate.approval.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.add(gate.approval)
    await db.commit()

    service = EnforcementService(db)
    reviewer = CurrentUser(
        id=uuid4(),
        email="owner@example.com",
        tenant_id=tenant.id,
        role=UserRole.OWNER,
    )
    with pytest.raises(HTTPException, match="has expired"):
        await service.approve_request(
            tenant_id=tenant.id,
            approval_id=gate.approval.id,
            reviewer=reviewer,
            notes="too late",
        )

    await db.refresh(gate.approval)
    await db.refresh(gate.decision)
    assert gate.approval.status == EnforcementApprovalStatus.EXPIRED
    assert gate.decision.reservation_active is False
    response_payload = gate.decision.response_payload or {}
    assert "approval_expired_at" in response_payload
