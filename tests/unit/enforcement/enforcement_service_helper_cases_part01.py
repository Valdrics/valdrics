# ruff: noqa: F403,F405
from tests.unit.enforcement.enforcement_service_helper_cases_common import *  # noqa: F401,F403



def test_datetime_and_numeric_helpers_cover_edge_cases() -> None:
    now = enforcement_service_module._utcnow()
    assert now.tzinfo is timezone.utc

    naive = datetime(2026, 2, 1, 12, 0, 0)
    aware = datetime(2026, 2, 1, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))

    assert enforcement_service_module._as_utc(naive).tzinfo is timezone.utc
    assert enforcement_service_module._as_utc(aware).hour == 12

    assert enforcement_service_module._parse_iso_datetime(aware) == enforcement_service_module._as_utc(aware)
    assert enforcement_service_module._parse_iso_datetime("2026-02-01T12:00:00Z") == datetime(
        2026, 2, 1, 12, 0, 0, tzinfo=timezone.utc
    )
    assert enforcement_service_module._parse_iso_datetime("invalid") is None
    assert enforcement_service_module._parse_iso_datetime(1234) is None

    assert enforcement_service_module._iso_or_empty(None) == ""
    assert enforcement_service_module._iso_or_empty(naive).endswith("+00:00")

    assert enforcement_service_module._to_decimal(Decimal("1.23")) == Decimal("1.23")
    assert enforcement_service_module._to_decimal("2.5") == Decimal("2.5")
    assert enforcement_service_module._to_decimal(None, default=Decimal("7")) == Decimal("7")
    assert enforcement_service_module._to_decimal("not-a-number", default=Decimal("9")) == Decimal("9")

    assert enforcement_service_module._quantize(Decimal("1.23456"), "0.0001") == Decimal("1.2346")



def test_string_hash_and_json_helpers_cover_edge_cases() -> None:
    assert enforcement_service_module._normalize_environment("production") == "prod"
    assert enforcement_service_module._normalize_environment("staging") == "nonprod"
    assert enforcement_service_module._normalize_environment(" ") == "nonprod"
    assert enforcement_service_module._is_production_environment("live") is True
    assert enforcement_service_module._is_production_environment("dev") is False

    normalized = enforcement_service_module._normalize_string_list(
        [" Prod ", "prod", "stage", "  "],
        normalizer=enforcement_service_module._normalize_environment,
    )
    assert normalized == ["prod", "nonprod"]

    assert enforcement_service_module._normalize_allowed_reviewer_roles(None) == [
        "owner",
        "admin",
    ]
    assert enforcement_service_module._normalize_allowed_reviewer_roles(
        ["owner", "OWNER", "member", "invalid"]
    ) == ["owner", "member"]
    assert enforcement_service_module._normalize_allowed_reviewer_roles(["invalid"]) == [
        "owner",
        "admin",
    ]

    assert (
        enforcement_service_module._default_required_permission_for_environment("prod")
        == APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD
    )
    assert (
        enforcement_service_module._default_required_permission_for_environment("dev")
        == APPROVAL_PERMISSION_REMEDIATION_APPROVE_NONPROD
    )

    payload_a = {"b": Decimal("1.20"), "a": datetime(2026, 2, 1, tzinfo=timezone.utc)}
    payload_b = {"a": datetime(2026, 2, 1, tzinfo=timezone.utc), "b": Decimal("1.20")}
    assert enforcement_service_module._payload_sha256(payload_a) == enforcement_service_module._payload_sha256(payload_b)

    assert enforcement_service_module._sanitize_csv_cell(None) == ""
    assert enforcement_service_module._sanitize_csv_cell("=SUM(1,2)") == "'=SUM(1,2)"
    assert enforcement_service_module._sanitize_csv_cell("-100") == "'-100"
    assert enforcement_service_module._sanitize_csv_cell("line1\nline2") == "line1 line2"

    unique = enforcement_service_module._unique_reason_codes([
        " budget_exceeded ",
        "BUDGET_EXCEEDED",
        "",
        "shadow_mode_budget_override",
    ])
    assert unique == ["budget_exceeded", "shadow_mode_budget_override"]

    assert enforcement_service_module._json_default(Decimal("1.23")) == "1.23"
    now = datetime.now(timezone.utc)
    assert enforcement_service_module._json_default(now) == now.isoformat()
    with pytest.raises(TypeError):
        enforcement_service_module._json_default(object())



