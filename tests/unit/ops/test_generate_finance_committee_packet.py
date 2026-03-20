from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_finance_committee_packet import main


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _telemetry_payload() -> dict[str, object]:
    return {
        "captured_at": "2026-02-28T12:00:00Z",
        "window": {
            "start": "2026-02-01T00:00:00Z",
            "end": "2026-02-27T23:59:59Z",
            "label": "2026-02",
        },
        "runtime": {
            "database_engine": "postgresql",
            "collector": "scripts/collect_finance_telemetry_snapshot.py",
        },
        "pricing_reference": {
            "free": {
                "monthly_price_usd": 0.0,
                "annual_price_usd": 0.0,
                "annual_monthly_factor": 0.0,
            },
            "starter": {
                "monthly_price_usd": 49.0,
                "annual_price_usd": 490.0,
                "annual_monthly_factor": 490.0 / (49.0 * 12.0),
            },
            "growth": {
                "monthly_price_usd": 149.0,
                "annual_price_usd": 1490.0,
                "annual_monthly_factor": 1490.0 / (149.0 * 12.0),
            },
            "pro": {
                "monthly_price_usd": 299.0,
                "annual_price_usd": 2990.0,
                "annual_monthly_factor": 2990.0 / (299.0 * 12.0),
            },
            "enterprise": {
                "monthly_price_usd": 799.0,
                "annual_price_usd": 7990.0,
                "annual_monthly_factor": 7990.0 / (799.0 * 12.0),
            },
        },
        "tier_subscription_snapshot": [
            {"tier": "free", "total_tenants": 220, "active_subscriptions": 180, "dunning_events": 0},
            {"tier": "starter", "total_tenants": 100, "active_subscriptions": 80, "dunning_events": 6},
            {"tier": "growth", "total_tenants": 70, "active_subscriptions": 50, "dunning_events": 5},
            {"tier": "pro", "total_tenants": 40, "active_subscriptions": 30, "dunning_events": 2},
            {"tier": "enterprise", "total_tenants": 20, "active_subscriptions": 15, "dunning_events": 1},
        ],
        "tier_llm_usage": [
            {
                "tier": "free",
                "total_cost_usd": 260.0,
                "tenant_monthly_cost_percentiles_usd": {"p50": 1.3, "p95": 4.0, "p99": 6.2},
            },
            {
                "tier": "starter",
                "total_cost_usd": 1200.0,
                "tenant_monthly_cost_percentiles_usd": {"p50": 5.0, "p95": 16.0, "p99": 22.0},
            },
            {
                "tier": "growth",
                "total_cost_usd": 1600.0,
                "tenant_monthly_cost_percentiles_usd": {"p50": 8.0, "p95": 21.0, "p99": 31.0},
            },
            {
                "tier": "pro",
                "total_cost_usd": 2200.0,
                "tenant_monthly_cost_percentiles_usd": {"p50": 12.0, "p95": 32.0, "p99": 45.0},
            },
            {
                "tier": "enterprise",
                "total_cost_usd": 3200.0,
                "tenant_monthly_cost_percentiles_usd": {"p50": 18.0, "p95": 48.0, "p99": 70.0},
            },
        ],
        "free_tier_compute_guardrails": {
            "tier": "free",
            "reference_tier": "starter",
            "limits": [
                {
                    "limit_name": "llm_analyses_per_day",
                    "free_limit": 1,
                    "starter_limit": 5,
                    "free_le_starter": True,
                },
                {
                    "limit_name": "llm_analyses_per_user_per_day",
                    "free_limit": 1,
                    "starter_limit": 2,
                    "free_le_starter": True,
                },
            ],
            "bounded_against_starter": True,
        },
        "free_tier_margin_watch": {
            "free_total_tenants": 220,
            "free_active_subscriptions": 180,
            "free_total_llm_cost_usd": 260.0,
            "free_p95_tenant_monthly_cost_usd": 4.0,
            "starter_gross_mrr_usd": 3920.0,
            "free_llm_cost_pct_of_starter_gross_mrr": (260.0 / 3920.0) * 100.0,
            "max_allowed_pct_of_starter_gross_mrr": 100.0,
        },
        "gate_results": {
            "telemetry_gate_required_tiers_present": True,
            "telemetry_gate_window_valid": True,
            "telemetry_gate_percentiles_valid": True,
            "telemetry_gate_artifact_fresh": True,
            "telemetry_gate_free_tier_guardrails_bounded": True,
            "telemetry_gate_free_tier_margin_guarded": True,
        },
    }


