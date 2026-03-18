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
