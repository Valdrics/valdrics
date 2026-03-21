from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import scripts.verify_python_module_preferred_budget_baseline as preferred_baseline_verifier
from scripts.verify_python_module_preferred_budget_baseline import (
    main,
    verify_against_baseline,
)
from scripts.verify_python_module_size_budget import ModuleSizePreferredBreach


def _write_lines(path: Path, line_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(f"line_{idx}" for idx in range(line_count)), encoding="utf-8")


def test_verify_against_baseline_reports_added_removed_and_changed() -> None:
    baseline = (
        ModuleSizePreferredBreach("app/a.py", 501, 500),
        ModuleSizePreferredBreach("app/b.py", 520, 500),
    )
    current = (
        ModuleSizePreferredBreach("app/b.py", 521, 500),
        ModuleSizePreferredBreach("app/c.py", 530, 500),
    )

    added, removed, changed = verify_against_baseline(
        current=current,
        baseline=baseline,
    )

    assert [item.path for item in added] == ["app/c.py"]
    assert [item.path for item in removed] == ["app/a.py"]
    assert [(old.path, old.lines, new.lines) for old, new in changed] == [
        ("app/b.py", 520, 521)
    ]


def test_main_roundtrip_write_and_verify(tmp_path: Path) -> None:
    _write_lines(tmp_path / "app/ok.py", 100)
    _write_lines(tmp_path / "app/large.py", 501)
    baseline_path = tmp_path / "baseline.json"

    write_exit = main(
        [
            "--root",
            str(tmp_path),
            "--baseline-path",
            str(baseline_path),
            "--write-baseline",
        ]
    )
    assert write_exit == 0

    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    assert payload["root"] == "."
    assert payload["breaches"][0]["path"] == "app/large.py"

    verify_exit = main(
        [
            "--root",
            str(tmp_path),
            "--baseline-path",
            str(baseline_path),
        ]
    )
    assert verify_exit == 0


def test_main_fails_when_repo_drift_exceeds_baseline(tmp_path: Path) -> None:
    _write_lines(tmp_path / "app/large.py", 505)
    baseline_path = tmp_path / "baseline.json"
    baseline_path.write_text(
        json.dumps(
            {
                "root": str(tmp_path),
                "breaches": [
                    {
                        "path": "app/large.py",
                        "lines": 501,
                        "preferred_max_lines": 500,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--baseline-path",
            str(baseline_path),
        ]
    )
    assert exit_code == 1


def test_main_write_baseline_does_not_leave_output_when_promotion_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_lines(tmp_path / "app/large.py", 501)
    baseline_path = tmp_path / "baseline.json"
    path_type = type(baseline_path)
    original_replace = path_type.replace

    def _failing_replace(self: Path, target: Path) -> Path:
        if self.parent == baseline_path.parent and Path(target) == baseline_path:
            raise OSError("simulated promotion failure")
        return original_replace(self, target)

    monkeypatch.setattr(path_type, "replace", _failing_replace)

    with pytest.raises(OSError, match="simulated promotion failure"):
        main(
            [
                "--root",
                str(tmp_path),
                "--baseline-path",
                str(baseline_path),
                "--write-baseline",
            ]
        )

    assert not baseline_path.exists()
    assert not list(baseline_path.parent.glob(f".{baseline_path.stem}.*{baseline_path.suffix}.tmp"))


def test_main_resolves_relative_root_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(preferred_baseline_verifier.__file__).resolve().parents[1]
    captured: dict[str, Path] = {}

    def _capture_breaches(
        root: Path,
        *,
        preferred_max_lines: int,
    ) -> tuple[ModuleSizePreferredBreach, ...]:
        captured["root"] = root
        return ()

    def _capture_write(
        *,
        path: Path,
        root: Path,
        breaches: tuple[ModuleSizePreferredBreach, ...],
    ) -> None:
        captured["baseline_path"] = path
        captured["write_root"] = root

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        preferred_baseline_verifier,
        "collect_module_size_preferred_breaches",
        _capture_breaches,
    )
    monkeypatch.setattr(
        preferred_baseline_verifier,
        "_write_baseline",
        _capture_write,
    )

    assert main(["--root", "app/..", "--write-baseline"]) == 0
    assert captured["root"] == repo_root
    assert captured["write_root"] == repo_root
    assert captured["baseline_path"] == (
        repo_root / "docs" / "ops" / "evidence" / "python_module_size_preferred_baseline.json"
    )


def test_main_rejects_relative_root_repo_escape() -> None:
    assert main(["--root", os.path.join("..", ".."), "--write-baseline"]) == 2


def test_main_rejects_relative_baseline_repo_escape(tmp_path: Path) -> None:
    _write_lines(tmp_path / "app/large.py", 501)

    assert (
        main(
            [
                "--root",
                str(tmp_path),
                "--baseline-path",
                os.path.join("..", "outside.json"),
                "--write-baseline",
            ]
        )
        == 2
    )