def _assumptions_payload() -> dict[str, object]:
    return {
        "captured_at": "2026-02-28T12:05:00Z",
        "thresholds": {
            "min_blended_gross_margin_percent": 55.0,
            "max_p95_tenant_llm_cogs_pct_mrr": 40.0,
            "max_annual_discount_impact_percent": 20.0,
            "min_growth_to_pro_conversion_mom_delta_percent": 0.0,
            "min_pro_to_enterprise_conversion_mom_delta_percent": 0.0,
            "min_stress_margin_percent": 50.0,
            "required_consecutive_margin_closes": 2,
        },
        "annual_mix_by_tier": {
            "starter": 0.7,
            "growth": 0.7,
            "pro": 0.7,
            "enterprise": 0.5,
        },
        "infra_cogs_percent_of_effective_mrr_by_tier": {
            "starter": 7.0,
            "growth": 7.0,
            "pro": 6.0,
            "enterprise": 5.0,
        },
        "support_cogs_per_active_subscription_usd_by_tier": {
            "starter": 5.0,
            "growth": 8.0,
            "pro": 12.0,
            "enterprise": 20.0,
        },
        "support_cogs_per_dunning_event_usd": 10.0,
        "conversion_signals": {
            "growth_to_pro_conversion_mom_delta_percent": 0.2,
            "pro_to_enterprise_conversion_mom_delta_percent": 0.1,
        },
        "stress_scenario": {"infra_cost_multiplier": 2.0},
        "close_history": [
            {"month": "2026-01", "blended_gross_margin_percent": 78.0}
        ],
        "scenario_models": {
            "price_sensitivity": [
                {
                    "name": "baseline",
                    "subscription_multipliers_by_tier": {
                        "starter": 1.0,
                        "growth": 1.0,
                        "pro": 1.0,
                        "enterprise": 1.0,
                    },
                    "monthly_price_multipliers_by_tier": {
                        "starter": 1.0,
                        "growth": 1.0,
                        "pro": 1.0,
                        "enterprise": 1.0,
                    },
                }
            ]
        },
        "self_hosted_tco_inputs": {
            "annual_staffing_usd": 250000.0,
            "annual_oncall_usd": 50000.0,
            "annual_security_compliance_usd": 40000.0,
            "annual_infra_ops_usd": 60000.0,
            "annual_tooling_usd": 30000.0,
        },
    }


def test_generate_finance_committee_packet_emits_expected_outputs(tmp_path: Path) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    output_dir = tmp_path / "output"
    _write(telemetry, _telemetry_payload())
    _write(assumptions, _assumptions_payload())

    assert (
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                str(output_dir),
                "--require-all-gates-pass",
            ]
        )
        == 0
    )

    assert (output_dir / "finance_guardrails_2026-02.json").exists()
    assert (output_dir / "finance_committee_packet_2026-02.json").exists()
    assert (output_dir / "finance_committee_tier_unit_economics_2026-02.csv").exists()
    assert (output_dir / "finance_committee_scenarios_2026-02.csv").exists()


def test_generate_finance_committee_packet_returns_non_zero_when_gate_fails(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    output_dir = tmp_path / "output"
    payload = _assumptions_payload()
    payload["thresholds"]["min_blended_gross_margin_percent"] = 99.0
    _write(telemetry, _telemetry_payload())
    _write(assumptions, payload)

    assert (
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                str(output_dir),
                "--require-all-gates-pass",
            ]
        )
        == 2
    )


