#!/usr/bin/env python3
"""Generate finance committee packet assumptions from runtime telemetry."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Any

from scripts.env_generation_common import (
    checked_in_evidence_paths as _checked_in_evidence_paths_shared,
    ensure_parent_dir as _ensure_parent_dir_shared,
    promote_staged_file as _promote_staged_file,
    protected_output_paths_from_root as _protected_output_paths_from_root,
    repo_root_for as _repo_root_for,
    resolve_output_path_from_root as _resolve_output_path_from_root,
    resolve_repo_relative_path_from_root as _resolve_repo_relative_path_from_root,
    stage_json_file as _stage_json_file_shared,
)
from scripts.finance_committee_packet_assumptions_engine import (
    derive_assumptions_inputs,
)
from scripts.finance_committee_packet_common import load_json
from scripts.verify_finance_telemetry_snapshot import verify_snapshot


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _checked_in_evidence_paths(repo_root: Path) -> set[Path]:
    return _checked_in_evidence_paths_shared(repo_root)


def _protected_output_paths() -> set[Path]:
    return _protected_output_paths_from_root(
        _repo_root(),
        __file__,
        "scripts/generate_finance_telemetry_snapshot.py",
        "scripts/verify_finance_telemetry_snapshot.py",
        "docs/ops/feature_enforceability_matrix.json",
        "docs/ops/key-rotation-drill-2026-02-27.md",
    )


def _resolve_repo_relative_path(value: str, *, field_name: str) -> Path:
    return _resolve_repo_relative_path_from_root(
        _repo_root(),
        value,
        field_name=field_name,
    )


def _resolve_output_path(value: str) -> Path:
    return _resolve_output_path_from_root(
        _repo_root(),
        value,
        field_name="output",
        protected_paths=_protected_output_paths(),
        protected_error=(
            "output must not overwrite finance assumptions source, telemetry generator, verifier, or checked-in evidence files"
        ),
    )


def _resolve_input_path(value: str) -> Path:
    return _resolve_repo_relative_path(value, field_name="telemetry_path")


def _ensure_output_parent_dir(output_path: Path) -> None:
    _ensure_parent_dir_shared(output_path, field_name="output")


def _stage_json_file(output_path: Path, payload: dict[str, Any]) -> Path:
    return _stage_json_file_shared(
        output_path,
        payload,
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate finance committee packet assumptions JSON from a telemetry snapshot."
        ),
    )
    parser.add_argument("--output", required=True, help="Output assumptions JSON path.")
    parser.add_argument(
        "--telemetry-path",
        default=None,
        help=(
            "Optional telemetry snapshot path. "
            "When omitted, a runtime telemetry snapshot is generated first."
        ),
    )
    return parser.parse_args(argv)


def _resolve_telemetry_payload(
    *,
    telemetry_path: Path | None,
) -> tuple[dict[str, Any], str]:
    if telemetry_path is not None:
        verify_snapshot(snapshot_path=telemetry_path, max_artifact_age_hours=24.0)
        return load_json(telemetry_path, field="telemetry_path"), str(telemetry_path.resolve())

    with tempfile.TemporaryDirectory(prefix="finance-assumptions-") as tmp_dir:
        from scripts.generate_finance_telemetry_snapshot import (
            main as generate_finance_telemetry_snapshot_main,
        )

        generated = Path(tmp_dir) / "finance_telemetry_snapshot.json"
        exit_code = generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(generated),
            ]
        )
        if exit_code != 0:
            raise RuntimeError(
                "failed to generate runtime telemetry snapshot for assumptions"
            )
        verify_snapshot(snapshot_path=generated, max_artifact_age_hours=24.0)
        return load_json(generated, field="generated_telemetry_path"), "runtime://generated"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    telemetry_path = (
        _resolve_input_path(str(args.telemetry_path))
        if args.telemetry_path
        else None
    )
    output_path = _resolve_output_path(str(args.output))
    _ensure_output_parent_dir(output_path)
    if telemetry_path is not None and telemetry_path.resolve() == output_path.resolve():
        raise ValueError("telemetry_path and output must be different files")
    telemetry, source_telemetry = _resolve_telemetry_payload(telemetry_path=telemetry_path)

    assumptions = derive_assumptions_inputs(telemetry=telemetry)
    assumptions["source_telemetry_path"] = source_telemetry

    staged_output_path = _stage_json_file(output_path, assumptions)
    _promote_staged_file(
        staged_output_path,
        output_path,
        cleanup_output_on_failure=True,
    )
    print(f"Generated finance committee packet assumptions: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