def test_computed_context_snapshot_int_parsing_edge_cases() -> None:
    snapshot = enforcement_service_module._computed_context_snapshot(
        {
            "computed_context": {
                "context_version": " v1 ",
                "generated_at": "2026-02-26T00:00:00Z",
                "month_start": "2026-02-01",
                "month_end": "2026-02-29",
                "month_elapsed_days": None,  # line 480 path
                "month_total_days": True,  # line 482 path
                "observed_cost_days": object(),  # line 484 path
                "latest_cost_date": "2026-02-25",
                "data_source_mode": "actual",
            }
        }
    )
    assert snapshot["month_elapsed_days"] == 0
    assert snapshot["month_total_days"] == 1
    assert snapshot["observed_cost_days"] == 0
    assert snapshot["context_version"] == "v1"

    invalid_numeric = enforcement_service_module._computed_context_snapshot(
        {
            "computed_context": {
                "month_elapsed_days": "not-an-int",  # line 487/488 path
                "month_total_days": Decimal("30"),
                "observed_cost_days": 12.9,
            }
        }
    )
    assert invalid_numeric["month_elapsed_days"] == 0
    assert invalid_numeric["month_total_days"] == 30
    assert invalid_numeric["observed_cost_days"] == 12

    non_mapping = enforcement_service_module._computed_context_snapshot(
        {"computed_context": ["unexpected"]}
    )
    assert non_mapping["month_elapsed_days"] == 0
    assert non_mapping["month_total_days"] == 0



@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("overrides", "detail_substring"),
    [
        ({"hard_deny_above_monthly_usd": Decimal("0")}, "greater than 0"),
        ({"auto_approve_below_monthly_usd": Decimal("-1")}, "greater than or equal to 0"),
        (
            {
                "auto_approve_below_monthly_usd": Decimal("101"),
                "hard_deny_above_monthly_usd": Decimal("100"),
            },
            "cannot exceed",
        ),
        (
            {"plan_monthly_ceiling_usd": Decimal("-1")},
            "greater than or equal to 0",
        ),
        (
            {"enterprise_monthly_ceiling_usd": Decimal("-1")},
            "greater than or equal to 0",
        ),
    ],
)
async def test_update_policy_rejects_invalid_thresholds(db, overrides, detail_substring: str) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)
    kwargs = _base_policy_update_kwargs(tenant_id=tenant.id)
    kwargs.update(overrides)

    with pytest.raises((HTTPException, ValidationError)) as exc:
        await service.update_policy(**kwargs)

    if isinstance(exc.value, HTTPException):
        assert exc.value.status_code == 422
        rendered = str(exc.value.detail)
    else:
        rendered = str(exc.value)
    assert detail_substring in rendered



@pytest.mark.asyncio
async def test_update_policy_normalizes_values_and_increments_version(db) -> None:
    tenant = await _seed_tenant(db)
    service = EnforcementService(db)

    kwargs = _base_policy_update_kwargs(tenant_id=tenant.id)
    kwargs.update(
        {
            "terraform_mode": EnforcementMode.HARD,
            "terraform_mode_prod": None,
            "terraform_mode_nonprod": EnforcementMode.SHADOW,
            "k8s_admission_mode": EnforcementMode.SOFT,
            "k8s_admission_mode_prod": None,
            "k8s_admission_mode_nonprod": EnforcementMode.HARD,
            "default_ttl_seconds": 999999,
            "approval_routing_rules": [
                {
                    "rule_id": "finance-prod",
                    "environments": ["production", "Prod"],
                    "action_prefixes": ["terraform.", "terraform."],
                    "min_monthly_delta_usd": "10",
                    "max_monthly_delta_usd": "250",
                    "risk_levels": ["HIGH", "high"],
                    "allowed_reviewer_roles": ["owner", "member", "owner"],
                    "required_permission": APPROVAL_PERMISSION_REMEDIATION_APPROVE_PROD,
                    "require_requester_reviewer_separation": True,
                }
            ],
        }
    )
    policy = await service.update_policy(**kwargs)

    assert policy.terraform_mode == EnforcementMode.HARD
    assert policy.terraform_mode_prod == EnforcementMode.HARD
    assert policy.terraform_mode_nonprod == EnforcementMode.SHADOW
    assert policy.k8s_admission_mode_nonprod == EnforcementMode.HARD
    assert policy.default_ttl_seconds == 86400
    assert policy.policy_version == 2

    rules = policy.approval_routing_rules
    assert isinstance(rules, list)
    assert rules[0]["environments"] == ["prod"]
    assert rules[0]["action_prefixes"] == ["terraform."]
    assert rules[0]["risk_levels"] == ["high"]
    assert rules[0]["allowed_reviewer_roles"] == ["owner", "member"]



