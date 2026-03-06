# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_helper_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_reserve_credit_from_grants_skips_subquantum_reserve_amount() -> None:
    class _Rows:
        def __init__(self, rows) -> None:
            self._rows = list(rows)

        def scalars(self):
            return SimpleNamespace(all=lambda: list(self._rows))

    class _Db:
        def __init__(self, row_batches: list[list[SimpleNamespace]]) -> None:
            self._row_batches = list(row_batches)
            self.added: list[object] = []

        async def execute(self, _stmt):
            return _Rows(self._row_batches.pop(0))

        def add(self, obj: object) -> None:
            self.added.append(obj)

    tenant_id = uuid4()
    decision_id = uuid4()
    now = datetime.now(timezone.utc)
    subquantum_grant = SimpleNamespace(
        id=uuid4(),
        scope_key="default",
        remaining_amount_usd=Decimal("0.00004"),
        total_amount_usd=Decimal("1.0000"),
        active=True,
        expires_at=None,
        created_at=now,
    )
    usable_grant = SimpleNamespace(
        id=uuid4(),
        scope_key="default",
        remaining_amount_usd=Decimal("0.0002"),
        total_amount_usd=Decimal("1.0000"),
        active=True,
        expires_at=None,
        created_at=now,
    )
    db = _Db([[subquantum_grant, usable_grant]])
    service = EnforcementService(db=db)

    allocations = await service._reserve_credit_from_grants(
        tenant_id=tenant_id,
        decision_id=decision_id,
        scope_key="default",
        pool_type=EnforcementCreditPoolType.RESERVED,
        reserve_target_usd=Decimal("0.0001"),
        now=now,
    )

    assert len(allocations) == 1
    assert allocations[0]["credit_grant_id"] == str(usable_grant.id)
    assert allocations[0]["reserved_amount_usd"] == "0.0001"
    assert subquantum_grant.remaining_amount_usd == Decimal("0.00004")
    assert usable_grant.remaining_amount_usd == Decimal("0.0001")
    assert len(db.added) == 1



@pytest.mark.asyncio
async def test_reserve_credit_from_grants_defensive_zero_reserve_amount_guard(
    monkeypatch,
) -> None:
    class _Rows:
        def __init__(self, rows) -> None:
            self._rows = list(rows)

        def scalars(self):
            return SimpleNamespace(all=lambda: list(self._rows))

    class _Db:
        def __init__(self, row_batches: list[list[SimpleNamespace]]) -> None:
            self._row_batches = list(row_batches)
            self.added: list[object] = []

        async def execute(self, _stmt):
            return _Rows(self._row_batches.pop(0))

        def add(self, obj: object) -> None:
            self.added.append(obj)

    tenant_id = uuid4()
    decision_id = uuid4()
    now = datetime.now(timezone.utc)
    grant = SimpleNamespace(
        id=uuid4(),
        scope_key="default",
        remaining_amount_usd=Decimal("1.0000"),
        total_amount_usd=Decimal("1.0000"),
        active=True,
        expires_at=None,
        created_at=now,
    )
    db = _Db([[grant]])
    service = EnforcementService(db=db)
    original_quantize = enforcement_service_module._quantize
    quantize_calls = {"count": 0}

    def _quantize_with_regression(value, quantum: str) -> Decimal:
        quantize_calls["count"] += 1
        if quantum == "0.0001" and quantize_calls["count"] == 3:
            return Decimal("0.0000")
        return original_quantize(value, quantum)

    monkeypatch.setattr(
        enforcement_service_module,
        "_quantize",
        _quantize_with_regression,
    )

    with pytest.raises(HTTPException, match="Insufficient credit grant headroom"):
        await service._reserve_credit_from_grants(
            tenant_id=tenant_id,
            decision_id=decision_id,
            scope_key="default",
            pool_type=EnforcementCreditPoolType.RESERVED,
            reserve_target_usd=Decimal("1.0000"),
            now=now,
        )

    assert grant.remaining_amount_usd == Decimal("1.0000")
    assert len(db.added) == 0