def test_generate_finance_committee_packet_rejects_duplicate_close_history_months(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    output_dir = tmp_path / "output"
    payload = _assumptions_payload()
    payload["close_history"] = [
        {"month": "2026-01", "blended_gross_margin_percent": 78.0},
        {"month": "2026-01", "blended_gross_margin_percent": 79.0},
    ]
    _write(telemetry, _telemetry_payload())
    _write(assumptions, payload)

    with pytest.raises(ValueError, match="duplicate month"):
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                str(output_dir),
            ]
        )


def test_generate_finance_committee_packet_sends_alert_when_gate_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    output_dir = tmp_path / "output"
    payload = _assumptions_payload()
    payload["thresholds"]["min_blended_gross_margin_percent"] = 99.0
    _write(telemetry, _telemetry_payload())
    _write(assumptions, payload)

    calls: list[str] = []

    class _Resp:
        status_code = 200

    def _mock_post(url: str, json: dict[str, object], timeout: float):  # type: ignore[override]
        del json, timeout
        calls.append(url)
        return _Resp()

    monkeypatch.setattr("scripts.generate_finance_committee_packet.httpx.post", _mock_post)

    exit_code = main(
        [
            "--telemetry-path",
            str(telemetry),
            "--assumptions-path",
            str(assumptions),
            "--output-dir",
            str(output_dir),
            "--alert-webhook-url",
            "https://alerts.example.test/hook",
        ]
    )
    assert exit_code == 0
    assert calls == ["https://alerts.example.test/hook"]


@pytest.mark.parametrize(
    ("input_kind", "reserved_name"),
    (
        ("telemetry", "finance_guardrails_2026-02.json"),
        ("assumptions", "finance_committee_packet_2026-02.json"),
    ),
)
def test_generate_finance_committee_packet_rejects_input_output_path_collisions(
    tmp_path: Path,
    input_kind: str,
    reserved_name: str,
) -> None:
    output_dir = tmp_path / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    telemetry = (
        output_dir / reserved_name
        if input_kind == "telemetry"
        else tmp_path / "telemetry.json"
    )
    assumptions = (
        output_dir / reserved_name
        if input_kind == "assumptions"
        else tmp_path / "assumptions.json"
    )
    _write(telemetry, _telemetry_payload())
    _write(assumptions, _assumptions_payload())

    with pytest.raises(ValueError, match="output_dir would overwrite"):
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                str(output_dir),
            ]
        )


def test_generate_finance_committee_packet_rejects_checked_in_guardrail_collisions(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    telemetry_payload = _telemetry_payload()
    telemetry_payload["window"]["label"] = "TEMPLATE"
    _write(telemetry, telemetry_payload)
    _write(assumptions, _assumptions_payload())

    repo_root = Path(__file__).resolve().parents[3]
    output_dir = repo_root / "docs" / "ops" / "evidence"

    with pytest.raises(ValueError, match="output_dir would overwrite checked-in finance evidence"):
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                str(output_dir),
            ]
        )


def test_generate_finance_committee_packet_rejects_relative_checked_in_guardrail_collisions_from_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(
        "scripts.generate_finance_committee_packet._repo_root",
        lambda: repo_root,
    )

    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    telemetry_payload = _telemetry_payload()
    telemetry_payload["window"]["label"] = "TEMPLATE"
    _write(telemetry, telemetry_payload)
    _write(assumptions, _assumptions_payload())

    with pytest.raises(ValueError, match="output_dir would overwrite checked-in finance evidence"):
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                "docs/ops/evidence",
            ]
        )