def test_normalize_policy_approval_routing_rules_rejects_invalid_inputs() -> None:
    service = _service()

    with pytest.raises(HTTPException, match="cannot exceed 64 rules"):
        service._normalize_policy_approval_routing_rules([{"rule_id": f"r{i}"} for i in range(65)])

    invalid_cases = [
        (["not-object"], "must be an object"),
        ([{}], "rule_id is required"),
        ([{"rule_id": "x" * 65}], "exceeds 64 chars"),
        ([{"rule_id": "dup"}, {"rule_id": "DUP"}], "Duplicate approval routing"),
        ([{"rule_id": "r1", "min_monthly_delta_usd": "-1"}], "min_monthly_delta_usd must be >= 0"),
        ([{"rule_id": "r1", "max_monthly_delta_usd": "-1"}], "max_monthly_delta_usd must be >= 0"),
        (
            [
                {
                    "rule_id": "r1",
                    "min_monthly_delta_usd": "10",
                    "max_monthly_delta_usd": "5",
                }
            ],
            "cannot exceed max_monthly_delta_usd",
        ),
        (
            [{"rule_id": "r1", "required_permission": "invalid"}],
            "required_permission must be one of",
        ),
        (
            [{"rule_id": "r1", "require_requester_reviewer_separation": "yes"}],
            "must be a boolean",
        ),
    ]

    for rules, expected in invalid_cases:
        with pytest.raises(HTTPException) as exc:
            service._normalize_policy_approval_routing_rules(rules)
        assert expected in str(exc.value.detail)



def test_resolve_policy_mode_covers_source_and_environment_paths() -> None:
    service = _service()
    tenant_id = uuid4()
    policy = EnforcementPolicy(
        tenant_id=tenant_id,
        terraform_mode=EnforcementMode.SOFT,
        terraform_mode_prod=EnforcementMode.HARD,
        terraform_mode_nonprod=EnforcementMode.SHADOW,
        k8s_admission_mode=EnforcementMode.SHADOW,
        k8s_admission_mode_prod=EnforcementMode.SOFT,
        k8s_admission_mode_nonprod=EnforcementMode.HARD,
    )

    mode, trace = service._resolve_policy_mode(
        policy=policy,
        source=EnforcementSource.TERRAFORM,
        environment="prod",
    )
    assert (mode, trace) == (EnforcementMode.HARD, "terraform:prod")

    mode, trace = service._resolve_policy_mode(
        policy=policy,
        source=EnforcementSource.TERRAFORM,
        environment="staging",
    )
    assert (mode, trace) == (EnforcementMode.SHADOW, "terraform:nonprod")

    mode, trace = service._resolve_policy_mode(
        policy=policy,
        source=EnforcementSource.TERRAFORM,
        environment="custom",
    )
    assert (mode, trace) == (EnforcementMode.SOFT, "terraform:default")

    mode, trace = service._resolve_policy_mode(
        policy=policy,
        source=EnforcementSource.K8S_ADMISSION,
        environment="prod",
    )
    assert (mode, trace) == (EnforcementMode.SOFT, "k8s_admission:prod")

    mode, trace = service._resolve_policy_mode(
        policy=policy,
        source=EnforcementSource.K8S_ADMISSION,
        environment="dev",
    )
    assert (mode, trace) == (EnforcementMode.HARD, "k8s_admission:nonprod")

    mode, trace = service._resolve_policy_mode(
        policy=policy,
        source=EnforcementSource.K8S_ADMISSION,
        environment="qa-custom",
    )
    assert (mode, trace) == (EnforcementMode.SHADOW, "k8s_admission:default")

    mode, trace = service._resolve_policy_mode(
        policy=policy,
        source=EnforcementSource.CLOUD_EVENT,
        environment="prod",
    )
    assert (mode, trace) == (EnforcementMode.SHADOW, "fallback:k8s_admission_default")



def test_materialize_policy_contract_rejects_invalid_policy_document_and_threshold_edges() -> None:
    service = _service()

    def _kwargs() -> dict[str, object]:
        return {
            "terraform_mode": EnforcementMode.SOFT,
            "terraform_mode_prod": None,
            "terraform_mode_nonprod": None,
            "k8s_admission_mode": EnforcementMode.SOFT,
            "k8s_admission_mode_prod": None,
            "k8s_admission_mode_nonprod": None,
            "require_approval_for_prod": False,
            "require_approval_for_nonprod": False,
            "plan_monthly_ceiling_usd": None,
            "enterprise_monthly_ceiling_usd": None,
            "auto_approve_below_monthly_usd": Decimal("10"),
            "hard_deny_above_monthly_usd": Decimal("100"),
            "default_ttl_seconds": 900,
            "enforce_prod_requester_reviewer_separation": True,
            "enforce_nonprod_requester_reviewer_separation": False,
            "approval_routing_rules": [],
            "policy_document": None,
        }

    with pytest.raises(HTTPException) as invalid_doc_exc:
        service._materialize_policy_contract(
            **{
                **_kwargs(),
                "policy_document": {"schema_version": "invalid-only"},
            }
        )
    assert invalid_doc_exc.value.status_code == 422
    assert invalid_doc_exc.value.detail["message"] == "policy_document is invalid"
    assert invalid_doc_exc.value.detail["errors"]

    # Sub-quantum positive hard deny passes pydantic `gt=0` but quantizes to 0.0000,
    # exercising the helper's post-quantization safety check (service.py line 812).
    with pytest.raises(HTTPException) as hard_deny_exc:
        service._materialize_policy_contract(
            **{
                **_kwargs(),
                "hard_deny_above_monthly_usd": Decimal("0.00004"),
            }
        )
    assert hard_deny_exc.value.status_code == 422
    assert "hard_deny_above_monthly_usd must be greater than 0" in str(
        hard_deny_exc.value.detail
    )

    # These negative values are rejected earlier by PolicyDocumentEntitlementMatrix
    # field constraints (pydantic), so the helper's redundant defensive checks do
    # not execute in the normal code path.
    prevalidated_cases = [
        {"auto_approve_below_monthly_usd": Decimal("-0.0001")},
        {"plan_monthly_ceiling_usd": Decimal("-1")},
        {"enterprise_monthly_ceiling_usd": Decimal("-1")},
    ]
    for overrides in prevalidated_cases:
        with pytest.raises(ValidationError):
            service._materialize_policy_contract(**{**_kwargs(), **overrides})



