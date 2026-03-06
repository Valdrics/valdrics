# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_consume_approval_token_rejects_rotated_secret_without_fallback(
    db, monkeypatch
) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    old_secret = "old-approval-signing-secret-09876543210987654321"
    new_secret = "new-approval-signing-secret-09876543210987654321"

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
    token, _, _ = await _issue_approved_token(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        idempotency_key="consume-rotation-no-fallback-1",
    )

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: _settings(new_secret),
    )
    service = EnforcementService(db)
    with pytest.raises(HTTPException) as exc:
        await service.consume_approval_token(
            tenant_id=tenant.id,
            approval_token=token,
            actor_id=actor_id,
        )
    assert exc.value.status_code == 401
    assert "invalid approval token" in str(exc.value.detail).lower()



@pytest.mark.asyncio
async def test_consume_approval_token_rejects_tampered_payload(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    token, _, _ = await _issue_approved_token(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        idempotency_key="consume-tamper-1",
    )
    header, payload, signature = token.split(".")
    decoded_payload = json.loads(base64.urlsafe_b64decode(payload + "==").decode())
    decoded_payload["resource_reference"] = "module.hijack.aws_iam_role.admin"
    tampered_payload = (
        base64.urlsafe_b64encode(json.dumps(decoded_payload).encode()).decode().rstrip("=")
    )
    tampered_token = f"{header}.{tampered_payload}.{signature}"

    service = EnforcementService(db)
    with pytest.raises(HTTPException) as exc:
        await service.consume_approval_token(
            tenant_id=tenant.id,
            approval_token=tampered_token,
            actor_id=actor_id,
        )
    assert exc.value.status_code == 401
    assert "invalid approval token" in str(exc.value.detail).lower()



@pytest.mark.asyncio
async def test_consume_approval_token_rejects_wrong_tenant(db) -> None:
    tenant_a = await _seed_tenant(db)
    tenant_b = await _seed_tenant(db)
    actor_id = uuid4()
    token, _, _ = await _issue_approved_token(
        db=db,
        tenant_id=tenant_a.id,
        actor_id=actor_id,
        idempotency_key="consume-wrong-tenant-1",
    )

    service = EnforcementService(db)
    with pytest.raises(HTTPException) as exc:
        await service.consume_approval_token(
            tenant_id=tenant_b.id,
            approval_token=token,
            actor_id=actor_id,
        )
    assert exc.value.status_code == 403
    assert "tenant mismatch" in str(exc.value.detail).lower()



@pytest.mark.asyncio
async def test_consume_approval_token_rejects_expected_binding_mismatch(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    token, _, _ = await _issue_approved_token(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        idempotency_key="consume-binding-mismatch-1",
    )

    service = EnforcementService(db)
    with pytest.raises(HTTPException) as exc:
        await service.consume_approval_token(
            tenant_id=tenant.id,
            approval_token=token,
            actor_id=actor_id,
            expected_resource_reference="module.other.aws_db_instance.main",
        )
    assert exc.value.status_code == 409
    assert "resource reference mismatch" in str(exc.value.detail).lower()



@pytest.mark.asyncio
async def test_approval_token_claims_include_project_and_hourly_cost_binding(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    project_id = "proj-alpha"
    token, approval, decision = await _issue_approved_token(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        project_id=project_id,
        idempotency_key="consume-claim-shape-1",
    )

    service = EnforcementService(db)
    payload = service._decode_approval_token(token)
    assert str(payload.get("token_type")) == "enforcement_approval"
    assert str(payload.get("project_id")) == project_id
    assert str(payload.get("max_monthly_delta_usd")) == str(
        decision.estimated_monthly_delta_usd
    )
    assert str(payload.get("max_hourly_delta_usd")) == str(
        decision.estimated_hourly_delta_usd
    )

    consumed_approval, consumed_decision = await service.consume_approval_token(
        tenant_id=tenant.id,
        approval_token=token,
        actor_id=actor_id,
        expected_project_id=project_id,
    )
    assert consumed_approval.id == approval.id
    assert consumed_decision.id == decision.id



@pytest.mark.asyncio
async def test_consume_approval_token_rejects_project_claim_mismatch(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    token, approval, _ = await _issue_approved_token(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        project_id="proj-bravo",
        idempotency_key="consume-project-mismatch-1",
    )
    service = EnforcementService(db)
    payload = dict(service._decode_approval_token(token))
    payload["project_id"] = "proj-evil"

    settings = enforcement_service_module.get_settings()
    secret = str(getattr(settings, "SUPABASE_JWT_SECRET", "") or "").strip()
    tampered_token = enforcement_service_module.jwt.encode(
        payload,
        secret,
        algorithm="HS256",
    )
    approval.approval_token_hash = enforcement_service_module.hashlib.sha256(
        tampered_token.encode("utf-8")
    ).hexdigest()
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await service.consume_approval_token(
            tenant_id=tenant.id,
            approval_token=tampered_token,
            actor_id=actor_id,
        )
    assert exc.value.status_code == 409
    assert "project binding mismatch" in str(exc.value.detail).lower()



@pytest.mark.asyncio
async def test_consume_approval_token_rejects_hourly_cost_claim_mismatch(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    token, approval, _ = await _issue_approved_token(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        idempotency_key="consume-hourly-mismatch-1",
    )
    service = EnforcementService(db)
    payload = dict(service._decode_approval_token(token))
    payload["max_hourly_delta_usd"] = "999.999999"

    settings = enforcement_service_module.get_settings()
    secret = str(getattr(settings, "SUPABASE_JWT_SECRET", "") or "").strip()
    tampered_token = enforcement_service_module.jwt.encode(
        payload,
        secret,
        algorithm="HS256",
    )
    approval.approval_token_hash = enforcement_service_module.hashlib.sha256(
        tampered_token.encode("utf-8")
    ).hexdigest()
    await db.commit()

    with pytest.raises(HTTPException) as exc:
        await service.consume_approval_token(
            tenant_id=tenant.id,
            approval_token=tampered_token,
            actor_id=actor_id,
        )
    assert exc.value.status_code == 409
    assert "cost binding mismatch" in str(exc.value.detail).lower()



@pytest.mark.asyncio
async def test_consume_approval_token_concurrency_single_use(db, async_engine) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    token, _, _ = await _issue_approved_token(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        idempotency_key="consume-concurrency-1",
    )

    session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def consume_once() -> int:
        async with session_maker() as session:
            service = EnforcementService(session)
            try:
                await service.consume_approval_token(
                    tenant_id=tenant.id,
                    approval_token=token,
                    actor_id=actor_id,
                )
                return 200
            except HTTPException as exc:
                return exc.status_code

    statuses = await asyncio.gather(*[consume_once() for _ in range(6)])
    assert statuses.count(200) == 1
    assert statuses.count(409) == 5



@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("mode", "expected_decision", "expected_reason", "expect_approval"),
    [
        (
            EnforcementMode.SHADOW,
            EnforcementDecisionType.ALLOW,
            "shadow_mode_fail_open",
            False,
        ),
        (
            EnforcementMode.SOFT,
            EnforcementDecisionType.REQUIRE_APPROVAL,
            "soft_mode_fail_safe_escalation",
            True,
        ),
        (
            EnforcementMode.HARD,
            EnforcementDecisionType.DENY,
            "hard_mode_fail_closed",
            False,
        ),
    ],
)
async def test_resolve_fail_safe_gate_timeout_mode_behavior(
    db,
    mode: EnforcementMode,
    expected_decision: EnforcementDecisionType,
    expected_reason: str,
    expect_approval: bool,
) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    service = EnforcementService(db)

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=mode,
        k8s_admission_mode=mode,
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
            estimated_monthly_delta_usd=Decimal("100"),
            estimated_hourly_delta_usd=Decimal("0.1"),
            metadata={"resource_type": "aws_eks_cluster"},
            idempotency_key=f"failsafe-timeout-{mode.value}",
        ),
        failure_reason_code="gate_timeout",
        failure_metadata={"timeout_seconds": "0.01"},
    )

    assert result.decision.decision == expected_decision
    assert "gate_timeout" in (result.decision.reason_codes or [])
    assert expected_reason in (result.decision.reason_codes or [])
    assert result.decision.reservation_active is False
    assert result.decision.reserved_allocation_usd == Decimal("0")
    assert result.decision.reserved_credit_usd == Decimal("0")
    assert (result.approval is not None) is expect_approval



@pytest.mark.asyncio
async def test_resolve_fail_safe_gate_idempotency_reuses_existing_decision(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    service = EnforcementService(db)

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

    gate_input = GateInput(
        project_id="default",
        environment="prod",
        action="terraform.apply",
        resource_reference="module.rds.aws_db_instance.main",
        estimated_monthly_delta_usd=Decimal("80"),
        estimated_hourly_delta_usd=Decimal("0.09"),
        metadata={"resource_type": "aws_db_instance"},
        idempotency_key="failsafe-idem-1",
    )

    first = await service.resolve_fail_safe_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=gate_input,
        failure_reason_code="gate_timeout",
        failure_metadata={"timeout_seconds": "0.01"},
    )
    second = await service.resolve_fail_safe_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=gate_input,
        failure_reason_code="gate_timeout",
        failure_metadata={"timeout_seconds": "0.01"},
    )

    assert first.decision.id == second.decision.id
    count = (
        await db.execute(
            select(func.count())
            .select_from(EnforcementDecision)
            .where(EnforcementDecision.tenant_id == tenant.id)
        )
    ).scalar_one()
    assert count == 1



@pytest.mark.asyncio
async def test_resolve_fail_safe_gate_blank_reason_dry_run_and_metadata_branches(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()
    service = EnforcementService(db)

    await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
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
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.ec2.aws_instance.failsafe-dryrun",
            estimated_monthly_delta_usd=Decimal("42"),
            estimated_hourly_delta_usd=Decimal("0.05"),
            metadata={"resource_type": "aws_instance", "risk_level": "manual"},
            idempotency_key="failsafe-blank-reason-dryrun-1",
            dry_run=True,
        ),
        failure_reason_code="   ",
        failure_metadata=None,
    )

    assert result.decision.decision == EnforcementDecisionType.REQUIRE_APPROVAL
    assert result.approval is None  # dry_run suppresses approval row creation
    assert "gate_evaluation_error" in (result.decision.reason_codes or [])
    assert "soft_mode_fail_safe_escalation" in (result.decision.reason_codes or [])
    assert "dry_run" in (result.decision.reason_codes or [])

    response_payload = result.decision.response_payload or {}
    request_payload = result.decision.request_payload or {}
    metadata_payload = (request_payload.get("metadata") or {})
    assert response_payload.get("fail_safe_trigger") == "gate_evaluation_error"
    assert response_payload.get("fail_safe_details") is None
    assert metadata_payload.get("risk_level") == "manual"  # preserve caller-provided risk level
    assert metadata_payload.get("computed_risk_class") == result.decision.risk_class
    assert metadata_payload.get("computed_risk_score") == result.decision.risk_score