@pytest.mark.asyncio
async def test_settle_credit_reservations_for_decision_missing_grant_and_drift_errors() -> None:
    class _Rows:
        def __init__(self, rows) -> None:
            self._rows = list(rows)

        def scalars(self):
            return SimpleNamespace(all=lambda: list(self._rows))

    class _Db:
        def __init__(self, row_batches: list[list[SimpleNamespace]]) -> None:
            self._row_batches = list(row_batches)

        async def execute(self, _stmt):
            return _Rows(self._row_batches.pop(0))

    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    missing_grant_allocation = SimpleNamespace(
        id=uuid4(),
        credit_grant_id=uuid4(),
        credit_pool_type=EnforcementCreditPoolType.RESERVED,
        reserved_amount_usd=Decimal("0.5000"),
        consumed_amount_usd=Decimal("0"),
        released_amount_usd=Decimal("0"),
        active=True,
        settled_at=None,
        created_at=now,
    )
    missing_grant_service = EnforcementService(db=_Db([[missing_grant_allocation], []]))
    with pytest.raises(HTTPException, match="Missing credit grant row for reservation allocation"):
        await missing_grant_service._settle_credit_reservations_for_decision(
            tenant_id=tenant_id,
            decision=SimpleNamespace(id=uuid4(), reserved_credit_usd=Decimal("0.5000")),
            consumed_credit_usd=Decimal("0.2500"),
            now=now,
        )

    drift_grant = SimpleNamespace(
        id=uuid4(),
        scope_key="default",
        remaining_amount_usd=Decimal("0.0000"),
        total_amount_usd=Decimal("1.0000"),
        expires_at=None,
        active=True,
    )
    drift_allocation = SimpleNamespace(
        id=uuid4(),
        credit_grant_id=drift_grant.id,
        credit_pool_type=EnforcementCreditPoolType.RESERVED,
        reserved_amount_usd=Decimal("0.5000"),
        consumed_amount_usd=Decimal("0"),
        released_amount_usd=Decimal("0"),
        active=True,
        settled_at=None,
        created_at=now,
    )
    drift_service = EnforcementService(db=_Db([[drift_allocation], [drift_grant]]))
    with pytest.raises(HTTPException, match="Credit reservation settlement drift detected"):
        await drift_service._settle_credit_reservations_for_decision(
            tenant_id=tenant_id,
            decision=SimpleNamespace(id=uuid4(), reserved_credit_usd=Decimal("1.0000")),
            consumed_credit_usd=Decimal("0"),
            now=now,
        )



@pytest.mark.asyncio
async def test_settle_credit_reservations_for_decision_clamps_release_and_grant_total() -> None:
    class _Rows:
        def __init__(self, rows) -> None:
            self._rows = list(rows)

        def scalars(self):
            return SimpleNamespace(all=lambda: list(self._rows))

    class _Db:
        def __init__(self, row_batches: list[list[SimpleNamespace]]) -> None:
            self._row_batches = list(row_batches)

        async def execute(self, _stmt):
            return _Rows(self._row_batches.pop(0))

    tenant_id = uuid4()
    now = datetime.now(timezone.utc)
    grant_one = SimpleNamespace(
        id=uuid4(),
        scope_key="default",
        remaining_amount_usd=Decimal("0.1000"),
        total_amount_usd=Decimal("10.0000"),
        expires_at=None,
        active=True,
    )
    grant_two = SimpleNamespace(
        id=uuid4(),
        scope_key="default",
        remaining_amount_usd=Decimal("9.9000"),
        total_amount_usd=Decimal("10.0000"),
        expires_at=None,
        active=True,
    )
    allocation_one = SimpleNamespace(
        id=uuid4(),
        credit_grant_id=grant_one.id,
        credit_pool_type=EnforcementCreditPoolType.RESERVED,
        reserved_amount_usd=Decimal("0.7500"),
        consumed_amount_usd=Decimal("0"),
        released_amount_usd=Decimal("0"),
        active=True,
        settled_at=None,
        created_at=now,
    )
    allocation_two = SimpleNamespace(
        id=uuid4(),
        credit_grant_id=grant_two.id,
        credit_pool_type=EnforcementCreditPoolType.EMERGENCY,
        reserved_amount_usd=Decimal("0.7500"),
        consumed_amount_usd=Decimal("0"),
        released_amount_usd=Decimal("0"),
        active=True,
        settled_at=None,
        created_at=now,
    )
    service = EnforcementService(db=_Db([[allocation_one, allocation_two], [grant_one, grant_two]]))

    diagnostics = await service._settle_credit_reservations_for_decision(
        tenant_id=tenant_id,
        decision=SimpleNamespace(id=uuid4(), reserved_credit_usd=Decimal("1.0000")),
        consumed_credit_usd=Decimal("0.7500"),
        now=now,
    )

    assert len(diagnostics) == 2
    assert diagnostics[0]["released_amount_usd"] == "0.0000"
    assert diagnostics[1]["released_amount_usd"] == "0.2500"
    assert diagnostics[1]["grant_remaining_amount_usd_after"] == "10.0000"
    assert allocation_one.consumed_amount_usd == Decimal("0.7500")
    assert allocation_one.released_amount_usd == Decimal("0.0000")
    assert allocation_two.consumed_amount_usd == Decimal("0.0000")
    assert allocation_two.released_amount_usd == Decimal("0.2500")
    assert allocation_one.active is False
    assert allocation_two.active is False
    assert grant_two.remaining_amount_usd == Decimal("10.0000")



