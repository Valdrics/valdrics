from __future__ import annotations

import os
from pathlib import Path

import pytest

import scripts.verify_docs_archive_hygiene as docs_archive_hygiene_verifier
from scripts.verify_docs_archive_hygiene import main, verify_docs_archive_hygiene


REPO_ROOT = Path(__file__).resolve().parents[3]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_verify_docs_archive_hygiene_accepts_registered_referenced_dated_doc(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/ops/key-rotation-drill-2026-02-27.md",
        "key rotation drill\n",
    )
    _write(
        tmp_path / "docs/ops/README.md",
        "See docs/ops/key-rotation-drill-2026-02-27.md for the active contract.\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == []


def test_verify_docs_archive_hygiene_flags_unregistered_dated_doc(tmp_path: Path) -> None:
    _write(
        tmp_path / "docs/ops/orphaned_snapshot_2026-03-03.md",
        "orphaned snapshot\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/ops/orphaned_snapshot_2026-03-03.md: active dated doc is not explicitly registered; archive it or add it to REGISTERED_ACTIVE_DATED_DOCS."
    ]


def test_verify_docs_archive_hygiene_rejects_referenced_unregistered_dated_doc_cluster(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/ops/competitive_parity_evidence_2026-02-19.md",
        "See docs/ops/gap_tracks_roadmap_2026-02-19.md.\n",
    )
    _write(
        tmp_path / "docs/ops/gap_tracks_roadmap_2026-02-19.md",
        "See docs/ops/competitive_parity_evidence_2026-02-19.md.\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert sorted(errors) == [
        "docs/ops/competitive_parity_evidence_2026-02-19.md: active dated doc is not explicitly registered; archive it or add it to REGISTERED_ACTIVE_DATED_DOCS.",
        "docs/ops/gap_tracks_roadmap_2026-02-19.md: active dated doc is not explicitly registered; archive it or add it to REGISTERED_ACTIVE_DATED_DOCS.",
    ]


def test_verify_docs_archive_hygiene_ignores_weak_inventory_reference(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/ops/workstream_categorization_all_changes_2026-03-02.md",
        "historical workstream register\n",
    )
    _write(
        tmp_path / "docs/ops/evidence/all_changes_inventory_2026-03-02.txt",
        "See docs/ops/workstream_categorization_all_changes_2026-03-02.md.\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert sorted(errors) == [
        "docs/ops/evidence/all_changes_inventory_2026-03-02.txt: prohibited active duplicate/orphan doc. Historical all-changes inventory snapshots — remove them.",
        "docs/ops/workstream_categorization_all_changes_2026-03-02.md: active dated doc is not explicitly registered; archive it or add it to REGISTERED_ACTIVE_DATED_DOCS.",
    ]


def test_verify_docs_archive_hygiene_accepts_supported_dated_doc_component(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/ops/key-rotation-drill-2026-02-27.md",
        "drill record\n",
    )
    _write(
        tmp_path / "scripts/verify_key_rotation_drill_evidence.py",
        "See docs/ops/key-rotation-drill-2026-02-27.md.\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == []


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


def test_verify_docs_archive_hygiene_flags_active_dated_change_categorization_doc(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/ops/all_changes_categorization_2026-04-12.md",
        "dated worktree report\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/ops/all_changes_categorization_2026-04-12.md: prohibited active duplicate/orphan doc. Dated change-categorization snapshots — remove them."
    ]


def test_verify_docs_archive_hygiene_flags_historical_closure_docs_in_active_ops_tree(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/ops/landing_page_audit_closure_2026-03-02.md",
        "landing closure snapshot\n",
    )
    _write(
        tmp_path / "docs/ops/pricing_packaging_correction_closure_2026-03-09.md",
        "pricing correction snapshot\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/ops/landing_page_audit_closure_2026-03-02.md: prohibited active duplicate/orphan doc. Historical landing audit closure — remove it.",
        "docs/ops/pricing_packaging_correction_closure_2026-03-09.md: prohibited active duplicate/orphan doc. Historical pricing/package correction closure — remove it.",
    ]


def test_verify_docs_archive_hygiene_flags_provider_specific_aws_smoke_runbook_in_active_tree(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/runbooks/aws_first_operator_flow.md",
        "provider-specific smoke flow\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/runbooks/aws_first_operator_flow.md: prohibited active duplicate/orphan doc. Provider-specific AWS tenant smoke runbook — remove it."
    ]


def test_verify_docs_archive_hygiene_flags_legacy_incident_response_duplicate_in_active_tree(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/ops/incident_response_runbook.md",
        "legacy duplicate incident runbook\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/ops/incident_response_runbook.md: prohibited active duplicate/orphan doc. Use docs/runbooks/incident_response.md for the canonical active incident runbook."
    ]


def test_verify_docs_archive_hygiene_flags_legacy_guides_not_in_active_tree(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "docs/guides/aws_scp_setup.md", "legacy aws scp guide\n")
    _write(tmp_path / "docs/guides/cicd_security.md", "legacy ci/cd security guide\n")

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/guides/aws_scp_setup.md: prohibited active duplicate/orphan doc. Legacy AWS SCP setup guidance is not part of the current active docs surface — remove it.",
        "docs/guides/cicd_security.md: prohibited active duplicate/orphan doc. Legacy CI/CD hardening narrative is superseded by active workflow/runbook contracts — remove it.",
    ]


def test_verify_docs_archive_hygiene_flags_archived_reference_notes_not_in_active_tree(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/architecture/identity_blueprint.md",
        "historical identity reference\n",
    )
    _write(
        tmp_path / "docs/architecture/discovery_wizard.md",
        "historical discovery reference\n",
    )
    _write(tmp_path / "docs/product/personas.md", "historical persona reference\n")

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/architecture/discovery_wizard.md: prohibited active duplicate/orphan doc. Historical discovery wizard note — remove it.",
        "docs/architecture/identity_blueprint.md: prohibited active duplicate/orphan doc. Historical identity reference — remove it.",
        "docs/product/personas.md: prohibited active duplicate/orphan doc. Historical product persona note — remove it.",
    ]


