from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.generate_provenance_manifest import (
    DEFAULT_DEPENDENCY_INPUTS,
    _resolve_output_path,
    generate_provenance_manifest,
    main,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_generate_provenance_manifest_emits_sha256_for_dependency_inputs(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='x'\n")
    _write(tmp_path / "uv.lock", "version = 1\n")
    _write(tmp_path / "Dockerfile", "FROM python:3.12-slim\n")
    _write(tmp_path / "Dockerfile.dashboard", "FROM node:24-alpine\n")
    _write(tmp_path / "dashboard/package.json", '{"name":"x"}\n')
    _write(tmp_path / "dashboard/pnpm-lock.yaml", "lockfileVersion: '9.0'\n")

    _write(tmp_path / "sbom/python.json", '{"bomFormat":"CycloneDX"}\n')

    env = {
        "GITHUB_REPOSITORY": "acme/valdrics",
        "GITHUB_SHA": "abc123",
        "GITHUB_REF": "refs/heads/main",
        "GITHUB_RUN_ID": "777",
        "GITHUB_RUN_ATTEMPT": "2",
        "GITHUB_WORKFLOW": "SBOM Generation",
    }

    manifest = generate_provenance_manifest(
        repo_root=tmp_path,
        dependency_inputs=DEFAULT_DEPENDENCY_INPUTS,
        sbom_dir=Path("sbom"),
        env=env,
    )

    assert manifest["build"]["git_sha"] == "abc123"
    assert manifest["build"]["workflow_run_id"] == "777"
    assert (
        manifest["build"]["workflow_run_url"]
        == "https://github.com/acme/valdrics/actions/runs/777"
    )
    assert len(manifest["dependency_inputs"]) == len(DEFAULT_DEPENDENCY_INPUTS)

    pyproject_digest = hashlib.sha256(
        (tmp_path / "pyproject.toml").read_bytes()
    ).hexdigest()
    pyproject_item = next(
        item for item in manifest["dependency_inputs"] if item["path"] == "pyproject.toml"
    )
    assert pyproject_item["sha256"] == pyproject_digest

    assert manifest["sbom_artifacts"]
    assert manifest["sbom_artifacts"][0]["path"] == "sbom/python.json"


def test_generate_provenance_manifest_requires_all_dependency_inputs(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='x'\n")
    _write(tmp_path / "dashboard/package.json", '{"name":"x"}\n')
    _write(tmp_path / "dashboard/pnpm-lock.yaml", "lockfileVersion: '9.0'\n")

    with pytest.raises(FileNotFoundError):
        generate_provenance_manifest(
            repo_root=tmp_path,
            dependency_inputs=DEFAULT_DEPENDENCY_INPUTS,
            sbom_dir=None,
            env={},
        )


def test_generate_provenance_manifest_is_json_serializable(tmp_path: Path) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='x'\n")
    _write(tmp_path / "uv.lock", "version = 1\n")
    _write(tmp_path / "Dockerfile", "FROM python:3.12-slim\n")
    _write(tmp_path / "Dockerfile.dashboard", "FROM node:24-alpine\n")
    _write(tmp_path / "dashboard/package.json", '{"name":"x"}\n')
    _write(tmp_path / "dashboard/pnpm-lock.yaml", "lockfileVersion: '9.0'\n")

    manifest = generate_provenance_manifest(
        repo_root=tmp_path,
        dependency_inputs=DEFAULT_DEPENDENCY_INPUTS,
        sbom_dir=None,
        env={},
    )

    encoded = json.dumps(manifest, sort_keys=True)
    assert "dependency_inputs" in encoded


def test_generate_provenance_manifest_rejects_duplicate_dependency_inputs(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "pyproject.toml", "[project]\nname='x'\n")

    with pytest.raises(ValueError, match="duplicate path"):
        generate_provenance_manifest(
            repo_root=tmp_path,
            dependency_inputs=(Path("pyproject.toml"), Path("./pyproject.toml")),
            sbom_dir=None,
            env={},
        )


def test_generate_provenance_manifest_rejects_dependency_inputs_outside_repo_root(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _write(tmp_path / "outside.txt", "top-secret\n")

    with pytest.raises(ValueError, match="must stay within repo root"):
        generate_provenance_manifest(
            repo_root=repo_root,
            dependency_inputs=(Path("../outside.txt"),),
            sbom_dir=None,
            env={},
        )


def test_generate_provenance_manifest_rejects_sbom_dir_outside_repo_root(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\n")
    _write(tmp_path / "external-sbom/python.json", '{"bomFormat":"CycloneDX"}\n')

    with pytest.raises(ValueError, match="sbom_dir must stay within repo root"):
        generate_provenance_manifest(
            repo_root=repo_root,
            dependency_inputs=(Path("pyproject.toml"),),
            sbom_dir=Path("../external-sbom"),
            env={},
        )


def test_generate_provenance_manifest_rejects_non_directory_repo_root(
    tmp_path: Path,
) -> None:
    repo_root_file = tmp_path / "repo-root.txt"
    repo_root_file.write_text("not-a-directory\n", encoding="utf-8")

    with pytest.raises(ValueError, match="repo_root must be a directory"):
        generate_provenance_manifest(
            repo_root=repo_root_file,
            dependency_inputs=(Path("pyproject.toml"),),
            sbom_dir=None,
            env={},
        )


def test_generate_provenance_manifest_rejects_non_directory_sbom_dir(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\n")
    _write(repo_root / "sbom.json", '{"bomFormat":"CycloneDX"}\n')

    with pytest.raises(ValueError, match="SBOM directory must be a directory"):
        generate_provenance_manifest(
            repo_root=repo_root,
            dependency_inputs=(Path("pyproject.toml"),),
            sbom_dir=Path("sbom.json"),
            env={},
        )


def test_resolve_output_path_rejects_output_outside_repo_root(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)

    with pytest.raises(ValueError, match="output must stay within repo root"):
        _resolve_output_path(repo_root, tmp_path / "outside.json")


def test_resolve_output_path_rejects_directory_output(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    output_dir = repo_root / "artifacts"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="output must be a file path within repo root"):
        _resolve_output_path(repo_root, output_dir)


@pytest.mark.parametrize(
    "protected_output",
    [
        Path("scripts/generate_provenance_manifest.py"),
        Path(".github/workflows/sbom.yml"),
        Path("docs/ops/evidence/finance_guardrails_TEMPLATE.json"),
        Path("docs/ops/evidence/valdrics_disposition_register_2026-02-28.json"),
        Path("docs/ops/key-rotation-drill-2026-02-27.md"),
        Path("docs/ops/evidence/README.md"),
    ],
)
def test_resolve_output_path_rejects_protected_supply_chain_assets(
    tmp_path: Path,
    protected_output: Path,
) -> None:
    repo_root = tmp_path / "repo"
    _write(repo_root / protected_output, "tracked\n")

    with pytest.raises(
        ValueError,
        match="output must not overwrite provenance generator source or checked-in supply-chain assets",
    ):
        _resolve_output_path(repo_root, protected_output)


def test_resolve_output_path_treats_relative_output_as_repo_root_relative(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)

    resolved = _resolve_output_path(repo_root, Path("artifacts/provenance.json"))

    assert resolved == (repo_root / "artifacts" / "provenance.json").resolve()


def test_main_rejects_blocked_output_parent(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    blocked_parent = repo_root / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\n")

    with pytest.raises(ValueError, match="output parent must be a directory path within repo root"):
        main(
            [
                "--repo-root",
                str(repo_root),
                "--output",
                str(blocked_parent / "provenance.json"),
                "--allow-missing-sbom",
                "--dependency-input",
                "pyproject.toml",
            ]
        )


def test_main_writes_relative_output_under_repo_root_when_run_from_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\n")
    monkeypatch.chdir(outside_cwd)

    assert (
        main(
            [
                "--repo-root",
                str(repo_root),
                "--output",
                "artifacts/provenance.json",
                "--allow-missing-sbom",
                "--dependency-input",
                "pyproject.toml",
            ]
        )
        == 0
    )
    assert (repo_root / "artifacts" / "provenance.json").exists()


def test_main_defaults_repo_root_to_repository_when_run_from_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\n")
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(
        "scripts.generate_provenance_manifest._repo_root",
        lambda: repo_root,
    )

    assert (
        main(
            [
                "--output",
                "artifacts/provenance.json",
                "--allow-missing-sbom",
                "--dependency-input",
                "pyproject.toml",
            ]
        )
        == 0
    )
    assert (repo_root / "artifacts" / "provenance.json").exists()


def test_main_rejects_non_directory_repo_root(tmp_path: Path) -> None:
    repo_root_file = tmp_path / "repo-root.txt"
    repo_root_file.write_text("not-a-directory\n", encoding="utf-8")

    with pytest.raises(ValueError, match="repo_root must be a directory"):
        main(
            [
                "--repo-root",
                str(repo_root_file),
                "--output",
                str(tmp_path / "provenance.json"),
                "--allow-missing-sbom",
                "--dependency-input",
                "pyproject.toml",
            ]
        )


def test_main_rejects_output_collision_with_dependency_input(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\n")

    with pytest.raises(ValueError, match="output must not overwrite dependency input"):
        main(
            [
                "--repo-root",
                str(repo_root),
                "--output",
                str(repo_root / "pyproject.toml"),
                "--allow-missing-sbom",
                "--dependency-input",
                "pyproject.toml",
            ]
        )


def test_main_rejects_output_collision_with_protected_supply_chain_asset(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\n")
    _write(repo_root / ".github/workflows/sbom.yml", "name: SBOM\n")

    with pytest.raises(
        ValueError,
        match="output must not overwrite provenance generator source or checked-in supply-chain assets",
    ):
        main(
            [
                "--repo-root",
                str(repo_root),
                "--output",
                str(repo_root / ".github/workflows/sbom.yml"),
                "--allow-missing-sbom",
                "--dependency-input",
                "pyproject.toml",
            ]
        )


def test_main_rejects_output_collision_with_sbom_artifact(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\n")
    _write(repo_root / "sbom/python.json", '{"bomFormat":"CycloneDX"}\n')

    with pytest.raises(ValueError, match="output must not overwrite SBOM artifact"):
        main(
            [
                "--repo-root",
                str(repo_root),
                "--output",
                str(repo_root / "sbom/python.json"),
                "--dependency-input",
                "pyproject.toml",
                "--sbom-dir",
                "sbom",
            ]
        )


def test_main_rejects_allow_missing_sbom_with_absolute_path_outside_repo_root(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\n")

    with pytest.raises(ValueError, match="sbom_dir must be relative to repo root"):
        main(
            [
                "--repo-root",
                str(repo_root),
                "--output",
                str(repo_root / "artifacts" / "provenance.json"),
                "--allow-missing-sbom",
                "--dependency-input",
                "pyproject.toml",
                "--sbom-dir",
                str(tmp_path / "missing-sbom"),
            ]
        )


def test_main_rejects_allow_missing_sbom_with_relative_escape_outside_repo_root(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    _write(repo_root / "pyproject.toml", "[project]\nname='x'\n")

    with pytest.raises(ValueError, match="sbom_dir must stay within repo root"):
        main(
            [
                "--repo-root",
                str(repo_root),
                "--output",
                str(repo_root / "artifacts" / "provenance.json"),
                "--allow-missing-sbom",
                "--dependency-input",
                "pyproject.toml",
                "--sbom-dir",
                "../missing-sbom",
            ]
        )
