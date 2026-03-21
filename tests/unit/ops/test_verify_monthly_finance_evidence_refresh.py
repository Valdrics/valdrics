from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

import scripts.verify_monthly_finance_evidence_refresh as monthly_refresh_verifier
from scripts.verify_monthly_finance_evidence_refresh import (
    main,
    verify_monthly_refresh,
)


def _write(path: Path, *, captured_at: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"captured_at": captured_at}), encoding="utf-8")


AS_OF_UTC = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)


def test_verify_monthly_finance_refresh_accepts_fresh_artifacts(tmp_path: Path) -> None:
    finance_guardrails = tmp_path / "finance-guardrails.json"
    finance_telemetry = tmp_path / "finance-telemetry.json"
    pkg_fin = tmp_path / "pkg-fin.json"
    _write(finance_guardrails, captured_at="2026-02-27T10:00:00Z")
    _write(finance_telemetry, captured_at="2026-02-28T12:00:00Z")
    _write(pkg_fin, captured_at="2026-02-28T06:30:00Z")

    assert (
        verify_monthly_refresh(
            finance_guardrails_path=finance_guardrails,
            finance_telemetry_snapshot_path=finance_telemetry,
            pkg_fin_policy_decisions_path=pkg_fin,
            max_age_days=35.0,
            max_capture_spread_days=14.0,
            max_future_skew_hours=24.0,
            as_of=AS_OF_UTC,
        )
        == 0
    )


def test_verify_monthly_finance_refresh_rejects_stale_artifact(tmp_path: Path) -> None:
    finance_guardrails = tmp_path / "finance-guardrails.json"
    finance_telemetry = tmp_path / "finance-telemetry.json"
    pkg_fin = tmp_path / "pkg-fin.json"
    _write(finance_guardrails, captured_at="2026-01-01T00:00:00Z")
    _write(finance_telemetry, captured_at="2026-02-28T12:00:00Z")
    _write(pkg_fin, captured_at="2026-02-28T06:30:00Z")

    with pytest.raises(ValueError, match="evidence is stale"):
        verify_monthly_refresh(
            finance_guardrails_path=finance_guardrails,
            finance_telemetry_snapshot_path=finance_telemetry,
            pkg_fin_policy_decisions_path=pkg_fin,
            max_age_days=35.0,
            max_capture_spread_days=14.0,
            max_future_skew_hours=24.0,
            as_of=AS_OF_UTC,
        )


def test_verify_monthly_finance_refresh_rejects_wide_capture_spread(
    tmp_path: Path,
) -> None:
    finance_guardrails = tmp_path / "finance-guardrails.json"
    finance_telemetry = tmp_path / "finance-telemetry.json"
    pkg_fin = tmp_path / "pkg-fin.json"
    _write(finance_guardrails, captured_at="2026-02-01T00:00:00Z")
    _write(finance_telemetry, captured_at="2026-02-28T12:00:00Z")
    _write(pkg_fin, captured_at="2026-02-28T06:30:00Z")

    with pytest.raises(ValueError, match="capture spread is too wide"):
        verify_monthly_refresh(
            finance_guardrails_path=finance_guardrails,
            finance_telemetry_snapshot_path=finance_telemetry,
            pkg_fin_policy_decisions_path=pkg_fin,
            max_age_days=60.0,
            max_capture_spread_days=7.0,
            max_future_skew_hours=24.0,
            as_of=AS_OF_UTC,
        )


def test_verify_monthly_finance_refresh_rejects_future_skew_beyond_limit(
    tmp_path: Path,
) -> None:
    finance_guardrails = tmp_path / "finance-guardrails.json"
    finance_telemetry = tmp_path / "finance-telemetry.json"
    pkg_fin = tmp_path / "pkg-fin.json"
    _write(finance_guardrails, captured_at="2026-03-16T12:00:00Z")
    _write(finance_telemetry, captured_at="2026-03-16T12:00:00Z")
    _write(pkg_fin, captured_at="2026-03-16T12:00:00Z")

    with pytest.raises(ValueError, match="too far in the future"):
        verify_monthly_refresh(
            finance_guardrails_path=finance_guardrails,
            finance_telemetry_snapshot_path=finance_telemetry,
            pkg_fin_policy_decisions_path=pkg_fin,
            max_age_days=35.0,
            max_capture_spread_days=14.0,
            max_future_skew_hours=1.0,
            as_of=AS_OF_UTC,
        )


