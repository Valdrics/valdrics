# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_helper_cases_common import *  # noqa: F401,F403



def test_build_approval_token_requires_secret_and_includes_kid(monkeypatch) -> None:
    service = _service()
    decision = SimpleNamespace(
        tenant_id=uuid4(),
        project_id="proj",
        id=uuid4(),
        source=EnforcementSource.TERRAFORM,
        environment="prod",
        request_fingerprint="b" * 64,
        estimated_monthly_delta_usd=Decimal("10.0000"),
        estimated_hourly_delta_usd=Decimal("0.010000"),
        resource_reference="module.app.aws_instance.main",
    )
    approval = SimpleNamespace(id=uuid4())
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: SimpleNamespace(
            SUPABASE_JWT_SECRET="short",
            API_URL="https://api.example.com",
            JWT_SIGNING_KID="kid-1",
        ),
    )
    with pytest.raises(HTTPException, match="not configured"):
        service._build_approval_token(
            decision=decision,
            approval=approval,
            expires_at=expires_at,
        )

    captured_headers: dict[str, str] = {}
    captured_payload: dict[str, object] = {}

    def _fake_encode(payload, secret, algorithm, headers=None):
        del secret, algorithm
        nonlocal captured_headers
        nonlocal captured_payload
        captured_headers = dict(headers or {})
        captured_payload = dict(payload or {})
        return "signed-token"

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: SimpleNamespace(
            SUPABASE_JWT_SECRET="s" * 32,
            API_URL="https://api.example.com",
            JWT_SIGNING_KID="kid-1",
        ),
    )
    monkeypatch.setattr(enforcement_service_module.jwt, "encode", _fake_encode)
    token = service._build_approval_token(
        decision=decision,
        approval=approval,
        expires_at=expires_at,
    )
    assert token == "signed-token"
    assert captured_headers == {"kid": "kid-1"}
    assert captured_payload.get("token_type") == "enforcement_approval"



