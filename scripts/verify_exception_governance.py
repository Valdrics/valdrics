"""Govern catch-all exception usage in production code paths."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)
import tempfile
from typing import Iterable


DEFAULT_ROOTS: tuple[Path, ...] = (Path("app"), Path("scripts"))
DEFAULT_BASELINE_PATH = Path("docs/ops/evidence/exception_governance_baseline.json")


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _normalize_site_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(_repo_root()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _resolve_root_path(path: Path) -> Path:
    return resolve_cli_path_from_root(_repo_root(), path, field_name="root")


def _resolve_baseline_path(path: Path) -> Path:
    resolved = resolve_cli_path_from_root(_repo_root(), path, field_name="baseline_path")
    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"baseline_path must be a file path: {resolved.as_posix()}")
    return resolved


@dataclass(frozen=True)
class ExceptionSite:
    path: str
    line: int
    kind: str

    def key(self) -> str:
        return f"{self.path}:{self.line}:{self.kind}"


def _iter_python_files(root: Path) -> Iterable[Path]:
    if root.is_file() and root.suffix == ".py":
        yield root
        return
    for candidate in root.rglob("*.py"):
        if candidate.is_file():
            yield candidate


def _type_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _catch_kind(handler_type: ast.expr | None) -> str | None:
    if handler_type is None:
        return "bare_except"

    if isinstance(handler_type, ast.Tuple):
        names = {_type_name(item) for item in handler_type.elts}
        if "BaseException" in names:
            return "tuple_baseexception"
        if "Exception" in names:
            return "tuple_exception"
        return None

    name = _type_name(handler_type)
    if name == "BaseException":
        return "baseexception"
    if name == "Exception":
        return "exception"
    return None


def collect_exception_sites(*, roots: tuple[Path, ...]) -> tuple[ExceptionSite, ...]:
    sites: list[ExceptionSite] = []
    for root in roots:
        for path in _iter_python_files(root):
            raw = path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(raw, filename=path.as_posix())
            for node in ast.walk(tree):
                if not isinstance(node, ast.ExceptHandler):
                    continue
                kind = _catch_kind(node.type)
                if kind is None:
                    continue
                sites.append(
                    ExceptionSite(
                        path=_normalize_site_path(path),
                        line=int(node.lineno),
                        kind=kind,
                    )
                )
    return tuple(sorted(sites, key=lambda item: (item.path, item.line, item.kind)))


def _ensure_baseline_parent_dir(baseline_path: Path) -> None:
    current = baseline_path.parent
    while True:
        if current.exists():
            if not current.is_dir():
                raise ValueError(
                    f"baseline_path parent must be a directory path: {current.as_posix()}"
                )
            return
        if current == current.parent:
            return
        current = current.parent


def write_baseline(
    *,
    baseline_path: Path,
    roots: tuple[Path, ...],
    sites: tuple[ExceptionSite, ...],
) -> None:
    if baseline_path.exists() and not baseline_path.is_file():
        raise ValueError(f"baseline_path must be a file path: {baseline_path.as_posix()}")
    _ensure_baseline_parent_dir(baseline_path)
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "roots": [_normalize_site_path(root) for root in roots],
        "sites": [asdict(site) for site in sites],
    }
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = baseline_path.suffix or ".json"
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=baseline_path.parent,
        prefix=f".{baseline_path.stem}.",
        suffix=f"{suffix}.tmp",
        delete=False,
    ) as handle:
        staged_path = Path(handle.name)
    staged_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    promotion_completed = False
    try:
        staged_path.replace(baseline_path)
        promotion_completed = True
    finally:
        if not promotion_completed:
            staged_path.unlink(missing_ok=True)
            baseline_path.unlink(missing_ok=True)


def _load_baseline(baseline_path: Path) -> tuple[ExceptionSite, ...]:
    if not baseline_path.exists():
        raise FileNotFoundError(
            f"Baseline file does not exist: {baseline_path.as_posix()}"
        )
    payload = json.loads(baseline_path.read_text(encoding="utf-8"))
    raw_sites = payload.get("sites", [])
    sites: list[ExceptionSite] = []
    for item in raw_sites:
        if not isinstance(item, dict):
            continue
        path = item.get("path")
        line = item.get("line")
        kind = item.get("kind")
        if not isinstance(path, str) or not isinstance(line, int) or not isinstance(kind, str):
            continue
        sites.append(ExceptionSite(path=path, line=line, kind=kind))
    return tuple(sorted(sites, key=lambda item: (item.path, item.line, item.kind)))


def verify_against_baseline(
    *,
    current: tuple[ExceptionSite, ...],
    baseline: tuple[ExceptionSite, ...],
) -> tuple[tuple[ExceptionSite, ...], tuple[ExceptionSite, ...], tuple[ExceptionSite, ...]]:
    current_keys = {site.key(): site for site in current}
    baseline_keys = {site.key(): site for site in baseline}

    added = tuple(
        sorted(
            (site for key, site in current_keys.items() if key not in baseline_keys),
            key=lambda item: (item.path, item.line, item.kind),
        )
    )
    removed = tuple(
        sorted(
            (site for key, site in baseline_keys.items() if key not in current_keys),
            key=lambda item: (item.path, item.line, item.kind),
        )
    )
    bare = tuple(site for site in current if site.kind == "bare_except")
    return added, removed, bare


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify catch-all exception governance against a checked-in baseline."
    )
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Root path to scan; defaults to app and scripts.",
    )
    parser.add_argument(
        "--baseline-path",
        type=Path,
        default=DEFAULT_BASELINE_PATH,
        help="Path to baseline JSON.",
    )
    parser.add_argument(
        "--write-baseline",
        action="store_true",
        help="Regenerate baseline file from current repository state.",
    )
    parser.add_argument(
        "--allow-missing-root",
        action="store_true",
        help="Skip missing roots instead of failing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        roots = (
            tuple(_resolve_root_path(Path(item)) for item in args.root)
            if args.root
            else tuple(_resolve_root_path(path) for path in DEFAULT_ROOTS)
        )
        baseline_path = _resolve_baseline_path(args.baseline_path)
    except ValueError as exc:
        print(f"[exception-governance] failed: {exc}")
        return 2
    missing = [root for root in roots if not root.exists()]
    if missing and not args.allow_missing_root:
        print("Missing scan roots: " + ", ".join(path.as_posix() for path in missing))
        return 2

    available_roots = tuple(root for root in roots if root.exists())
    current = collect_exception_sites(roots=available_roots)

    if args.write_baseline:
        write_baseline(
            baseline_path=baseline_path,
            roots=available_roots,
            sites=current,
        )
        print(
            f"Exception baseline refreshed: {baseline_path.as_posix()} "
            f"(sites={len(current)})"
        )
        return 0

    try:
        baseline = _load_baseline(baseline_path)
    except FileNotFoundError as exc:
        print(f"[exception-governance] failed: {exc}")
        return 2
    added, removed, bare = verify_against_baseline(current=current, baseline=baseline)
    if bare:
        print("Bare except handlers are forbidden:")
        for site in bare:
            print(f"- {site.path}:{site.line} [{site.kind}]")
        return 1

    if added:
        print(
            "New catch-all handlers detected (update code or refresh baseline with approval):"
        )
        for site in added:
            print(f"- {site.path}:{site.line} [{site.kind}]")
        return 1

    if removed:
        print(f"Catch-all governance improvements detected (removed={len(removed)}).")
    print(
        "Exception governance check passed "
        f"(current={len(current)}, baseline={len(baseline)})."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