def test_generate_finance_committee_packet_resolves_relative_paths_from_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    inputs_dir = repo_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    telemetry = inputs_dir / "telemetry.json"
    assumptions = inputs_dir / "assumptions.json"
    _write(telemetry, _telemetry_payload())
    _write(assumptions, _assumptions_payload())
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(
        "scripts.generate_finance_committee_packet._repo_root",
        lambda: repo_root,
    )

    verify_snapshot_calls: list[dict[str, object]] = []
    verify_evidence_calls: list[dict[str, object]] = []

    def _fake_verify_snapshot(**kwargs: object) -> int:
        verify_snapshot_calls.append(kwargs)
        return 0

    def _fake_verify_evidence(**kwargs: object) -> int:
        verify_evidence_calls.append(kwargs)
        return 0

    monkeypatch.setattr(
        "scripts.generate_finance_committee_packet.verify_snapshot",
        _fake_verify_snapshot,
    )
    monkeypatch.setattr(
        "scripts.generate_finance_committee_packet.verify_evidence",
        _fake_verify_evidence,
    )

    assert (
        main(
            [
                "--telemetry-path",
                "inputs/telemetry.json",
                "--assumptions-path",
                "inputs/assumptions.json",
                "--output-dir",
                "artifacts",
            ]
        )
        == 0
    )

    output_dir = repo_root / "artifacts"
    guardrails_path = output_dir / "finance_guardrails_2026-02.json"
    committee_path = output_dir / "finance_committee_packet_2026-02.json"
    tiers_csv_path = output_dir / "finance_committee_tier_unit_economics_2026-02.csv"
    scenarios_csv_path = output_dir / "finance_committee_scenarios_2026-02.csv"
    assert guardrails_path.exists()
    assert committee_path.exists()
    assert tiers_csv_path.exists()
    assert scenarios_csv_path.exists()
    assert verify_snapshot_calls == [
        {
            "snapshot_path": telemetry,
            "max_artifact_age_hours": None,
        }
    ]
    assert len(verify_evidence_calls) == 1
    assert verify_evidence_calls[0]["allow_failed_gates"] is True
    assert verify_evidence_calls[0]["evidence_path"].name == guardrails_path.name
    assert verify_evidence_calls[0]["evidence_path"] != guardrails_path


def test_generate_finance_committee_packet_rejects_relative_paths_that_escape_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    inputs_dir = repo_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    assumptions = inputs_dir / "assumptions.json"
    _write(assumptions, _assumptions_payload())
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(
        "scripts.generate_finance_committee_packet._repo_root",
        lambda: repo_root,
    )

    with pytest.raises(
        ValueError,
        match="telemetry_path must stay within repo root when relative",
    ):
        main(
            [
                "--telemetry-path",
                "../escape/telemetry.json",
                "--assumptions-path",
                "inputs/assumptions.json",
                "--output-dir",
                "artifacts",
            ]
        )


def test_generate_finance_committee_packet_rejects_output_dir_parent_file(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")
    _write(telemetry, _telemetry_payload())
    _write(assumptions, _assumptions_payload())

    with pytest.raises(ValueError, match="output_dir parent must be a directory path"):
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                str(blocked_parent / "committee-output"),
            ]
        )


def test_generate_finance_committee_packet_does_not_leave_outputs_when_verification_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    output_dir = tmp_path / "output"
    _write(telemetry, _telemetry_payload())
    _write(assumptions, _assumptions_payload())

    monkeypatch.setattr(
        "scripts.generate_finance_committee_packet.verify_evidence",
        lambda **_: (_ for _ in ()).throw(ValueError("finance guardrails verification failed")),
    )

    with pytest.raises(ValueError, match="finance guardrails verification failed"):
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                str(output_dir),
            ]
        )

    assert not (output_dir / "finance_guardrails_2026-02.json").exists()
    assert not (output_dir / "finance_committee_packet_2026-02.json").exists()
    assert not (output_dir / "finance_committee_tier_unit_economics_2026-02.csv").exists()
    assert not (output_dir / "finance_committee_scenarios_2026-02.csv").exists()