@pytest.mark.asyncio
async def test_consume_approval_token_reject_matrix_covers_binding_and_expected_mismatches(
    monkeypatch,
) -> None:
    service = _service()
    token_events = _FakeCounter()
    fixed_now = datetime(2026, 2, 26, 12, 0, 0, tzinfo=timezone.utc)
    tenant_id = uuid4()
    approval_id = uuid4()
    decision_id = uuid4()
    token_value = "approval-token"
    token_hash = enforcement_service_module.hashlib.sha256(
        token_value.encode("utf-8")
    ).hexdigest()

    monkeypatch.setattr(
        enforcement_service_module,
        "ENFORCEMENT_APPROVAL_TOKEN_EVENTS_TOTAL",
        token_events,
    )
    monkeypatch.setattr(enforcement_service_module, "_utcnow", lambda: fixed_now)
    monkeypatch.setattr(service, "_decode_approval_token", lambda _token: {"sub": "stub"})

    state: dict[str, object] = {}

    def _base_token_context() -> SimpleNamespace:
        return SimpleNamespace(
            tenant_id=tenant_id,
            approval_id=approval_id,
            decision_id=decision_id,
            expires_at=fixed_now + timedelta(minutes=10),
            source=EnforcementSource.TERRAFORM,
            project_id="proj-alpha",
            environment="prod",
            request_fingerprint="f" * 64,
            resource_reference="module.db.aws_db_instance.main",
            max_monthly_delta_usd=Decimal("10.0000"),
            max_hourly_delta_usd=Decimal("0.010000"),
        )

    def _base_approval() -> SimpleNamespace:
        return SimpleNamespace(
            id=approval_id,
            status=EnforcementApprovalStatus.APPROVED,
            approval_token_hash=token_hash,
            approval_token_expires_at=fixed_now + timedelta(minutes=10),
            approval_token_consumed_at=None,
        )

    def _base_decision() -> SimpleNamespace:
        return SimpleNamespace(
            id=decision_id,
            source=EnforcementSource.TERRAFORM,
            project_id="proj-alpha",
            environment="prod",
            request_fingerprint="f" * 64,
            resource_reference="module.db.aws_db_instance.main",
            estimated_monthly_delta_usd=Decimal("10.0000"),
            estimated_hourly_delta_usd=Decimal("0.010000"),
            token_expires_at=None,
        )

    monkeypatch.setattr(
        service,
        "_extract_token_context",
        lambda _payload: state["token_context"],
    )

    async def _fake_load_approval_with_decision(*, tenant_id, approval_id):
        assert tenant_id == state["tenant_id"]
        assert approval_id == state["approval_id"]
        return state["approval"], state["decision"]

    monkeypatch.setattr(service, "_load_approval_with_decision", _fake_load_approval_with_decision)

    async def _assert_reject(
        *,
        expected_event: str,
        expected_status: int,
        expected_detail_substring: str,
        approval_token: str = token_value,
        mutate=None,
        kwargs: dict[str, object] | None = None,
    ) -> None:
        token_context = _base_token_context()
        approval = _base_approval()
        decision = _base_decision()
        if mutate is not None:
            mutate(token_context=token_context, approval=approval, decision=decision)
        state["tenant_id"] = tenant_id
        state["approval_id"] = approval_id
        state["token_context"] = token_context
        state["approval"] = approval
        state["decision"] = decision
        before = len(token_events.calls)
        with pytest.raises(HTTPException) as exc:
            await service.consume_approval_token(
                tenant_id=tenant_id,
                approval_token=approval_token,
                **(kwargs or {}),
            )
        assert exc.value.status_code == expected_status
        assert expected_detail_substring.lower() in str(exc.value.detail).lower()
        assert len(token_events.calls) == before + 1
        assert token_events.calls[-1][0]["event"] == expected_event

    await _assert_reject(
        expected_event="token_missing",
        expected_status=422,
        expected_detail_substring="required",
        approval_token="   ",
    )
    await _assert_reject(
        expected_event="decision_binding_mismatch",
        expected_status=409,
        expected_detail_substring="decision binding mismatch",
        mutate=lambda **objs: setattr(objs["token_context"], "decision_id", uuid4()),
    )
    await _assert_reject(
        expected_event="status_not_active",
        expected_status=409,
        expected_detail_substring="not active",
        mutate=lambda **objs: setattr(
            objs["approval"], "status", EnforcementApprovalStatus.DENIED
        ),
    )
    await _assert_reject(
        expected_event="token_hash_mismatch",
        expected_status=409,
        expected_detail_substring="token mismatch",
        mutate=lambda **objs: setattr(objs["approval"], "approval_token_hash", None),
    )
    await _assert_reject(
        expected_event="token_expired",
        expected_status=409,
        expected_detail_substring="expired",
        mutate=lambda **objs: setattr(
            objs["approval"], "approval_token_expires_at", fixed_now - timedelta(seconds=1)
        ),
    )
    await _assert_reject(
        expected_event="source_mismatch",
        expected_status=409,
        expected_detail_substring="source mismatch",
        mutate=lambda **objs: setattr(
            objs["token_context"], "source", EnforcementSource.K8S_ADMISSION
        ),
    )
    await _assert_reject(
        expected_event="environment_mismatch",
        expected_status=409,
        expected_detail_substring="environment mismatch",
        mutate=lambda **objs: setattr(objs["token_context"], "environment", "staging"),
    )
    await _assert_reject(
        expected_event="fingerprint_mismatch",
        expected_status=409,
        expected_detail_substring="fingerprint mismatch",
        mutate=lambda **objs: setattr(objs["token_context"], "request_fingerprint", "a" * 64),
    )
    await _assert_reject(
        expected_event="resource_binding_mismatch",
        expected_status=409,
        expected_detail_substring="resource binding mismatch",
        mutate=lambda **objs: setattr(
            objs["token_context"], "resource_reference", "module.other.aws_db_instance.main"
        ),
    )
    await _assert_reject(
        expected_event="cost_binding_mismatch",
        expected_status=409,
        expected_detail_substring="cost binding mismatch",
        mutate=lambda **objs: setattr(
            objs["token_context"], "max_monthly_delta_usd", Decimal("11.0000")
        ),
    )
    await _assert_reject(
        expected_event="expected_source_mismatch",
        expected_status=409,
        expected_detail_substring="Expected source mismatch",
        kwargs={"expected_source": EnforcementSource.K8S_ADMISSION},
    )
    await _assert_reject(
        expected_event="expected_project_mismatch",
        expected_status=409,
        expected_detail_substring="Expected project mismatch",
        kwargs={"expected_project_id": "proj-other"},
    )
    await _assert_reject(
        expected_event="expected_environment_mismatch",
        expected_status=409,
        expected_detail_substring="Expected environment mismatch",
        kwargs={"expected_environment": "nonprod"},
    )
    await _assert_reject(
        expected_event="expected_fingerprint_mismatch",
        expected_status=409,
        expected_detail_substring="Expected request fingerprint mismatch",
        kwargs={"expected_request_fingerprint": "e" * 64},
    )



