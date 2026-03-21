from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest

import scripts.verify_valdrics_disposition_freshness as valdrics_verifier
from scripts.verify_valdrics_disposition_freshness import (
    DEFAULT_REQUIRED_FINDING_IDS,
    main,
    verify_disposition_register,
)


AS_OF_UTC = datetime(2026, 3, 15, 0, 0, tzinfo=timezone.utc)
RUNTIME_PROBE_RESULTS = [
    {
        "probe_id": "adapter_coverage",
        "command": "python scripts/verify_adapter_test_coverage.py",
        "passed": True,
        "output_excerpt": "ok",
    },
    {
        "probe_id": "module_size_budget",
        "command": "python scripts/verify_python_module_size_budget.py --enforcement-mode strict",
        "passed": False,
        "output_excerpt": "size budget exceeded",
    },
    {
        "probe_id": "dependency_locking",
        "command": "python scripts/verify_dependency_locking.py",
        "passed": True,
        "output_excerpt": "ok",
    },
    {
        "probe_id": "env_hygiene",
        "command": "python scripts/verify_env_hygiene.py",
        "passed": True,
        "output_excerpt": "ok",
    },
    {
        "probe_id": "audit_controls",
        "command": "python scripts/verify_audit_report_resolved.py --skip-report-check",
        "passed": True,
        "output_excerpt": "ok",
    },
]
CONTROL_PROBES_BY_FINDING = {
    "VAL-ADAPT-001": ["adapter_coverage", "module_size_budget"],
    "VAL-ADAPT-002+": ["module_size_budget", "audit_controls"],
    "VAL-DB-002": ["env_hygiene", "audit_controls"],
    "VAL-DB-003": ["dependency_locking", "audit_controls"],
    "VAL-DB-004": ["audit_controls"],
    "VAL-API-001": ["audit_controls"],
    "VAL-API-002": ["audit_controls"],
    "VAL-API-004": ["env_hygiene", "audit_controls"],
}


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _valid_payload() -> dict[str, object]:
    probe_pass_by_id = {
        str(item["probe_id"]): bool(item["passed"])
        for item in RUNTIME_PROBE_RESULTS
    }
    dispositions: list[dict[str, object]] = []
    for finding_id in DEFAULT_REQUIRED_FINDING_IDS:
        control_probe_ids = CONTROL_PROBES_BY_FINDING[finding_id]
        all_control_probes_passed = all(
            probe_pass_by_id.get(probe_id, False) for probe_id in control_probe_ids
        )
        item: dict[str, object] = {
            "finding_id": finding_id,
            "status": "documented_exception" if all_control_probes_passed else "planned_refactor",
            "owner": "platform-owner@valdrics.io",
            "review_by": "2026-03-31",
            "rationale": f"{finding_id} disposition rationale recorded for release gate.",
            "exit_criteria": f"{finding_id} closure criteria tracked in remediation backlog.",
            "control_probe_ids": control_probe_ids,
        }
        if item["status"] == "planned_refactor":
            item["backlog_ref"] = "VAL-ADAPT-002+"
        dispositions.append(item)

    return {
        "captured_at": "2026-02-28T15:20:00Z",
        "source_audit_path": "/tmp/VALDRX_CODEBASE_AUDIT_2026-02-28.md.resolved",
        "runtime_probe_results": RUNTIME_PROBE_RESULTS,
        "dispositions": dispositions,
    }


def test_verify_valdrics_disposition_freshness_accepts_valid_payload(
    tmp_path: Path,
) -> None:
    path = tmp_path / "valdrics-disposition.json"
    _write(path, _valid_payload())

    assert (
        verify_disposition_register(
            register_path=path,
            max_artifact_age_days=45.0,
            max_review_window_days=120.0,
            as_of=AS_OF_UTC,
        )
        == 0
    )