@pytest.mark.asyncio
async def test_load_approval_with_decision_and_assert_pending_error_paths() -> None:
    class _Result:
        def __init__(self, value) -> None:
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _Db:
        def __init__(self, values: list[object | None]) -> None:
            self._values = list(values)

        async def execute(self, _stmt):
            return _Result(self._values.pop(0))

    tenant_id = uuid4()
    approval_id = uuid4()

    service_missing_approval = EnforcementService(db=_Db([None]))
    with pytest.raises(HTTPException, match="Approval request not found"):
        await service_missing_approval._load_approval_with_decision(
            tenant_id=tenant_id,
            approval_id=approval_id,
        )

    approval = SimpleNamespace(
        id=approval_id,
        tenant_id=tenant_id,
        decision_id=uuid4(),
        status=EnforcementApprovalStatus.PENDING,
    )
    service_missing_decision = EnforcementService(db=_Db([approval, None]))
    with pytest.raises(HTTPException, match="Approval decision not found"):
        await service_missing_decision._load_approval_with_decision(
            tenant_id=tenant_id,
            approval_id=approval_id,
        )

    service = _service()
    with pytest.raises(HTTPException, match="already approved"):
        service._assert_pending(
            SimpleNamespace(status=EnforcementApprovalStatus.APPROVED)
        )



@pytest.mark.asyncio
async def test_enforce_reviewer_authority_updates_routing_trace_and_rejects_missing_permission(
    monkeypatch,
) -> None:
    service = _service()
    tenant_id = uuid4()
    policy = EnforcementPolicy(tenant_id=tenant_id, approval_routing_rules=[])
    approval = SimpleNamespace(
        routing_rule_id=None,
        routing_trace=None,
        requested_by_user_id=uuid4(),
    )
    decision = SimpleNamespace(
        environment="prod",
        action="terraform.apply",
        estimated_monthly_delta_usd=Decimal("100"),
        request_payload={"metadata": {"risk_level": "medium"}},
    )
    reviewer = SimpleNamespace(id=uuid4(), role="member")
    routing_trace = {
        "rule_id": "  explicit-rule  ",
        "required_permission": None,
        "allowed_reviewer_roles": ["member"],
        "require_requester_reviewer_separation": False,
    }

    monkeypatch.setattr(service, "_routing_trace_or_default", lambda **_kwargs: dict(routing_trace))

    async def _unexpected_permission_check(*_args, **_kwargs):
        raise AssertionError("permission lookup should not run when required_permission is missing")

    monkeypatch.setattr(
        enforcement_service_module,
        "user_has_approval_permission",
        _unexpected_permission_check,
    )

    with pytest.raises(HTTPException, match="missing required_permission") as exc:
        await service._enforce_reviewer_authority(
            tenant_id=tenant_id,
            policy=policy,
            approval=approval,
            decision=decision,
            reviewer=reviewer,
            enforce_requester_separation=False,
        )

    assert exc.value.status_code == 409
    assert approval.routing_rule_id == "explicit-rule"
    assert approval.routing_trace == routing_trace



@pytest.mark.asyncio
async def test_credit_headroom_helpers_cover_legacy_uncovered_and_spillover_paths() -> None:
    class _ScalarResult:
        def __init__(self, value: object) -> None:
            self._value = value

        def scalar_one(self) -> object:
            return self._value

    class _Db:
        def __init__(self, values: list[object]) -> None:
            self._values = list(values)

        async def execute(self, _stmt):
            return _ScalarResult(self._values.pop(0))

    tenant_id = uuid4()
    now = datetime.now(timezone.utc)

    # Legacy uncovered reservation exceeds reserved headroom and spills into emergency.
    service = EnforcementService(
        db=_Db([Decimal("5"), Decimal("3"), Decimal("10"), Decimal("2")])
    )
    reserved, emergency = await service._get_credit_headrooms(
        tenant_id=tenant_id,
        scope_key=" Prod ",
        now=now,
    )
    assert reserved == Decimal("0.0000")
    assert emergency == Decimal("0.0000")

    # Legacy uncovered reservation is fully absorbed by reserved pool; emergency untouched.
    service = EnforcementService(
        db=_Db([Decimal("10"), Decimal("4"), Decimal("12"), Decimal("10")])
    )
    reserved, emergency = await service._get_credit_headrooms(
        tenant_id=tenant_id,
        scope_key="default",
        now=now,
    )
    assert reserved == Decimal("8.0000")
    assert emergency == Decimal("4.0000")

    # No uncovered legacy reservation; branch should bypass legacy reduction entirely.
    service = EnforcementService(
        db=_Db([Decimal("7"), Decimal("2"), Decimal("4"), Decimal("4")])
    )
    reserved, emergency = await service._get_credit_headrooms(
        tenant_id=tenant_id,
        scope_key="default",
        now=now,
    )
    assert reserved == Decimal("7.0000")
    assert emergency == Decimal("2.0000")