def test_main_accepts_valid_payloads(tmp_path: Path) -> None:
    finance_guardrails = tmp_path / "finance-guardrails.json"
    finance_telemetry = tmp_path / "finance-telemetry.json"
    pkg_fin = tmp_path / "pkg-fin.json"
    _write(finance_guardrails, captured_at="2026-02-27T10:00:00Z")
    _write(finance_telemetry, captured_at="2026-02-28T12:00:00Z")
    _write(pkg_fin, captured_at="2026-02-28T06:30:00Z")

    exit_code = main(
        [
            "--finance-guardrails-path",
            str(finance_guardrails),
            "--finance-telemetry-snapshot-path",
            str(finance_telemetry),
            "--pkg-fin-policy-decisions-path",
            str(pkg_fin),
            "--max-age-days",
            "35",
            "--max-capture-spread-days",
            "14",
            "--as-of",
            "2026-03-15T00:00:00Z",
        ]
    )
    assert exit_code == 0


def test_main_resolves_relative_paths_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = monthly_refresh_verifier.Path(monthly_refresh_verifier.__file__).resolve().parents[1]
    finance_guardrails = repo_root / "docs" / "ops" / "evidence" / "finance_guardrails_2026-02-27.json"
    finance_telemetry = repo_root / "docs" / "ops" / "evidence" / "finance_telemetry_snapshot_2026-02-28.json"
    pkg_fin = repo_root / "docs" / "ops" / "evidence" / "pkg_fin_policy_decisions_2026-02-28.json"
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "--finance-guardrails-path",
                os.path.relpath(finance_guardrails, repo_root),
                "--finance-telemetry-snapshot-path",
                os.path.relpath(finance_telemetry, repo_root),
                "--pkg-fin-policy-decisions-path",
                os.path.relpath(pkg_fin, repo_root),
                "--as-of",
                "2026-03-15T00:00:00Z",
            ]
        )
        == 0
    )


def test_main_rejects_relative_repo_escape(tmp_path: Path) -> None:
    outside_artifact = tmp_path / "outside.json"
    _write(outside_artifact, captured_at="2026-02-27T10:00:00Z")
    repo_root = monthly_refresh_verifier.Path(monthly_refresh_verifier.__file__).resolve().parents[1]

    assert (
        main(
            [
                "--finance-guardrails-path",
                os.path.relpath(outside_artifact, repo_root),
                "--finance-telemetry-snapshot-path",
                str(outside_artifact),
                "--pkg-fin-policy-decisions-path",
                str(outside_artifact),
                "--as-of",
                "2026-03-15T00:00:00Z",
            ]
        )
        == 2
    )


def test_main_rejects_directory_artifact_path(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifact-dir"
    artifact_dir.mkdir()
    artifact_file = tmp_path / "artifact.json"
    _write(artifact_file, captured_at="2026-02-27T10:00:00Z")

    assert (
        main(
            [
                "--finance-guardrails-path",
                str(artifact_dir),
                "--finance-telemetry-snapshot-path",
                str(artifact_file),
                "--pkg-fin-policy-decisions-path",
                str(artifact_file),
                "--as-of",
                "2026-03-15T00:00:00Z",
            ]
        )
        == 2
    )


@pytest.mark.parametrize(
    ("kwargs", "expected_message"),
    [
        (
            {"max_age_days": math.nan, "max_capture_spread_days": 14.0, "max_future_skew_hours": 24.0},
            "max_age_days must be finite",
        ),
        (
            {"max_age_days": 35.0, "max_capture_spread_days": math.inf, "max_future_skew_hours": 24.0},
            "max_capture_spread_days must be finite",
        ),
        (
            {"max_age_days": 35.0, "max_capture_spread_days": 14.0, "max_future_skew_hours": math.nan},
            "max_future_skew_hours must be finite",
        ),
    ],
)
def test_verify_monthly_finance_refresh_rejects_non_finite_bounds(
    tmp_path: Path,
    kwargs: dict[str, float],
    expected_message: str,
) -> None:
    finance_guardrails = tmp_path / "finance-guardrails.json"
    finance_telemetry = tmp_path / "finance-telemetry.json"
    pkg_fin = tmp_path / "pkg-fin.json"
    _write(finance_guardrails, captured_at="2026-02-27T10:00:00Z")
    _write(finance_telemetry, captured_at="2026-02-28T12:00:00Z")
    _write(pkg_fin, captured_at="2026-02-28T06:30:00Z")

    with pytest.raises(ValueError, match=expected_message):
        verify_monthly_refresh(
            finance_guardrails_path=finance_guardrails,
            finance_telemetry_snapshot_path=finance_telemetry,
            pkg_fin_policy_decisions_path=pkg_fin,
            as_of=AS_OF_UTC,
            **kwargs,
        )
