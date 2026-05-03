from __future__ import annotations

import os
from pathlib import Path

import pytest

import scripts.verify_reports_archive_hygiene as reports_archive_hygiene_verifier
from scripts.verify_reports_archive_hygiene import (
    main,
    verify_reports_archive_hygiene,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_verify_reports_archive_hygiene_flags_active_production_fix_pack(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "reports/production_fixes/DEPLOYMENT_FIXES_GUIDE.md", "stale\n")

    errors = verify_reports_archive_hygiene(root=tmp_path)
    assert errors == [
        "reports/production_fixes: prohibited active duplicate/orphan report pack. Historical production hardening pack — remove it."
    ]


def test_verify_reports_archive_hygiene_flags_active_dated_audit_snapshot(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "reports/audit/LANDING_PUBLIC_IMPLEMENTATION_REPORT_2026-03-21.md",
        "stale audit snapshot\n",
    )

    errors = verify_reports_archive_hygiene(root=tmp_path)
    assert errors == [
        "reports/audit/LANDING_PUBLIC_IMPLEMENTATION_REPORT_2026-03-21.md: prohibited active duplicate/orphan historical report. Historical dated audit snapshots — remove them."
    ]


def test_verify_reports_archive_hygiene_accepts_archived_report_locations(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path
        / "reports/archive/2026-q1/production_fixes/DEPLOYMENT_FIXES_GUIDE.md",
        "archived pack\n",
    )
    _write(
        tmp_path / "reports/archive/2026-q1/audit/FULL_STACK_AUDIT_REPORT_2026-02-13.md",
        "archived audit\n",
    )
    _write(
        tmp_path
        / "reports/audit/archive/2026_01_24_audit/TECHNICAL_REVIEW_MASTER_SUMMARY.md",
        "existing archive\n",
    )

    assert verify_reports_archive_hygiene(root=tmp_path) == []


def test_main_returns_zero_when_root_is_clean(tmp_path: Path) -> None:
    _write(tmp_path / "README.md", "clean\n")
    assert main(["--root", str(tmp_path)]) == 0


def test_main_returns_one_when_prohibited_reports_exist(tmp_path: Path) -> None:
    _write(tmp_path / "reports/production_fixes/INDEX.md", "stale\n")
    assert main(["--root", str(tmp_path)]) == 1


def test_verify_reports_archive_hygiene_rejects_non_directory_root(
    tmp_path: Path,
) -> None:
    root = tmp_path / "root.txt"
    root.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a directory"):
        verify_reports_archive_hygiene(root=root)


def test_main_rejects_non_directory_root(tmp_path: Path) -> None:
    root = tmp_path / "root.txt"
    root.write_text("not-a-directory", encoding="utf-8")

    assert main(["--root", str(root)]) == 2


def test_main_resolves_relative_root_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(reports_archive_hygiene_verifier.__file__).resolve().parents[1]
    captured: dict[str, Path] = {}

    def _capture(*, root: Path) -> list[str]:
        captured["root"] = root
        return []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        reports_archive_hygiene_verifier,
        "verify_reports_archive_hygiene",
        _capture,
    )

    assert main(["--root", "."]) == 0
    assert captured["root"] == repo_root


def test_main_rejects_relative_root_repo_escape() -> None:
    assert main(["--root", os.path.join("..", "..")]) == 2
