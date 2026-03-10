from __future__ import annotations

from pathlib import Path

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
    (tmp_path / "README.md").write_text("ok", encoding="utf-8")

    violations = collect_root_hygiene_violations(tmp_path)
    assert [item.name for item in violations] == [
        "artifact.json",
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

    assert 'async def async_engine(tmp_path_factory):' in conftest_text
    assert 'build_sqlite_test_database_path(tmp_path_factory.mktemp("sqlite-db"))' in conftest_text
    assert 'db_file = f"test_{uuid4().hex}.sqlite"' not in conftest_text
