# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_helper_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_acquire_gate_evaluation_lock_timeout_raises_lock_reason(monkeypatch) -> None:
    class _SlowDb:
        def __init__(self) -> None:
            self.rollback_calls = 0

        async def execute(self, _stmt):
            await asyncio.sleep(0.05)
            return SimpleNamespace(rowcount=1)

        async def rollback(self) -> None:
            self.rollback_calls += 1

    db = _SlowDb()
    service = EnforcementService(db=db)
    policy = EnforcementPolicy(tenant_id=uuid4())
    policy.id = uuid4()
    lock_events = _FakeCounter()
    lock_wait = _FakeHistogram()
    perf_values = iter([300.0, 300.05])

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
        lambda: 0.01,
    )
    monkeypatch.setattr(
        enforcement_service_module.time,
        "perf_counter",
        lambda: next(perf_values),
    )

    with pytest.raises(HTTPException) as exc:
        await service._acquire_gate_evaluation_lock(
            policy=policy,
            source=EnforcementSource.K8S_ADMISSION,
        )

    assert exc.value.status_code == 503
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail["code"] == "gate_lock_timeout"
    assert db.rollback_calls == 1
    assert any(
        call[0]["event"] == "timeout" and call[0]["source"] == "k8s_admission"
        for call in lock_events.calls
    )
    assert any(
        call[0]["event"] == "contended" and call[0]["source"] == "k8s_admission"
        for call in lock_events.calls
    )
    assert len(lock_wait.calls) == 1
    assert lock_wait.calls[0][0]["outcome"] == "timeout"



def test_policy_document_hash_and_gate_timeout_helper_branches(monkeypatch) -> None:
    assert enforcement_service_module._parse_iso_datetime("   ") is None

    december = datetime(2026, 12, 15, 9, 0, 0, tzinfo=timezone.utc)
    month_start, month_end = enforcement_service_module._month_bounds(december)
    assert month_start.month == 12
    assert month_end.month == 1
    assert month_end.year == 2027

    assert (
        enforcement_service_module._normalize_policy_document_schema_version(None)
        == "valdrics.enforcement.policy.v1"
    )
    assert len(
        enforcement_service_module._normalize_policy_document_schema_version("x" * 100)
    ) == 64
    assert (
        enforcement_service_module._normalize_policy_document_sha256("invalid")
        == "0" * 64
    )
    assert (
        enforcement_service_module._normalize_policy_document_sha256("g" * 64)
        == "0" * 64
    )
    assert enforcement_service_module._normalize_policy_document_sha256("a" * 64) == (
        "a" * 64
    )

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: SimpleNamespace(ENFORCEMENT_GATE_TIMEOUT_SECONDS="bad"),
    )
    assert enforcement_service_module._gate_lock_timeout_seconds() == pytest.approx(1.6)

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: SimpleNamespace(ENFORCEMENT_GATE_TIMEOUT_SECONDS=0),
    )
    assert enforcement_service_module._gate_lock_timeout_seconds() == pytest.approx(0.05)

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: SimpleNamespace(ENFORCEMENT_GATE_TIMEOUT_SECONDS=1000),
    )
    assert enforcement_service_module._gate_lock_timeout_seconds() == pytest.approx(5.0)



def test_policy_document_contract_backfill_required_branches() -> None:
    service = _service()
    canonical_policy = enforcement_service_module.canonical_policy_document_payload(
        enforcement_service_module.PolicyDocument().model_dump(mode="json")
    )
    valid_hash = enforcement_service_module.policy_document_sha256(canonical_policy)
    valid_policy = SimpleNamespace(
        policy_document_schema_version=enforcement_service_module.POLICY_DOCUMENT_SCHEMA_VERSION,
        policy_document=canonical_policy,
        policy_document_sha256=valid_hash,
    )
    assert service._policy_document_contract_backfill_required(valid_policy) is False

    bad_schema = SimpleNamespace(
        policy_document_schema_version="legacy",
        policy_document=canonical_policy,
        policy_document_sha256=valid_hash,
    )
    assert service._policy_document_contract_backfill_required(bad_schema) is True

    non_mapping_policy_document = SimpleNamespace(
        policy_document_schema_version=enforcement_service_module.POLICY_DOCUMENT_SCHEMA_VERSION,
        policy_document="not-a-mapping",
        policy_document_sha256=valid_hash,
    )
    assert (
        service._policy_document_contract_backfill_required(non_mapping_policy_document)
        is True
    )

    invalid_policy_document = SimpleNamespace(
        policy_document_schema_version=enforcement_service_module.POLICY_DOCUMENT_SCHEMA_VERSION,
        policy_document={"schema_version": "invalid"},
        policy_document_sha256=valid_hash,
    )
    assert (
        service._policy_document_contract_backfill_required(invalid_policy_document)
        is True
    )

    invalid_hash = SimpleNamespace(
        policy_document_schema_version=enforcement_service_module.POLICY_DOCUMENT_SCHEMA_VERSION,
        policy_document=canonical_policy,
        policy_document_sha256="xyz",
    )
    assert service._policy_document_contract_backfill_required(invalid_hash) is True



