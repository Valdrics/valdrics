from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from scripts.verify_pkg_fin_operational_readiness import (
    main,
    verify_operational_readiness,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
POLICY_PATH = (
    REPO_ROOT / "docs" / "ops" / "evidence" / "pkg_fin_policy_decisions_2026-02-28.json"
)
FINANCE_PATH = (
    REPO_ROOT / "docs" / "ops" / "evidence" / "finance_guardrails_2026-02-27.json"
)
TELEMETRY_PATH = (
    REPO_ROOT / "docs" / "ops" / "evidence" / "finance_telemetry_snapshot_2026-02-28.json"
)


def test_verify_operational_readiness_returns_expected_prelaunch_summary() -> None:
    summary = verify_operational_readiness(
        policy_decisions_path=POLICY_PATH,
        finance_guardrails_path=FINANCE_PATH,
        telemetry_snapshot_path=TELEMETRY_PATH,
    )

    derived = summary["derived"]
    assert derived["policy_all_gates_pass"] is True
    assert derived["finance_all_gates_pass"] is True
    assert derived["telemetry_all_gates_pass"] is True
    assert derived["prelaunch_operational_ready"] is True
    assert derived["postlaunch_pricing_motion_ready"] is False
    assert derived["production_observed_telemetry_ready"] is False
    assert derived["segregated_approval_governance_ready"] is False

    remaining = summary["remaining_work_items"]
    assert len(remaining) == 2
    assert any("production_observed telemetry" in item for item in remaining)
    assert any("segregated_owners" in item for item in remaining)
    assert summary["artifacts"] == {
        "policy_decisions_path": "docs/ops/evidence/pkg_fin_policy_decisions_2026-02-28.json",
        "finance_guardrails_path": "docs/ops/evidence/finance_guardrails_2026-02-27.json",
        "telemetry_snapshot_path": "docs/ops/evidence/finance_telemetry_snapshot_2026-02-28.json",
    }


def test_verify_operational_readiness_can_fail_on_required_production_telemetry() -> None:
    with pytest.raises(ValueError, match="production_observed telemetry requirement failed"):
        verify_operational_readiness(
            policy_decisions_path=POLICY_PATH,
            finance_guardrails_path=FINANCE_PATH,
            telemetry_snapshot_path=TELEMETRY_PATH,
            require_production_observed_telemetry=True,
        )


def test_verify_operational_readiness_can_fail_on_required_segregated_owners() -> None:
    with pytest.raises(ValueError, match="segregated owner governance requirement failed"):
        verify_operational_readiness(
            policy_decisions_path=POLICY_PATH,
            finance_guardrails_path=FINANCE_PATH,
            telemetry_snapshot_path=TELEMETRY_PATH,
            require_segregated_owners=True,
        )


def test_main_writes_summary_artifact(tmp_path: Path) -> None:
    output_path = tmp_path / "pkg_fin_operational_readiness.json"

    assert (
        main(
            [
                "--policy-decisions-path",
                str(POLICY_PATH),
                "--finance-guardrails-path",
                str(FINANCE_PATH),
                "--telemetry-snapshot-path",
                str(TELEMETRY_PATH),
                "--output-path",
                str(output_path),
            ]
        )
        == 0
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload["derived"]["prelaunch_operational_ready"] is True
    assert payload["derived"]["postlaunch_pricing_motion_ready"] is False


def test_main_rejects_directory_output_path(tmp_path: Path) -> None:
    output_dir = tmp_path / "pkg-fin-output"
    output_dir.mkdir()

    assert (
        main(
            [
                "--policy-decisions-path",
                str(POLICY_PATH),
                "--finance-guardrails-path",
                str(FINANCE_PATH),
                "--telemetry-snapshot-path",
                str(TELEMETRY_PATH),
                "--output-path",
                str(output_dir),
            ]
        )
        == 2
    )


def test_main_rejects_blocked_output_parent(tmp_path: Path) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    assert (
        main(
            [
                "--policy-decisions-path",
                str(POLICY_PATH),
                "--finance-guardrails-path",
                str(FINANCE_PATH),
                "--telemetry-snapshot-path",
                str(TELEMETRY_PATH),
                "--output-path",
                str(blocked_parent / "pkg_fin_operational_readiness.json"),
            ]
        )
        == 2
    )


def test_main_does_not_leave_output_when_summary_promotion_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "pkg_fin_operational_readiness.json"
    path_type = type(output_path)
    original_replace = path_type.replace

    def _failing_replace(self: Path, target: Path) -> Path:
        if self.parent == output_path.parent and Path(target) == output_path:
            raise OSError("simulated promotion failure")
        return original_replace(self, target)

    monkeypatch.setattr(path_type, "replace", _failing_replace)

    with pytest.raises(OSError, match="simulated promotion failure"):
        main(
            [
                "--policy-decisions-path",
                str(POLICY_PATH),
                "--finance-guardrails-path",
                str(FINANCE_PATH),
                "--telemetry-snapshot-path",
                str(TELEMETRY_PATH),
                "--output-path",
                str(output_path),
            ]
        )

    assert not output_path.exists()
    assert not list(output_path.parent.glob(f".{output_path.stem}.*{output_path.suffix}.tmp"))


def test_main_resolves_relative_artifact_paths_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)

    assert (
        main(
            [
                "--policy-decisions-path",
                os.path.relpath(POLICY_PATH, REPO_ROOT),
                "--finance-guardrails-path",
                os.path.relpath(FINANCE_PATH, REPO_ROOT),
                "--telemetry-snapshot-path",
                os.path.relpath(TELEMETRY_PATH, REPO_ROOT),
            ]
        )
        == 0
    )


def test_main_rejects_relative_artifact_repo_escape(tmp_path: Path) -> None:
    outside_artifact = tmp_path / "outside.json"
    outside_artifact.write_text("{}", encoding="utf-8")
    relative_escape = os.path.relpath(outside_artifact, REPO_ROOT)

    assert (
        main(
            [
                "--policy-decisions-path",
                relative_escape,
                "--finance-guardrails-path",
                str(FINANCE_PATH),
                "--telemetry-snapshot-path",
                str(TELEMETRY_PATH),
            ]
        )
        == 2
    )


def test_main_rejects_directory_artifact_input(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifact-dir"
    artifact_dir.mkdir()

    assert (
        main(
            [
                "--policy-decisions-path",
                str(artifact_dir),
                "--finance-guardrails-path",
                str(FINANCE_PATH),
                "--telemetry-snapshot-path",
                str(TELEMETRY_PATH),
            ]
        )
        == 2
    )
