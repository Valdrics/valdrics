from __future__ import annotations

import os
from pathlib import Path

import pytest

import scripts.verify_frontend_module_size_budget as frontend_budget_verifier
from scripts.verify_frontend_module_size_budget import (
    PREFERRED_MAX_LINES,
    collect_frontend_module_size_preferred_breaches,
    collect_frontend_module_size_violations,
    main,
)


def _write_lines(path: Path, line_count: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(f"line_{idx}" for idx in range(line_count))
    path.write_text(body, encoding="utf-8")


def test_collect_frontend_module_size_violations_uses_default_budget(
    tmp_path: Path,
) -> None:
    _write_lines(tmp_path / "dashboard/src/small.svelte", 10)
    _write_lines(tmp_path / "dashboard/src/large.ts", 550)

    violations = collect_frontend_module_size_violations(
        tmp_path,
        default_max_lines=500,
    )
    assert [item.path for item in violations] == ["dashboard/src/large.ts"]


def test_collect_frontend_module_size_violations_honors_overrides(
    tmp_path: Path,
) -> None:
    _write_lines(tmp_path / "dashboard/src/over.js", 550)

    violations = collect_frontend_module_size_violations(
        tmp_path,
        default_max_lines=500,
        overrides={"dashboard/src/over.js": 600},
    )
    assert violations == ()


def test_collect_frontend_module_size_violations_ignores_non_frontend_extensions(
    tmp_path: Path,
) -> None:
    _write_lines(tmp_path / "dashboard/src/readme.md", 600)
    _write_lines(tmp_path / "dashboard/src/within.css", 100)

    violations = collect_frontend_module_size_violations(
        tmp_path,
        default_max_lines=500,
    )
    assert violations == ()


def test_collect_frontend_module_size_preferred_breaches_flags_warning_paths(
    tmp_path: Path,
) -> None:
    _write_lines(tmp_path / "dashboard/src/within.svelte", PREFERRED_MAX_LINES)
    _write_lines(tmp_path / "dashboard/src/above.svelte", PREFERRED_MAX_LINES + 1)

    breaches = collect_frontend_module_size_preferred_breaches(
        tmp_path,
        preferred_max_lines=PREFERRED_MAX_LINES,
    )
    assert [item.path for item in breaches] == ["dashboard/src/above.svelte"]


def test_main_returns_failure_when_any_frontend_module_exceeds_budget(
    tmp_path: Path,
) -> None:
    _write_lines(tmp_path / "dashboard/src/too_big.css", 510)
    assert main(["--root", str(tmp_path), "--default-max-lines", "500"]) == 1


def test_main_returns_success_with_preferred_warnings(
    tmp_path: Path,
    capsys,
) -> None:
    _write_lines(tmp_path / "dashboard/src/above_preferred.ts", 401)

    exit_code = main(
        [
            "--root",
            str(tmp_path),
            "--default-max-lines",
            "500",
            "--preferred-max-lines",
            "400",
        ]
    )
    captured = capsys.readouterr().out
    assert exit_code == 0
    assert "warning found 1 module(s) above preferred target" in captured


def test_collect_frontend_module_size_violations_rejects_non_directory_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root.txt"
    root.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a directory"):
        collect_frontend_module_size_violations(root)


def test_main_rejects_non_directory_root(tmp_path: Path) -> None:
    root = tmp_path / "root.txt"
    root.write_text("not-a-directory", encoding="utf-8")

    assert main(["--root", str(root)]) == 2


def test_main_resolves_relative_root_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(frontend_budget_verifier.__file__).resolve().parents[1]
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
        frontend_budget_verifier,
        "collect_frontend_module_size_preferred_breaches",
        _capture_preferred,
    )
    monkeypatch.setattr(
        frontend_budget_verifier,
        "collect_frontend_module_size_violations",
        _capture_violations,
    )

    assert main(["--root", "dashboard/.."]) == 0
    assert captured["root"] == repo_root


def test_main_rejects_relative_root_repo_escape() -> None:
    assert main(["--root", os.path.join("..", "..")]) == 2
