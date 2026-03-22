"""Shared helpers for env rendering and repository-safe staged outputs."""

from __future__ import annotations

import json
from pathlib import Path
import shlex
import tempfile
from typing import Any, Iterable


def repo_root_for(script_path: str | Path) -> Path:
    return Path(script_path).resolve().parents[1]


def resolve_default_path_from_root(repo_root: Path, path: Path) -> Path:
    return (repo_root / path).resolve()


def resolve_default_repo_path(script_path: str | Path, path: Path) -> Path:
    return resolve_default_path_from_root(repo_root_for(script_path), path)


def resolve_cli_path_from_root(
    repo_root: Path,
    path: Path,
    *,
    field_name: str,
) -> Path:
    raw = Path(path).expanduser()
    if raw.is_absolute():
        return raw.resolve()

    resolved = (repo_root / raw).resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"{field_name} must stay within repo root when relative") from exc
    return resolved


def resolve_cli_repo_path(
    script_path: str | Path,
    path: Path,
    *,
    field_name: str,
) -> Path:
    return resolve_cli_path_from_root(repo_root_for(script_path), path, field_name=field_name)


def resolve_repo_relative_path_from_root(
    repo_root: Path,
    path: str | Path,
    *,
    field_name: str,
) -> Path:
    return resolve_cli_path_from_root(repo_root, Path(str(path)), field_name=field_name)


def resolve_contained_repo_path_from_root(
    repo_root: Path,
    path: str | Path,
    *,
    field_name: str,
) -> Path:
    resolved = Path(str(path)).expanduser()
    if not resolved.is_absolute():
        resolved = (repo_root / resolved).resolve()
    else:
        resolved = resolved.resolve()

    try:
        resolved.relative_to(repo_root)
    except ValueError as exc:
        raise ValueError(f"{field_name} must resolve inside the repository root") from exc
    return resolved


def checked_in_evidence_paths(repo_root: Path) -> set[Path]:
    evidence_dir = repo_root / "docs" / "ops" / "evidence"
    if not evidence_dir.exists():
        return set()
    return {path.resolve() for path in evidence_dir.iterdir() if path.is_file()}


def protected_output_paths(
    script_path: str | Path,
    *relative_paths: str | Path,
) -> set[Path]:
    repo_root = repo_root_for(script_path)
    return protected_output_paths_from_root(repo_root, script_path, *relative_paths)


def protected_output_paths_from_root(
    repo_root: Path,
    script_path: str | Path,
    *relative_paths: str | Path,
) -> set[Path]:
    protected = {Path(script_path).resolve(), *checked_in_evidence_paths(repo_root)}
    protected.update((repo_root / Path(relative_path)).resolve() for relative_path in relative_paths)
    return protected


def resolve_output_path_from_root(
    repo_root: Path,
    path: str | Path,
    *,
    field_name: str,
    protected_paths: Iterable[Path],
    protected_error: str,
) -> Path:
    resolved = resolve_repo_relative_path_from_root(repo_root, path, field_name=field_name)
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"{field_name} must be a file path: {resolved.as_posix()}")
    if resolved in set(protected_paths):
        raise ValueError(protected_error)
    return resolved


def ensure_parent_dir(path: Path, *, field_name: str) -> None:
    current = path.parent
    while True:
        if current.exists():
            if not current.is_dir():
                raise ValueError(
                    f"{field_name} parent must be a directory path: {current.as_posix()}"
                )
            return
        if current == current.parent:
            return
        current = current.parent


def ensure_directory_path(path: Path, *, field_name: str) -> None:
    current = path
    while True:
        if current.exists():
            if not current.is_dir():
                raise ValueError(
                    f"{field_name} parent must be a directory path: {current.as_posix()}"
                )
            return
        if current == current.parent:
            return
        current = current.parent


def stage_text_file(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.stem}.",
        suffix=f"{path.suffix}.tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
    return temp_path


def stage_json_file(
    path: Path,
    payload: Any,
    *,
    indent: int = 2,
    sort_keys: bool = True,
    trailing_newline: bool = False,
) -> Path:
    suffix = path.suffix or ".json"
    content = json.dumps(payload, indent=indent, sort_keys=sort_keys)
    if trailing_newline:
        content += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f".{path.stem}.",
        suffix=f"{suffix}.tmp",
        delete=False,
    ) as handle:
        temp_path = Path(handle.name)
        handle.write(content)
    return temp_path


def promote_staged_file(
    staged_path: Path,
    output_path: Path,
    *,
    cleanup_output_on_failure: bool = False,
) -> None:
    promotion_completed = False
    try:
        staged_path.replace(output_path)
        promotion_completed = True
    finally:
        if not promotion_completed:
            staged_path.unlink(missing_ok=True)
            if cleanup_output_on_failure:
                output_path.unlink(missing_ok=True)


def render_env_value(value: str) -> str:
    if value == "":
        return ""
    return shlex.quote(value)


def render_env(template_lines: list[str], overrides: dict[str, str]) -> str:
    output_lines: list[str] = []
    seen: set[str] = set()
    for raw_line in template_lines:
        line = raw_line.rstrip("\n")
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            output_lines.append(line)
            continue

        key, _, value = line.partition("=")
        normalized_key = key.strip()
        if normalized_key in overrides:
            output_lines.append(
                f"{normalized_key}={render_env_value(overrides[normalized_key])}"
            )
            seen.add(normalized_key)
            continue

        output_lines.append(f"{normalized_key}={render_env_value(value)}")

    for key in sorted(candidate for candidate in overrides if candidate not in seen):
        output_lines.append(f"{key}={render_env_value(overrides[key])}")

    output_lines.append("")
    return "\n".join(output_lines)


def parse_env_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in str(text or "").splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#") or "=" not in raw_line:
            continue
        key, _, value = raw_line.partition("=")
        rendered_value = value.strip()
        if rendered_value == "":
            values[key.strip()] = ""
            continue
        if rendered_value.startswith(("[", "{")):
            values[key.strip()] = rendered_value
            continue
        parsed = shlex.split(rendered_value, posix=True)
        values[key.strip()] = parsed[0] if parsed else ""
    return values


def parse_env_file(path: Path) -> dict[str, str]:
    return parse_env_text(path.read_text(encoding="utf-8"))
