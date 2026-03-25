#!/usr/bin/env python3
"""Validate frontend API paths against backend router declarations.

This checker is evidence-focused:
- extracts backend paths from FastAPI router decorators + app router prefixes
- extracts frontend paths from edgeApiPath(...) and `${EDGE_API_BASE}/...` usages
- fails if a frontend path cannot be matched to any backend path template
"""

from __future__ import annotations

import os
import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch
from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)


@dataclass(frozen=True)
class FrontendPathRef:
    path: str
    file_path: Path
    expression: str


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_repo_root(path: Path) -> Path:
    return resolve_cli_path_from_root(_repo_root(), path, field_name="repo_root")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_backend_paths(repo_root: Path) -> set[str]:
    # Force deterministic, audit-safe settings regardless of operator shell state.
    env_overrides = {
        "TESTING": "true",
        "DEBUG": "false",
        "CSRF_SECRET_KEY": os.environ.get("CSRF_SECRET_KEY", "abcdefghijklmnopqrstuvwxyz123456"),
        "ENCRYPTION_KEY": os.environ.get("ENCRYPTION_KEY", "abcdefghijklmnopqrstuvwxyz123456"),
        "SUPABASE_JWT_SECRET": os.environ.get("SUPABASE_JWT_SECRET", "abcdefghijklmnopqrstuvwxyz123456"),
        "SUPABASE_SERVICE_ROLE_KEY": os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "abcdefghijklmnopqrstuvwxyz123456"),
        "SUPABASE_ANON_KEY": os.environ.get("SUPABASE_ANON_KEY", "abcdefghijklmnopqrstuvwxyz123456"),
        "SUPABASE_URL": os.environ.get("SUPABASE_URL", "https://example.supabase.co"),
        "KDF_SALT": os.environ.get("KDF_SALT", "S0RGX1NBTFRfRk9SX1RFU1RJTkdfMzJfQllURVNfT0s="),
        "CORS_ORIGINS": os.environ.get("CORS_ORIGINS", "[\"http://localhost:4173\"]"),
    }

    inserted_repo_root = False
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)
        inserted_repo_root = True
    try:
        with patch.dict(os.environ, env_overrides, clear=False):
            from app.main import app  # pylint: disable=import-outside-toplevel
    finally:
        if inserted_repo_root:
            try:
                sys.path.remove(repo_root_str)
            except ValueError:
                pass

    backend_paths: set[str] = set()
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = getattr(route, "methods", None)
        if not path or not methods:
            continue
        if any(method in {"GET", "POST", "PUT", "PATCH", "DELETE"} for method in methods):
            backend_paths.add(path)
    return backend_paths


EDGE_CALL_PATTERN = re.compile(r"edgeApiPath\(\s*([\"'`])(.*?)\1\s*\)", flags=re.DOTALL)
EDGE_BASE_PATTERN = re.compile(r"\$\{EDGE_API_BASE\}([^\"'`\n\r]*)")
BASE_API_PATTERN = re.compile(r"\$\{base\}((?:/api|/health)[^\"'`\n\r]*)")
TEMPLATE_EXPR_PATTERN = re.compile(r"\$\{[^}]+\}")
SVELTE_SCRIPT_PATTERN = re.compile(r"<script\b[^>]*>(.*?)</script>", flags=re.DOTALL | re.IGNORECASE)


def normalize_front_path(raw_path: str) -> str:
    path = raw_path.strip()
    if not path:
        return ""
    path = TEMPLATE_EXPR_PATTERN.sub("{param}", path)
    path = path.split("?", 1)[0]
    path = re.sub(r"/{2,}", "/", path)
    if not path.startswith("/"):
        path = f"/{path}"
    return path


def _extract_source_for_api_scan(file_path: Path) -> str:
    source = _read_text(file_path)
    if file_path.suffix != ".svelte":
        return source
    script_blocks = [match.group(1) for match in SVELTE_SCRIPT_PATTERN.finditer(source)]
    return "\n".join(script_blocks)


def _normalize_sveltekit_route_segment(segment: str) -> str:
    if segment.startswith("[...") and segment.endswith("]"):
        return "{" + segment[4:-1] + ":path}"
    if segment.startswith("[[...") and segment.endswith("]]"):
        return "{" + segment[5:-2] + ":path}"
    if segment.startswith("[") and segment.endswith("]"):
        return "{" + segment[1:-1] + "}"
    if segment.startswith("[[") and segment.endswith("]]"):
        return "{" + segment[2:-2] + "}"
    return segment


def parse_dashboard_server_paths(repo_root: Path) -> set[str]:
    api_root = repo_root / "dashboard/src/routes/api"
    if not api_root.exists():
        return set()

    paths: set[str] = set()
    for server_path in api_root.rglob("+server.ts"):
        relative_parent = server_path.parent.relative_to(repo_root / "dashboard/src/routes")
        normalized_parts = [_normalize_sveltekit_route_segment(part) for part in relative_parent.parts]
        route_path = "/" + "/".join(normalized_parts)
        paths.add(route_path)
    return paths


