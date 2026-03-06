# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_cases_common import *  # noqa: F401,F403



@pytest.mark.asyncio
async def test_build_export_bundle_reconciles_counts_and_is_deterministic(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()

    first_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="export-bundle-1",
    )
    second_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="prod",
        require_approval_for_prod=True,
        require_approval_for_nonprod=True,
        idempotency_key="export-bundle-2",
    )
    assert first_gate.approval is not None
    assert second_gate.approval is not None

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=1)
    window_end = now + timedelta(days=1)

    service = EnforcementService(db)
    first_bundle = await service.build_export_bundle(
        tenant_id=tenant.id,
        window_start=window_start,
        window_end=window_end,
        max_rows=1000,
    )
    second_bundle = await service.build_export_bundle(
        tenant_id=tenant.id,
        window_start=window_start,
        window_end=window_end,
        max_rows=1000,
    )

    assert first_bundle.decision_count_db == 2
    assert first_bundle.decision_count_exported == 2
    assert first_bundle.approval_count_db == 2
    assert first_bundle.approval_count_exported == 2
    assert first_bundle.parity_ok is True

    assert first_bundle.decisions_sha256 == second_bundle.decisions_sha256
    assert first_bundle.approvals_sha256 == second_bundle.approvals_sha256
    assert first_bundle.policy_lineage_sha256 == second_bundle.policy_lineage_sha256
    assert first_bundle.policy_lineage == second_bundle.policy_lineage
    assert (
        first_bundle.computed_context_lineage_sha256
        == second_bundle.computed_context_lineage_sha256
    )
    assert first_bundle.computed_context_lineage == second_bundle.computed_context_lineage
    assert len(first_bundle.policy_lineage_sha256) == 64
    assert len(first_bundle.computed_context_lineage_sha256) == 64
    assert sum(int(item["decision_count"]) for item in first_bundle.policy_lineage) == 2
    assert (
        sum(int(item["decision_count"]) for item in first_bundle.computed_context_lineage)
        == 2
    )
    assert all(
        int(item["decision_count"]) >= 1
        and len(str(item["policy_document_sha256"])) == 64
        and str(item["policy_document_schema_version"]).strip()
        for item in first_bundle.policy_lineage
    )
    assert all(
        int(item["decision_count"]) >= 1
        and str(item["month_start"]).strip()
        and str(item["month_end"]).strip()
        and str(item["data_source_mode"]).strip()
        for item in first_bundle.computed_context_lineage
    )
    decision_rows = list(csv.DictReader(io.StringIO(first_bundle.decisions_csv)))
    assert len(decision_rows) == 2
    assert all(
        row["policy_document_schema_version"] == "valdrics.enforcement.policy.v1"
        and len(row["policy_document_sha256"]) == 64
        for row in decision_rows
    )
    assert all(
        row["computed_context_month_start"]
        and row["computed_context_month_end"]
        and row["computed_context_data_source_mode"]
        for row in decision_rows
    )

    first_manifest = service.build_signed_export_manifest(
        tenant_id=tenant.id,
        bundle=first_bundle,
    )
    second_manifest = service.build_signed_export_manifest(
        tenant_id=tenant.id,
        bundle=second_bundle,
    )
    assert first_manifest.content_sha256 == second_manifest.content_sha256
    assert first_manifest.signature == second_manifest.signature
    assert first_manifest.signature_algorithm == "hmac-sha256"
    assert first_manifest.policy_lineage_sha256 == first_bundle.policy_lineage_sha256
    assert first_manifest.policy_lineage == first_bundle.policy_lineage
    assert (
        first_manifest.computed_context_lineage_sha256
        == first_bundle.computed_context_lineage_sha256
    )
    assert first_manifest.computed_context_lineage == first_bundle.computed_context_lineage
    assert first_manifest.signature_key_id == second_manifest.signature_key_id
    assert first_manifest.to_payload()["manifest_content_sha256"] == first_manifest.content_sha256

    decision_reader = csv.reader(io.StringIO(first_bundle.decisions_csv))
    approval_reader = csv.reader(io.StringIO(first_bundle.approvals_csv))
    decision_rows = list(decision_reader)
    approval_rows = list(approval_reader)
    assert len(decision_rows) == first_bundle.decision_count_exported + 1
    assert len(approval_rows) == first_bundle.approval_count_exported + 1



