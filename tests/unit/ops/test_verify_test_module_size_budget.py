from __future__ import annotations

import os
from pathlib import Path

import pytest

import scripts.verify_test_module_size_budget as test_budget_verifier
from scripts.verify_test_module_size_budget import (
    PREFERRED_MAX_LINES,
    collect_test_module_size_preferred_breaches,
    collect_test_module_size_violations,
    main,
)


def _write_lines(path: Path, line_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"line_{idx}" for idx in range(line_count))
    path.write_text(body, encoding="utf-8")


def test_collect_test_module_size_violations_uses_default_budget(tmp_path: Path) -> None:
    _write_lines(tmp_path / "tests/small.py", 10)
    _write_lines(tmp_path / "tests/large.py", 2200)

    violations = collect_test_module_size_violations(tmp_path, default_max_lines=2000)
    assert [item.path for item in violations] == ["tests/large.py"]


def test_collect_test_module_size_violations_honors_overrides(tmp_path: Path) -> None:
    _write_lines(tmp_path / "tests/big.py", 2200)

    violations = collect_test_module_size_violations(
        tmp_path,
        default_max_lines=2000,
        overrides={"tests/big.py": 2300},
    )
    assert violations == ()


def test_main_returns_failure_when_any_test_module_exceeds_budget(
    tmp_path: Path,
) -> None:
    _write_lines(tmp_path / "tests/too_big.py", 2200)
    assert main(["--root", str(tmp_path), "--default-max-lines", "2000"]) == 1


def test_collect_test_module_size_preferred_breaches_flags_warning_paths(
    tmp_path: Path,
) -> None:
    _write_lines(tmp_path / "tests/within.py", PREFERRED_MAX_LINES)
    _write_lines(tmp_path / "tests/above.py", PREFERRED_MAX_LINES + 1)

    breaches = collect_test_module_size_preferred_breaches(
        tmp_path,
        preferred_max_lines=PREFERRED_MAX_LINES,
    )
    assert [item.path for item in breaches] == ["tests/above.py"]


def test_main_returns_success_with_preferred_warnings(
    tmp_path: Path,
    capsys,
) -> None:
    _write_lines(tmp_path / "tests/above_preferred.py", 1100)
    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--default-max-lines",
            "2000",
            "--preferred-max-lines",
            "1000",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "warning found 1 module(s) above preferred target" in captured


def test_collect_test_module_size_violations_rejects_non_directory_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root.txt"
    root.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a directory"):
        collect_test_module_size_violations(root)


def test_main_rejects_non_directory_root(tmp_path: Path) -> None:
    root = tmp_path / "root.txt"
    root.write_text("not-a-directory", encoding="utf-8")

    assert main(["--root", str(root)]) == 2


def test_main_resolves_relative_root_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(test_budget_verifier.__file__).resolve().parents[1]
    captured: dict[str, Path] = {}

    def _capture_preferred(root: Path, *, preferred_max_lines: int) -> tuple[object, ...]:
        captured["root"] = root
        return ()

    def _capture_violations(
        root: Path,
        *,
        default_max_lines: int,
        overrides: dict[str, int] | None = None,
    ) -> tuple[object, ...]:
        captured["root"] = root
        return ()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        test_budget_verifier,
        "collect_test_module_size_preferred_breaches",
        _capture_preferred,
    )
    monkeypatch.setattr(
        test_budget_verifier,
        "collect_test_module_size_violations",
        _capture_violations,
    )

    assert main(["--root", "tests/.."]) == 0
    assert captured["root"] == repo_root


def test_main_rejects_relative_root_repo_escape() -> None:
    assert main(["--root", os.path.join("..", "..")]) == 2
