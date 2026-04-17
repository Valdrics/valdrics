"""Generate a signed-attestation subject manifest for supply-chain provenance."""

from __future__ import annotations

import argparse
import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from scripts.env_generation_common import (
    checked_in_evidence_paths as _checked_in_evidence_paths_shared,
    ensure_parent_dir as _ensure_parent_dir_shared,
    promote_staged_file as _promote_staged_file,
    protected_output_paths_from_root as _protected_output_paths_from_root,
    repo_root_for as _repo_root_for,
    resolve_contained_repo_path_from_root as _resolve_contained_repo_path_from_root,
    stage_json_file as _stage_json_file,
)

SCHEMA_VERSION = "2026-02-23"
DEFAULT_DEPENDENCY_INPUTS: tuple[Path, ...] = (
    Path("pyproject.toml"),
    Path("uv.lock"),
    Path("Dockerfile"),
    Path("Dockerfile.dashboard"),
    Path("dashboard/package.json"),
    Path("dashboard/pnpm-lock.yaml"),
)


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now_iso() -> str:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return now.isoformat().replace("+00:00", "Z")


def _normalize_repo_relative_path(
    repo_root: Path,
    path: Path,
    *,
    field: str,
) -> Path:
    raw = Path(path)
    if raw.is_absolute():
        raise ValueError(f"{field} must be relative to repo root")

    resolved = (repo_root / raw).resolve()
    try:
        return resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"{field} must stay within repo root: {raw.as_posix()}") from exc


def _normalize_dependency_inputs(
    repo_root: Path,
    dependency_inputs: Sequence[Path],
) -> tuple[Path, ...]:
    normalized_paths: list[Path] = []
    seen_paths: set[str] = set()
    for idx, dependency_input in enumerate(dependency_inputs):
        normalized = _normalize_repo_relative_path(
            repo_root,
            Path(dependency_input),
            field=f"dependency_inputs[{idx}]",
        )
        key = normalized.as_posix()
        if key in seen_paths:
            raise ValueError(f"dependency_inputs contains duplicate path: {key}")
        seen_paths.add(key)
        normalized_paths.append(normalized)
    return tuple(normalized_paths)


def _resolve_repo_root(repo_root: Path) -> Path:
    resolved = repo_root.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"repo_root does not exist: {resolved.as_posix()}")
    if not resolved.is_dir():
        raise ValueError(f"repo_root must be a directory: {resolved.as_posix()}")
    return resolved


def _checked_in_evidence_paths(repo_root: Path) -> set[Path]:
    return _checked_in_evidence_paths_shared(repo_root)


def _protected_output_paths(repo_root: Path) -> set[Path]:
    return _protected_output_paths_from_root(
        repo_root,
        repo_root / "scripts" / "generate_provenance_manifest.py",
        ".github/workflows/sbom.yml",
        "docs/ops/feature_enforceability_matrix.json",
        "docs/ops/key-rotation-drill-2026-02-27.md",
        "docs/ops/evidence/finance_guardrails_TEMPLATE.json",
        "docs/ops/evidence/valdrics_disposition_register_2026-02-28.json",
        "docs/ops/evidence/README.md",
    )


def _resolve_output_path(repo_root: Path, output: Path) -> Path:
    try:
        resolved = _resolve_contained_repo_path_from_root(
            repo_root,
            output,
            field_name="output",
        )
    except ValueError as exc:
        raise ValueError("output must stay within repo root") from exc
    if resolved.exists() and not resolved.is_file():
        raise ValueError("output must be a file path within repo root")
    if resolved in _protected_output_paths(repo_root):
        raise ValueError(
            "output must not overwrite provenance generator source or checked-in supply-chain assets"
        )
    return resolved


def _ensure_output_parent_dir(output_path: Path) -> None:
    try:
        _ensure_parent_dir_shared(output_path, field_name="output")
    except ValueError as exc:
        raise ValueError(
            f"output parent must be a directory path within repo root: {output_path.parent.as_posix()}"
        ) from exc


def _stage_manifest_file(output_path: Path, manifest: dict[str, Any]) -> Path:
    return _stage_json_file(
        output_path,
        manifest,
        trailing_newline=True,
    )


def _resolve_file(repo_root: Path, relative_path: Path) -> Path:
    candidate = repo_root / relative_path
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(
            f"Required dependency input missing: {relative_path.as_posix()}"
        )
    return candidate


def _build_file_digest_entry(repo_root: Path, relative_path: Path) -> dict[str, Any]:
    absolute = _resolve_file(repo_root, relative_path)
    return {
        "path": relative_path.as_posix(),
        "sha256": _sha256_file(absolute),
        "size_bytes": absolute.stat().st_size,
    }


