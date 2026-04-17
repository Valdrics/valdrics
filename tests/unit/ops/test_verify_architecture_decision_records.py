from __future__ import annotations

from pathlib import Path

import pytest

from scripts.verify_architecture_decision_records import (
    REQUIRED_DOCUMENTS,
    _resolve_docs_root,
    main,
    verify_architecture_docs,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _required_doc_text(path: str) -> str:
    if path == "scheduler_orchestration_sequence.md":
        return """# Managed Scheduler Orchestration Sequence
```mermaid
sequenceDiagram
participant A as Cloud Scheduler
participant B as internal_orchestration.py
participant C as managed_work_runners.py
A->>B: dispatch
B->>C: run managed work
```
## Repository-Managed Local Loop
local worker loop
## Concurrency and Deterministic Replay
deterministic replay controls
## Observability and Snapshot Stability
trace and snapshot controls
## Failure Modes and Operational Misconfiguration Guards
Cloud Tasks
Cloud Run Jobs
fail-closed
"""

    token_map: dict[str, str] = {
        "ADR-0005-paystack-over-stripe.md": "Paystack and Stripe evaluation",
        "ADR-0006-supabase-managed-auth-platform.md": "Supabase over self-hosted auth",
        "ADR-0008-codecarbon-emissions-observability.md": "CodeCarbon emissions telemetry",
    }
    payload = token_map[path]
    return (
        "# Title\n"
        "## Context\n"
        f"{payload}\n"
        "## Decision\n"
        "Accepted.\n"
        "## Consequences\n"
        "Known tradeoffs documented.\n"
    )


def _write_all_required_docs(docs_root: Path) -> None:
    for requirement in REQUIRED_DOCUMENTS:
        _write(
            docs_root / requirement.path,
            _required_doc_text(requirement.path),
        )


def test_verify_architecture_docs_accepts_complete_set(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs" / "architecture"
    _write_all_required_docs(docs_root)
    assert verify_architecture_docs(docs_root) == ()


def test_verify_architecture_docs_rejects_missing_file(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs" / "architecture"
    _write_all_required_docs(docs_root)
    (docs_root / "ADR-0005-paystack-over-stripe.md").unlink()
    errors = verify_architecture_docs(docs_root)
    assert any("missing architecture doc" in error for error in errors)


def test_verify_architecture_docs_rejects_placeholder_token(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs" / "architecture"
    _write_all_required_docs(docs_root)
    _write(
        docs_root / "ADR-0006-supabase-managed-auth-platform.md",
        "# Title\n## Context\ntodo\n## Decision\nx\n## Consequences\ny\nSupabase self-hosted\n",
    )
    errors = verify_architecture_docs(docs_root)
    assert any("placeholder token present" in error for error in errors)


def test_verify_architecture_docs_rejects_forbidden_legacy_scheduler_terms(
    tmp_path: Path,
) -> None:
    docs_root = tmp_path / "docs" / "architecture"
    _write_all_required_docs(docs_root)
    _write(
        docs_root / "scheduler_orchestration_sequence.md",
        "# Managed Scheduler Orchestration Sequence\nCelery\n",
    )
    errors = verify_architecture_docs(docs_root)
    assert any("forbidden token present" in error for error in errors)


def test_main_returns_nonzero_when_requirements_fail(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs" / "architecture"
    docs_root.mkdir(parents=True, exist_ok=True)
    assert main(["--docs-root", str(docs_root)]) == 1


def test_main_rejects_missing_docs_root(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs" / "architecture"
    assert main(["--docs-root", str(docs_root)]) == 2


def test_main_rejects_non_directory_docs_root(tmp_path: Path) -> None:
    docs_root_file = tmp_path / "architecture.txt"
    docs_root_file.write_text("not-a-directory\n", encoding="utf-8")
    assert main(["--docs-root", str(docs_root_file)]) == 2


def test_resolve_docs_root_rejects_relative_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(
        "scripts.verify_architecture_decision_records._repo_root", lambda: repo_root
    )

    with pytest.raises(
        ValueError, match="docs_root must stay within repo root when relative"
    ):
        _resolve_docs_root("../escape/docs")


def test_main_resolves_relative_docs_root_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    docs_root = repo_root / "docs" / "architecture"
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    _write_all_required_docs(docs_root)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(
        "scripts.verify_architecture_decision_records._repo_root", lambda: repo_root
    )

    assert main(["--docs-root", "docs/architecture"]) == 0
