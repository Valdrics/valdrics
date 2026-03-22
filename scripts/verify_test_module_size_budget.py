"""Guardrail for oversized Python test modules."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)


DEFAULT_MAX_LINES = 2000
PREFERRED_MAX_LINES = 1000

# Transitional exceptions while decomposition work is in progress.
TEST_MODULE_LINE_BUDGET_OVERRIDES: dict[str, int] = {}


@dataclass(frozen=True)
class TestModuleSizeViolation:
    path: str
    lines: int
    max_lines: int


@dataclass(frozen=True)
class TestModuleSizePreferredBreach:
    path: str
    lines: int
    preferred_max_lines: int


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_root(path: Path) -> Path:
    return resolve_cli_path_from_root(_repo_root(), path, field_name="root")


def _validate_root(root: Path) -> None:
    if not root.exists():
        raise ValueError(f"root does not exist: {root}")
    if not root.is_dir():
        raise ValueError(f"root must be a directory: {root}")


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def collect_test_module_size_violations(
    root: Path,
    *,
    default_max_lines: int = DEFAULT_MAX_LINES,
    overrides: dict[str, int] | None = None,
) -> tuple[TestModuleSizeViolation, ...]:
    _validate_root(root)
    normalized_overrides = overrides or TEST_MODULE_LINE_BUDGET_OVERRIDES
    tests_root = root / "tests"
    violations: list[TestModuleSizeViolation] = []
    for module_path in sorted(tests_root.rglob("*.py")):
        relative = module_path.relative_to(root).as_posix()
        max_lines = int(normalized_overrides.get(relative, default_max_lines))
        lines = _line_count(module_path)
        if lines > max_lines:
            violations.append(
                TestModuleSizeViolation(path=relative, lines=lines, max_lines=max_lines)
            )
    return tuple(violations)


def collect_test_module_size_preferred_breaches(
    root: Path,
    *,
    preferred_max_lines: int = PREFERRED_MAX_LINES,
) -> tuple[TestModuleSizePreferredBreach, ...]:
    _validate_root(root)
    tests_root = root / "tests"
    breaches: list[TestModuleSizePreferredBreach] = []
    for module_path in sorted(tests_root.rglob("*.py")):
        relative = module_path.relative_to(root).as_posix()
        lines = _line_count(module_path)
        if lines > preferred_max_lines:
            breaches.append(
                TestModuleSizePreferredBreach(
                    path=relative,
                    lines=lines,
                    preferred_max_lines=preferred_max_lines,
                )
            )
    return tuple(breaches)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fail when Python test modules exceed line-count budgets. "
            "Default budget applies to all tests modules unless explicitly overridden."
        )
    )
    parser.add_argument(
        "--root",
        default=str(_repo_root()),
        help="Repository root path.",
    )
    parser.add_argument(
        "--default-max-lines",
        type=int,
        default=DEFAULT_MAX_LINES,
        help="Hard line budget for tests Python modules.",
    )
    parser.add_argument(
        "--preferred-max-lines",
        type=int,
        default=PREFERRED_MAX_LINES,
        help=(
            "Preferred line budget for tests modules. Modules above this threshold are "
            "reported as warnings but do not fail the check."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        root = _resolve_root(Path(str(args.root)))
        preferred_breaches = collect_test_module_size_preferred_breaches(
            root,
            preferred_max_lines=int(args.preferred_max_lines),
        )
        violations = collect_test_module_size_violations(
            root,
            default_max_lines=int(args.default_max_lines),
        )
    except ValueError as exc:
        print(f"[test-module-size-budget] failed: {exc}")
        return 2
    if not violations:
        print(
            "[test-module-size-budget] ok "
            f"root={root} default_max_lines={args.default_max_lines} "
            f"preferred_max_lines={args.preferred_max_lines}"
        )
        if preferred_breaches:
            print(
                "[test-module-size-budget] warning "
                f"found {len(preferred_breaches)} module(s) above preferred target:"
            )
            for breach in preferred_breaches:
                print(
                    f" - {breach.path}: {breach.lines} lines "
                    f"(preferred={breach.preferred_max_lines})"
                )
        return 0

    print(
        "[test-module-size-budget] "
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
