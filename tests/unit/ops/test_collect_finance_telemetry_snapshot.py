from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

import scripts.collect_finance_telemetry_snapshot as telemetry_collector
from scripts.collect_finance_telemetry_snapshot import (
    _build_snapshot_payload,
    _percentile,
    main,
)


def test_percentile_interpolation_is_deterministic() -> None:
    values = [1.0, 5.0, 9.0, 13.0]
    assert _percentile(values, 0.0) == 1.0
    assert _percentile(values, 50.0) == 7.0
    assert _percentile(values, 95.0) >= 12.0
    assert _percentile(values, 100.0) == 13.0


def test_build_snapshot_payload_populates_tier_revenue_and_gates() -> None:
    payload = _build_snapshot_payload(
        window_start=datetime(2026, 2, 1, tzinfo=timezone.utc),
        window_end_exclusive=datetime(2026, 3, 1, tzinfo=timezone.utc),
        label="2026-02",
        db_engine="postgresql",
        subscription_snapshot={
            "free": {"total_tenants": 200, "active_subscriptions": 160, "dunning_events": 0},
            "starter": {"total_tenants": 100, "active_subscriptions": 80, "dunning_events": 8},
            "growth": {"total_tenants": 80, "active_subscriptions": 60, "dunning_events": 5},
            "pro": {"total_tenants": 40, "active_subscriptions": 30, "dunning_events": 2},
            "enterprise": {"total_tenants": 20, "active_subscriptions": 15, "dunning_events": 1},
        },
        llm_snapshot={
            "free": {"total_cost_usd": 240.0, "p50": 1.2, "p95": 4.4, "p99": 7.2},
            "starter": {"total_cost_usd": 1100.0, "p50": 5.0, "p95": 12.0, "p99": 18.0},
            "growth": {"total_cost_usd": 1500.0, "p50": 8.0, "p95": 19.0, "p99": 26.0},
            "pro": {"total_cost_usd": 2300.0, "p50": 13.0, "p95": 32.0, "p99": 44.0},
            "enterprise": {"total_cost_usd": 3100.0, "p50": 20.0, "p95": 49.0, "p99": 66.0},
        },
    )

    assert payload["window"]["label"] == "2026-02"
    assert payload["runtime"]["database_engine"] == "postgresql"
    assert payload["gate_results"]["telemetry_gate_required_tiers_present"] is True
    assert payload["gate_results"]["telemetry_gate_free_tier_guardrails_bounded"] is True
    assert payload["gate_results"]["telemetry_gate_free_tier_margin_guarded"] is True
    assert payload["free_tier_compute_guardrails"]["tier"] == "free"
    assert payload["free_tier_compute_guardrails"]["bounded_against_starter"] is True
    assert payload["free_tier_margin_watch"]["free_active_subscriptions"] == 160

    revenues = {row["tier"]: row["gross_mrr_usd"] for row in payload["tier_revenue_inputs"]}
    assert revenues["free"] == 0.0
    assert revenues["starter"] > 0.0
    assert revenues["growth"] > revenues["starter"]


def test_main_resolves_relative_output_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(telemetry_collector.__file__).resolve().parents[1]
    output_path = repo_root / "tmp-finance-telemetry.json"
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        telemetry_collector,
        "_default_window",
        lambda: (datetime(2026, 2, 1, tzinfo=timezone.utc).date(), datetime(2026, 2, 28, tzinfo=timezone.utc).date()),
    )
    async def _fake_collect_snapshot(**kwargs):
        del kwargs
        return {
            "captured_at": "2026-02-28T00:00:00Z",
            "window": {"start": "2026-02-01T00:00:00Z", "end": "2026-03-01T00:00:00Z", "label": "2026-02"},
        }

    monkeypatch.setattr(telemetry_collector, "collect_snapshot", _fake_collect_snapshot)
    try:
        assert main(["--output", "tmp-finance-telemetry.json"]) == 0
        assert json.loads(output_path.read_text(encoding="utf-8"))["captured_at"] == "2026-02-28T00:00:00Z"
    finally:
        output_path.unlink(missing_ok=True)


def test_main_rejects_relative_output_repo_escape() -> None:
    assert main(["--output", os.path.join("..", "outside.json")]) == 2


def test_main_rejects_directory_output_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="output must be a file path"):
        telemetry_collector._resolve_output_path(output_dir)


def test_main_rejects_blocked_output_parent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    blocked_parent = tmp_path / "blocked"
    blocked_parent.write_text("not-a-dir", encoding="utf-8")
    async def _fake_collect_snapshot(**kwargs):
        del kwargs
        return {"captured_at": "2026-02-28T00:00:00Z"}

    monkeypatch.setattr(telemetry_collector, "collect_snapshot", _fake_collect_snapshot)
    monkeypatch.setattr(
        telemetry_collector,
        "_default_window",
        lambda: (datetime(2026, 2, 1, tzinfo=timezone.utc).date(), datetime(2026, 2, 28, tzinfo=timezone.utc).date()),
    )

    assert main(["--output", str(blocked_parent / "out.json")]) == 2


def test_main_returns_two_when_output_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_collect_snapshot(**kwargs):
        del kwargs
        return {"captured_at": "2026-02-28T00:00:00Z"}

    monkeypatch.setattr(telemetry_collector, "collect_snapshot", _fake_collect_snapshot)
    monkeypatch.setattr(
        telemetry_collector,
        "_default_window",
        lambda: (
            datetime(2026, 2, 1, tzinfo=timezone.utc).date(),
            datetime(2026, 2, 28, tzinfo=timezone.utc).date(),
        ),
    )
    monkeypatch.setattr(
        telemetry_collector,
        "stage_json_file",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("disk full")),
    )

    assert main(["--output", str(tmp_path / "out.json")]) == 2
