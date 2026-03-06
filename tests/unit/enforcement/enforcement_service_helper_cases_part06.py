# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_helper_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_active_headroom_and_reserve_credit_for_decision_helper_branches(
    monkeypatch,
) -> None:
    service = _service()
    tenant_id = uuid4()
    decision_id = uuid4()
    now = datetime.now(timezone.utc)

    async def _fake_headrooms(**_kwargs):
        return (Decimal("1.23456"), Decimal("2.00005"))

    monkeypatch.setattr(service, "_get_credit_headrooms", _fake_headrooms)
    total = await service._get_active_credit_headroom(
        tenant_id=tenant_id,
        scope_key="default",
        now=now,
    )
    assert total == Decimal("3.2346")

    reserve_calls: list[dict[str, object]] = []

    async def _fake_reserve(**kwargs):
        reserve_calls.append(dict(kwargs))
        pool_type = kwargs["pool_type"]
        if pool_type == EnforcementCreditPoolType.RESERVED:
            return [{"pool_type": "reserved"}]
        return [{"pool_type": "emergency"}]

    monkeypatch.setattr(service, "_reserve_credit_from_grants", _fake_reserve)
    allocations = await service._reserve_credit_for_decision(
        tenant_id=tenant_id,
        decision_id=decision_id,
        scope_key=" PROD ",
        reserve_reserved_credit_usd=Decimal("1"),
        reserve_emergency_credit_usd=Decimal("2"),
        now=now,
    )
    emergency_only = await service._reserve_credit_for_decision(
        tenant_id=tenant_id,
        decision_id=decision_id,
        scope_key="default",
        reserve_reserved_credit_usd=Decimal("0"),
        reserve_emergency_credit_usd=Decimal("1"),
        now=now,
    )
    reserved_only = await service._reserve_credit_for_decision(
        tenant_id=tenant_id,
        decision_id=decision_id,
        scope_key="default",
        reserve_reserved_credit_usd=Decimal("1"),
        reserve_emergency_credit_usd=Decimal("0"),
        now=now,
    )

    assert allocations == [{"pool_type": "reserved"}, {"pool_type": "emergency"}]
    assert emergency_only == [{"pool_type": "emergency"}]
    assert reserved_only == [{"pool_type": "reserved"}]
    assert reserve_calls[0]["scope_key"] == "prod"
    assert reserve_calls[0]["pool_type"] == EnforcementCreditPoolType.RESERVED
    assert reserve_calls[1]["pool_type"] == EnforcementCreditPoolType.EMERGENCY
    assert reserve_calls[2]["pool_type"] == EnforcementCreditPoolType.EMERGENCY
    assert reserve_calls[3]["pool_type"] == EnforcementCreditPoolType.RESERVED



def test_decode_approval_token_deduplicates_candidate_secrets(monkeypatch) -> None:
    service = _service()
    decode_attempts: list[str] = []

    def _fake_decode(_token, secret, **_kwargs):
        decode_attempts.append(secret)
        if secret == "a" * 32:
            raise enforcement_service_module.jwt.InvalidTokenError("bad primary")
        return {"ok": True, "token_type": "enforcement_approval"}

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: SimpleNamespace(
            SUPABASE_JWT_SECRET="a" * 32,
            ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS=["a" * 32, "b" * 32, "b" * 32],
            API_URL="https://api.example.com",
        ),
    )
    monkeypatch.setattr(enforcement_service_module.jwt, "decode", _fake_decode)

    payload = service._decode_approval_token("token")
    assert payload == {"ok": True, "token_type": "enforcement_approval"}
    assert decode_attempts == ["a" * 32, "b" * 32]



def test_extract_token_context_rejects_invalid_decimal_claims() -> None:
    service = _service()
    payload = {
        "approval_id": str(uuid4()),
        "decision_id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "project_id": "project",
        "source": EnforcementSource.TERRAFORM.value,
        "environment": "prod",
        "request_fingerprint": "a" * 64,
        "resource_reference": "module.db.aws_db_instance.main",
        "max_monthly_delta_usd": "Infinity",
        "max_hourly_delta_usd": "0.010000",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 600,
    }

    with pytest.raises(HTTPException, match="Invalid approval token"):
        service._extract_token_context(payload)



@pytest.mark.asyncio
async def test_list_helpers_cover_active_reservations_and_decision_ledger_filters() -> None:
    class _Rows:
        def __init__(self, rows) -> None:
            self._rows = list(rows)

        def scalars(self):
            return SimpleNamespace(all=lambda: list(self._rows))

    class _Db:
        def __init__(self, row_batches: list[list[object]]) -> None:
            self._row_batches = list(row_batches)

        async def execute(self, _stmt):
            return _Rows(self._row_batches.pop(0))

    tenant_id = uuid4()
    reservation_a = SimpleNamespace(id=uuid4())
    reservation_b = SimpleNamespace(id=uuid4())
    ledger_a = SimpleNamespace(id=uuid4(), recorded_at=datetime.now(timezone.utc))
    ledger_b = SimpleNamespace(id=uuid4(), recorded_at=datetime.now(timezone.utc))
    service = EnforcementService(
        db=_Db(
            [
                [reservation_a, reservation_b],
                [ledger_a, ledger_b],
            ]
        )
    )

    active = await service.list_active_reservations(tenant_id=tenant_id, limit=5000)
    assert active == [reservation_a, reservation_b]

    ledger = await service.list_decision_ledger(
        tenant_id=tenant_id,
        limit=9999,
        start_at=datetime(2026, 2, 26, 0, 0, 0),  # naive -> _as_utc path
        end_at=datetime(2026, 2, 26, 23, 59, 59, tzinfo=timezone.utc),
    )
    assert [entry.entry for entry in ledger] == [ledger_a, ledger_b]



