from __future__ import annotations

import json
from pathlib import Path

import pytest

import scripts.generate_feature_enforceability_matrix as matrix_generator
import scripts.verify_feature_enforceability_matrix as matrix_verifier
from scripts.generate_feature_enforceability_matrix import (
    _feature_runtime_gate_for_file,
    _resolve_output_path,
    generate_matrix,
    main,
)
from scripts.verify_feature_enforceability_matrix import verify_matrix


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_generated_feature_enforceability_matrix_verifies(tmp_path: Path) -> None:
    payload = generate_matrix(repo_root=REPO_ROOT)
    features = payload.get("features", {})
    assert features["api_access"]["status"] == "runtime_gated"
    assert features["policy_configuration"]["status"] == "runtime_gated"
    out = tmp_path / "matrix.json"
    out.write_text(json.dumps(payload), encoding="utf-8")
    verify_matrix(artifact_path=out, repo_root=REPO_ROOT)


def test_verify_feature_enforceability_matrix_rejects_missing_paid_feature(
    tmp_path: Path,
) -> None:
    payload = generate_matrix(repo_root=REPO_ROOT)
    features = dict(payload.get("features", {}))
    features.pop(next(iter(features.keys())))
    payload["features"] = features
    out = tmp_path / "matrix.json"
    out.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="missing paid-tier features"):
        verify_matrix(artifact_path=out, repo_root=REPO_ROOT)


def test_feature_runtime_gate_detection_handles_multiline_calls() -> None:
    raw = """
from app.shared.core.dependencies import requires_feature
from app.shared.core.pricing import FeatureFlag

Depends(
    requires_feature(
        FeatureFlag.COMPLIANCE_EXPORTS,
        required_role="admin",
    )
)
"""

    assert _feature_runtime_gate_for_file(
        token="FeatureFlag.COMPLIANCE_EXPORTS",
        raw=raw,
    )


def test_resolve_output_path_rejects_repo_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="out must resolve inside the repository root"):
        _resolve_output_path(
            repo_root=REPO_ROOT,
            output=str(tmp_path / "outside.json"),
        )


def test_main_rejects_repo_escape_output(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="out must resolve inside the repository root"):
        main(["--out", str(tmp_path / "outside.json")])


@pytest.mark.parametrize(
    "output",
    [
        "app/shared/core/pricing.py",
        "app/modules/reporting/api/v1/costs.py",
    ],
)
def test_resolve_output_path_rejects_scanned_source_roots(output: str) -> None:
    with pytest.raises(ValueError, match="out must not overwrite scanned source roots"):
        _resolve_output_path(
            repo_root=REPO_ROOT,
            output=output,
        )


def test_main_rejects_scanned_source_root_output() -> None:
    with pytest.raises(ValueError, match="out must not overwrite scanned source roots"):
        main(["--out", "app/shared/core/pricing.py"])


@pytest.mark.parametrize(
    "output",
    [
        "scripts/verify_feature_enforceability_matrix.py",
        "docs/ops/feature_enforceability_matrix_2026-02-27.json",
        "docs/ops/evidence/finance_telemetry_snapshot_TEMPLATE.json",
        "docs/ops/evidence/enforcement_stress_artifact_2026-02-27.json",
        "docs/ops/key-rotation-drill-2026-02-27.md",
    ],
)
def test_resolve_output_path_rejects_protected_artifacts(output: str) -> None:
    with pytest.raises(
        ValueError,
        match="out must not overwrite feature-enforceability source, verifier, or checked-in artifact files",
    ):
        _resolve_output_path(
            repo_root=REPO_ROOT,
            output=output,
        )


def test_main_rejects_protected_artifact_output() -> None:
    with pytest.raises(
        ValueError,
        match="out must not overwrite feature-enforceability source, verifier, or checked-in artifact files",
    ):
        main(["--out", "docs/ops/feature_enforceability_matrix_2026-02-27.json"])


def test_main_rejects_output_parent_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    monkeypatch.setattr(matrix_generator, "_repo_root", lambda: tmp_path)

    with pytest.raises(ValueError, match="out parent must be a directory path"):
        main(["--out", "blocked-parent/matrix.json"])


def test_main_rejects_directory_output_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_dir = tmp_path / "matrix-output"
    output_dir.mkdir()

    monkeypatch.setattr(matrix_generator, "_repo_root", lambda: tmp_path)

    with pytest.raises(ValueError, match="out must be a file path inside the repository root"):
        main(["--out", "matrix-output"])


def test_main_self_verifies_generated_matrix(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "ops" / "matrix.json"
    verify_calls: list[tuple[Path, Path]] = []

    def _fake_repo_root() -> Path:
        return tmp_path

    def _fake_generate_matrix(*, repo_root: Path) -> dict[str, object]:
        assert repo_root == tmp_path
        return {
            "captured_at": "2026-03-19T12:00:00+00:00",
            "scope": {
                "paid_tiers": ["starter", "growth", "pro", "enterprise"],
                "source_of_truth": "app/shared/core/pricing.py",
                "scanner_roots": ["app/modules", "app/shared"],
            },
            "features": {
                "api_access": {
                    "status": "runtime_gated",
                    "evidence": ["app/modules/example.py"],
                }
            },
        }

    def _fake_verify_matrix(*, artifact_path: Path, repo_root: Path) -> None:
        verify_calls.append((artifact_path, repo_root))

    monkeypatch.setattr(matrix_generator, "_repo_root", _fake_repo_root)
    monkeypatch.setattr(matrix_generator, "generate_matrix", _fake_generate_matrix)
    monkeypatch.setattr(matrix_verifier, "verify_matrix", _fake_verify_matrix)

    assert main(["--out", "ops/matrix.json"]) == 0
    assert output.exists()
    assert len(verify_calls) == 1
    artifact_path, repo_root = verify_calls[0]
    assert repo_root == tmp_path
    assert artifact_path.parent == output.parent
    assert artifact_path != output


def test_main_does_not_leave_output_when_verification_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "ops" / "matrix.json"

    monkeypatch.setattr(matrix_generator, "_repo_root", lambda: tmp_path)
    monkeypatch.setattr(
        matrix_generator,
        "generate_matrix",
        lambda *, repo_root: {
            "captured_at": "2026-03-19T12:00:00+00:00",
            "scope": {
                "paid_tiers": ["starter", "growth", "pro", "enterprise"],
                "source_of_truth": "app/shared/core/pricing.py",
                "scanner_roots": ["app/modules", "app/shared"],
            },
            "features": {
                "api_access": {
                    "status": "runtime_gated",
                    "evidence": ["app/modules/example.py"],
                }
            },
        },
    )
    monkeypatch.setattr(
        matrix_verifier,
        "verify_matrix",
        lambda **_: (_ for _ in ()).throw(ValueError("matrix verification failed")),
    )

    with pytest.raises(ValueError, match="matrix verification failed"):
        main(["--out", "ops/matrix.json"])

    assert not output.exists()
