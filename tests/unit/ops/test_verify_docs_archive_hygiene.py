from __future__ import annotations

from pathlib import Path

from scripts.verify_docs_archive_hygiene import verify_docs_archive_hygiene


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