def test_verify_docs_archive_hygiene_flags_archived_and_legacy_relocated_paths(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "docs/evidence/ci-green-2026-02-27.md", "historical ci green\n")
    _write(
        tmp_path / "docs/ops/drills/enforcement_incident_drill_2026-02-23.md",
        "historical drill record\n",
    )
    _write(
        tmp_path / "docs/ops/enforcement_stress_evidence_2026-02-25.md",
        "dated stress protocol\n",
    )
    _write(
        tmp_path / "docs/ops/alert-evidence-2026-02-25.md",
        "dated alert evidence\n",
    )
    _write(
        tmp_path / "docs/ops/enforcement_post_closure_sanity_2026-02-26.md",
        "dated post-closure policy\n",
    )
    _write(
        tmp_path / "docs/ops/enforcement_failure_injection_matrix_2026-02-25.md",
        "dated failure-injection matrix\n",
    )
    _write(
        tmp_path / "docs/ops/benchmark_alignment_profiles_2026-02-27.md",
        "dated benchmark profile\n",
    )
    _write(
        tmp_path / "docs/ops/feature_enforceability_matrix_2026-02-27.json",
        "{\"captured_at\":\"2026-03-10T00:00:00+00:00\",\"features\":{}}\n",
    )
    _write(
        tmp_path / "docs/security/jwt_bcp_checklist_2026-02-27.json",
        "{\"metadata\":{\"source_urls\":[\"https://www.rfc-editor.org/rfc/rfc8725\"]},\"controls\":[]}\n",
    )
    _write(
        tmp_path / "docs/security/ssdf_traceability_matrix_2026-02-25.json",
        "{\"metadata\":{\"source_urls\":[\"https://csrc.nist.gov/pubs/sp/800/218/final\"]},\"practices\":[]}\n",
    )
    _write(
        tmp_path / "docs/ops/landing_funnel_alerting_2026-03-10.md",
        "dated landing contract\n",
    )
    _write(
        tmp_path / "docs/ops/incident_response_runbook.md",
        "legacy duplicate incident runbook\n",
    )
    _write(tmp_path / "docs/guides/aws_scp_setup.md", "legacy aws scp guide\n")
    _write(tmp_path / "docs/guides/cicd_security.md", "legacy ci/cd security guide\n")
    _write(
        tmp_path / "docs/architecture/identity_blueprint.md",
        "historical identity reference\n",
    )
    _write(
        tmp_path / "docs/architecture/discovery_wizard.md",
        "historical discovery reference\n",
    )
    _write(tmp_path / "docs/product/personas.md", "historical persona reference\n")

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/architecture/discovery_wizard.md: prohibited active duplicate/orphan doc. Historical discovery wizard note — remove it.",
        "docs/architecture/identity_blueprint.md: prohibited active duplicate/orphan doc. Historical identity reference — remove it.",
        "docs/evidence/ci-green-2026-02-27.md: prohibited active duplicate/orphan doc. Historical CI green-run promotion packet — remove it.",
        "docs/guides/aws_scp_setup.md: prohibited active duplicate/orphan doc. Legacy AWS SCP setup guidance is not part of the current active docs surface — remove it.",
        "docs/guides/cicd_security.md: prohibited active duplicate/orphan doc. Legacy CI/CD hardening narrative is superseded by active workflow/runbook contracts — remove it.",
        "docs/ops/alert-evidence-2026-02-25.md: prohibited active duplicate/orphan doc. Use docs/ops/alert-evidence.md for the canonical active evidence contract.",
        "docs/ops/benchmark_alignment_profiles_2026-02-27.md: prohibited active duplicate/orphan doc. Use docs/ops/benchmark_alignment_profiles.md for the canonical active benchmark profile.",
        "docs/ops/drills/enforcement_incident_drill_2026-02-23.md: prohibited active duplicate/orphan doc. Historical enforcement incident drill record — remove it.",
        "docs/ops/enforcement_failure_injection_matrix_2026-02-25.md: prohibited active duplicate/orphan doc. Use docs/ops/enforcement_failure_injection_matrix.md for the canonical active matrix.",
        "docs/ops/enforcement_post_closure_sanity_2026-02-26.md: prohibited active duplicate/orphan doc. Use docs/ops/enforcement_post_closure_sanity.md for the canonical active policy.",
        "docs/ops/enforcement_stress_evidence_2026-02-25.md: prohibited active duplicate/orphan doc. Use docs/ops/enforcement_stress_evidence.md for the canonical active protocol.",
        "docs/ops/feature_enforceability_matrix_2026-02-27.json: prohibited active duplicate/orphan doc. Use docs/ops/feature_enforceability_matrix.json for the canonical active matrix.",
        "docs/ops/incident_response_runbook.md: prohibited active duplicate/orphan doc. Use docs/runbooks/incident_response.md for the canonical active incident runbook.",
        "docs/ops/landing_funnel_alerting_2026-03-10.md: prohibited active duplicate/orphan doc. Use docs/ops/landing_funnel_alerting.md for the canonical active contract.",
        "docs/product/personas.md: prohibited active duplicate/orphan doc. Historical product persona note — remove it.",
        "docs/security/jwt_bcp_checklist_2026-02-27.json: prohibited active duplicate/orphan doc. Use docs/security/jwt_bcp_checklist.json for the canonical active checklist.",
        "docs/security/ssdf_traceability_matrix_2026-02-25.json: prohibited active duplicate/orphan doc. Use docs/security/ssdf_traceability_matrix.json for the canonical active matrix.",
    ]