def test_resolve_monthly_ceiling_none_and_positive_tier_limit_paths(monkeypatch) -> None:
    service = _service()
    tenant_id = uuid4()

    monkeypatch.setattr(
        enforcement_service_module,
        "get_tier_limit",
        lambda _tier, _key: None,
    )
    assert (
        asyncio.run(
            service._resolve_plan_monthly_ceiling_usd(
                policy=EnforcementPolicy(tenant_id=tenant_id, plan_monthly_ceiling_usd=None),
                tenant_tier=enforcement_service_module.PricingTier.PRO,
            )
        )
        is None
    )
    assert (
        asyncio.run(
            service._resolve_enterprise_monthly_ceiling_usd(
                policy=EnforcementPolicy(
                    tenant_id=tenant_id, enterprise_monthly_ceiling_usd=None
                ),
                tenant_tier=enforcement_service_module.PricingTier.PRO,
            )
        )
        is None
    )

    monkeypatch.setattr(
        enforcement_service_module,
        "get_tier_limit",
        lambda _tier, key: (
            Decimal("333.2222")
            if key == "enforcement_plan_monthly_ceiling_usd"
            else Decimal("777.4444")
        ),
    )
    assert asyncio.run(
        service._resolve_plan_monthly_ceiling_usd(
            policy=EnforcementPolicy(tenant_id=tenant_id, plan_monthly_ceiling_usd=None),
            tenant_tier=enforcement_service_module.PricingTier.PRO,
        )
    ) == Decimal("333.2222")
    assert asyncio.run(
        service._resolve_enterprise_monthly_ceiling_usd(
            policy=EnforcementPolicy(tenant_id=tenant_id, enterprise_monthly_ceiling_usd=None),
            tenant_tier=enforcement_service_module.PricingTier.PRO,
        )
    ) == Decimal("777.4444")



def test_extract_decision_risk_level_handles_missing_and_empty_metadata() -> None:
    service = _service()
    assert (
        service._extract_decision_risk_level(
            SimpleNamespace(request_payload={"metadata": "not-a-dict"})
        )
        is None
    )
    assert (
        service._extract_decision_risk_level(
            SimpleNamespace(request_payload={"metadata": {"risk_level": "", "risk": None}})
        )
        is None
    )



def test_resolve_approval_routing_trace_skips_unmatched_rules_and_falls_back_permission() -> None:
    service = _service()
    tenant_id = uuid4()
    policy = EnforcementPolicy(
        tenant_id=tenant_id,
        enforce_prod_requester_reviewer_separation=True,
        approval_routing_rules=[
            "not-a-rule",
            {"rule_id": "disabled", "enabled": False},
            {
                "rule_id": "action-miss",
                "action_prefixes": ["terraform.destroy"],
            },
            {
                "rule_id": "min-too-high",
                "min_monthly_delta_usd": "1000",
            },
            {
                "rule_id": "max-too-low",
                "max_monthly_delta_usd": "10",
            },
            {
                "rule_id": "risk-miss",
                "risk_levels": ["critical"],
            },
            {
                "rule_id": "matched",
                "required_permission": "invalid-permission",
                "allowed_reviewer_roles": ["member"],
            },
        ],
    )
    decision = SimpleNamespace(
        environment="prod",
        action="terraform.apply",
        estimated_monthly_delta_usd=Decimal("50"),
        request_payload={"metadata": {"risk_level": "high"}},
    )

    trace = service._resolve_approval_routing_trace(policy=policy, decision=decision)
    assert trace["matched_rule"] == "policy_rule"
    assert trace["rule_id"] == "matched"
    assert (
        trace["required_permission"]
        == APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD
    )
    assert trace["allowed_reviewer_roles"] == ["member"]



def test_export_manifest_signing_secret_and_key_id_resolution(monkeypatch) -> None:
    service = _service()

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: SimpleNamespace(
            ENFORCEMENT_EXPORT_SIGNING_SECRET="a" * 32,
            SUPABASE_JWT_SECRET="b" * 32,
            ENFORCEMENT_EXPORT_SIGNING_KID="explicit-kid",
            JWT_SIGNING_KID="jwt-kid",
        ),
    )
    assert service._resolve_export_manifest_signing_secret() == "a" * 32
    assert service._resolve_export_manifest_signing_key_id() == "explicit-kid"

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: SimpleNamespace(
            ENFORCEMENT_EXPORT_SIGNING_SECRET="short",
            SUPABASE_JWT_SECRET="b" * 32,
            ENFORCEMENT_EXPORT_SIGNING_KID="",
            JWT_SIGNING_KID="jwt-kid",
        ),
    )
    assert service._resolve_export_manifest_signing_secret() == "b" * 32
    assert service._resolve_export_manifest_signing_key_id() == "jwt-kid"

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: SimpleNamespace(
            ENFORCEMENT_EXPORT_SIGNING_SECRET="",
            SUPABASE_JWT_SECRET="",
            ENFORCEMENT_EXPORT_SIGNING_KID="",
            JWT_SIGNING_KID="",
        ),
    )
    with pytest.raises(HTTPException, match="not configured"):
        service._resolve_export_manifest_signing_secret()
    assert (
        service._resolve_export_manifest_signing_key_id()
        == "enforcement-export-hmac-v1"
    )



