"""Verify Python dependency locking and reproducible install discipline."""

from __future__ import annotations

import argparse
import re
import tomllib
from pathlib import Path

DEFAULT_REPO_ROOT = Path(".")
DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")
DEFAULT_LOCK_PATH = Path("uv.lock")
DEFAULT_WORKFLOWS_ROOT = Path(".github/workflows")
DEFAULT_DOCKERFILE_PATHS = (Path("Dockerfile"),)
STRICT_BOUNDED_DEPENDENCY_NAMES = {
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic-settings",
    "sqlalchemy",
    "alembic",
}

SETUP_UV_VERSION_PIN_RE = re.compile(
    r'^(?:"?[0-9]+\.[0-9]+\.[0-9]+"?|"?\$\{\{\s*env\.UV_VERSION\s*\}\}"?)$'
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _is_open_ended_spec(spec: str) -> bool:
    dependency = spec.split(";", 1)[0].strip()
    if not dependency or "@" in dependency:
        return False
    has_upper_bound = "<" in dependency
    if "==" in dependency or "~=" in dependency or has_upper_bound:
        return False
    return ">=" in dependency or ">" in dependency


def _dependency_name(spec: str) -> str:
    dependency = spec.split(";", 1)[0].strip()
    if not dependency:
        return ""
    token = re.split(r"[<>=!~\s]", dependency, maxsplit=1)[0].strip()
    if "[" in token:
        token = token.split("[", 1)[0]
    return token.lower()


def _dependency_specs(pyproject_path: Path) -> tuple[str, ...]:
    payload = tomllib.loads(_read_text(pyproject_path))
    project_block = payload.get("project", {})
    specs: list[str] = []
    for key in ("dependencies",):
        values = project_block.get(key, [])
        if isinstance(values, list):
            specs.extend(str(item) for item in values)

    optional = project_block.get("optional-dependencies", {})
    if isinstance(optional, dict):
        for values in optional.values():
            if isinstance(values, list):
                specs.extend(str(item) for item in values)

    dependency_groups = payload.get("dependency-groups", {})
    if isinstance(dependency_groups, dict):
        for values in dependency_groups.values():
            if isinstance(values, list):
                specs.extend(str(item) for item in values)

    return tuple(specs)


def _iter_uv_sync_commands(workflows_root: Path) -> tuple[tuple[Path, int, str], ...]:
    commands: list[tuple[Path, int, str]] = []
    if not workflows_root.exists():
        return ()
    for workflow in sorted(workflows_root.glob("*.y*ml")):
        for idx, raw_line in enumerate(_read_text(workflow).splitlines(), start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if "uv sync" not in line:
                continue
            commands.append((workflow, idx, line))
    return tuple(commands)


def _iter_setup_uv_version_entries(
    workflows_root: Path,
) -> tuple[tuple[Path, int, str | None], ...]:
    entries: list[tuple[Path, int, str | None]] = []
    if not workflows_root.exists():
        return ()
    for workflow in sorted(workflows_root.glob("*.y*ml")):
        lines = _read_text(workflow).splitlines()
        for idx, raw_line in enumerate(lines):
            if "uses: astral-sh/setup-uv@" not in raw_line:
                continue
            uses_indent = len(raw_line) - len(raw_line.lstrip(" "))
            version_value: str | None = None
            version_line = idx + 1
            for follow_idx in range(idx + 1, min(idx + 12, len(lines))):
                follow_line = lines[follow_idx]
                stripped = follow_line.strip()
                if not stripped or stripped.startswith("#"):
                    continue
                indent = len(follow_line) - len(follow_line.lstrip(" "))
                if indent <= uses_indent and stripped.startswith("- "):
                    break
                if stripped.startswith("version:"):
                    version_line = follow_idx + 1
                    version_value = stripped.split(":", 1)[1].strip()
                    break
            entries.append((workflow, version_line, version_value))
    return tuple(entries)


def _dockerfile_errors(path: Path) -> tuple[str, ...]:
    if not path.exists():
        return ()
    text = _read_text(path)
    errors: list[str] = []
    if 'ARG UV_VERSION=' not in text:
        errors.append(f"Dockerfile must pin uv with ARG UV_VERSION: {path.as_posix()}")
    if 'pip install --no-cache-dir "uv==${UV_VERSION}"' not in text:
        errors.append(
            "Dockerfile must install a pinned uv release: "
            f"{path.as_posix()}"
        )
    if "uv pip install" in text:
        errors.append(
            "Dockerfile must not bypass the lockfile with `uv pip install`: "
            f"{path.as_posix()}"
        )
    if "uv sync --frozen" not in text and "uv sync --locked" not in text:
        errors.append(
            "Dockerfile dependency install must be lock-enforced via `uv sync`: "
            f"{path.as_posix()}"
        )
    return tuple(errors)


def verify_dependency_locking(
    *,
    repo_root: Path,
    pyproject_path: Path = DEFAULT_PYPROJECT_PATH,
    lock_path: Path = DEFAULT_LOCK_PATH,
    workflows_root: Path = DEFAULT_WORKFLOWS_ROOT,
    dockerfile_paths: tuple[Path, ...] = DEFAULT_DOCKERFILE_PATHS,
) -> tuple[str, ...]:
    errors: list[str] = []
    pyproject = pyproject_path if pyproject_path.is_absolute() else repo_root / pyproject_path
    lockfile = lock_path if lock_path.is_absolute() else repo_root / lock_path
    workflows = (
        workflows_root
        if workflows_root.is_absolute()
        else repo_root / workflows_root
    )
    dockerfiles = tuple(
        path if path.is_absolute() else repo_root / path for path in dockerfile_paths
    )

    if not pyproject.exists():
        return (f"missing pyproject file: {pyproject.as_posix()}",)

    specs = _dependency_specs(pyproject)
    open_ended_specs = [spec for spec in specs if _is_open_ended_spec(spec)]
    if not lockfile.exists():
        errors.append(f"lockfile missing: {lockfile.as_posix()}")
    strict_open_ended_specs = [
        spec
        for spec in open_ended_specs
        if _dependency_name(spec) in STRICT_BOUNDED_DEPENDENCY_NAMES
    ]
    if strict_open_ended_specs:
        normalized = ", ".join(sorted(dict.fromkeys(strict_open_ended_specs)))
        errors.append(
            "critical dependencies must use bounded compatibility (`~=` or `<` upper bound): "
            f"{normalized}"
        )

    for workflow_path, line_no, command in _iter_uv_sync_commands(workflows):
        if "--locked" in command or "--frozen" in command:
            continue
        errors.append(
            "workflow install must be lock-enforced: "
            f"{workflow_path.as_posix()}:{line_no} -> {command}"
        )

    for workflow_path, line_no, version_value in _iter_setup_uv_version_entries(workflows):
        if version_value is None:
            errors.append(
                "setup-uv action must pin an explicit version: "
                f"{workflow_path.as_posix()}:{line_no}"
            )
            continue
        normalized = version_value.strip()
        if normalized == '"latest"' or normalized == "latest":
            errors.append(
                "setup-uv action must not use the mutable `latest` channel: "
                f"{workflow_path.as_posix()}:{line_no}"
            )
            continue
        if not SETUP_UV_VERSION_PIN_RE.match(normalized):
            errors.append(
                "setup-uv action version must be a pinned semver or `${{ env.UV_VERSION }}`: "
                f"{workflow_path.as_posix()}:{line_no} -> {normalized}"
            )

    for dockerfile in dockerfiles:
        errors.extend(_dockerfile_errors(dockerfile))

    return tuple(errors)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Verify lockfile-based reproducible dependency install discipline."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Repository root path.",
    )
    parser.add_argument(
        "--pyproject-path",
        type=Path,
        default=DEFAULT_PYPROJECT_PATH,
        help="Path to pyproject.toml (relative to repo root by default).",
    )
    parser.add_argument(
        "--lock-path",
        type=Path,
        default=DEFAULT_LOCK_PATH,
        help="Path to uv lockfile (relative to repo root by default).",
    )
    parser.add_argument(
        "--workflows-root",
        type=Path,
        default=DEFAULT_WORKFLOWS_ROOT,
        help="Directory containing workflow yaml files.",
    )
    parser.add_argument(
        "--dockerfile-path",
        action="append",
        type=Path,
        default=[],
        help="Dockerfile path to validate (relative to repo root by default). Can be repeated.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    errors = verify_dependency_locking(
        repo_root=repo_root,
        pyproject_path=args.pyproject_path,
        lock_path=args.lock_path,
        workflows_root=args.workflows_root,
        dockerfile_paths=tuple(args.dockerfile_path) or DEFAULT_DOCKERFILE_PATHS,
    )
    if errors:
        print("[dependency-locking] FAILED")
        for item in errors:
            print(f"- {item}")
        return 1
    print(
        "[dependency-locking] ok "
        f"repo_root={repo_root.as_posix()} lock_path={args.lock_path.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
