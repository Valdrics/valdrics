from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.verify_jwt_bcp_checklist import (
    DEFAULT_CHECKLIST_PATH,
    REQUIRED_CONTROL_IDS,
    _resolve_checklist_path,
    load_checklist,
    main,
    validate_checklist,
    verify_checklist_file,
)


REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_default_jwt_bcp_checklist_verifies() -> None:
    exit_code = verify_checklist_file(REPO_ROOT / DEFAULT_CHECKLIST_PATH)
    assert exit_code == 0


def test_validate_checklist_rejects_missing_required_control(tmp_path: Path) -> None:
    checklist = load_checklist(REPO_ROOT / DEFAULT_CHECKLIST_PATH)
    controls = list(checklist["controls"])
    checklist["controls"] = [
        c for c in controls if c.get("control_id") != REQUIRED_CONTROL_IDS[0]
    ]
    _write_json(tmp_path / "checklist.json", checklist)

    with pytest.raises(ValueError, match="missing required control IDs"):
        validate_checklist(load_checklist(tmp_path / "checklist.json"), repo_root=REPO_ROOT)


def test_validate_checklist_rejects_duplicate_control_id(tmp_path: Path) -> None:
    checklist = load_checklist(REPO_ROOT / DEFAULT_CHECKLIST_PATH)
    checklist["controls"].append(dict(checklist["controls"][0]))
    _write_json(tmp_path / "checklist.json", checklist)

    with pytest.raises(ValueError, match="Duplicate JWT BCP control_id"):
        validate_checklist(load_checklist(tmp_path / "checklist.json"), repo_root=REPO_ROOT)


def test_validate_checklist_rejects_missing_evidence_path(tmp_path: Path) -> None:
    checklist = load_checklist(REPO_ROOT / DEFAULT_CHECKLIST_PATH)
    checklist["controls"][0]["evidence"] = ["docs/security/does_not_exist.md"]
    _write_json(tmp_path / "checklist.json", checklist)

    with pytest.raises(ValueError, match="does not exist"):
        validate_checklist(load_checklist(tmp_path / "checklist.json"), repo_root=REPO_ROOT)


def test_validate_checklist_rejects_directory_evidence_path(tmp_path: Path) -> None:
    checklist = load_checklist(REPO_ROOT / DEFAULT_CHECKLIST_PATH)
    evidence_dir = REPO_ROOT / "docs" / "runbooks"
    assert evidence_dir.is_dir()
    checklist["controls"][-1]["evidence"] = ["docs/runbooks"]
    _write_json(tmp_path / "checklist.json", checklist)

    with pytest.raises(ValueError, match="must be a file"):
        validate_checklist(load_checklist(tmp_path / "checklist.json"), repo_root=REPO_ROOT)


def test_validate_checklist_rejects_evidence_path_that_escapes_repo_root(tmp_path: Path) -> None:
    checklist = load_checklist(REPO_ROOT / DEFAULT_CHECKLIST_PATH)
    checklist["controls"][0]["evidence"] = ["../outside.md"]
    _write_json(tmp_path / "checklist.json", checklist)

    with pytest.raises(ValueError, match="must stay within repo root"):
        validate_checklist(load_checklist(tmp_path / "checklist.json"), repo_root=REPO_ROOT)


def test_validate_checklist_rejects_invalid_status(tmp_path: Path) -> None:
    checklist = load_checklist(REPO_ROOT / DEFAULT_CHECKLIST_PATH)
    checklist["controls"][0]["status"] = "invalid"
    _write_json(tmp_path / "checklist.json", checklist)

    with pytest.raises(ValueError, match="invalid status"):
        validate_checklist(load_checklist(tmp_path / "checklist.json"), repo_root=REPO_ROOT)


def test_validate_checklist_rejects_non_baseline_required_control_status(
    tmp_path: Path,
) -> None:
    checklist = load_checklist(REPO_ROOT / DEFAULT_CHECKLIST_PATH)
    checklist["controls"][0]["status"] = "partial"
    _write_json(tmp_path / "checklist.json", checklist)

    with pytest.raises(ValueError, match="implemented_baseline"):
        validate_checklist(load_checklist(tmp_path / "checklist.json"), repo_root=REPO_ROOT)


def test_validate_checklist_rejects_irrelevant_evidence_paths_for_required_control(
    tmp_path: Path,
) -> None:
    checklist = load_checklist(REPO_ROOT / DEFAULT_CHECKLIST_PATH)
    checklist["controls"][0]["evidence"] = ["README.md"]
    _write_json(tmp_path / "checklist.json", checklist)

    with pytest.raises(ValueError, match="app/modules/enforcement/domain/"):
        validate_checklist(load_checklist(tmp_path / "checklist.json"), repo_root=REPO_ROOT)


def test_resolve_checklist_path_rejects_relative_path_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr("scripts.verify_jwt_bcp_checklist._repo_root", lambda: repo_root)

    with pytest.raises(ValueError, match="checklist_path must stay within repo root when relative"):
        _resolve_checklist_path(Path("../escape/jwt.json"))


def test_main_resolves_relative_checklist_path_from_repo_root_when_run_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    checklist_path = repo_root / "docs" / "security" / "jwt.json"
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr("scripts.verify_jwt_bcp_checklist._repo_root", lambda: repo_root)
    captured: dict[str, object] = {}

    def _fake_verify_checklist_file(path: Path) -> int:
        captured["checklist_path"] = path
        return 0

    monkeypatch.setattr("scripts.verify_jwt_bcp_checklist.verify_checklist_file", _fake_verify_checklist_file)

    exit_code = main(["--checklist-path", "docs/security/jwt.json"])

    assert exit_code == 0
    assert captured["checklist_path"] == checklist_path.resolve()
