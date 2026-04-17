from __future__ import annotations

import os
from pathlib import Path

import pytest

import scripts.verify_repo_root_hygiene as repo_root_hygiene_verifier
from scripts.verify_repo_root_hygiene import (
    collect_root_hygiene_violations,
    main,
)


def test_collect_root_hygiene_violations_detects_exact_and_glob_matches(
    tmp_path: Path,
) -> None:
    (tmp_path / "artifact.json").write_text("x", encoding="utf-8")
    (tmp_path / "test_alpha.sqlite").write_text("", encoding="utf-8")
    (tmp_path / "valdrics_local_dev.sqlite3").write_text("", encoding="utf-8")
    (tmp_path / "helm" / "valdrics").mkdir(parents=True)
    (tmp_path / "terraform" / "modules" / "legacy").mkdir(parents=True)
    (tmp_path / "README.md").write_text("ok", encoding="utf-8")

    violations = collect_root_hygiene_violations(tmp_path)
    assert [item.name for item in violations] == [
        "artifact.json",
        "helm",
        "terraform/modules",
        "test_alpha.sqlite",
        "valdrics_local_dev.sqlite3",
    ]


def test_main_returns_zero_when_root_is_clean(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("ok", encoding="utf-8")
    assert main(["--root", str(tmp_path)]) == 0


def test_main_returns_one_when_prohibited_files_exist(tmp_path: Path) -> None:
    (tmp_path / "feedback.md").write_text("note", encoding="utf-8")
    assert main(["--root", str(tmp_path)]) == 1


def test_pytest_async_engine_uses_temp_directory_fixture() -> None:
    conftest_text = Path("tests/conftest.py").read_text(encoding="utf-8")

    assert 'def async_engine(tmp_path_factory):' in conftest_text
    assert 'build_sqlite_test_database_path(tmp_path_factory.mktemp("sqlite-db"))' in conftest_text
    assert 'db_file = f"test_{uuid4().hex}.sqlite"' not in conftest_text


def test_collect_root_hygiene_violations_rejects_non_directory_root(tmp_path: Path) -> None:
    root = tmp_path / "root.txt"
    root.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a directory"):
        collect_root_hygiene_violations(root)


def test_main_rejects_non_directory_root(tmp_path: Path) -> None:
    root = tmp_path / "root.txt"
    root.write_text("not-a-directory", encoding="utf-8")

    assert main(["--root", str(root)]) == 2


def test_main_resolves_relative_root_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(repo_root_hygiene_verifier.__file__).resolve().parents[1]
    captured: dict[str, Path] = {}

    def _capture(
        root: Path,
        *,
        prohibited_patterns: tuple[str, ...] = (),
        prohibited_paths: tuple[str, ...] = (),
    ) -> tuple[object, ...]:
        captured["root"] = root
        return ()

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        repo_root_hygiene_verifier,
        "collect_root_hygiene_violations",
        _capture,
    )

    assert main(["--root", "."]) == 0
    assert captured["root"] == repo_root


def test_main_rejects_relative_root_repo_escape() -> None:
    assert main(["--root", os.path.join("..", "..")]) == 2
