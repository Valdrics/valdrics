from __future__ import annotations

from pathlib import Path
import json

import pytest

from scripts.verify_ssdf_traceability_matrix import (
    DEFAULT_MATRIX_PATH,
    REQUIRED_PRACTICE_IDS,
    _resolve_matrix_path,
    load_matrix,
    main,
    validate_matrix,
    verify_matrix_file,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_default_ssdf_matrix_verifies() -> None:
    exit_code = verify_matrix_file(REPO_ROOT / DEFAULT_MATRIX_PATH)
    assert exit_code == 0


def test_validate_matrix_rejects_missing_required_practice(tmp_path: Path) -> None:
    matrix = load_matrix(REPO_ROOT / DEFAULT_MATRIX_PATH)
    practices = list(matrix["practices"])
    matrix["practices"] = [
        p for p in practices if p.get("practice_id") != REQUIRED_PRACTICE_IDS[0]
    ]
    sample_file = REPO_ROOT / "scripts" / "verify_ssdf_traceability_matrix.py"
    assert sample_file.exists()
    _write_json(tmp_path / "matrix.json", matrix)

    with pytest.raises(ValueError, match="missing required practice IDs"):
        validate_matrix(
            load_matrix(tmp_path / "matrix.json"),
            repo_root=REPO_ROOT,
        )


def test_validate_matrix_rejects_duplicate_practice_id(tmp_path: Path) -> None:
    matrix = load_matrix(REPO_ROOT / DEFAULT_MATRIX_PATH)
    duplicated = dict(matrix["practices"][0])
    matrix["practices"].append(duplicated)
    _write_json(tmp_path / "matrix.json", matrix)

    with pytest.raises(ValueError, match="Duplicate SSDF practice_id"):
        validate_matrix(
            load_matrix(tmp_path / "matrix.json"),
            repo_root=REPO_ROOT,
        )


def test_validate_matrix_rejects_missing_evidence_path(tmp_path: Path) -> None:
    matrix = load_matrix(REPO_ROOT / DEFAULT_MATRIX_PATH)
    matrix["practices"][0]["evidence"] = ["docs/security/does_not_exist.md"]
    _write_json(tmp_path / "matrix.json", matrix)

    with pytest.raises(ValueError, match="does not exist"):
        validate_matrix(
            load_matrix(tmp_path / "matrix.json"),
            repo_root=REPO_ROOT,
        )


def test_validate_matrix_rejects_directory_evidence_path(tmp_path: Path) -> None:
    matrix = load_matrix(REPO_ROOT / DEFAULT_MATRIX_PATH)
    evidence_dir = REPO_ROOT / "docs" / "security"
    assert evidence_dir.is_dir()
    matrix["practices"][0]["evidence"] = ["docs/security"]
    _write_json(tmp_path / "matrix.json", matrix)

    with pytest.raises(ValueError, match="must be a file"):
        validate_matrix(
            load_matrix(tmp_path / "matrix.json"),
            repo_root=REPO_ROOT,
        )


def test_validate_matrix_rejects_evidence_path_that_escapes_repo_root(tmp_path: Path) -> None:
    matrix = load_matrix(REPO_ROOT / DEFAULT_MATRIX_PATH)
    matrix["practices"][0]["evidence"] = ["../outside.md"]
    _write_json(tmp_path / "matrix.json", matrix)

    with pytest.raises(ValueError, match="must stay within repo root"):
        validate_matrix(
            load_matrix(tmp_path / "matrix.json"),
            repo_root=REPO_ROOT,
        )


def test_validate_matrix_rejects_invalid_status(tmp_path: Path) -> None:
    matrix = load_matrix(REPO_ROOT / DEFAULT_MATRIX_PATH)
    matrix["practices"][0]["status"] = "unknown"
    _write_json(tmp_path / "matrix.json", matrix)

    with pytest.raises(ValueError, match="invalid status"):
        validate_matrix(
            load_matrix(tmp_path / "matrix.json"),
            repo_root=REPO_ROOT,
        )


def test_resolve_matrix_path_rejects_relative_path_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("scripts.verify_ssdf_traceability_matrix._repo_root", lambda: repo_root)

    with pytest.raises(ValueError, match="matrix_path must stay within repo root when relative"):
        _resolve_matrix_path(Path("../escape/ssdf.json"))


def test_main_resolves_relative_matrix_path_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    matrix_path = repo_root / "docs" / "security" / "traceability.json"
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr("scripts.verify_ssdf_traceability_matrix._repo_root", lambda: repo_root)
    captured: dict[str, object] = {}

    def _fake_verify_matrix_file(path: Path) -> int:
        captured["matrix_path"] = path
        return 0

    monkeypatch.setattr("scripts.verify_ssdf_traceability_matrix.verify_matrix_file", _fake_verify_matrix_file)

    exit_code = main(["--matrix-path", "docs/security/traceability.json"])

    assert exit_code == 0
    assert captured["matrix_path"] == matrix_path.resolve()
