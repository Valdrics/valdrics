"""Guardrail for oversized Python modules in the application package."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MAX_LINES = 700
PREFERRED_MAX_LINES = 500
ENFORCEMENT_MODES: tuple[str, ...] = ("advisory", "strict")
CLUSTER_MIN_LINES = 495
CLUSTER_MAX_LINES = 500
EMIT_PREFERRED_SIGNALS_DEFAULT = False
EMIT_CLUSTER_SIGNALS_DEFAULT = False

MODULE_LINE_BUDGET_OVERRIDES: dict[str, int] = {}


@dataclass(frozen=True)
class ModuleSizeViolation:
    path: str
    lines: int
    max_lines: int


@dataclass(frozen=True)
class ModuleSizePreferredBreach:
    path: str
    lines: int
    preferred_max_lines: int


@dataclass(frozen=True)
class ModuleSizeClusterSignal:
    path: str
    lines: int
    cluster_min_lines: int
    cluster_max_lines: int


def _line_count(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for _ in handle)


def collect_module_size_violations(
    root: Path,
    *,
    default_max_lines: int = DEFAULT_MAX_LINES,
    overrides: dict[str, int] | None = None,
) -> tuple[ModuleSizeViolation, ...]:
    normalized_overrides = overrides or MODULE_LINE_BUDGET_OVERRIDES
    app_root = root / "app"
    violations: list[ModuleSizeViolation] = []
    for module_path in sorted(app_root.rglob("*.py")):
        relative = module_path.relative_to(root).as_posix()
        override_budget = int(normalized_overrides.get(relative, default_max_lines))
        max_lines = max(default_max_lines, override_budget)
        lines = _line_count(module_path)
        if lines > max_lines:
            violations.append(
                ModuleSizeViolation(path=relative, lines=lines, max_lines=max_lines)
            )
    return tuple(violations)


def collect_module_size_preferred_breaches(
    root: Path,
    *,
    preferred_max_lines: int = PREFERRED_MAX_LINES,
) -> tuple[ModuleSizePreferredBreach, ...]:
    app_root = root / "app"
    breaches: list[ModuleSizePreferredBreach] = []
    for module_path in sorted(app_root.rglob("*.py")):
        relative = module_path.relative_to(root).as_posix()
        lines = _line_count(module_path)
        if lines > preferred_max_lines:
            breaches.append(
                ModuleSizePreferredBreach(
                    path=relative,
                    lines=lines,
                    preferred_max_lines=preferred_max_lines,
                )
            )
    return tuple(breaches)


def collect_module_size_cluster_signals(
    root: Path,
    *,
    cluster_min_lines: int = CLUSTER_MIN_LINES,
    cluster_max_lines: int = CLUSTER_MAX_LINES,
) -> tuple[ModuleSizeClusterSignal, ...]:
    app_root = root / "app"
    signals: list[ModuleSizeClusterSignal] = []
    for module_path in sorted(app_root.rglob("*.py")):
        relative = module_path.relative_to(root).as_posix()
        lines = _line_count(module_path)
        if cluster_min_lines <= lines <= cluster_max_lines:
            signals.append(
                ModuleSizeClusterSignal(
                    path=relative,
                    lines=lines,
                    cluster_min_lines=cluster_min_lines,
                    cluster_max_lines=cluster_max_lines,
                )
            )
    return tuple(signals)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Enforce module-size maintainability signals with a strict default hard guardrail. "
            "Use advisory mode only for explicit non-blocking analysis. "
            "Complexity gates (for example C901) remain complementary cohesion controls."
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
        help=(
            "Hard-fail line budget for app Python modules. "
            "Per-file overrides can only raise this budget."
        ),
    )
    parser.add_argument(
        "--preferred-max-lines",
        type=int,
        default=PREFERRED_MAX_LINES,
        help=(
            "Preferred line budget for app modules. Modules above this threshold are "
            "reported as warnings but do not fail the check."
        ),
    )
    parser.add_argument(
        "--emit-preferred-signals",
        action="store_true",
        default=EMIT_PREFERRED_SIGNALS_DEFAULT,
        help=(
            "Emit preferred-threshold warnings for long modules. Disabled by default "
            "to avoid line-count-driven fragmentation pressure."
        ),
    )
    parser.add_argument(
        "--enforcement-mode",
        choices=ENFORCEMENT_MODES,
        default="strict",
        help=(
            "strict: fail when a module exceeds the hard budget. "
            "advisory: report drift without failing."
        ),
    )
    parser.add_argument(
        "--cluster-min-lines",
        type=int,
        default=CLUSTER_MIN_LINES,
        help=(
            "Lower bound for near-limit clustering signal (advisory). "
            "Use with --cluster-max-lines to detect suspicious budget-edge files."
        ),
    )
    parser.add_argument(
        "--cluster-max-lines",
        type=int,
        default=CLUSTER_MAX_LINES,
        help="Upper bound for near-limit clustering signal (advisory).",
    )
    parser.add_argument(
        "--emit-cluster-signals",
        action="store_true",
        default=EMIT_CLUSTER_SIGNALS_DEFAULT,
        help=(
            "Emit near-limit clustering warnings for modules inside the cluster range. "
            "Disabled by default to avoid artificial file-splitting pressure."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    preferred_breaches: tuple[ModuleSizePreferredBreach, ...] = ()
    if bool(args.emit_preferred_signals):
        preferred_breaches = collect_module_size_preferred_breaches(
            root,
            preferred_max_lines=int(args.preferred_max_lines),
        )
    violations = collect_module_size_violations(
        root,
        default_max_lines=int(args.default_max_lines),
    )
    cluster_signals: tuple[ModuleSizeClusterSignal, ...] = ()
    if bool(args.emit_cluster_signals):
        cluster_signals = collect_module_size_cluster_signals(
            root,
            cluster_min_lines=int(args.cluster_min_lines),
            cluster_max_lines=int(args.cluster_max_lines),
        )
    print(
        "[python-module-size-budget] "
        f"root={root} mode={args.enforcement_mode} "
        f"default_max_lines={args.default_max_lines} "
        f"preferred_max_lines={args.preferred_max_lines} "
        f"emit_preferred_signals={bool(args.emit_preferred_signals)}"
    )

    if preferred_breaches:
        print(
            "[python-module-size-budget] warning "
            f"found {len(preferred_breaches)} module(s) above preferred target:"
        )
        for breach in preferred_breaches:
            print(
                f" - {breach.path}: {breach.lines} lines "
                f"(preferred={breach.preferred_max_lines})"
            )

    if cluster_signals:
        print(
            "[python-module-size-budget] warning "
            f"found {len(cluster_signals)} module(s) clustered near line budget "
            f"({args.cluster_min_lines}-{args.cluster_max_lines}):"
        )
        for signal in cluster_signals:
            print(
                f" - {signal.path}: {signal.lines} lines "
                f"(cluster={signal.cluster_min_lines}-{signal.cluster_max_lines})"
            )

    if not violations:
        print("[python-module-size-budget] ok no module exceeded hard budget.")
        return 0

    level = "FAILED" if args.enforcement_mode == "strict" else "warning"
    print(
        "[python-module-size-budget] "
        f"{level} found {len(violations)} module(s) above hard budget:"
    )
    for violation in violations:
        print(
            f" - {violation.path}: {violation.lines} lines "
            f"(budget={violation.max_lines})"
        )
    if args.enforcement_mode == "strict":
        return 1
    print(
        "[python-module-size-budget] advisory mode is explicitly non-blocking; "
        "strict mode remains the default governance gate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
