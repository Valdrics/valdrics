from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import scripts.generate_pkg_fin_policy_decisions as generator
from scripts.generate_pkg_fin_policy_decisions import main


def _telemetry_payload() -> dict[str, object]:
    return {
        "window": {
            "start": "2026-02-01T00:00:00Z",
            "end": "2026-02-28T23:59:59Z",
            "label": "2026-02",
        },
        "pricing_reference": {
            "starter": {"annual_monthly_factor": 0.9},
            "growth": {"annual_monthly_factor": 0.9},
            "pro": {"annual_monthly_factor": 0.9},
            "enterprise": {"annual_monthly_factor": 0.9},
        },
        "tier_revenue_inputs": [
            {"tier": "starter", "gross_mrr_usd": 1000.0},
            {"tier": "growth", "gross_mrr_usd": 2000.0},
            {"tier": "pro", "gross_mrr_usd": 3000.0},
            {"tier": "enterprise", "gross_mrr_usd": 4000.0},
        ],
        "tier_llm_usage": [
            {"tier": "starter", "total_cost_usd": 100.0},
            {"tier": "growth", "total_cost_usd": 150.0},
            {"tier": "pro", "total_cost_usd": 200.0},
            {"tier": "enterprise", "total_cost_usd": 250.0},
        ],
        "tier_subscription_snapshot": [
            {"tier": "starter", "active_subscriptions": 10},
            {"tier": "growth", "active_subscriptions": 20},
            {"tier": "pro", "active_subscriptions": 30},
            {"tier": "enterprise", "active_subscriptions": 40},
        ],
    }


