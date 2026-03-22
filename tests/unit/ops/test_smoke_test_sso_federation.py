from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import scripts.smoke_test_sso_federation as sso_smoke


def test_main_rejects_relative_output_repo_escape() -> None:
    with pytest.raises(SystemExit, match="out must stay within repo root when relative"):
        sso_smoke.main(
            [
                "--email",
                "admin@example.com",
                "--out",
                os.path.join("..", "escape.json"),
            ]
        )


def test_resolve_output_path_rejects_directory(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="out must be a file path"):
        sso_smoke._resolve_output_path(output_dir)


def test_write_json_stages_before_promotion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "sso.json"
    staged_path = tmp_path / ".sso.json.tmp"

    def _fake_stage(path: Path, payload: object, **_: object) -> Path:
        assert path == output_path
        staged_path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
        return staged_path

    def _fake_promote(staged: Path, output: Path) -> None:
        staged.replace(output)

    monkeypatch.setattr(sso_smoke, "stage_json_file", _fake_stage)
    monkeypatch.setattr(sso_smoke, "promote_staged_file", _fake_promote)

    sso_smoke._write_json(output_path, {"passed": True})

    assert json.loads(output_path.read_text(encoding="utf-8"))["passed"] is True