def test_verify_docs_archive_hygiene_flags_active_inventory_snapshot_in_ops_evidence_tree(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/ops/evidence/all_changes_inventory_followup_2026-03-02.txt",
        "historical inventory snapshot\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/ops/evidence/all_changes_inventory_followup_2026-03-02.txt: prohibited active duplicate/orphan doc. Historical all-changes inventory snapshots — remove them."
    ]


def test_verify_docs_archive_hygiene_rejects_referenced_unregistered_dated_doc(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "docs/ops/release_packet_2026-04-12.md",
        "dated release packet\n",
    )
    _write(
        tmp_path / "docs/ops/README.md",
        "See docs/ops/release_packet_2026-04-12.md for the current packet.\n",
    )

    errors = verify_docs_archive_hygiene(root=tmp_path)
    assert errors == [
        "docs/ops/release_packet_2026-04-12.md: active dated doc is not explicitly registered; archive it or add it to REGISTERED_ACTIVE_DATED_DOCS."
    ]


def test_repo_prunes_q2_change_categorization_snapshots_out_of_active_ops_tree() -> None:
    active_docs = sorted((REPO_ROOT / "docs" / "ops").glob("all_changes_categorization_*.md"))
    assert active_docs == []

    archived_q2 = sorted(
        (REPO_ROOT / "docs" / "archive" / "ops" / "2026-q2").glob(
            "all_changes_categorization_*.md"
        )
    )
    assert archived_q2 == []


def test_repo_prunes_mechanical_q1_change_categorization_archive_snapshots() -> None:
    archived_q1 = sorted(
        (REPO_ROOT / "docs" / "archive" / "ops" / "2026-q1").glob(
            "all_changes_categorization_*.md"
        )
    )
    assert archived_q1 == []


def test_repo_registered_active_dated_docs_match_repo_state() -> None:
    active_dated_docs = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "docs").rglob("*")
        if path.is_file()
        and path.suffix.lower() in {".md", ".json"}
        and docs_archive_hygiene_verifier.DATED_DOC_PATTERN.search(path.stem)
        and not path.relative_to(REPO_ROOT).as_posix().startswith("docs/archive/")
    }
    assert active_dated_docs == docs_archive_hygiene_verifier.REGISTERED_ACTIVE_DATED_DOCS


