from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import scripts.verify_enforcement_post_closure_sanity as post_closure_verifier
from scripts.verify_enforcement_post_closure_sanity import (
    ARTIFACT_TEMPLATE_TOKENS,
    DIMENSION_TOKENS,
    EvidenceToken,
    main,
    validate_release_gate_contract,
    validate_tokens,
    verify_post_closure_sanity,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_validate_tokens_fails_for_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        validate_tokens(
            (EvidenceToken("missing.txt", "token"),),
            repo_root=tmp_path,
        )


def test_validate_tokens_fails_for_missing_token(tmp_path: Path) -> None:
    payload = tmp_path / "sample.txt"
    payload.write_text("hello-world", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing token"):
        validate_tokens(
            (EvidenceToken("sample.txt", "nope"),),
            repo_root=tmp_path,
        )


def test_verify_post_closure_sanity_passes_against_repo_contracts() -> None:
    exit_code = verify_post_closure_sanity(
        doc_path=REPO_ROOT / "docs/ops/enforcement_post_closure_sanity.md",
        contract_path=REPO_ROOT / "docs/ops/enforcement_release_gate_contract.json",
        repo_root=REPO_ROOT,
    )
    assert exit_code == 0


def test_dimension_tokens_include_lock_contention_and_snapshot_export_evidence() -> None:
    observability = {(t.path, t.token) for t in DIMENSION_TOKENS["observability"]}
    deterministic = {(t.path, t.token) for t in DIMENSION_TOKENS["deterministic_replay"]}
    snapshot = {(t.path, t.token) for t in DIMENSION_TOKENS["snapshot_stability"]}
    export_integrity = {(t.path, t.token) for t in DIMENSION_TOKENS["export_integrity"]}

    assert (
        "tests/unit/enforcement/enforcement_api_cases_part04.py",
        "test_gate_lock_failures_route_to_failsafe_with_lock_reason_codes",
    ) in observability
    assert (
        "docs/runbooks/enforcement_preprovision_integrations.md",
        "valdrics_ops_enforcement_gate_lock_events_total",
    ) in observability
    assert (
        "docs/ops/key-rotation-drill-2026-02-27.md",
        "rollback_validation_passed: true",
    ) in deterministic
    assert (
        "tests/unit/enforcement/enforcement_service_cases_part08.py",
        "computed_context_month_start",
    ) in snapshot
    assert (
        "tests/unit/enforcement/enforcement_service_cases_part08.py",
        "computed_context_data_source_mode",
    ) in snapshot
    assert (
        "tests/unit/enforcement/enforcement_service_cases_part08.py",
        "test_build_export_bundle_reconciles_counts_and_is_deterministic",
    ) in export_integrity


def test_operational_misconfiguration_tokens_use_active_admission_review_evidence() -> None:
    operational = {
        (t.path, t.token) for t in DIMENSION_TOKENS["operational_misconfiguration"]
    }

    assert (
        "tests/unit/enforcement/enforcement_api_cases_part01.py",
        "test_gate_k8s_admission_review_contract_allow",
    ) in operational
    assert (
        "tests/unit/enforcement/enforcement_api_cases_part02.py",
        "test_gate_k8s_admission_review_rejects_invalid_cost_annotation",
    ) in operational
    assert (
        "docs/runbooks/enforcement_preprovision_integrations.md",
        "`failurePolicy: Fail` requires API HA",
    ) in operational


def test_artifact_template_contract_tokens_cover_release_packet_templates() -> None:
    artifact_tokens = {(entry.path, entry.token) for entry in ARTIFACT_TEMPLATE_TOKENS}
    assert (
        "docs/ops/evidence/enforcement_stress_artifact_TEMPLATE.json",
        '"profile": "enforcement"',
    ) in artifact_tokens
    assert (
        "docs/ops/evidence/enforcement_failure_injection_TEMPLATE.json",
        '"profile": "enforcement_failure_injection"',
    ) in artifact_tokens
    assert (
        "docs/evidence/ci-green-template.md",
        "coverage-enterprise-gate.xml",
    ) in artifact_tokens


def test_release_gate_contract_snapshot_tokens_include_required_closure_markers() -> None:
    contract = (
        REPO_ROOT / "docs/ops/enforcement_release_gate_contract.json"
    ).read_text(encoding="utf-8")
    required = set(json.loads(contract)["post_closure_sanity"]["required_snapshot_tokens"])
    assert "CI-EVID-001" in required
    assert "BENCH-DOC-001" in required
    assert "docs/ops/evidence/ci-green-YYYY-MM-DD.md" in required
    assert "docs/evidence/ci-green-YYYY-MM-DD.md" not in required


def test_release_gate_contract_accepts_forbidden_token_allowlist_values(
    tmp_path: Path,
) -> None:
    payload = tmp_path / "contract.json"
    payload.write_text(
        json.dumps(
            {
                "post_closure_sanity": {
                    "required_snapshot_tokens": ["CI-EVID-001"],
                    "forbidden_snapshot_tokens": [
                        "test_enforcement_webhook_helm_contract"
                    ],
                }
            }
        ),
        encoding="utf-8",
    )

    validate_release_gate_contract(contract_path=payload)


def test_live_release_gate_contract_scopes_removed_helm_refs_out_of_active_surface() -> None:
    raw = (
        REPO_ROOT / "docs/ops/enforcement_release_gate_contract.json"
    ).read_text(encoding="utf-8")
    contract = json.loads(raw)
    forbidden = contract["post_closure_sanity"]["forbidden_snapshot_tokens"]

    assert "Kubernetes webhook production guidance profile" in forbidden
    assert (
        "deployable webhook template + explicit failure-policy profiles via chart values and runbook contract"
        in forbidden
    )
    assert "docs/ops/evidence/ci-green-YYYY-MM-DD.md" in raw
    assert "docs/evidence/ci-green-YYYY-MM-DD.md" not in raw


def test_main_resolves_relative_paths_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    doc_path = repo_root / "docs" / "ops" / "sanity.md"
    contract_path = repo_root / "docs" / "ops" / "contract.json"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("sanity", encoding="utf-8")
    contract_path.write_text(
        json.dumps(
            {
                "post_closure_sanity": {
                    "required_snapshot_tokens": ["CI-EVID-001"],
                    "forbidden_snapshot_tokens": ["forbidden-token"]
                }
            }
        ),
        encoding="utf-8",
    )
    captured: dict[str, Path] = {}

    def _capture(*, doc_path: Path, contract_path: Path, repo_root: Path) -> int:
        captured["doc"] = doc_path
        captured["contract"] = contract_path
        captured["repo_root"] = repo_root
        return 0

    monkeypatch.setattr(post_closure_verifier, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(post_closure_verifier, "verify_post_closure_sanity", _capture)
    monkeypatch.chdir(tmp_path)

    assert (
        main(["--doc-path", "docs/ops/sanity.md", "--contract-path", "docs/ops/contract.json"])
        == 0
    )
    assert captured["doc"] == doc_path
    assert captured["contract"] == contract_path
    assert captured["repo_root"] == repo_root


def test_main_rejects_relative_repo_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(post_closure_verifier, "_repo_root", lambda: repo_root)

    assert main(["--doc-path", os.path.join("..", "escape.md")]) == 2


def test_main_rejects_relative_contract_path_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    monkeypatch.setattr(post_closure_verifier, "_repo_root", lambda: repo_root)

    assert main(["--contract-path", os.path.join("..", "escape.json")]) == 2


def test_main_rejects_directory_inputs(tmp_path: Path) -> None:
    doc_dir = tmp_path / "doc-dir"
    gap_dir = tmp_path / "contract-dir"
    doc_dir.mkdir()
    gap_dir.mkdir()

    assert main(["--doc-path", str(doc_dir), "--contract-path", str(gap_dir)]) == 2