def test_generate_finance_committee_packet_does_not_leave_outputs_when_alert_fail_on_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    output_dir = tmp_path / "output"
    payload = _assumptions_payload()
    payload["thresholds"]["min_blended_gross_margin_percent"] = 99.0
    _write(telemetry, _telemetry_payload())
    _write(assumptions, payload)

    monkeypatch.setattr(
        "scripts.generate_finance_committee_packet.httpx.post",
        lambda *_, **__: (_ for _ in ()).throw(RuntimeError("webhook failed")),
    )

    with pytest.raises(RuntimeError, match="failed to send finance alert webhook"):
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                str(output_dir),
                "--alert-webhook-url",
                "https://alerts.example.test/hook",
                "--alert-webhook-fail-on-error",
            ]
        )

    assert not (output_dir / "finance_guardrails_2026-02.json").exists()
    assert not (output_dir / "finance_committee_packet_2026-02.json").exists()
    assert not (output_dir / "finance_committee_tier_unit_economics_2026-02.csv").exists()
    assert not (output_dir / "finance_committee_scenarios_2026-02.csv").exists()


def test_generate_finance_committee_packet_does_not_leave_outputs_when_csv_staging_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    output_dir = tmp_path / "output"
    _write(telemetry, _telemetry_payload())
    _write(assumptions, _assumptions_payload())
    original_write_csv = __import__(
        "scripts.generate_finance_committee_packet",
        fromlist=["write_csv"],
    ).write_csv

    def _failing_write_csv(path: Path, rows: list[dict[str, object]]) -> None:
        if path.name == "finance_committee_scenarios_2026-02.csv":
            raise RuntimeError("scenario csv staging failed")
        original_write_csv(path, rows)

    monkeypatch.setattr(
        "scripts.generate_finance_committee_packet.write_csv",
        _failing_write_csv,
    )

    with pytest.raises(RuntimeError, match="scenario csv staging failed"):
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                str(output_dir),
            ]
        )

    assert not (output_dir / "finance_guardrails_2026-02.json").exists()
    assert not (output_dir / "finance_committee_packet_2026-02.json").exists()
    assert not (output_dir / "finance_committee_tier_unit_economics_2026-02.csv").exists()
    assert not (output_dir / "finance_committee_scenarios_2026-02.csv").exists()


def test_generate_finance_committee_packet_rejects_directory_assumptions_path(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions_dir = tmp_path / "assumptions-dir"
    output_dir = tmp_path / "output"
    assumptions_dir.mkdir()
    _write(telemetry, _telemetry_payload())

    with pytest.raises(ValueError, match="assumptions_path must be a file"):
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions_dir),
                "--output-dir",
                str(output_dir),
            ]
        )
    assert not output_dir.exists()


@pytest.mark.parametrize(
    ("arg_name", "arg_value", "expected_message"),
    [
        ("--max-telemetry-age-hours", "nan", "max_telemetry_age_hours must be finite"),
        ("--max-telemetry-age-hours", "-inf", "max_telemetry_age_hours must be finite"),
        ("--alert-webhook-timeout-seconds", "inf", "alert_webhook_timeout_seconds must be finite"),
        ("--alert-webhook-timeout-seconds", "0", "alert_webhook_timeout_seconds must be > 0"),
    ],
)
def test_generate_finance_committee_packet_rejects_invalid_float_args(
    tmp_path: Path,
    arg_name: str,
    arg_value: str,
    expected_message: str,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    assumptions = tmp_path / "assumptions.json"
    output_dir = tmp_path / "output"
    _write(telemetry, _telemetry_payload())
    _write(assumptions, _assumptions_payload())
    arg_tokens = (
        [f"{arg_name}={arg_value}"]
        if arg_value.startswith("-")
        else [arg_name, arg_value]
    )

    with pytest.raises(ValueError, match=expected_message):
        main(
            [
                "--telemetry-path",
                str(telemetry),
                "--assumptions-path",
                str(assumptions),
                "--output-dir",
                str(output_dir),
                *arg_tokens,
            ]
        )
