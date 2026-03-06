from __future__ import annotations

from pathlib import Path

from scripts.verify_architecture_decision_records import (
    REQUIRED_DOCUMENTS,
    main,
    verify_architecture_docs,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _required_doc_text(path: str) -> str:
    if path == "scheduler_orchestration_sequence.md":
        return """# Scheduler Orchestration Sequence
```mermaid
sequenceDiagram
participant A as scheduler_tasks.py
participant B as orchestrator.py
A->>B: run
```
## Concurrency and Deterministic Replay
deterministic replay controls
## Observability and Snapshot Stability
trace and snapshot controls
## Failure Modes and Operational Misconfiguration Guards
failure guard controls
"""

    token_map: dict[str, str] = {
        "ADR-0005-paystack-over-stripe.md": "Paystack and Stripe evaluation",
        "ADR-0006-supabase-managed-auth-platform.md": "Supabase over self-hosted auth",
        "ADR-0007-redis-backed-circuit-breakers.md": "Redis versus in-memory breakers",
        "ADR-0008-codecarbon-emissions-observability.md": "CodeCarbon emissions telemetry",
        "ADR-0009-celery-redis-job-orchestration.md": "Celery with BackgroundTasks comparison",
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


def test_main_returns_nonzero_when_requirements_fail(tmp_path: Path) -> None:
    docs_root = tmp_path / "docs" / "architecture"
    docs_root.mkdir(parents=True, exist_ok=True)
    assert main(["--docs-root", str(docs_root)]) == 1

