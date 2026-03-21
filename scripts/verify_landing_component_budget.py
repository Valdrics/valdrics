"""Verify landing component decomposition and size budgets remain within guardrails."""

from __future__ import annotations

import argparse
from pathlib import Path
from scripts.env_generation_common import (
    repo_root_for as _repo_root_for,
    resolve_cli_path_from_root,
)
from typing import Any

DEFAULT_HERO_PATH = Path("dashboard/src/lib/components/LandingHero.svelte")
DEFAULT_COMPONENT_DIR = Path("dashboard/src/lib/components/landing")
DEFAULT_MAX_HERO_LINES = 800
REQUIRED_COMPONENT_FILES = (
    "LandingHeroCopy.svelte",
    "LandingSignalMapCard.svelte",
    "LandingRoiSimulator.svelte",
    "LandingCloudHookSection.svelte",
    "LandingWorkflowSection.svelte",
    "LandingBenefitsSection.svelte",
    "LandingPlansSection.svelte",
    "LandingPersonaSection.svelte",
    "LandingCapabilitiesSection.svelte",
    "LandingTrustSection.svelte",
    "LandingRoiPlannerCta.svelte",
    "LandingLeadCaptureSection.svelte",
    "LandingExitIntentPrompt.svelte",
    "LandingCookieConsent.svelte",
)


class LandingBudgetVerificationError(RuntimeError):
    pass


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _resolve_repo_relative_path(path: Path, *, field_name: str) -> Path:
    try:
        return resolve_cli_path_from_root(_repo_root(), path, field_name=field_name)
    except ValueError as exc:
        raise LandingBudgetVerificationError(
            f"{field_name} must stay within repo root when relative"
        ) from exc


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def verify_landing_component_budget(
    *,
    hero_path: Path = DEFAULT_HERO_PATH,
    component_dir: Path = DEFAULT_COMPONENT_DIR,
    max_hero_lines: int = DEFAULT_MAX_HERO_LINES,
) -> dict[str, Any]:
    if not hero_path.exists():
        raise LandingBudgetVerificationError(f"Hero file not found: {hero_path}")
    if not hero_path.is_file():
        raise LandingBudgetVerificationError(f"hero_path must be a file: {hero_path}")
    if component_dir.exists() and not component_dir.is_dir():
        raise LandingBudgetVerificationError(
            f"component_dir must be a directory: {component_dir}"
        )
    if max_hero_lines < 200:
        raise LandingBudgetVerificationError(
            "max_hero_lines is unrealistically low; expected >= 200"
        )

    hero_lines = _line_count(hero_path)
    if hero_lines > max_hero_lines:
        raise LandingBudgetVerificationError(
            f"Landing hero line budget exceeded: {hero_lines} > {max_hero_lines}"
        )

    missing_components = [
        name for name in REQUIRED_COMPONENT_FILES if not (component_dir / name).exists()
    ]
    if missing_components:
        raise LandingBudgetVerificationError(
            "Required landing decomposition components missing: "
            + ", ".join(sorted(missing_components))
        )

    component_line_counts = {
        name: _line_count(component_dir / name) for name in REQUIRED_COMPONENT_FILES
    }

    return {
        "hero_path": str(hero_path),
        "hero_lines": hero_lines,
        "max_hero_lines": max_hero_lines,
        "component_dir": str(component_dir),
        "required_component_count": len(REQUIRED_COMPONENT_FILES),
        "component_line_counts": component_line_counts,
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verify LandingHero.svelte decomposition and line-count budget."
    )
    parser.add_argument(
        "--hero-path",
        default=str(DEFAULT_HERO_PATH),
        help="Path to landing hero component.",
    )
    parser.add_argument(
        "--component-dir",
        default=str(DEFAULT_COMPONENT_DIR),
        help="Path to landing component decomposition directory.",
    )
    parser.add_argument(
        "--max-hero-lines",
        type=int,
        default=DEFAULT_MAX_HERO_LINES,
        help=f"Maximum allowed LandingHero lines (default: {DEFAULT_MAX_HERO_LINES}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        summary = verify_landing_component_budget(
            hero_path=_resolve_repo_relative_path(
                Path(str(args.hero_path)),
                field_name="hero_path",
            ),
            component_dir=_resolve_repo_relative_path(
                Path(str(args.component_dir)),
                field_name="component_dir",
            ),
            max_hero_lines=int(args.max_hero_lines),
        )
    except LandingBudgetVerificationError as exc:
        print(f"[landing-budget-verify] failed: {exc}")
        return 2

    print(
        "[landing-budget-verify] passed: "
        f"hero_lines={summary['hero_lines']} max={summary['max_hero_lines']} "
        f"components={summary['required_component_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
