from __future__ import annotations

import json
from pathlib import Path
import subprocess
from unittest.mock import MagicMock

import pytest

from scripts import generate_enforcement_failure_injection_evidence as generator


def test_generate_evidence_requires_separation_of_duties(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be distinct"):
        generator.generate_evidence(
            output=tmp_path / "artifact.json",
            executed_by="same@valdrics.local",
            approved_by="same@valdrics.local",
            profile="enforcement_failure_injection",
            cwd=tmp_path,
            timeout_seconds=60.0,
        )


def test_generate_evidence_requires_non_empty_identities(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be non-empty"):
        generator.generate_evidence(
            output=tmp_path / "artifact.json",
            executed_by="   ",
            approved_by="approver@valdrics.local",
            profile="enforcement_failure_injection",
            cwd=tmp_path,
            timeout_seconds=60.0,
        )


def test_generate_evidence_requires_non_empty_profile(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="profile must be non-empty"):
        generator.generate_evidence(
            output=tmp_path / "artifact.json",
            executed_by="exec@valdrics.local",
            approved_by="approver@valdrics.local",
            profile="   ",
            cwd=tmp_path,
            timeout_seconds=60.0,
        )


@pytest.mark.parametrize(
    "relative_output",
    [
        "scripts/verify_enforcement_failure_injection_evidence.py",
        "tests/unit/enforcement/test_enforcement_api.py",
        "docs/ops/evidence/enforcement_failure_injection_2026-02-27.json",
        "docs/ops/evidence/finance_telemetry_snapshot_TEMPLATE.json",
        "docs/ops/evidence/valdrics_disposition_register_2026-02-28.json",
        "docs/ops/evidence/README.md",
    ],
)
def test_generate_evidence_rejects_protected_output_collisions(
    monkeypatch: pytest.MonkeyPatch,
    relative_output: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    output = repo_root / relative_output

    def _unexpected_run_scenario(
        *args: object, **kwargs: object
    ) -> tuple[dict[str, object], bool]:
        raise AssertionError(
            "scenario execution should not run for protected output paths"
        )

    monkeypatch.setattr(generator, "_run_scenario", _unexpected_run_scenario)

    with pytest.raises(ValueError, match="output must not overwrite failure-injection"):
        generator.generate_evidence(
            output=output,
            executed_by="exec@valdrics.local",
            approved_by="approver@valdrics.local",
            profile="enforcement_failure_injection",
            cwd=repo_root,
            timeout_seconds=60.0,
        )


def test_generate_evidence_rejects_relative_protected_output_from_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    protected_output = (
        repo_root
        / "docs"
        / "ops"
        / "evidence"
        / "enforcement_failure_injection_2026-02-27.json"
    )
    protected_output.parent.mkdir(parents=True, exist_ok=True)
    protected_output.write_text("{}", encoding="utf-8")
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(generator, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        generator,
        "_run_scenario",
        lambda *_, **__: (_ for _ in ()).throw(
            AssertionError(
                "scenario execution should not run for protected output paths"
            )
        ),
    )

    with pytest.raises(ValueError, match="output must not overwrite failure-injection"):
        generator.generate_evidence(
            output=Path(
                "docs/ops/evidence/enforcement_failure_injection_2026-02-27.json"
            ),
            executed_by="exec@valdrics.local",
            approved_by="approver@valdrics.local",
            profile="enforcement_failure_injection",
            cwd=repo_root,
            timeout_seconds=60.0,
        )


def test_generate_evidence_rejects_relative_output_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(generator, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        generator,
        "_run_scenario",
        lambda *_, **__: (_ for _ in ()).throw(
            AssertionError(
                "scenario execution should not run for escaping output paths"
            )
        ),
    )

    with pytest.raises(
        ValueError,
        match="output must stay within repo root when relative",
    ):
        generator.generate_evidence(
            output=Path("../escape/failure_injection.json"),
            executed_by="exec@valdrics.local",
            approved_by="approver@valdrics.local",
            profile="enforcement_failure_injection",
            cwd=repo_root,
            timeout_seconds=60.0,
        )


def test_generate_evidence_rejects_profile_contract_drift(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="profile must equal"):
        generator.generate_evidence(
            output=tmp_path / "artifact.json",
            executed_by="exec@valdrics.local",
            approved_by="approver@valdrics.local",
            profile="custom_profile",
            cwd=tmp_path,
            timeout_seconds=60.0,
        )


def test_generate_evidence_rejects_output_parent_file(
    tmp_path: Path,
) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="output parent must be a directory path"):
        generator.generate_evidence(
            output=blocked_parent / "artifact.json",
            executed_by="exec@valdrics.local",
            approved_by="approver@valdrics.local",
            profile="enforcement_failure_injection",
            cwd=tmp_path,
            timeout_seconds=60.0,
        )


def test_generate_evidence_rejects_directory_output_path(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "artifact-dir"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="output must be a file path"):
        generator.generate_evidence(
            output=output_dir,
            executed_by="exec@valdrics.local",
            approved_by="approver@valdrics.local",
            profile="enforcement_failure_injection",
            cwd=tmp_path,
            timeout_seconds=60.0,
        )


def test_generate_evidence_writes_summary_and_scenarios(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = {"count": 0}

    def _fake_run_scenario(
        scenario: generator.FailureScenario, *, cwd: Path, timeout_seconds: float
    ) -> tuple[dict[str, object], bool]:
        assert timeout_seconds == 60.0
        calls["count"] += 1
        passed = scenario.scenario_id != "FI-003"
        return (
            {
                "id": scenario.scenario_id,
                "status": "pass" if passed else "fail",
                "duration_seconds": 1.5,
                "checks": list(scenario.checks),
                "evidence_refs": list(scenario.selectors),
                "command": "uv run pytest --no-cov -q ...",
                "result_tail": "ok",
            },
            passed,
        )

    monkeypatch.setattr(generator, "_run_scenario", _fake_run_scenario)
    monkeypatch.setattr(generator, "verify_evidence", lambda **_: 0)

    output = tmp_path / "evidence.json"
    artifact, overall_passed = generator.generate_evidence(
        output=output,
        executed_by="executor@valdrics.local",
        approved_by="approver@valdrics.local",
        profile="enforcement_failure_injection",
        cwd=tmp_path,
        timeout_seconds=60.0,
    )

    assert overall_passed is False
    assert calls["count"] == len(generator.SCENARIOS)
    assert artifact["summary"] == {
        "total_scenarios": len(generator.SCENARIOS),
        "passed_scenarios": len(generator.SCENARIOS) - 1,
        "failed_scenarios": 1,
        "overall_passed": False,
    }
    assert [row["id"] for row in artifact["scenarios"]] == [
        scenario.scenario_id for scenario in generator.SCENARIOS
    ]

    on_disk = json.loads(output.read_text(encoding="utf-8"))
    assert on_disk["runner"] == "staged_failure_injection"
    assert on_disk["execution_class"] == "staged"


def test_generate_evidence_does_not_leave_output_when_verification_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_run_scenario(
        scenario: generator.FailureScenario, *, cwd: Path, timeout_seconds: float
    ) -> tuple[dict[str, object], bool]:
        del cwd, timeout_seconds
        return (
            {
                "id": scenario.scenario_id,
                "status": "pass",
                "duration_seconds": 0.5,
                "checks": list(scenario.checks),
                "evidence_refs": list(scenario.selectors),
                "command": "pytest",
                "result_tail": "ok",
            },
            True,
        )

    monkeypatch.setattr(generator, "_run_scenario", _fake_run_scenario)
    monkeypatch.setattr(
        generator,
        "verify_evidence",
        lambda **_: (_ for _ in ()).throw(
            ValueError("failure injection verification failed")
        ),
    )

    output = tmp_path / "evidence.json"
    with pytest.raises(ValueError, match="failure injection verification failed"):
        generator.generate_evidence(
            output=output,
            executed_by="executor@valdrics.local",
            approved_by="approver@valdrics.local",
            profile="enforcement_failure_injection",
            cwd=tmp_path,
            timeout_seconds=60.0,
        )

    assert not output.exists()


def test_main_exit_code_follows_overall_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured_outputs: list[Path] = []

    def _fake_generate_evidence(**kwargs: object) -> tuple[dict[str, object], bool]:
        output = kwargs["output"]
        assert isinstance(output, Path)
        captured_outputs.append(output)
        output.write_text(
            json.dumps(
                {
                    "profile": "enforcement_failure_injection",
                    "summary": {
                        "total_scenarios": 5,
                        "passed_scenarios": 5,
                        "failed_scenarios": 0,
                        "overall_passed": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        return (
            {
                "profile": "enforcement_failure_injection",
                "summary": {
                    "total_scenarios": 5,
                    "passed_scenarios": 5,
                    "failed_scenarios": 0,
                    "overall_passed": True,
                },
            },
            True,
        )

    monkeypatch.setattr(generator, "generate_evidence", _fake_generate_evidence)

    exit_code = generator.main(
        [
            "--output",
            str(tmp_path / "artifact.json"),
            "--executed-by",
            "exec@valdrics.local",
            "--approved-by",
            "approve@valdrics.local",
        ]
    )
    assert exit_code == 0
    assert captured_outputs == [tmp_path / "artifact.json"]
    assert (tmp_path / "artifact.json").exists()


def test_main_does_not_leave_output_when_verification_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "artifact.json"

    def _fake_generate_evidence(**kwargs: object) -> tuple[dict[str, object], bool]:
        assert kwargs["output"] == output
        raise ValueError("failure injection verification failed")

    monkeypatch.setattr(generator, "generate_evidence", _fake_generate_evidence)

    with pytest.raises(ValueError, match="failure injection verification failed"):
        generator.main(
            [
                "--output",
                str(output),
                "--executed-by",
                "exec@valdrics.local",
                "--approved-by",
                "approve@valdrics.local",
            ]
        )

    assert not output.exists()


def test_main_promotes_verified_temp_output_to_final_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "artifact.json"
    captured_outputs: list[Path] = []

    def _fake_generate_evidence(**kwargs: object) -> tuple[dict[str, object], bool]:
        final_output = kwargs["output"]
        assert isinstance(final_output, Path)
        captured_outputs.append(final_output)
        final_output.write_text(
            json.dumps(
                {
                    "profile": "enforcement_failure_injection",
                    "summary": {
                        "total_scenarios": 5,
                        "passed_scenarios": 5,
                        "failed_scenarios": 0,
                        "overall_passed": True,
                    },
                }
            ),
            encoding="utf-8",
        )
        return (
            {
                "profile": "enforcement_failure_injection",
                "summary": {
                    "total_scenarios": 5,
                    "passed_scenarios": 5,
                    "failed_scenarios": 0,
                    "overall_passed": True,
                },
            },
            True,
        )

    monkeypatch.setattr(generator, "generate_evidence", _fake_generate_evidence)

    assert (
        generator.main(
            [
                "--output",
                str(output),
                "--executed-by",
                "exec@valdrics.local",
                "--approved-by",
                "approve@valdrics.local",
            ]
        )
        == 0
    )

    assert output.exists()
    assert captured_outputs == [output]


def test_main_resolves_relative_output_from_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(generator, "_repo_root", lambda: repo_root)

    def _fake_run_scenario(
        scenario: generator.FailureScenario, *, cwd: Path, timeout_seconds: float
    ) -> tuple[dict[str, object], bool]:
        del cwd, timeout_seconds
        return (
            {
                "id": scenario.scenario_id,
                "status": "pass",
                "duration_seconds": 0.5,
                "checks": list(scenario.checks),
                "evidence_refs": list(scenario.selectors),
                "command": "pytest",
                "result_tail": "ok",
            },
            True,
        )

    monkeypatch.setattr(generator, "_run_scenario", _fake_run_scenario)
    verify_calls: list[dict[str, object]] = []

    def _fake_verify(**kwargs: object) -> int:
        verify_calls.append(kwargs)
        return 0

    monkeypatch.setattr(generator, "verify_evidence", _fake_verify)

    assert (
        generator.main(
            [
                "--output",
                "artifacts/failure_injection.json",
                "--executed-by",
                "exec@valdrics.local",
                "--approved-by",
                "approve@valdrics.local",
            ]
        )
        == 0
    )
    expected_output = repo_root / "artifacts" / "failure_injection.json"
    assert expected_output.exists()
    assert len(verify_calls) == 1
    verify_path = verify_calls[0]["evidence_path"]
    assert isinstance(verify_path, Path)
    assert verify_path.parent == expected_output.parent
    assert verify_path != expected_output
    assert verify_calls[0]["expected_profile"] == "enforcement_failure_injection"
    assert verify_calls[0]["max_artifact_age_hours"] == 4.0


def test_main_rejects_invalid_profile_before_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        generator,
        "_run_scenario",
        lambda *_, **__: (_ for _ in ()).throw(
            AssertionError("scenario execution should not run")
        ),
    )

    with pytest.raises(ValueError, match="profile must equal"):
        generator.main(
            [
                "--output",
                str(tmp_path / "artifact.json"),
                "--executed-by",
                "exec@valdrics.local",
                "--approved-by",
                "approve@valdrics.local",
                "--profile",
                "custom_profile",
            ]
        )


def test_run_scenario_uses_isolated_pytest_env(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _fake_run(*args: object, **kwargs: object) -> MagicMock:
        captured["env"] = kwargs.get("env")
        captured["timeout"] = kwargs.get("timeout")
        completed = MagicMock()
        completed.returncode = 0
        completed.stdout = "ok"
        completed.stderr = ""
        return completed

    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://prod.example/app")
    monkeypatch.setenv("DB_SSL_MODE", "require")
    monkeypatch.setenv("PGSSLMODE", "require")
    monkeypatch.setattr(generator.subprocess, "run", _fake_run)

    scenario = generator.FailureScenario(
        scenario_id="FI-TEST",
        checks=("isolated env",),
        selectors=(
            "tests/unit/enforcement/test_enforcement_api.py::test_gate_failsafe_timeout_and_error_modes",
        ),
    )
    payload, passed = generator._run_scenario(
        scenario,
        cwd=Path("."),
        timeout_seconds=240.0,
    )
    timeout = captured.get("timeout")

    assert passed is True
    assert payload["status"] == "pass"
    env = captured["env"]
    assert isinstance(env, dict)
    assert "DATABASE_URL" not in env
    assert "DB_SSL_MODE" not in env
    assert "PGSSLMODE" not in env
    assert env["TESTING"] == "true"
    assert env["DEBUG"] == "false"
    assert timeout == 240.0


def test_run_scenario_marks_timeout_as_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    def _timeout(*args: object, **kwargs: object) -> MagicMock:
        raise subprocess.TimeoutExpired(cmd=kwargs.get("args", "pytest"), timeout=5.0)

    monkeypatch.setattr(generator.subprocess, "run", _timeout)
    scenario = generator.FailureScenario(
        scenario_id="FI-TEST",
        checks=("timeout",),
        selectors=(
            "tests/unit/enforcement/test_enforcement_api.py::test_gate_failsafe_timeout_and_error_modes",
        ),
    )

    payload, passed = generator._run_scenario(
        scenario,
        cwd=Path("."),
        timeout_seconds=5.0,
    )

    assert passed is False
    assert payload["status"] == "fail"
    assert "timeout after 5.0s" in str(payload["result_tail"])


def test_main_rejects_non_positive_pytest_timeout_before_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        generator,
        "generate_evidence",
        lambda **_: (_ for _ in ()).throw(AssertionError("generation should not run")),
    )

    with pytest.raises(ValueError, match="pytest_timeout_seconds must be > 0"):
        generator.main(
            [
                "--output",
                str(tmp_path / "artifact.json"),
                "--executed-by",
                "exec@valdrics.local",
                "--approved-by",
                "approve@valdrics.local",
                "--pytest-timeout-seconds",
                "0",
            ]
        )