@pytest.mark.asyncio
async def test_export_policy_lineage_remains_consistent_across_policy_updates(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    actor_id = uuid4()

    first_policy = await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        terraform_mode_prod=EnforcementMode.SOFT,
        terraform_mode_nonprod=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        k8s_admission_mode_prod=EnforcementMode.SOFT,
        k8s_admission_mode_nonprod=EnforcementMode.SOFT,
        require_approval_for_prod=False,
        require_approval_for_nonprod=False,
        plan_monthly_ceiling_usd=Decimal("1000"),
        enterprise_monthly_ceiling_usd=Decimal("2000"),
        auto_approve_below_monthly_usd=Decimal("25"),
        hard_deny_above_monthly_usd=Decimal("5000"),
        default_ttl_seconds=900,
    )

    first_hash = first_policy.policy_document_sha256
    first_version = int(first_policy.policy_version)
    assert len(first_hash) == 64

    first_decision = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.policy-hash-1",
            estimated_monthly_delta_usd=Decimal("30"),
            estimated_hourly_delta_usd=Decimal("0.04"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="policy-lineage-1",
        ),
    )

    assert first_decision.decision.policy_document_sha256 == first_hash
    assert int(first_decision.decision.policy_version) == first_version

    second_policy = await service.update_policy(
        tenant_id=tenant.id,
        terraform_mode=EnforcementMode.SOFT,
        terraform_mode_prod=EnforcementMode.SOFT,
        terraform_mode_nonprod=EnforcementMode.SOFT,
        k8s_admission_mode=EnforcementMode.SOFT,
        k8s_admission_mode_prod=EnforcementMode.SOFT,
        k8s_admission_mode_nonprod=EnforcementMode.SOFT,
        require_approval_for_prod=False,
        require_approval_for_nonprod=False,
        plan_monthly_ceiling_usd=Decimal("1"),
        enterprise_monthly_ceiling_usd=Decimal("2"),
        auto_approve_below_monthly_usd=Decimal("0"),
        hard_deny_above_monthly_usd=Decimal("10"),
        default_ttl_seconds=300,
        policy_document={
            "schema_version": POLICY_DOCUMENT_SCHEMA_VERSION,
            "mode_matrix": {
                "terraform_default": "hard",
                "terraform_prod": "hard",
                "terraform_nonprod": "shadow",
                "k8s_admission_default": "shadow",
                "k8s_admission_prod": "hard",
                "k8s_admission_nonprod": "soft",
            },
            "approval": {
                "require_approval_prod": True,
                "require_approval_nonprod": True,
                "enforce_prod_requester_reviewer_separation": True,
                "enforce_nonprod_requester_reviewer_separation": False,
                "routing_rules": [],
            },
            "entitlements": {
                "plan_monthly_ceiling_usd": "333.3",
                "enterprise_monthly_ceiling_usd": "444.4",
                "auto_approve_below_monthly_usd": "5",
                "hard_deny_above_monthly_usd": "900",
            },
            "execution": {"default_ttl_seconds": 1800},
        },
    )

    second_hash = second_policy.policy_document_sha256
    second_version = int(second_policy.policy_version)
    assert second_hash != first_hash
    assert second_version > first_version
    # Policy document remains the single source of truth even when scalar
    # arguments are provided in the same update call.
    assert second_policy.terraform_mode == EnforcementMode.HARD
    assert second_policy.k8s_admission_mode == EnforcementMode.SHADOW
    assert second_policy.plan_monthly_ceiling_usd == Decimal("333.3000")

    second_decision = await service.evaluate_gate(
        tenant_id=tenant.id,
        actor_id=actor_id,
        source=EnforcementSource.TERRAFORM,
        gate_input=GateInput(
            project_id="default",
            environment="nonprod",
            action="terraform.apply",
            resource_reference="module.app.aws_instance.policy-hash-2",
            estimated_monthly_delta_usd=Decimal("20"),
            estimated_hourly_delta_usd=Decimal("0.03"),
            metadata={"resource_type": "aws_instance"},
            idempotency_key="policy-lineage-2",
        ),
    )

    assert second_decision.decision.policy_document_sha256 == second_hash
    assert int(second_decision.decision.policy_version) == second_version

    now = datetime.now(timezone.utc)
    bundle = await service.build_export_bundle(
        tenant_id=tenant.id,
        window_start=now - timedelta(days=1),
        window_end=now + timedelta(days=1),
        max_rows=1000,
    )

    decision_rows = list(csv.DictReader(io.StringIO(bundle.decisions_csv)))
    row_by_id = {str(row["decision_id"]): row for row in decision_rows}
    assert row_by_id[str(first_decision.decision.id)]["policy_document_sha256"] == first_hash
    assert row_by_id[str(second_decision.decision.id)]["policy_document_sha256"] == second_hash
    assert int(row_by_id[str(first_decision.decision.id)]["policy_version"]) == first_version
    assert int(row_by_id[str(second_decision.decision.id)]["policy_version"]) == second_version

    lineage_counts = {
        str(item["policy_document_sha256"]): int(item["decision_count"])
        for item in bundle.policy_lineage
    }
    assert lineage_counts[first_hash] == 1
    assert lineage_counts[second_hash] == 1
    assert sum(lineage_counts.values()) == 2
    assert len(bundle.computed_context_lineage_sha256) == 64
    assert sum(
        int(item["decision_count"]) for item in bundle.computed_context_lineage
    ) == 2



