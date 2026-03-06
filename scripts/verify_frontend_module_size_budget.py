"""Guardrail for oversized frontend source modules."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MAX_LINES = 500
PREFERRED_MAX_LINES = 400
FRONTEND_EXTENSIONS = {".svelte", ".ts", ".js", ".css"}
FRONTEND_SOURCE_ROOT = Path("dashboard/src")

# Transitional exceptions while decomposition work is in progress.
FRONTEND_MODULE_LINE_BUDGET_OVERRIDES: dict[str, int] = {}


@dataclass(frozen=True)
class FrontendModuleSizeViolation:
    path: str
    lines: int
    max_lines: int


@dataclass(frozen=True)
class FrontendModuleSizePreferredBreach:
    path: str
    lines: int
    preferred_max_lines: int


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def _iter_frontend_modules(root: Path) -> tuple[Path, ...]:
    frontend_root = root / FRONTEND_SOURCE_ROOT
    modules: list[Path] = []
    for source_path in sorted(frontend_root.rglob("*")):
        if not source_path.is_file():
            continue
        if source_path.suffix not in FRONTEND_EXTENSIONS:
            continue
        modules.append(source_path)
    return tuple(modules)


def collect_frontend_module_size_violations(
    root: Path,
    *,
    default_max_lines: int = DEFAULT_MAX_LINES,
    overrides: dict[str, int] | None = None,
) -> tuple[FrontendModuleSizeViolation, ...]:
    normalized_overrides = overrides or FRONTEND_MODULE_LINE_BUDGET_OVERRIDES
    violations: list[FrontendModuleSizeViolation] = []
    for module_path in _iter_frontend_modules(root):
        relative = module_path.relative_to(root).as_posix()
        max_lines = int(normalized_overrides.get(relative, default_max_lines))
        lines = _line_count(module_path)
        if lines > max_lines:
            violations.append(
                FrontendModuleSizeViolation(path=relative, lines=lines, max_lines=max_lines)
            )
    return tuple(violations)


def collect_frontend_module_size_preferred_breaches(
    root: Path,
    *,
    preferred_max_lines: int = PREFERRED_MAX_LINES,
) -> tuple[FrontendModuleSizePreferredBreach, ...]:
    breaches: list[FrontendModuleSizePreferredBreach] = []
    for module_path in _iter_frontend_modules(root):
        relative = module_path.relative_to(root).as_posix()
        lines = _line_count(module_path)
        if lines > preferred_max_lines:
            breaches.append(
                FrontendModuleSizePreferredBreach(
                    path=relative,
                    lines=lines,
                    preferred_max_lines=preferred_max_lines,
                )
            )
    return tuple(breaches)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when frontend modules exceed line-count budgets. "
            "Default budget applies to all dashboard/src source files unless overridden."
        )
    )
    parser.add_argument(
        "--root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root path.",
    )
    parser.add_argument(
        "--default-max-lines",
        type=int,
        default=DEFAULT_MAX_LINES,
        help="Hard line budget for frontend source modules.",
    )
    parser.add_argument(
        "--preferred-max-lines",
        type=int,
        default=PREFERRED_MAX_LINES,
        help=(
            "Preferred line budget for frontend modules. Modules above this threshold are "
            "reported as warnings but do not fail the check."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    preferred_breaches = collect_frontend_module_size_preferred_breaches(
        root,
        preferred_max_lines=int(args.preferred_max_lines),
    )
    violations = collect_frontend_module_size_violations(
        root,
        default_max_lines=int(args.default_max_lines),
    )

    if not violations:
        print(
            "[frontend-module-size-budget] ok "
            f"root={root} default_max_lines={args.default_max_lines} "
            f"preferred_max_lines={args.preferred_max_lines}"
        )
        if preferred_breaches:
            print(
                "[frontend-module-size-budget] warning "
                f"found {len(preferred_breaches)} module(s) above preferred target:"
            )
            for breach in preferred_breaches:
                print(
                    f" - {breach.path}: {breach.lines} lines "
                    f"(preferred={breach.preferred_max_lines})"
                )
        return 0

    print(
        "[frontend-module-size-budget] "
        f"found {len(violations)} oversized module(s):"
    )
    for violation in violations:
        print(
            f" - {violation.path}: {violation.lines} lines "
            f"(budget={violation.max_lines})"
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
