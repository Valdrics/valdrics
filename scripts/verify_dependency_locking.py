"""Verify Python dependency locking and reproducible install discipline."""

from __future__ import annotations

import argparse
import tomllib
from pathlib import Path

DEFAULT_REPO_ROOT = Path(".")
DEFAULT_PYPROJECT_PATH = Path("pyproject.toml")
DEFAULT_LOCK_PATH = Path("uv.lock")
DEFAULT_WORKFLOWS_ROOT = Path(".github/workflows")


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


def verify_dependency_locking(
    *,
    repo_root: Path,
    pyproject_path: Path = DEFAULT_PYPROJECT_PATH,
    lock_path: Path = DEFAULT_LOCK_PATH,
    workflows_root: Path = DEFAULT_WORKFLOWS_ROOT,
) -> tuple[str, ...]:
    errors: list[str] = []
    pyproject = pyproject_path if pyproject_path.is_absolute() else repo_root / pyproject_path
    lockfile = lock_path if lock_path.is_absolute() else repo_root / lock_path
    workflows = (
        workflows_root
        if workflows_root.is_absolute()
        else repo_root / workflows_root
    )

    if not pyproject.exists():
        return (f"missing pyproject file: {pyproject.as_posix()}",)

    specs = _dependency_specs(pyproject)
    open_ended_specs = [spec for spec in specs if _is_open_ended_spec(spec)]
    if open_ended_specs and not lockfile.exists():
        errors.append(
            "open-ended dependency specifiers detected but lockfile missing: "
            f"{lockfile.as_posix()}"
        )

    for workflow_path, line_no, command in _iter_uv_sync_commands(workflows):
        if "--locked" in command or "--frozen" in command:
            continue
        errors.append(
            "workflow install must be lock-enforced: "
            f"{workflow_path.as_posix()}:{line_no} -> {command}"
        )

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
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = args.repo_root.resolve()
    errors = verify_dependency_locking(
        repo_root=repo_root,
        pyproject_path=args.pyproject_path,
        lock_path=args.lock_path,
        workflows_root=args.workflows_root,
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

