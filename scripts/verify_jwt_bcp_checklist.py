"""Validate JWT BCP checklist structure and evidence-path integrity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)
from typing import Any


DEFAULT_CHECKLIST_PATH = Path("docs/security/jwt_bcp_checklist_2026-02-27.json")

REQUIRED_CONTROL_IDS: tuple[str, ...] = (
    "JWT-ALG-ALLOWLIST",
    "JWT-ISS-AUD-BOUND",
    "JWT-TYPE-BINDING",
    "JWT-TEMPORAL-CLAIMS",
    "JWT-BINDING-CLAIMS",
    "JWT-REPLAY-PROTECTION",
    "JWT-KEY-ROTATION-FALLBACK",
)

ALLOWED_STATUSES: set[str] = {"implemented_baseline", "partial", "planned"}
BASELINE_REQUIRED_STATUS = "implemented_baseline"
CONTROL_EVIDENCE_PREFIXES: dict[str, tuple[str, ...]] = {
    control_id: (
        "app/modules/enforcement/domain/",
        "tests/unit/enforcement/",
    )
    for control_id in REQUIRED_CONTROL_IDS
}
CONTROL_EVIDENCE_PREFIXES["JWT-KEY-ROTATION-FALLBACK"] = (
    "app/modules/enforcement/domain/",
    "tests/unit/enforcement/",
    "docs/runbooks/",
)


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_checklist_path(path: Path) -> Path:
    return resolve_cli_path_from_root(_repo_root(), path, field_name="checklist_path")


def load_checklist(checklist_path: Path) -> dict[str, Any]:
    if not checklist_path.exists():
        raise FileNotFoundError(f"JWT BCP checklist file not found: {checklist_path}")
    if not checklist_path.is_file():
        raise ValueError(f"JWT BCP checklist path must be a file: {checklist_path}")
    raw = checklist_path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in JWT BCP checklist: {checklist_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("JWT BCP checklist root must be an object")
    return payload


def validate_checklist(checklist: dict[str, Any], *, repo_root: Path) -> None:
    metadata = checklist.get("metadata")
    if not isinstance(metadata, dict):
        raise ValueError("JWT BCP checklist must include object metadata")

    source_urls = metadata.get("source_urls")
    if not isinstance(source_urls, list) or not source_urls:
        raise ValueError("JWT BCP checklist metadata.source_urls must be non-empty")
    source_urls_text = " ".join(str(item) for item in source_urls)
    if "rfc-editor.org/rfc/rfc8725" not in source_urls_text:
        raise ValueError("JWT BCP source_urls must include RFC 8725 URL")

    controls = checklist.get("controls")
    if not isinstance(controls, list) or not controls:
        raise ValueError("JWT BCP checklist must include non-empty controls array")

    seen_ids: set[str] = set()
    for idx, control in enumerate(controls):
        if not isinstance(control, dict):
            raise ValueError(f"Control entry at index {idx} must be an object")

        control_id = control.get("control_id")
        if not isinstance(control_id, str) or not control_id.strip():
            raise ValueError(f"Control entry at index {idx} has invalid control_id")
        if control_id in seen_ids:
            raise ValueError(f"Duplicate JWT BCP control_id found: {control_id}")
        seen_ids.add(control_id)

        status = control.get("status")
        if status not in ALLOWED_STATUSES:
            raise ValueError(
                f"Control {control_id} has invalid status: {status!r}; "
                f"allowed={sorted(ALLOWED_STATUSES)}"
            )
        if control_id in REQUIRED_CONTROL_IDS and status != BASELINE_REQUIRED_STATUS:
            raise ValueError(
                f"Control {control_id} must be {BASELINE_REQUIRED_STATUS!r} "
                f"for release-gate verification"
            )

        title = control.get("title")
        if not isinstance(title, str) or not title.strip():
            raise ValueError(f"Control {control_id} is missing title")

        requirement = control.get("requirement")
        if not isinstance(requirement, str) or not requirement.strip():
            raise ValueError(f"Control {control_id} is missing requirement")

        evidence = control.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            raise ValueError(f"Control {control_id} must include evidence paths")

        normalized_evidence_paths: list[str] = []
        for raw_path in evidence:
            if not isinstance(raw_path, str) or not raw_path.strip():
                raise ValueError(f"Control {control_id} has invalid evidence path entry")
            rel_path = Path(raw_path)
            if rel_path.is_absolute():
                raise ValueError(
                    f"Control {control_id} evidence path must be relative: {raw_path}"
                )
            full_path = (repo_root / rel_path).resolve()
            try:
                full_path.relative_to(repo_root.resolve())
            except ValueError as exc:
                raise ValueError(
                    f"Control {control_id} evidence path must stay within repo root: {raw_path}"
                ) from exc
            if not full_path.exists():
                raise ValueError(
                    f"Control {control_id} evidence path does not exist: {raw_path}"
                )
            if not full_path.is_file():
                raise ValueError(
                    f"Control {control_id} evidence path must be a file: {raw_path}"
                )
            normalized_evidence_paths.append(rel_path.as_posix())

        required_prefixes = CONTROL_EVIDENCE_PREFIXES.get(control_id)
        if required_prefixes is not None:
            for prefix in required_prefixes:
                if not any(path.startswith(prefix) for path in normalized_evidence_paths):
                    raise ValueError(
                        f"Control {control_id} evidence must include at least one path "
                        f"under {prefix}"
                    )

    missing = sorted(set(REQUIRED_CONTROL_IDS) - seen_ids)
    if missing:
        raise ValueError(
            "JWT BCP checklist missing required control IDs: " + ", ".join(missing)
        )


def verify_checklist_file(checklist_path: Path) -> int:
    checklist = load_checklist(checklist_path)
    validate_checklist(checklist, repo_root=_repo_root())
    print(
        f"JWT BCP checklist verified: {checklist_path} "
        f"({len(checklist.get('controls', []))} controls)"
    )
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate JWT BCP checklist structure and evidence paths."
    )
    parser.add_argument(
        "--checklist-path",
        default=str(DEFAULT_CHECKLIST_PATH),
        help="Path to JWT BCP checklist JSON file.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    checklist_path = _resolve_checklist_path(Path(str(args.checklist_path)))
    return verify_checklist_file(checklist_path)


if __name__ == "__main__":
    raise SystemExit(main())
