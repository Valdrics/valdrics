from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.generate_finance_committee_packet_assumptions as finance_assumptions_generator
from scripts.finance_committee_packet_assumptions_engine import (
    derive_assumptions_inputs,
)
from scripts.finance_committee_packet_common import TRACKED_TIERS
from scripts.generate_finance_committee_packet_assumptions import main


def _telemetry_payload() -> dict[str, object]:
    pricing_reference = {
        "free": {"monthly_price_usd": 0.0, "annual_monthly_factor": 1.0},
        "starter": {"monthly_price_usd": 49.0, "annual_monthly_factor": 0.84},
        "growth": {"monthly_price_usd": 149.0, "annual_monthly_factor": 0.83},
        "pro": {"monthly_price_usd": 299.0, "annual_monthly_factor": 0.82},
        "enterprise": {"monthly_price_usd": 799.0, "annual_monthly_factor": 0.81},
    }
    tier_subscription_snapshot = []
    tier_llm_usage = []
    for index, tier in enumerate(TRACKED_TIERS):
        tier_subscription_snapshot.append(
            {
                "tier": tier,
                "active_subscriptions": 20 + (index * 10),
                "dunning_events": index,
            }
        )
        tier_llm_usage.append(
            {
                "tier": tier,
                "total_cost_usd": 100.0 + (index * 25.0),
                "tenant_monthly_cost_percentiles_usd": {
                    "p50": 1.0 + index,
                    "p95": 3.0 + index,
                    "p99": 5.0 + index,
                },
            }
        )
    return {
        "pricing_reference": pricing_reference,
        "tier_subscription_snapshot": tier_subscription_snapshot,
        "tier_llm_usage": tier_llm_usage,
        "window": {"label": "2026-03"},
        "free_tier_margin_watch": {
            "free_total_tenants": 100,
            "free_active_subscriptions": 20,
            "free_total_llm_cost_usd": 100.0,
            "free_p95_tenant_monthly_cost_usd": 5.0,
            "starter_gross_mrr_usd": 1000.0,
            "free_llm_cost_pct_of_starter_gross_mrr": 10.0,
            "max_allowed_pct_of_starter_gross_mrr": 100.0,
        },
    }


def test_derive_assumptions_inputs_emits_expected_shape() -> None:
    payload = derive_assumptions_inputs(telemetry=_telemetry_payload())

    assert payload["source_window_label"] == "2026-03"
    assert payload["thresholds"]["required_consecutive_margin_closes"] == 2
    assert set(payload["annual_mix_by_tier"]) == set(TRACKED_TIERS)
    assert set(payload["infra_cogs_percent_of_effective_mrr_by_tier"]) == set(TRACKED_TIERS)
    assert set(payload["support_cogs_per_active_subscription_usd_by_tier"]) == set(TRACKED_TIERS)
    assert len(payload["scenario_models"]["price_sensitivity"]) == 3


def test_derive_assumptions_inputs_rejects_invalid_subscription_rows() -> None:
    telemetry = _telemetry_payload()
    telemetry["tier_subscription_snapshot"] = ["invalid-row"]
    with pytest.raises(
        ValueError,
        match=r"telemetry\.tier_subscription_snapshot\[0\] must be an object",
    ):
        derive_assumptions_inputs(telemetry=telemetry)


def test_derive_assumptions_inputs_rejects_duplicate_tier_rows() -> None:
    telemetry = _telemetry_payload()
    first_row = dict(telemetry["tier_subscription_snapshot"][0])
    telemetry["tier_subscription_snapshot"] = [
        *telemetry["tier_subscription_snapshot"],
        first_row,
    ]
    with pytest.raises(ValueError, match="duplicate tier: starter"):
        derive_assumptions_inputs(telemetry=telemetry)


def test_generate_finance_committee_packet_assumptions_rejects_input_output_collision(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match="telemetry_path and output must be different files"):
        main(
            [
                "--output",
                str(telemetry),
                "--telemetry-path",
                str(telemetry),
            ]
        )


