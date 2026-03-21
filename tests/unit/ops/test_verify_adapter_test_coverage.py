from __future__ import annotations

import os
from pathlib import Path

import pytest

import scripts.verify_adapter_test_coverage as adapter_verifier
from scripts.verify_adapter_test_coverage import find_uncovered_adapters, main


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_find_uncovered_adapters_detects_missing_references(tmp_path: Path) -> None:
    adapters_root = tmp_path / "adapters"
    tests_root = tmp_path / "tests"

    _write(adapters_root / "alpha.py", "VALUE = 1\n")
    _write(adapters_root / "beta.py", "VALUE = 2\n")
    _write(
        tests_root / "test_alpha_adapter.py",
        "from app.shared.adapters.alpha import VALUE\n",
    )

    missing = find_uncovered_adapters(
        adapters_root=adapters_root,
        tests_root=tests_root,
    )

    assert missing == ("beta",)


def test_find_uncovered_adapters_honors_allowlist(tmp_path: Path) -> None:
    adapters_root = tmp_path / "adapters"
    tests_root = tmp_path / "tests"
    _write(adapters_root / "beta.py", "VALUE = 2\n")

    missing = find_uncovered_adapters(
        adapters_root=adapters_root,
        tests_root=tests_root,
        allowlist={"beta"},
    )

    assert missing == ()


def test_main_returns_success_when_all_adapters_covered(tmp_path: Path) -> None:
    adapters_root = tmp_path / "adapters"
    tests_root = tmp_path / "tests"
    _write(adapters_root / "alpha.py", "VALUE = 1\n")
    _write(
        tests_root / "test_adapter_refs.py",
        "import app.shared.adapters.alpha\n",
    )

    exit_code = main(
        [
            "--adapters-root",
            str(adapters_root),
            "--tests-root",
            str(tests_root),
        ]
    )

    assert exit_code == 0


def test_main_resolves_relative_roots_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    adapters_root = repo_root / "adapters"
    tests_root = repo_root / "tests"
    _write(adapters_root / "alpha.py", "VALUE = 1\n")
    _write(tests_root / "test_adapter_refs.py", "import app.shared.adapters.alpha\n")
    monkeypatch.setattr(adapter_verifier, "_repo_root", lambda: repo_root)

    old_cwd = Path.cwd()
    try:
        os.chdir(tmp_path)
        exit_code = main(["--adapters-root", "adapters", "--tests-root", "tests"])
    finally:
        os.chdir(old_cwd)

    assert exit_code == 0


def test_main_rejects_relative_root_repo_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(adapter_verifier, "_repo_root", lambda: repo_root)

    assert main(["--adapters-root", "../escape/adapters"]) == 2