@pytest.mark.asyncio
async def test_build_export_bundle_rejects_window_above_max_rows(db) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()

    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="export-bundle-limit-1",
    )
    assert gate.approval is not None

    now = datetime.now(timezone.utc)
    service = EnforcementService(db)
    with pytest.raises(HTTPException) as exc:
        await service.build_export_bundle(
            tenant_id=tenant.id,
            window_start=now - timedelta(days=1),
            window_end=now + timedelta(days=1),
            max_rows=0,
        )

    assert exc.value.status_code == 422
    assert "max_rows" in str(exc.value.detail).lower()



@pytest.mark.asyncio
async def test_build_export_bundle_rejects_max_rows_upper_bound_and_invalid_window(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    now = datetime.now(timezone.utc)

    with pytest.raises(HTTPException) as max_rows_exc:
        await service.build_export_bundle(
            tenant_id=tenant.id,
            window_start=now - timedelta(days=1),
            window_end=now + timedelta(days=1),
            max_rows=50001,
        )
    assert max_rows_exc.value.status_code == 422
    assert "max_rows must be <=" in str(max_rows_exc.value.detail)

    with pytest.raises(HTTPException) as window_exc:
        await service.build_export_bundle(
            tenant_id=tenant.id,
            window_start=now,
            window_end=now,
            max_rows=1000,
        )
    assert window_exc.value.status_code == 422
    assert "window_start must be before window_end" in str(window_exc.value.detail)



@pytest.mark.asyncio
async def test_build_export_bundle_rejects_when_decision_count_exceeds_max_rows(db, monkeypatch) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()

    first_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="export-bundle-count-limit-1",
    )
    second_gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="export-bundle-count-limit-2",
    )
    assert first_gate.approval is not None
    assert second_gate.approval is not None

    counter = _FakeCounter()
    monkeypatch.setattr(
        enforcement_service_runtime_ops_module,
        "ENFORCEMENT_EXPORT_EVENTS_TOTAL",
        counter,
    )

    now = datetime.now(timezone.utc)
    service = EnforcementService(db)
    with pytest.raises(HTTPException) as exc:
        await service.build_export_bundle(
            tenant_id=tenant.id,
            window_start=now - timedelta(days=1),
            window_end=now + timedelta(days=1),
            max_rows=1,
        )

    assert exc.value.status_code == 422
    assert "exceeds max_rows" in str(exc.value.detail)
    assert ("artifact", "bundle") in tuple(counter.calls[0][0].items())
    assert counter.calls[0][0]["artifact"] == "bundle"
    assert counter.calls[0][0]["outcome"] == "rejected_limit"



@pytest.mark.asyncio
async def test_build_export_bundle_empty_window_returns_empty_lineage_and_success_metric(
    db, monkeypatch
) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    counter = _FakeCounter()
    monkeypatch.setattr(
        enforcement_service_runtime_ops_module,
        "ENFORCEMENT_EXPORT_EVENTS_TOTAL",
        counter,
    )

    now = datetime.now(timezone.utc)
    bundle = await service.build_export_bundle(
        tenant_id=tenant.id,
        window_start=now - timedelta(days=1),
        window_end=now + timedelta(days=1),
        max_rows=1000,
    )

    assert bundle.decision_count_db == 0
    assert bundle.decision_count_exported == 0
    assert bundle.approval_count_db == 0
    assert bundle.approval_count_exported == 0
    assert bundle.policy_lineage == []
    assert bundle.computed_context_lineage == []
    assert bundle.parity_ok is True
    assert len(bundle.policy_lineage_sha256) == 64
    assert len(bundle.computed_context_lineage_sha256) == 64
    assert counter.calls[-1][0]["artifact"] == "bundle"
    assert counter.calls[-1][0]["outcome"] == "success"



@pytest.mark.asyncio
async def test_build_signed_export_manifest_requires_signing_secret(db, monkeypatch) -> None:
    tenant = await _seed_tenant(db)
    actor_id = uuid4()

    gate = await _issue_pending_approval(
        db=db,
        tenant_id=tenant.id,
        actor_id=actor_id,
        environment="nonprod",
        require_approval_for_prod=False,
        require_approval_for_nonprod=True,
        idempotency_key="export-signing-key-required-1",
    )
    assert gate.approval is not None

    now = datetime.now(timezone.utc)
    service = EnforcementService(db)
    bundle = await service.build_export_bundle(
        tenant_id=tenant.id,
        window_start=now - timedelta(days=1),
        window_end=now + timedelta(days=1),
        max_rows=1000,
    )

    monkeypatch.setattr(
        enforcement_service_module,
        "get_settings",
        lambda: SimpleNamespace(
            ENFORCEMENT_EXPORT_SIGNING_SECRET="",
            SUPABASE_JWT_SECRET="",
            ENFORCEMENT_EXPORT_SIGNING_KID="export-key-v1",
            JWT_SIGNING_KID="",
        ),
    )

    with pytest.raises(HTTPException) as exc:
        service.build_signed_export_manifest(
            tenant_id=tenant.id,
            bundle=bundle,
        )

    assert exc.value.status_code == 503
    assert "signing key" in str(exc.value.detail).lower()