def test_render_approvals_csv_handles_non_list_roles() -> None:
    service = _service()
    now = datetime(2026, 2, 25, 12, 0, 0, tzinfo=timezone.utc)
    approval = SimpleNamespace(
        id=uuid4(),
        decision_id=uuid4(),
        status=EnforcementApprovalStatus.PENDING,
        requested_by_user_id=uuid4(),
        reviewed_by_user_id=None,
        review_notes=None,
        routing_rule_id="rule-1",
        routing_trace={"required_permission": "perm", "allowed_reviewer_roles": "owner"},
        approval_token_expires_at=None,
        approval_token_consumed_at=None,
        expires_at=now + timedelta(minutes=5),
        approved_at=None,
        denied_at=None,
        created_at=now,
        updated_at=now,
    )
    csv_payload = service._render_approvals_csv([approval])
    rows = csv_payload.strip().splitlines()
    assert len(rows) == 2
    assert "routing_allowed_reviewer_roles" in rows[0]
    assert ",," in rows[1]



def test_decode_and_extract_approval_token_error_branches(monkeypatch) -> None:
    service = _service()
    with monkeypatch.context() as context:
        context.setattr(
            enforcement_service_module,
            "get_settings",
            lambda: SimpleNamespace(SUPABASE_JWT_SECRET="too-short", API_URL="https://api"),
        )
        with pytest.raises(HTTPException, match="not configured"):
            service._decode_approval_token("token")

    def _raise_expired(*_args, **_kwargs):
        raise enforcement_service_module.jwt.ExpiredSignatureError("expired")

    with monkeypatch.context() as context:
        context.setattr(
            enforcement_service_module,
            "get_settings",
            lambda: SimpleNamespace(
                SUPABASE_JWT_SECRET="s" * 32,
                ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS=[],
                API_URL="https://api",
            ),
        )
        context.setattr(enforcement_service_module.jwt, "decode", _raise_expired)
        with pytest.raises(HTTPException, match="expired"):
            service._decode_approval_token("token")

    with monkeypatch.context() as context:
        context.setattr(
            enforcement_service_module,
            "get_settings",
            lambda: SimpleNamespace(
                SUPABASE_JWT_SECRET="s" * 32,
                ENFORCEMENT_APPROVAL_TOKEN_FALLBACK_SECRETS=[],
                API_URL="https://api",
            ),
        )
        context.setattr(
            enforcement_service_module.jwt,
            "decode",
            lambda *_args, **_kwargs: {"token_type": "wrong"},
        )
        with pytest.raises(HTTPException, match="Invalid approval token"):
            service._decode_approval_token("token")

    base_payload = {
        "approval_id": str(uuid4()),
        "decision_id": str(uuid4()),
        "tenant_id": str(uuid4()),
        "project_id": "project",
        "source": EnforcementSource.TERRAFORM.value,
        "environment": "prod",
        "request_fingerprint": "a" * 64,
        "resource_reference": "module.db.aws_db_instance.main",
        "max_monthly_delta_usd": "10.0000",
        "max_hourly_delta_usd": "0.010000",
        "exp": int(datetime.now(timezone.utc).timestamp()) + 600,
    }
    context = service._extract_token_context(base_payload)
    assert context.project_id == "project"

    bad_uuid_payload = dict(base_payload)
    bad_uuid_payload["approval_id"] = "not-uuid"
    with pytest.raises(HTTPException, match="Invalid approval token"):
        service._extract_token_context(bad_uuid_payload)

    bad_source_payload = dict(base_payload)
    bad_source_payload["source"] = "invalid"
    with pytest.raises(HTTPException, match="Invalid approval token"):
        service._extract_token_context(bad_source_payload)

    bad_exp_type_payload = dict(base_payload)
    bad_exp_type_payload["exp"] = object()
    with pytest.raises(HTTPException, match="Invalid approval token"):
        service._extract_token_context(bad_exp_type_payload)

    bad_exp_value_payload = dict(base_payload)
    bad_exp_value_payload["exp"] = "NaN"
    with pytest.raises(HTTPException, match="Invalid approval token"):
        service._extract_token_context(bad_exp_value_payload)

    bad_fingerprint_payload = dict(base_payload)
    bad_fingerprint_payload["request_fingerprint"] = "short"
    with pytest.raises(HTTPException, match="Invalid approval token"):
        service._extract_token_context(bad_fingerprint_payload)

    bad_resource_payload = dict(base_payload)
    bad_resource_payload["resource_reference"] = ""
    with pytest.raises(HTTPException, match="Invalid approval token"):
        service._extract_token_context(bad_resource_payload)

    bad_project_payload = dict(base_payload)
    bad_project_payload["project_id"] = ""
    with pytest.raises(HTTPException, match="Invalid approval token"):
        service._extract_token_context(bad_project_payload)
