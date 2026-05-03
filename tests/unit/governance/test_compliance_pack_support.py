from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

import app.modules.governance.domain.security.compliance_pack_support as compliance_pack_support
from app.modules.governance.domain.security.compliance_pack_contracts import (
    CompliancePackValidationError,
)
from app.modules.governance.domain.security.compliance_pack_support import (
    SUPPORTED_FOCUS_EXPORT_PROVIDERS,
    _project_root,
    load_reference_documents,
    normalize_optional_provider,
    resolve_window,
)
from app.shared.core.runtime_paths import PROJECT_ROOT


def test_normalize_optional_provider_rejects_unsupported_values() -> None:
    with pytest.raises(CompliancePackValidationError, match="Unsupported focus_provider"):
        normalize_optional_provider(
            provider="oracle",
            provider_name="focus_provider",
        )


def test_focus_export_provider_allowlist_is_explicitly_broader() -> None:
    assert (
        normalize_optional_provider(
            provider="ai",
            provider_name="focus_provider",
            supported_providers=SUPPORTED_FOCUS_EXPORT_PROVIDERS,
        )
        == "ai"
    )
    with pytest.raises(
        CompliancePackValidationError, match="Unsupported savings_provider"
    ):
        normalize_optional_provider(
            provider="ai",
            provider_name="savings_provider",
        )


def test_resolve_window_raises_domain_validation_error_for_inverted_dates() -> None:
    with pytest.raises(CompliancePackValidationError, match="window must be ordered"):
        resolve_window(
            start=date(2026, 3, 8),
            end=date(2026, 3, 1),
            default_start=date(2026, 2, 1),
            default_end=date(2026, 2, 28),
            error_detail="window must be ordered",
        )


def test_resolve_window_uses_defaults_when_inputs_missing() -> None:
    start, end = resolve_window(
        start=None,
        end=None,
        default_start=date(2026, 2, 1),
        default_end=date(2026, 2, 28),
        error_detail="window must be ordered",
    )

    assert start == date(2026, 2, 1)
    assert end == date(2026, 2, 28)


def test_project_root_uses_runtime_paths_project_root() -> None:
    assert _project_root() == PROJECT_ROOT


def test_load_reference_documents_uses_project_root_instead_of_cwd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    doc_path = repo_root / "docs" / "ops" / "acceptance_evidence_capture.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("acceptance evidence docs", encoding="utf-8")

    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    monkeypatch.chdir(outside_dir)
    monkeypatch.setattr(compliance_pack_support, "PROJECT_ROOT", repo_root)
    monkeypatch.setattr(
        compliance_pack_support,
        "_REFERENCE_DOC_PATHS",
        (("acceptance_doc", "docs/ops/acceptance_evidence_capture.md"),),
    )

    docs, included_files = load_reference_documents()

    assert docs == {"acceptance_doc": "acceptance evidence docs"}
    assert included_files == ["docs/ops/acceptance_evidence_capture.md"]