def parse_frontend_paths(repo_root: Path) -> list[FrontendPathRef]:
    src_root = repo_root / "dashboard/src"
    refs: list[FrontendPathRef] = []
    source_files = list(src_root.rglob("*.svelte")) + list(src_root.rglob("*.ts"))
    for file_path in source_files:
        if file_path.name.endswith(".test.ts"):
            continue
        source = _extract_source_for_api_scan(file_path)

        for match in EDGE_CALL_PATTERN.finditer(source):
            raw = match.group(2)
            normalized = normalize_front_path(raw)
            if not normalized or normalized == "/":
                continue
            # edgeApiPath('/foo') maps to backend '/api/v1/foo'
            backend_style = f"/api/v1{normalized}" if not normalized.startswith("/api/v1") else normalized
            refs.append(
                FrontendPathRef(
                    path=backend_style,
                    file_path=file_path.relative_to(repo_root),
                    expression=match.group(0).replace("\n", " "),
                )
            )

        for match in EDGE_BASE_PATTERN.finditer(source):
            raw = match.group(1)
            normalized = normalize_front_path(raw)
            if not normalized or normalized == "/" or not normalized.startswith("/"):
                continue
            backend_style = f"/api/v1{normalized}" if not normalized.startswith("/api/v1") else normalized
            refs.append(
                FrontendPathRef(
                    path=backend_style,
                    file_path=file_path.relative_to(repo_root),
                    expression=match.group(0).replace("\n", " "),
                )
            )

        for match in BASE_API_PATTERN.finditer(source):
            raw = match.group(1)
            normalized = normalize_front_path(raw)
            if not normalized or normalized == "/":
                continue
            refs.append(
                FrontendPathRef(
                    path=normalized,
                    file_path=file_path.relative_to(repo_root),
                    expression=match.group(0).replace("\n", " "),
                )
            )

        # buildUnitEconomicsUrl(base, ...) is currently used with EDGE_API_BASE.
        if "buildUnitEconomicsUrl(EDGE_API_BASE" in source:
            refs.append(
                FrontendPathRef(
                    path="/api/v1/costs/unit-economics",
                    file_path=file_path.relative_to(repo_root),
                    expression="buildUnitEconomicsUrl(EDGE_API_BASE, ...)",
                )
            )

        if "buildCompliancePackPath(" in source:
            refs.append(
                FrontendPathRef(
                    path="/api/v1/audit/compliance-pack",
                    file_path=file_path.relative_to(repo_root),
                    expression="buildCompliancePackPath(...)",
                )
            )

        if "buildFocusExportPath(" in source:
            refs.append(
                FrontendPathRef(
                    path="/api/v1/costs/export/focus",
                    file_path=file_path.relative_to(repo_root),
                    expression="buildFocusExportPath(...)",
                )
            )

    return refs


def _is_templated_segment(segment: str) -> bool:
    return segment.startswith("{") and segment.endswith("}")


def _is_path_catchall_segment(segment: str) -> bool:
    return _is_templated_segment(segment) and segment[1:-1].endswith(":path")


def path_matches(front_path: str, backend_path: str) -> bool:
    if front_path == backend_path:
        return True
    front_parts = [p for p in front_path.split("/") if p]
    back_parts = [p for p in backend_path.split("/") if p]
    front_idx = 0
    back_idx = 0
    while front_idx < len(front_parts) and back_idx < len(back_parts):
        front_part = front_parts[front_idx]
        back_part = back_parts[back_idx]
        if _is_path_catchall_segment(back_part) or _is_path_catchall_segment(front_part):
            return True
        if _is_templated_segment(back_part) or _is_templated_segment(front_part):
            front_idx += 1
            back_idx += 1
            continue
        if front_part != back_part:
            return False
        front_idx += 1
        back_idx += 1

    if front_idx == len(front_parts) and back_idx == len(back_parts):
        return True
    if back_idx == len(back_parts) - 1 and _is_path_catchall_segment(back_parts[back_idx]):
        return True
    if front_idx == len(front_parts) - 1 and _is_path_catchall_segment(front_parts[front_idx]):
        return True
    return False


def run(repo_root: Path) -> int:
    declared_paths = parse_backend_paths(repo_root) | parse_dashboard_server_paths(repo_root)
    frontend_refs = parse_frontend_paths(repo_root)

    # Keep only API/lifecycle routes we intentionally support from frontend.
    relevant_frontend_refs = [
        ref
        for ref in frontend_refs
        if ref.path.startswith("/api/") or ref.path.startswith("/health/")
    ]
    missing: list[FrontendPathRef] = []
    for ref in relevant_frontend_refs:
        if not any(path_matches(ref.path, declared_path) for declared_path in declared_paths):
            missing.append(ref)

    print(
        f"[api-contract] declared paths: {len(declared_paths)} | frontend references: {len(relevant_frontend_refs)}"
    )
    if missing:
        print(f"[api-contract] missing backend matches: {len(missing)}")
        for ref in missing:
            print(f"  - {ref.path} :: {ref.file_path} :: {ref.expression}")
        return 1

    print("[api-contract] OK: all frontend API paths match backend-declared routes.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(_repo_root()),
        help="Repository root path",
    )
    args = parser.parse_args(argv)
    try:
        return run(_resolve_repo_root(Path(str(args.repo_root))))
    except ValueError as exc:
        print(f"[api-contract] failed: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