def test_verify_valdrics_disposition_freshness_rejects_overdue_review(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    payload["dispositions"][0]["review_by"] = "2026-03-01"
    path = tmp_path / "valdrics-disposition.json"
    _write(path, payload)

    with pytest.raises(ValueError, match="review_by is overdue"):
        verify_disposition_register(
            register_path=path,
            max_artifact_age_days=45.0,
            max_review_window_days=120.0,
            as_of=AS_OF_UTC,
        )


def test_verify_valdrics_disposition_freshness_rejects_placeholder_owner(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    payload["dispositions"][0]["owner"] = "owner@example.com"
    path = tmp_path / "valdrics-disposition.json"
    _write(path, payload)

    with pytest.raises(ValueError, match="must not contain placeholder tokens"):
        verify_disposition_register(
            register_path=path,
            max_artifact_age_days=45.0,
            max_review_window_days=120.0,
            as_of=AS_OF_UTC,
        )


def test_verify_valdrics_disposition_freshness_rejects_missing_required_finding(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    payload["dispositions"] = payload["dispositions"][:-1]
    path = tmp_path / "valdrics-disposition.json"
    _write(path, payload)

    with pytest.raises(ValueError, match="missing required finding IDs"):
        verify_disposition_register(
            register_path=path,
            max_artifact_age_days=45.0,
            max_review_window_days=120.0,
            as_of=AS_OF_UTC,
        )


def test_verify_valdrics_disposition_freshness_rejects_missing_runtime_probe_results(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    payload["runtime_probe_results"] = None
    path = tmp_path / "valdrics-disposition.json"
    _write(path, payload)

    with pytest.raises(ValueError, match="runtime_probe_results must be a non-empty array"):
        verify_disposition_register(
            register_path=path,
            max_artifact_age_days=45.0,
            max_review_window_days=120.0,
            as_of=AS_OF_UTC,
        )


def test_verify_valdrics_disposition_freshness_rejects_documented_exception_with_failed_probe(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    payload["dispositions"][2]["status"] = "documented_exception"
    payload["runtime_probe_results"][3]["passed"] = False
    path = tmp_path / "valdrics-disposition.json"
    _write(path, payload)

    with pytest.raises(ValueError, match="documented_exception must reference only passing"):
        verify_disposition_register(
            register_path=path,
            max_artifact_age_days=45.0,
            max_review_window_days=120.0,
            as_of=AS_OF_UTC,
        )


def test_verify_valdrics_disposition_freshness_rejects_planned_refactor_without_failed_probe(
    tmp_path: Path,
) -> None:
    payload = _valid_payload()
    payload["runtime_probe_results"][1]["passed"] = True
    path = tmp_path / "valdrics-disposition.json"
    _write(path, payload)

    with pytest.raises(ValueError, match="planned_refactor must reference at least one failing"):
        verify_disposition_register(
            register_path=path,
            max_artifact_age_days=45.0,
            max_review_window_days=120.0,
            as_of=AS_OF_UTC,
        )


def test_main_accepts_valid_payload(tmp_path: Path) -> None:
    path = tmp_path / "valdrics-disposition.json"
    _write(path, _valid_payload())
    assert (
        main(
            [
                "--register-path",
                str(path),
                "--max-artifact-age-days",
                "45",
                "--max-review-window-days",
                "120",
                "--as-of",
                "2026-03-15T00:00:00Z",
            ]
        )
        == 0
    )


def test_main_resolves_relative_register_path_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    register_path = repo_root / "docs" / "ops" / "valdrics.json"
    _write(register_path, _valid_payload())

    monkeypatch.setattr(valdrics_verifier, "_repo_root", lambda: repo_root)
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "--register-path",
                "docs/ops/valdrics.json",
                "--max-artifact-age-days",
                "45",
                "--max-review-window-days",
                "120",
                "--as-of",
                "2026-03-15T00:00:00Z",
            ]
        )
        == 0
    )


def test_main_rejects_relative_register_repo_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(valdrics_verifier, "_repo_root", lambda: repo_root)

    assert main(["--register-path", os.path.join("..", "escape.json")]) == 2


def test_main_rejects_directory_register_path(tmp_path: Path) -> None:
    register_dir = tmp_path / "register-dir"
    register_dir.mkdir()

    assert main(["--register-path", str(register_dir)]) == 2


@pytest.mark.parametrize(
    ("kwargs", "expected_message"),
    [
        (
            {"max_artifact_age_days": math.nan, "max_review_window_days": 120.0},
            "max_artifact_age_days must be finite",
        ),
        (
            {"max_artifact_age_days": 45.0, "max_review_window_days": math.inf},
            "max_review_window_days must be finite",
        ),
    ],
)
def test_verify_valdrics_disposition_freshness_rejects_non_finite_bounds(
    tmp_path: Path,
    kwargs: dict[str, float],
    expected_message: str,
) -> None:
    path = tmp_path / "valdrics-disposition.json"
    _write(path, _valid_payload())

    with pytest.raises(ValueError, match=expected_message):
        verify_disposition_register(
            register_path=path,
            as_of=AS_OF_UTC,
            **kwargs,
        )