def _build_sbom_entries(repo_root: Path, sbom_dir: Path | None) -> list[dict[str, Any]]:
    if sbom_dir is None:
        return []

    normalized_sbom_dir = _normalize_repo_relative_path(
        repo_root,
        sbom_dir,
        field="sbom_dir",
    )
    absolute_sbom_dir = (repo_root / normalized_sbom_dir).resolve()
    if absolute_sbom_dir.exists() and not absolute_sbom_dir.is_dir():
        raise ValueError(
            f"SBOM directory must be a directory: {normalized_sbom_dir.as_posix()}"
        )
    if not absolute_sbom_dir.exists():
        raise FileNotFoundError(
            f"SBOM directory does not exist: {normalized_sbom_dir.as_posix()}"
        )

    entries: list[dict[str, Any]] = []
    for candidate in sorted(absolute_sbom_dir.glob("*.json")):
        relative_path = candidate.relative_to(repo_root)
        entries.append(
            {
                "path": relative_path.as_posix(),
                "sha256": _sha256_file(candidate),
                "size_bytes": candidate.stat().st_size,
            }
        )
    return entries


def generate_provenance_manifest(
    *,
    repo_root: Path,
    dependency_inputs: Sequence[Path],
    sbom_dir: Path | None,
    env: Mapping[str, str],
) -> dict[str, Any]:
    resolved_repo_root = _resolve_repo_root(repo_root)
    normalized_dependency_inputs = _normalize_dependency_inputs(
        resolved_repo_root,
        dependency_inputs,
    )
    dependency_entries = [
        _build_file_digest_entry(resolved_repo_root, relative_path)
        for relative_path in normalized_dependency_inputs
    ]
    sbom_entries = _build_sbom_entries(resolved_repo_root, sbom_dir)

    repository = env.get("GITHUB_REPOSITORY", "")
    run_id = env.get("GITHUB_RUN_ID", "")
    run_url = (
        f"https://github.com/{repository}/actions/runs/{run_id}"
        if repository and run_id
        else ""
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now_iso(),
        "build": {
            "repository": repository,
            "git_sha": env.get("GITHUB_SHA", ""),
            "git_ref": env.get("GITHUB_REF", ""),
            "workflow": env.get("GITHUB_WORKFLOW", ""),
            "workflow_run_id": run_id,
            "workflow_run_attempt": env.get("GITHUB_RUN_ATTEMPT", ""),
            "workflow_run_url": run_url,
        },
        "dependency_inputs": dependency_entries,
        "sbom_artifacts": sbom_entries,
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic supply-chain provenance manifest."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_repo_root(),
        help="Repository root path (default: this repository root).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output JSON path for the provenance manifest.",
    )
    parser.add_argument(
        "--sbom-dir",
        type=Path,
        default=Path("sbom"),
        help="Directory that contains generated SBOM JSON artifacts.",
    )
    parser.add_argument(
        "--allow-missing-sbom",
        action="store_true",
        help="Allow generation when the SBOM directory is missing.",
    )
    parser.add_argument(
        "--dependency-input",
        action="append",
        default=[],
        metavar="RELATIVE_PATH",
        help=(
            "Additional dependency input file path relative to repo root. "
            "If omitted, enterprise defaults are used."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)

    dependency_inputs = (
        tuple(Path(item) for item in args.dependency_input)
        if args.dependency_input
        else DEFAULT_DEPENDENCY_INPUTS
    )

    repo_root = _resolve_repo_root(args.repo_root)
    output_path = _resolve_output_path(repo_root, args.output)
    normalized_dependency_inputs = _normalize_dependency_inputs(
        repo_root,
        dependency_inputs,
    )
    normalized_sbom_dir = _normalize_repo_relative_path(
        repo_root,
        args.sbom_dir,
        field="sbom_dir",
    )
    sbom_dir: Path | None
    if args.allow_missing_sbom and not (repo_root / normalized_sbom_dir).exists():
        sbom_dir = None
    else:
        sbom_dir = normalized_sbom_dir
    output_relative = output_path.relative_to(repo_root)
    if output_relative in normalized_dependency_inputs:
        raise ValueError(
            "output must not overwrite dependency input: "
            f"{output_relative.as_posix()}"
        )
    if sbom_dir is not None:
        absolute_sbom_dir = (repo_root / sbom_dir).resolve()
        if absolute_sbom_dir.exists() and absolute_sbom_dir.is_dir():
            for candidate in absolute_sbom_dir.glob("*.json"):
                if output_path == candidate.resolve():
                    raise ValueError(
                        "output must not overwrite SBOM artifact: "
                        f"{candidate.relative_to(repo_root).as_posix()}"
                    )

    manifest = generate_provenance_manifest(
        repo_root=repo_root,
        dependency_inputs=dependency_inputs,
        sbom_dir=sbom_dir,
        env=os.environ,
    )

    _ensure_output_parent_dir(output_path)
    staged_output_path = _stage_manifest_file(output_path, manifest)
    _promote_staged_file(
        staged_output_path,
        output_path,
        cleanup_output_on_failure=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
