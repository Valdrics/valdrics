from __future__ import annotations

import json
import math
import os
from pathlib import Path

import pytest

import scripts.verify_enforcement_failure_injection_evidence as failure_verifier
from scripts.verify_enforcement_failure_injection_evidence import (
    main,
    verify_evidence,
)


BASE_VERIFY_KWARGS = {
    "expected_profile": "enforcement_failure_injection",
}


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _verify(path: Path, **overrides: object) -> int:
    kwargs = dict(BASE_VERIFY_KWARGS)
    kwargs.update(overrides)
    return verify_evidence(evidence_path=path, **kwargs)


def _valid_payload() -> dict[str, object]:
    scenarios = []
    for idx, scenario_id in enumerate(
        ["FI-001", "FI-002", "FI-003", "FI-004", "FI-005"],
        start=1,
    ):
        scenarios.append(
            {
                "id": scenario_id,
                "status": "pass",
                "duration_seconds": float(idx),
                "checks": [f"{scenario_id}:condition", f"{scenario_id}:routing"],
                "evidence_refs": [f"logs://{scenario_id.lower()}", f"trace://{scenario_id.lower()}"],
            }
        )
    return {
        "profile": "enforcement_failure_injection",
        "runner": "staged_failure_injection",
        "execution_class": "staged",
        "captured_at": "2026-02-27T09:15:00Z",
        "executed_by": "oncall-ops-1",
        "approved_by": "security-reviewer-2",
        "scenarios": scenarios,
        "summary": {
            "total_scenarios": 5,
            "passed_scenarios": 5,
            "failed_scenarios": 0,
            "overall_passed": True,
        },
    }


def test_verify_evidence_accepts_valid_payload(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"
    _write(path, _valid_payload())
    assert _verify(path) == 0


def test_verify_evidence_rejects_profile_or_runner_contract(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["profile"] = "other"
    path = tmp_path / "profile-invalid.json"
    _write(path, payload)
    with pytest.raises(ValueError, match="Unexpected profile"):
        _verify(path)

    payload = _valid_payload()
    payload["runner"] = "manual"
    path = tmp_path / "runner-invalid.json"
    _write(path, payload)
    with pytest.raises(ValueError, match="runner must equal"):
        _verify(path)


def test_verify_evidence_rejects_non_staged_or_reviewer_separation_violations(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    payload["execution_class"] = "dry-run"
    path = tmp_path / "execution-class-invalid.json"
    _write(path, payload)
    with pytest.raises(ValueError, match="execution_class"):
        _verify(path)

    payload = _valid_payload()
    payload["approved_by"] = payload["executed_by"]
    path = tmp_path / "separation-invalid.json"
    _write(path, payload)
    with pytest.raises(ValueError, match="must be distinct"):
        _verify(path)


def test_verify_evidence_rejects_missing_or_duplicate_scenarios(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["scenarios"] = payload["scenarios"][:-1]
    path = tmp_path / "missing-fi-005.json"
    _write(path, payload)
    with pytest.raises(ValueError, match="missing required failure scenarios"):
        _verify(path)

    payload = _valid_payload()
    payload["scenarios"][1]["id"] = "FI-001"
    path = tmp_path / "duplicate-scenario.json"
    _write(path, payload)
    with pytest.raises(ValueError, match="Duplicate scenario id"):
        _verify(path)


def test_verify_evidence_rejects_summary_integrity_drift(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["summary"]["passed_scenarios"] = 4
    path = tmp_path / "summary-pass-drift.json"
    _write(path, payload)
    with pytest.raises(ValueError, match="passed_scenarios"):
        _verify(path)

    payload = _valid_payload()
    payload["summary"]["overall_passed"] = False
    path = tmp_path / "summary-overall-false.json"
    _write(path, payload)
    with pytest.raises(ValueError, match="overall_passed"):
        _verify(path)


def test_verify_evidence_rejects_stale_or_invalid_freshness_bound(tmp_path: Path) -> None:
    payload = _valid_payload()
    payload["captured_at"] = "2024-01-01T00:00:00Z"
    path = tmp_path / "stale.json"
    _write(path, payload)
    with pytest.raises(ValueError, match="captured_at is too old"):
        _verify(path, max_artifact_age_hours=24.0)

    path = tmp_path / "valid.json"
    _write(path, _valid_payload())
    with pytest.raises(ValueError, match="max_artifact_age_hours must be > 0"):
        _verify(path, max_artifact_age_hours=0.0)


@pytest.mark.parametrize(
    ("field_path", "value", "expected_message"),
    [
        (("scenarios", 0, "duration_seconds"), math.nan, r"scenarios\[0\]\.duration_seconds must be finite"),
        (("scenarios", 1, "duration_seconds"), math.inf, r"scenarios\[1\]\.duration_seconds must be finite"),
    ],
)
def test_verify_evidence_rejects_non_finite_duration_seconds(
    tmp_path: Path,
    field_path: tuple[object, ...],
    value: float,
    expected_message: str,
) -> None:
    payload = _valid_payload()
    target: object = payload
    for part in field_path[:-1]:
        target = target[part]  # type: ignore[index]
    target[field_path[-1]] = value  # type: ignore[index]
    path = tmp_path / "duration-non-finite.json"
    _write(path, payload)
    with pytest.raises(ValueError, match=expected_message):
        _verify(path)


def test_main_succeeds_for_valid_payload(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"
    _write(path, _valid_payload())
    exit_code = main(["--evidence-path", str(path)])
    assert exit_code == 0


def test_main_resolves_relative_evidence_path_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    path = repo_root / "docs" / "ops" / "failure.json"
    _write(path, _valid_payload())
    monkeypatch.setattr(failure_verifier, "_repo_root", lambda: repo_root)

    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        assert main(["--evidence-path", "docs/ops/failure.json"]) == 0
    finally:
        os.chdir(old_cwd)


def test_main_rejects_relative_evidence_repo_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(failure_verifier, "_repo_root", lambda: repo_root)

    assert main(["--evidence-path", "../escape/failure.json"]) == 2