@pytest.mark.asyncio
async def test_acquire_gate_evaluation_lock_error_and_not_acquired_branches(
    monkeypatch,
) -> None:
    class _ErrorDb:
        async def execute(self, _stmt):
            raise RuntimeError("db failure")

        async def rollback(self) -> None:
            return None

    class _NoLockDb:
        async def execute(self, _stmt):
            return SimpleNamespace(rowcount=0)

        async def rollback(self) -> None:
            return None

    policy = EnforcementPolicy(tenant_id=uuid4())
    policy.id = uuid4()

    lock_events = _FakeCounter()
    lock_wait = _FakeHistogram()
    perf_values = iter([700.0, 700.1, 800.0, 800.01])
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

    error_service = EnforcementService(db=_ErrorDb())
    with pytest.raises(RuntimeError, match="db failure"):
        await error_service._acquire_gate_evaluation_lock(
            policy=policy,
            source=EnforcementSource.TERRAFORM,
        )
    assert any(call[0]["event"] == "error" for call in lock_events.calls)

    nolock_service = EnforcementService(db=_NoLockDb())
    with pytest.raises(HTTPException, match="Unable to acquire enforcement gate evaluation lock"):
        await nolock_service._acquire_gate_evaluation_lock(
            policy=policy,
            source=EnforcementSource.TERRAFORM,
        )
    assert any(call[0]["event"] == "not_acquired" for call in lock_events.calls)



@pytest.mark.asyncio
async def test_reserve_credit_from_grants_zero_target_and_insufficient_headroom() -> None:
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
    zero_remaining_grant = SimpleNamespace(
        id=uuid4(),
        scope_key="default",
        remaining_amount_usd=Decimal("0"),
        total_amount_usd=Decimal("100"),
        active=True,
        expires_at=None,
        created_at=now,
    )
    partial_grant = SimpleNamespace(
        id=uuid4(),
        scope_key="default",
        remaining_amount_usd=Decimal("1"),
        total_amount_usd=Decimal("100"),
        active=True,
        expires_at=None,
        created_at=now,
    )
    full_grant = SimpleNamespace(
        id=uuid4(),
        scope_key="default",
        remaining_amount_usd=Decimal("5"),
        total_amount_usd=Decimal("100"),
        active=True,
        expires_at=None,
        created_at=now,
    )
    trailing_grant = SimpleNamespace(
        id=uuid4(),
        scope_key="default",
        remaining_amount_usd=Decimal("2"),
        total_amount_usd=Decimal("100"),
        active=True,
        expires_at=None,
        created_at=now,
    )
    db = _Db([[zero_remaining_grant, partial_grant], [full_grant, trailing_grant]])
    service = EnforcementService(db=db)

    assert (
        await service._reserve_credit_from_grants(
            tenant_id=tenant_id,
            decision_id=decision_id,
            scope_key="default",
            pool_type=EnforcementCreditPoolType.RESERVED,
            reserve_target_usd=Decimal("0"),
            now=now,
        )
        == []
    )

    with pytest.raises(HTTPException, match="Insufficient credit grant headroom"):
        await service._reserve_credit_from_grants(
            tenant_id=tenant_id,
            decision_id=decision_id,
            scope_key="default",
            pool_type=EnforcementCreditPoolType.RESERVED,
            reserve_target_usd=Decimal("5"),
            now=now,
        )

    allocations = await service._reserve_credit_from_grants(
        tenant_id=tenant_id,
        decision_id=decision_id,
        scope_key="default",
        pool_type=EnforcementCreditPoolType.RESERVED,
        reserve_target_usd=Decimal("1"),
        now=now,
    )
    assert len(allocations) == 1