@pytest.mark.asyncio
async def test_list_reconciliation_exceptions_covers_filtering_fallbacks_and_limit_break() -> None:
    class _Rows:
        def __init__(self, rows) -> None:
            self._rows = list(rows)

        def scalars(self):
            return SimpleNamespace(all=lambda: list(self._rows))

    class _Db:
        def __init__(self, rows) -> None:
            self._rows = list(rows)

        async def execute(self, _stmt):
            return _Rows(self._rows)

    tenant_id = uuid4()
    base_time = datetime(2026, 2, 26, 12, 0, 0, tzinfo=timezone.utc)
    decision_without_reconciliation = SimpleNamespace(
        id=uuid4(),
        created_at=base_time,
        response_payload={"reservation_reconciliation": "not-a-dict"},
    )
    decision_zero_drift = SimpleNamespace(
        id=uuid4(),
        created_at=base_time - timedelta(minutes=1),
        response_payload={
            "reservation_reconciliation": {
                "drift_usd": "0",
                "expected_reserved_usd": "5",
                "actual_monthly_delta_usd": "5",
            }
        },
    )
    decision_savings_non_list_credit = SimpleNamespace(
        id=uuid4(),
        created_at=base_time - timedelta(minutes=2),
        response_payload={
            "reservation_reconciliation": {
                "drift_usd": "-1.2500",
                "status": "unexpected",
                "expected_reserved_usd": "10",
                "actual_monthly_delta_usd": "8.7500",
                "reconciled_at": "2026-02-26T10:00:00Z",
                "notes": "  saved money  ",
                "credit_settlement": "not-a-list",
            }
        },
    )
    decision_overage_list_credit = SimpleNamespace(
        id=uuid4(),
        created_at=base_time - timedelta(minutes=3),
        response_payload={
            "reservation_reconciliation": {
                "drift_usd": "1.5000",
                "status": "",
                "expected_reserved_usd": "6",
                "actual_monthly_delta_usd": "7.5000",
                "reconciled_at": None,
                "notes": None,
                "credit_settlement": [
                    "skip-me",
                    {" ": "drop", "pool": "reserved", "amount": Decimal("1.25")},
                ],
            }
        },
    )
    service = EnforcementService(
        db=_Db(
            [
                decision_without_reconciliation,
                decision_zero_drift,
                decision_savings_non_list_credit,
                decision_overage_list_credit,
            ]
        )
    )

    exceptions = await service.list_reconciliation_exceptions(
        tenant_id=tenant_id,
        limit=2,  # force line 2904 break after second exception append
    )

    assert len(exceptions) == 2
    assert [item.decision.id for item in exceptions] == [
        decision_savings_non_list_credit.id,
        decision_overage_list_credit.id,
    ]
    assert exceptions[0].status == "savings"
    assert exceptions[0].notes == "saved money"
    assert exceptions[0].credit_settlement == []
    assert exceptions[1].status == "overage"
    assert exceptions[1].notes is None
    assert exceptions[1].credit_settlement == [{"pool": "reserved", "amount": "1.25"}]



def test_build_reservation_reconciliation_idempotent_replay_reject_branches() -> None:
    service = _service()
    decision_id = uuid4()

    base_reconciliation = {
        "idempotency_key": "idem-1",
        "actual_monthly_delta_usd": "12.5000",
        "notes": "match-notes",
        "status": "matched",
        "drift_usd": "0.0000",
        "expected_reserved_usd": "12.5000",
        "reconciled_at": "2026-02-26T11:00:00Z",
    }

    # line 2923: reservation_reconciliation is not a mapping
    result = service._build_reservation_reconciliation_idempotent_replay(
        decision=SimpleNamespace(
            id=decision_id,
            response_payload={"reservation_reconciliation": "invalid"},
        ),
        actual_monthly_delta_usd=Decimal("12.5000"),
        notes="match-notes",
        idempotency_key="idem-1",
    )
    assert result is None

    # line 2927: stored idempotency key missing/mismatch
    result = service._build_reservation_reconciliation_idempotent_replay(
        decision=SimpleNamespace(
            id=decision_id,
            response_payload={"reservation_reconciliation": {**base_reconciliation, "idempotency_key": "other"}},
        ),
        actual_monthly_delta_usd=Decimal("12.5000"),
        notes="match-notes",
        idempotency_key="idem-1",
    )
    assert result is None

    # line 2948: notes mismatch conflict
    with pytest.raises(HTTPException, match="payload mismatch .*notes"):
        service._build_reservation_reconciliation_idempotent_replay(
            decision=SimpleNamespace(
                id=decision_id,
                response_payload={"reservation_reconciliation": dict(base_reconciliation)},
            ),
            actual_monthly_delta_usd=Decimal("12.5000"),
            notes="different-notes",
            idempotency_key="idem-1",
        )

    # line 2958: invalid stored status for replay
    with pytest.raises(HTTPException, match="invalid .*status"):
        service._build_reservation_reconciliation_idempotent_replay(
            decision=SimpleNamespace(
                id=decision_id,
                response_payload={
                    "reservation_reconciliation": {
                        **base_reconciliation,
                        "notes": None,
                        "status": "corrupt",
                    }
                },
            ),
            actual_monthly_delta_usd=Decimal("12.5000"),
            notes=None,
            idempotency_key="idem-1",
        )