def test_policy_entitlement_matrix_prevalidates_negative_thresholds() -> None:
    # service.py defensive guards at lines 817/844/849 should remain unreachable
    # in normal flow because entitlement model validation fails earlier.
    with pytest.raises(ValidationError):
        enforcement_service_module.PolicyDocumentEntitlementMatrix(
            auto_approve_below_monthly_usd=Decimal("-0.0001"),
            hard_deny_above_monthly_usd=Decimal("1"),
        )

    with pytest.raises(ValidationError):
        enforcement_service_module.PolicyDocumentEntitlementMatrix(
            plan_monthly_ceiling_usd=Decimal("-1"),
            hard_deny_above_monthly_usd=Decimal("1"),
        )

    with pytest.raises(ValidationError):
        enforcement_service_module.PolicyDocumentEntitlementMatrix(
            enterprise_monthly_ceiling_usd=Decimal("-1"),
            hard_deny_above_monthly_usd=Decimal("1"),
        )



def test_materialize_policy_contract_defensive_threshold_guards_on_quantize_regression(
    monkeypatch,
) -> None:
    service = _service()

    base_kwargs: dict[str, object] = {
        "terraform_mode": EnforcementMode.SOFT,
        "terraform_mode_prod": None,
        "terraform_mode_nonprod": None,
        "k8s_admission_mode": EnforcementMode.SOFT,
        "k8s_admission_mode_prod": None,
        "k8s_admission_mode_nonprod": None,
        "require_approval_for_prod": False,
        "require_approval_for_nonprod": False,
        "plan_monthly_ceiling_usd": None,
        "enterprise_monthly_ceiling_usd": None,
        "auto_approve_below_monthly_usd": Decimal("10"),
        "hard_deny_above_monthly_usd": Decimal("100"),
        "default_ttl_seconds": 900,
        "enforce_prod_requester_reviewer_separation": True,
        "enforce_nonprod_requester_reviewer_separation": False,
        "approval_routing_rules": [],
        "policy_document": None,
    }
    original_quantize = enforcement_service_module._quantize

    def _run_case(
        *,
        trigger_value: Decimal,
        expected_detail: str,
        overrides: dict[str, object] | None = None,
    ) -> None:
        def _regressive_quantize(value: Decimal, quantum: str) -> Decimal:
            decimal_value = enforcement_service_module._to_decimal(value)
            if quantum == "0.0001" and decimal_value == trigger_value:
                return Decimal("-0.0001")
            return original_quantize(value, quantum)

        monkeypatch.setattr(
            enforcement_service_module,
            "_quantize",
            _regressive_quantize,
        )
        kwargs = dict(base_kwargs)
        if overrides:
            kwargs.update(overrides)
        with pytest.raises(HTTPException, match=expected_detail):
            service._materialize_policy_contract(**kwargs)

    # Explicitly execute redundant defensive guards that are unreachable in
    # normal flow because the entitlement model prevalidates these fields.
    _run_case(
        trigger_value=Decimal("10"),
        expected_detail="auto_approve_below_monthly_usd must be >= 0",
    )
    _run_case(
        trigger_value=Decimal("50"),
        expected_detail="plan_monthly_ceiling_usd must be >= 0 when provided",
        overrides={"plan_monthly_ceiling_usd": Decimal("50")},
    )
    _run_case(
        trigger_value=Decimal("500"),
        expected_detail="enterprise_monthly_ceiling_usd must be >= 0 when provided",
        overrides={"enterprise_monthly_ceiling_usd": Decimal("500")},
    )