@pytest.mark.parametrize(
    "relative_output",
    [
        "scripts/verify_finance_telemetry_snapshot.py",
        "scripts/generate_finance_telemetry_snapshot.py",
        "docs/ops/evidence/finance_committee_packet_assumptions_TEMPLATE.json",
        "docs/ops/evidence/finance_telemetry_snapshot_TEMPLATE.json",
        "docs/ops/evidence/finance_telemetry_snapshot_2026-02-28.json",
        "docs/ops/evidence/pricing_benchmark_register_TEMPLATE.json",
        "docs/ops/key-rotation-drill-2026-02-27.md",
        "docs/ops/evidence/README.md",
    ],
)
def test_generate_finance_committee_packet_assumptions_rejects_protected_output_collisions(
    tmp_path: Path,
    relative_output: str,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[3]
    output = repo_root / relative_output

    with pytest.raises(ValueError, match="output must not overwrite finance assumptions"):
        main(
            [
                "--output",
                str(output),
                "--telemetry-path",
                str(telemetry),
            ]
        )


def test_generate_finance_committee_packet_assumptions_rejects_output_parent_file(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="output parent must be a directory path"):
        main(
            [
                "--output",
                str(blocked_parent / "finance_committee_packet_assumptions.json"),
                "--telemetry-path",
                str(telemetry),
            ]
        )


def test_generate_finance_committee_packet_assumptions_rejects_directory_output_path(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    output_dir = tmp_path / "assumptions-output"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    output_dir.mkdir()

    with pytest.raises(ValueError, match="output must be a file path"):
        main(
            [
                "--output",
                str(output_dir),
                "--telemetry-path",
                str(telemetry),
            ]
        )


def test_generate_finance_committee_packet_assumptions_rejects_directory_telemetry_path(
    tmp_path: Path,
) -> None:
    telemetry_dir = tmp_path / "telemetry-dir"
    telemetry_dir.mkdir()

    with pytest.raises(ValueError, match="Finance telemetry snapshot file must be a file"):
        main(
            [
                "--output",
                str(tmp_path / "finance_committee_packet_assumptions.json"),
                "--telemetry-path",
                str(telemetry_dir),
            ]
        )


def test_generate_finance_committee_packet_assumptions_rejects_relative_protected_output_from_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    protected_output = (
        repo_root / "docs" / "ops" / "evidence" / "finance_committee_packet_assumptions_TEMPLATE.json"
    )
    protected_output.parent.mkdir(parents=True, exist_ok=True)
    protected_output.write_text("{}", encoding="utf-8")
    telemetry = repo_root / "telemetry.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(finance_assumptions_generator, "_repo_root", lambda: repo_root)

    with pytest.raises(ValueError, match="output must not overwrite finance assumptions"):
        main(
            [
                "--output",
                "docs/ops/evidence/finance_committee_packet_assumptions_TEMPLATE.json",
                "--telemetry-path",
                "telemetry.json",
            ]
        )


def test_generate_finance_committee_packet_assumptions_resolves_relative_paths_from_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    telemetry = repo_root / "telemetry.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(finance_assumptions_generator, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(finance_assumptions_generator, "verify_snapshot", lambda **_: 0)

    assert (
        main(
            [
                "--output",
                "artifacts/finance_committee_packet_assumptions.json",
                "--telemetry-path",
                "telemetry.json",
            ]
        )
        == 0
    )
    assert (
        repo_root / "artifacts" / "finance_committee_packet_assumptions.json"
    ).exists()


def test_generate_finance_committee_packet_assumptions_rejects_relative_paths_that_escape_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    inputs_dir = repo_root / "inputs"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    telemetry = inputs_dir / "telemetry.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(finance_assumptions_generator, "_repo_root", lambda: repo_root)

    with pytest.raises(
        ValueError,
        match="telemetry_path must stay within repo root when relative",
    ):
        main(
            [
                "--output",
                "artifacts/finance_committee_packet_assumptions.json",
                "--telemetry-path",
                "../escape/finance_telemetry_snapshot.json",
            ]
        )


def test_generate_finance_committee_packet_assumptions_does_not_leave_output_when_promotion_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    output = tmp_path / "artifacts" / "finance_committee_packet_assumptions.json"
    path_type = type(output)
    original_replace = path_type.replace

    def _failing_replace(self: Path, target: Path) -> Path:
        if self.parent == output.parent and Path(target) == output:
            raise OSError("simulated promotion failure")
        return original_replace(self, target)

    monkeypatch.setattr(path_type, "replace", _failing_replace)
    monkeypatch.setattr(finance_assumptions_generator, "verify_snapshot", lambda **_: 0)

    with pytest.raises(OSError, match="simulated promotion failure"):
        main(
            [
                "--output",
                str(output),
                "--telemetry-path",
                str(telemetry),
            ]
        )

    assert not output.exists()
    assert not list(output.parent.glob(f".{output.stem}.*{output.suffix}.tmp"))
