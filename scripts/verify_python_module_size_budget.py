"""Guardrail for oversized Python modules in the application package."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path


DEFAULT_MAX_LINES = 700
PREFERRED_MAX_LINES = 500
ENFORCEMENT_MODES: tuple[str, ...] = ("advisory", "strict")

# Transitional exceptions while decomposition work is in progress.
# Overrides can only raise the hard budget to avoid forcing artificial splits.
MODULE_LINE_BUDGET_OVERRIDES: dict[str, int] = {
    "app/main.py": 551,
    "app/models/enforcement.py": 778,
    "app/modules/billing/domain/billing/paystack_service_impl.py": 599,
    "app/modules/enforcement/api/v1/enforcement.py": 668,
    "app/modules/enforcement/domain/actions.py": 565,
    "app/modules/enforcement/domain/gate_evaluation_ops.py": 620,
    "app/modules/enforcement/domain/service.py": 527,
    "app/modules/enforcement/domain/service_runtime_ops.py": 610,
    "app/modules/governance/api/v1/health_dashboard.py": 694,
    "app/modules/governance/api/v1/scim.py": 742,
    "app/modules/governance/api/v1/scim_membership_ops.py": 597,
    "app/modules/governance/api/v1/settings/notifications.py": 870,
    "app/modules/governance/domain/jobs/handlers/acceptance.py": 741,
    "app/modules/governance/api/v1/audit_evidence.py": 500,
    "app/modules/governance/domain/security/compliance_pack_bundle.py": 500,
    "app/modules/reporting/api/v1/carbon.py": 586,
    "app/modules/reporting/api/v1/costs.py": 797,
    "app/modules/reporting/domain/aggregator.py": 630,
    "app/modules/reporting/domain/attribution_engine_allocation_ops.py": 512,
    "app/modules/reporting/domain/attribution_engine.py": 748,
    "app/modules/reporting/domain/persistence.py": 602,
    "app/modules/reporting/domain/reconciliation.py": 500,
    "app/modules/reporting/domain/savings_proof.py": 720,
    "app/modules/optimization/api/v1/zombies.py": 500,
    "app/modules/optimization/domain/service.py": 500,
    "app/modules/optimization/domain/strategy_service.py": 500,
    "app/modules/optimization/domain/remediation_execute.py": 500,
    "app/schemas/connections.py": 730,
    "app/shared/analysis/azure_usage_analyzer.py": 505,
    "app/shared/analysis/cur_usage_analyzer.py": 531,
    "app/shared/adapters/aws_cur.py": 791,
    "app/shared/adapters/hybrid.py": 872,
    "app/shared/adapters/platform.py": 961,
    "app/shared/connections/discovery.py": 883,
    "app/shared/core/auth.py": 524,
    "app/shared/core/config.py": 771,
    "app/shared/core/performance_testing.py": 595,
    "app/shared/core/pricing.py": 804,
    "app/shared/db/session.py": 724,
    "app/shared/llm/analyzer.py": 500,
    "app/shared/llm/budget_execution.py": 595,
    "app/shared/llm/budget_fair_use.py": 844,
    "app/tasks/scheduler_tasks.py": 598,
}


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Report module-size maintainability signals. "
            "Use --enforcement-mode strict only when a hard fail is intentionally required."
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
        "--enforcement-mode",
        choices=ENFORCEMENT_MODES,
        default="advisory",
        help=(
            "advisory: never fail on line-count budget drift. "
            "strict: fail when a module exceeds the hard budget."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    root = Path(args.root).resolve()
    preferred_breaches = collect_module_size_preferred_breaches(
        root,
        preferred_max_lines=int(args.preferred_max_lines),
    )
    violations = collect_module_size_violations(
        root,
        default_max_lines=int(args.default_max_lines),
    )
    print(
        "[python-module-size-budget] "
        f"root={root} mode={args.enforcement_mode} "
        f"default_max_lines={args.default_max_lines} "
        f"preferred_max_lines={args.preferred_max_lines}"
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
        "[python-module-size-budget] advisory mode keeps line counts non-blocking; "
        "use complexity checks (e.g., C901) as the hard governance gate."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