def test_repo_prunes_historical_ci_green_release_packet_and_canonicalizes_landing_contract() -> None:
    assert not (REPO_ROOT / "docs" / "evidence" / "ci-green-2026-02-27.md").exists()
    assert not (
        REPO_ROOT
        / "docs"
        / "archive"
        / "evidence"
        / "2026-q1"
        / "ci-green-2026-02-27.md"
    ).exists()
    assert not (
        REPO_ROOT / "docs" / "ops" / "landing_funnel_alerting_2026-03-10.md"
    ).exists()
    assert (REPO_ROOT / "docs" / "ops" / "landing_funnel_alerting.md").exists()
    assert not (
        REPO_ROOT / "docs" / "ops" / "drills" / "enforcement_incident_drill_2026-02-23.md"
    ).exists()
    assert not (
        REPO_ROOT
        / "docs"
        / "archive"
        / "ops"
        / "2026-q1"
        / "drills"
        / "enforcement_incident_drill_2026-02-23.md"
    ).exists()
    assert not (
        REPO_ROOT / "docs" / "ops" / "enforcement_stress_evidence_2026-02-25.md"
    ).exists()
    assert (REPO_ROOT / "docs" / "ops" / "enforcement_stress_evidence.md").exists()
    assert not (REPO_ROOT / "docs" / "ops" / "alert-evidence-2026-02-25.md").exists()
    assert (REPO_ROOT / "docs" / "ops" / "alert-evidence.md").exists()
    assert not (
        REPO_ROOT / "docs" / "ops" / "enforcement_post_closure_sanity_2026-02-26.md"
    ).exists()
    assert (REPO_ROOT / "docs" / "ops" / "enforcement_post_closure_sanity.md").exists()
    assert not (
        REPO_ROOT
        / "docs"
        / "ops"
        / "enforcement_failure_injection_matrix_2026-02-25.md"
    ).exists()
    assert (
        REPO_ROOT / "docs" / "ops" / "enforcement_failure_injection_matrix.md"
    ).exists()
    assert not (
        REPO_ROOT / "docs" / "ops" / "benchmark_alignment_profiles_2026-02-27.md"
    ).exists()
    assert (REPO_ROOT / "docs" / "ops" / "benchmark_alignment_profiles.md").exists()
    assert not (
        REPO_ROOT / "docs" / "ops" / "feature_enforceability_matrix_2026-02-27.json"
    ).exists()
    assert (REPO_ROOT / "docs" / "ops" / "feature_enforceability_matrix.json").exists()
    assert not (
        REPO_ROOT / "docs" / "security" / "jwt_bcp_checklist_2026-02-27.json"
    ).exists()
    assert (REPO_ROOT / "docs" / "security" / "jwt_bcp_checklist.json").exists()
    assert not (
        REPO_ROOT / "docs" / "security" / "ssdf_traceability_matrix_2026-02-25.json"
    ).exists()
    assert (REPO_ROOT / "docs" / "security" / "ssdf_traceability_matrix.json").exists()


def test_repo_prunes_mechanical_all_changes_inventory_snapshots() -> None:
    active_inventory_snapshots = sorted(
        (REPO_ROOT / "docs" / "ops" / "evidence").glob("all_changes_inventory*.txt")
    )
    assert active_inventory_snapshots == []

    archived_inventory_snapshots = sorted(
        (REPO_ROOT / "docs" / "archive" / "ops" / "2026-q1" / "evidence").glob(
            "all_changes_inventory*.txt"
        )
    )
    assert archived_inventory_snapshots == []


def test_repo_prunes_historical_landing_and_pricing_closure_snapshots() -> None:
    assert not (
        REPO_ROOT / "docs" / "ops" / "landing_page_audit_closure_2026-03-02.md"
    ).exists()
    assert not (
        REPO_ROOT / "docs" / "ops" / "pricing_packaging_correction_closure_2026-03-09.md"
    ).exists()
    assert not (
        REPO_ROOT
        / "docs"
        / "archive"
        / "ops"
        / "2026-q1"
        / "landing_page_audit_closure_2026-03-02.md"
    ).exists()
    assert not (
        REPO_ROOT
        / "docs"
        / "archive"
        / "ops"
        / "2026-q1"
        / "pricing_packaging_correction_closure_2026-03-09.md"
    ).exists()
    assert not (
        REPO_ROOT / "docs" / "security" / "ssdf_traceability_matrix_2026-02-25.md"
    ).exists()


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