@pytest.mark.asyncio
async def test_reconcile_reservation_early_error_branches_and_overdue_empty_fast_path(
    monkeypatch,
) -> None:
    class _ScalarResult:
        def __init__(self, value) -> None:
            self._value = value

        def scalar_one_or_none(self):
            return self._value

    class _Rows:
        def __init__(self, rows) -> None:
            self._rows = list(rows)

        def scalars(self):
            return SimpleNamespace(all=lambda: list(self._rows))

    class _CursorResult:
        def __init__(self, rowcount: int) -> None:
            self.rowcount = rowcount

    class _Db:
        def __init__(self, results: list[object]) -> None:
            self._results = list(results)
            self.rollback_calls = 0

        async def execute(self, _stmt):
            return self._results.pop(0)

        async def rollback(self) -> None:
            self.rollback_calls += 1

    tenant_id = uuid4()
    actor_id = uuid4()
    decision_id = uuid4()

    # line 3000: decision not found on initial lookup
    not_found_service = EnforcementService(db=_Db([_ScalarResult(None)]))
    with pytest.raises(HTTPException, match="Decision not found") as exc:
        await not_found_service.reconcile_reservation(
            tenant_id=tenant_id,
            decision_id=decision_id,
            actor_id=actor_id,
            actual_monthly_delta_usd=Decimal("1"),
            notes=None,
        )
    assert exc.value.status_code == 404

    # line 3004: negative actual rejected after lookup
    negative_service = EnforcementService(
        db=_Db([_ScalarResult(SimpleNamespace(reservation_active=True))])
    )
    with pytest.raises(HTTPException, match="must be >= 0") as exc:
        await negative_service.reconcile_reservation(
            tenant_id=tenant_id,
            decision_id=decision_id,
            actor_id=actor_id,
            actual_monthly_delta_usd=Decimal("-0.0001"),
            notes=None,
        )
    assert exc.value.status_code == 422

    # line 3049: claim loses race and refreshed row no longer exists
    claim_miss_db = _Db(
        [
            _ScalarResult(SimpleNamespace(reservation_active=True)),
            _CursorResult(0),
            _ScalarResult(None),
        ]
    )
    claim_miss_service = EnforcementService(db=claim_miss_db)
    with pytest.raises(HTTPException, match="Decision not found") as exc:
        await claim_miss_service.reconcile_reservation(
            tenant_id=tenant_id,
            decision_id=decision_id,
            actor_id=actor_id,
            actual_monthly_delta_usd=Decimal("1"),
            notes=None,
        )
    assert exc.value.status_code == 404
    assert claim_miss_db.rollback_calls == 1

    # line 3062: claim loses race, refreshed row exists but is inactive with no replay payload/key
    refreshed_inactive = SimpleNamespace(reservation_active=False)
    inactive_db = _Db(
        [
            _ScalarResult(SimpleNamespace(reservation_active=True)),
            _CursorResult(0),
            _ScalarResult(refreshed_inactive),
        ]
    )
    inactive_service = EnforcementService(db=inactive_db)
    with pytest.raises(HTTPException, match="Reservation is not active") as exc:
        await inactive_service.reconcile_reservation(
            tenant_id=tenant_id,
            decision_id=decision_id,
            actor_id=actor_id,
            actual_monthly_delta_usd=Decimal("1"),
            notes=None,
        )
    assert exc.value.status_code == 409
    assert inactive_db.rollback_calls == 1

    # line 3176: overdue scan returns empty set fast-path
    fixed_now = datetime(2026, 2, 26, 12, 0, 0, tzinfo=timezone.utc)
    monkeypatch.setattr(enforcement_service_module, "_utcnow", lambda: fixed_now)
    overdue_service = EnforcementService(db=_Db([_Rows([])]))
    summary = await overdue_service.reconcile_overdue_reservations(
        tenant_id=tenant_id,
        actor_id=actor_id,
        older_than_seconds=30,  # bounded to 60
        limit=0,  # bounded to 1
    )
    assert summary.released_count == 0
    assert summary.total_released_usd == Decimal("0.0000")
    assert summary.decision_ids == []
    assert summary.older_than_seconds == 60
