from __future__ import annotations

from pathlib import Path

import pytest

import scripts.generate_key_rotation_drill_evidence as drill_generator


def _failing_execution() -> tuple[dict[str, bool], dict[str, bool], dict[str, str]]:
    field_results = {
        check.key: True for check in drill_generator._all_drill_checks()
    }
    field_results["pre_rotation_tokens_accepted"] = False

    selector_results = {
        check.selector: field_results[check.key]
        for check in drill_generator._all_drill_checks()
    }
    selector_logs = {
        check.selector: (
            f"{check.key} failed"
            if not field_results[check.key]
            else f"{check.key} ok"
        )
        for check in drill_generator._all_drill_checks()
    }
    return field_results, selector_results, selector_logs


def test_main_allow_check_failures_emits_fail_artifact_and_skips_verifier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "key_rotation_drill.md"
    monkeypatch.setattr(drill_generator, "_execute_checks", lambda **_: _failing_execution())

    verifier_called = False

    def _unexpected_verify(**_: object) -> int:
        nonlocal verifier_called
        verifier_called = True
        raise AssertionError("verifier should be skipped for failing allow_check_failures output")

    monkeypatch.setattr(
        drill_generator,
        "verify_key_rotation_drill_evidence",
        _unexpected_verify,
    )

    exit_code = drill_generator.main(
        [
            "--output",
            str(output),
            "--allow-check-failures",
        ]
    )

    text = output.read_text(encoding="utf-8")
    assert exit_code == 2
    assert verifier_called is False
    assert "- pre_rotation_tokens_accepted: false" in text
    assert "- post_drill_status: FAIL" in text


def test_main_writes_fail_artifact_before_raising_when_failures_not_allowed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "key_rotation_drill.md"
    monkeypatch.setattr(drill_generator, "_execute_checks", lambda **_: _failing_execution())
    monkeypatch.setattr(
        drill_generator,
        "verify_key_rotation_drill_evidence",
        lambda **_: (_ for _ in ()).throw(AssertionError("verifier should not run")),
    )

    with pytest.raises(RuntimeError, match="key-rotation live checks failed for"):
        drill_generator.main(
            [
                "--output",
                str(output),
            ]
        )

    text = output.read_text(encoding="utf-8")
    assert "- pre_rotation_tokens_accepted: false" in text
    assert "- post_drill_status: FAIL" in text


def test_main_rejects_non_positive_pytest_timeout_before_running_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "key_rotation_drill.md"
    monkeypatch.setattr(
        drill_generator,
        "_execute_checks",
        lambda **_: (_ for _ in ()).throw(AssertionError("checks should not run")),
    )

    with pytest.raises(ValueError, match="pytest_timeout_seconds must be > 0"):
        drill_generator.main(
            [
                "--output",
                str(output),
                "--pytest-timeout-seconds",
                "0",
            ]
        )


def test_main_rejects_negative_selector_retries_before_running_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "key_rotation_drill.md"
    monkeypatch.setattr(
        drill_generator,
        "_execute_checks",
        lambda **_: (_ for _ in ()).throw(AssertionError("checks should not run")),
    )

    with pytest.raises(ValueError, match="selector_retries must be >= 0"):
        drill_generator.main(
            [
                "--output",
                str(output),
                "--selector-retries",
                "-1",
            ]
        )


def test_main_rejects_non_positive_max_drill_age_before_running_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "key_rotation_drill.md"
    monkeypatch.setattr(
        drill_generator,
        "_execute_checks",
        lambda **_: (_ for _ in ()).throw(AssertionError("checks should not run")),
    )

    with pytest.raises(ValueError, match="max_drill_age_days must be > 0"):
        drill_generator.main(
            [
                "--output",
                str(output),
                "--max-drill-age-days",
                "0",
            ]
        )


@pytest.mark.parametrize(
    "output",
    [
        "tests/unit/enforcement/test_key_rotation_drill_selectors.py",
        "scripts/verify_key_rotation_drill_evidence.py",
        "docs/ops/key-rotation-drill-2026-02-27.md",
    ],
)
def test_main_rejects_output_collisions_with_protected_drill_files(
    monkeypatch: pytest.MonkeyPatch,
    output: str,
) -> None:
    monkeypatch.setattr(
        drill_generator,
        "_execute_checks",
        lambda **_: (_ for _ in ()).throw(AssertionError("checks should not run")),
    )

    with pytest.raises(
        ValueError,
        match="output must not overwrite key-rotation drill source or verifier files",
    ):
        drill_generator.main(["--output", output])


def test_main_rejects_relative_protected_output_from_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(drill_generator, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        drill_generator,
        "_execute_checks",
        lambda **_: (_ for _ in ()).throw(AssertionError("checks should not run")),
    )

    with pytest.raises(
        ValueError,
        match="output must not overwrite key-rotation drill source or verifier files",
    ):
        drill_generator.main(
            ["--output", "docs/ops/key-rotation-drill-2026-02-27.md"]
        )


def test_main_resolves_relative_output_from_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(drill_generator, "_repo_root", lambda: repo_root)

    field_results = {check.key: True for check in drill_generator._all_drill_checks()}
    selector_results = {
        check.selector: True for check in drill_generator._all_drill_checks()
    }
    selector_logs = {
        check.selector: f"{check.key} ok"
        for check in drill_generator._all_drill_checks()
    }
    monkeypatch.setattr(
        drill_generator,
        "_execute_checks",
        lambda **_: (field_results, selector_results, selector_logs),
    )
    verify_calls: list[dict[str, object]] = []

    def _fake_verify(**kwargs: object) -> int:
        verify_calls.append(kwargs)
        return 0

    monkeypatch.setattr(
        drill_generator,
        "verify_key_rotation_drill_evidence",
        _fake_verify,
    )

    assert (
        drill_generator.main(["--output", "artifacts/key_rotation_drill.md"]) == 0
    )
    expected_output = repo_root / "artifacts" / "key_rotation_drill.md"
    assert expected_output.exists()
    assert verify_calls == [
        {
            "drill_path": expected_output,
            "max_drill_age_days": 120.0,
        }
    ]


def test_main_rejects_output_parent_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")
    monkeypatch.setattr(
        drill_generator,
        "_execute_checks",
        lambda **_: (_ for _ in ()).throw(AssertionError("checks should not run")),
    )

    with pytest.raises(ValueError, match="output parent must be a directory path"):
        drill_generator.main(["--output", str(blocked_parent / "key_rotation_drill.md")])


def test_main_rejects_directory_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "drill-output"
    output_dir.mkdir()
    monkeypatch.setattr(
        drill_generator,
        "_execute_checks",
        lambda **_: (_ for _ in ()).throw(AssertionError("checks should not run")),
    )

    with pytest.raises(ValueError, match="output must be a file path"):
        drill_generator.main(["--output", str(output_dir)])


def test_execute_checks_runs_selectors_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cwd_calls: list[Path] = []

    class _Completed:
        returncode = 0
        stdout = "ok\n"
        stderr = ""

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args
        cwd_calls.append(kwargs["cwd"])
        return _Completed()

    monkeypatch.setattr(drill_generator.subprocess, "run", _fake_run)

    drill_generator._execute_checks(timeout_seconds=1.0, retries=0)

    assert cwd_calls
    assert all(cwd == drill_generator._repo_root() for cwd in cwd_calls)
