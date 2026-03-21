from __future__ import annotations

import os
from pathlib import Path

import pytest

import scripts.verify_docs_archive_hygiene as docs_archive_hygiene_verifier
from scripts.verify_docs_archive_hygiene import main, verify_docs_archive_hygiene


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_verify_docs_archive_hygiene_accepts_referenced_dated_doc(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs/ops/landing_page_audit_closure_2026-03-02.md",
        "landing closure snapshot\n",
    )
    _write(
        tmp_path / "docs/ops/README.md",
        "See docs/ops/landing_page_audit_closure_2026-03-02.md for the active closure record.\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == []


def test_verify_docs_archive_hygiene_flags_orphaned_dated_doc(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs/ops/orphaned_snapshot_2026-03-03.md",
        "orphaned snapshot\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/ops/orphaned_snapshot_2026-03-03.md: orphaned dated doc should be archived or referenced explicitly."
    ]


def test_verify_docs_archive_hygiene_flags_prohibited_active_duplicate_doc(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "docs/incident_response_plan.md", "old duplicate\n")
    _write(
        tmp_path / "docs/runbooks/incident_response.md",
        "active runbook\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert any("docs/incident_response_plan.md" in error for error in errors)


def test_verify_docs_archive_hygiene_rejects_missing_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="root does not exist"):
        verify_docs_archive_hygiene(root=tmp_path / "missing")


def test_verify_docs_archive_hygiene_rejects_non_directory_root(tmp_path: Path) -> None:
    root = tmp_path / "root.txt"
    root.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a directory"):
        verify_docs_archive_hygiene(root=root)


def test_main_resolves_relative_root_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = Path(docs_archive_hygiene_verifier.__file__).resolve().parents[1]
    captured: dict[str, Path] = {}

    def _capture(*, root: Path) -> list[str]:
        captured["root"] = root
        return []

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        docs_archive_hygiene_verifier,
        "verify_docs_archive_hygiene",
        _capture,
    )

    assert main(["--root", "docs/.."]) == 0
    assert captured["root"] == repo_root


def test_main_rejects_relative_root_repo_escape() -> None:
    assert main(["--root", os.path.join("..", "..")]) == 2