def test_generate_pkg_fin_policy_decisions_rejects_input_output_collision(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")

    with pytest.raises(ValueError, match="telemetry_snapshot_path and output must be different files"):
        main(
            [
                "--output",
                str(telemetry),
                "--telemetry-snapshot-path",
                str(telemetry),
            ]
        )


@pytest.mark.parametrize(
    "relative_output",
    [
        "scripts/verify_pkg_fin_policy_decisions.py",
        "docs/ops/evidence/pkg_fin_policy_decisions_TEMPLATE.json",
        "docs/ops/evidence/pkg_fin_policy_decisions_2026-02-28.json",
    ],
)
def test_generate_pkg_fin_policy_decisions_rejects_protected_output_collisions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative_output: str,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[3]
    output = repo_root / relative_output
    called = {"verify_snapshot": False}

    def _unexpected_verify_snapshot(**_: object) -> int:
        called["verify_snapshot"] = True
        raise AssertionError("telemetry verification should not run for protected output paths")

    monkeypatch.setattr(generator, "verify_snapshot", _unexpected_verify_snapshot)

    with pytest.raises(ValueError, match="output must not overwrite PKG/FIN"):
        main(
            [
                "--output",
                str(output),
                "--telemetry-snapshot-path",
                str(telemetry),
            ]
        )

    assert called["verify_snapshot"] is False


def test_generate_pkg_fin_policy_decisions_rejects_output_parent_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    monkeypatch.setattr(generator, "verify_snapshot", lambda **_: 0)

    with pytest.raises(ValueError, match="output parent must be a directory path"):
        main(
            [
                "--output",
                str(blocked_parent / "pkg_fin_policy_decisions.json"),
                "--telemetry-snapshot-path",
                str(telemetry),
            ]
        )


def test_generate_pkg_fin_policy_decisions_rejects_directory_output_path(
    tmp_path: Path,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    output_dir = tmp_path / "pkg-fin-output"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    output_dir.mkdir()

    with pytest.raises(ValueError, match="output must be a file path"):
        main(
            [
                "--output",
                str(output_dir),
                "--telemetry-snapshot-path",
                str(telemetry),
            ]
        )


def test_generate_pkg_fin_policy_decisions_rejects_directory_telemetry_snapshot_path(
    tmp_path: Path,
) -> None:
    telemetry_dir = tmp_path / "telemetry-dir"
    telemetry_dir.mkdir()

    with pytest.raises(ValueError, match="Finance telemetry snapshot file must be a file"):
        main(
            [
                "--output",
                str(tmp_path / "pkg_fin_policy_decisions.json"),
                "--telemetry-snapshot-path",
                str(telemetry_dir),
            ]
        )


def test_generate_pkg_fin_policy_decisions_rejects_relative_protected_output_from_outside_repo(
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
    monkeypatch.setattr(generator, "_repo_root", lambda: repo_root)

    with pytest.raises(ValueError, match="output must not overwrite PKG/FIN"):
        main(
            [
                "--output",
                "docs/ops/evidence/pkg_fin_policy_decisions_TEMPLATE.json",
                "--telemetry-snapshot-path",
                "telemetry.json",
            ]
        )


def test_generate_pkg_fin_policy_decisions_resolves_relative_paths_from_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    telemetry = repo_root / "telemetry.json"
    output = repo_root / "artifacts" / "pkg_fin_policy_decisions.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(generator, "_repo_root", lambda: repo_root)

    verify_snapshot_calls: list[dict[str, object]] = []
    verify_evidence_calls: list[dict[str, object]] = []

    def _fake_verify_snapshot(**kwargs: object) -> int:
        verify_snapshot_calls.append(kwargs)
        return 0

    def _fake_verify_evidence(**kwargs: object) -> int:
        verify_evidence_calls.append(kwargs)
        return 0

    monkeypatch.setattr(generator, "verify_snapshot", _fake_verify_snapshot)
    monkeypatch.setattr(generator, "verify_evidence", _fake_verify_evidence)

    assert (
        main(
            [
                "--output",
                "artifacts/pkg_fin_policy_decisions.json",
                "--telemetry-snapshot-path",
                "telemetry.json",
            ]
        )
        == 0
    )

    assert verify_snapshot_calls == [
        {
            "snapshot_path": telemetry,
            "max_artifact_age_hours": 24.0,
        }
    ]
    assert verify_evidence_calls == [
        {
            "evidence_path": output,
            "max_artifact_age_hours": 4.0,
        }
    ]


def test_generate_pkg_fin_policy_decisions_verifies_telemetry_snapshot_first(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    telemetry = tmp_path / "telemetry.json"
    output = tmp_path / "pkg_fin_policy_decisions.json"
    telemetry.write_text(json.dumps(_telemetry_payload()), encoding="utf-8")

    verify_snapshot_calls: list[dict[str, object]] = []
    verify_evidence_calls: list[dict[str, object]] = []

    def _fake_verify_snapshot(**kwargs: object) -> int:
        verify_snapshot_calls.append(kwargs)
        return 0

    def _fake_verify_evidence(**kwargs: object) -> int:
        verify_evidence_calls.append(kwargs)
        return 0

    monkeypatch.setattr(generator, "verify_snapshot", _fake_verify_snapshot)
    monkeypatch.setattr(generator, "verify_evidence", _fake_verify_evidence)

    assert (
        main(
            [
                "--output",
                str(output),
                "--telemetry-snapshot-path",
                str(telemetry),
            ]
        )
        == 0
    )

    assert verify_snapshot_calls == [
        {
            "snapshot_path": telemetry,
            "max_artifact_age_hours": 24.0,
        }
    ]
    assert verify_evidence_calls == [
        {
            "evidence_path": output,
            "max_artifact_age_hours": 4.0,
        }
    ]


@pytest.mark.parametrize(
    ("field_path", "value", "expected_message"),
    [
        (("tier_revenue_inputs", 0, "gross_mrr_usd"), math.nan, "tier_revenue_inputs.starter.gross_mrr_usd must be finite"),
        (("tier_llm_usage", 1, "total_cost_usd"), math.inf, "tier_llm_usage.growth.total_cost_usd must be finite"),
        (
            ("pricing_reference", "pro", "annual_monthly_factor"),
            -math.inf,
            "pricing_reference.pro.annual_monthly_factor must be finite",
        ),
    ],
)
def test_generate_pkg_fin_policy_decisions_rejects_non_finite_finance_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    field_path: tuple[object, ...],
    value: float,
    expected_message: str,
) -> None:
    telemetry_payload = _telemetry_payload()
    mutated: object = telemetry_payload
    for path_part in field_path[:-1]:
        mutated = mutated[path_part]  # type: ignore[index]
    mutated[field_path[-1]] = value  # type: ignore[index]

    telemetry = tmp_path / "telemetry.json"
    output = tmp_path / "pkg_fin_policy_decisions.json"
    telemetry.write_text(json.dumps(telemetry_payload), encoding="utf-8")

    monkeypatch.setattr(generator, "verify_snapshot", lambda **_: 0)
    monkeypatch.setattr(generator, "verify_evidence", lambda **_: 0)

    with pytest.raises(ValueError, match=expected_message):
        main(
            [
                "--output",
                str(output),
                "--telemetry-snapshot-path",
                str(telemetry),
            ]
        )
