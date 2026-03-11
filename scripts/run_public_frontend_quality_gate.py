#!/usr/bin/env python3
"""Run the public-site browser quality gates from the repo root."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parents[1]


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]


def build_public_quality_commands(
    *,
    include_a11y: bool = True,
    include_perf: bool = True,
    include_visual: bool = True,
) -> list[tuple[str, list[str]]]:
    commands: list[tuple[str, list[str]]] = [
        (
            "public critical-path smoke",
            [
                "pnpm",
                "--dir",
                "dashboard",
                "exec",
                "playwright",
                "test",
                "e2e/public-marketing.spec.ts",
                "--reporter=line",
            ],
        )
    ]
    if include_a11y:
        commands.append(
            (
                "public accessibility gate",
                ["pnpm", "--dir", "dashboard", "run", "test:a11y:public"],
            )
        )
    if include_perf:
        commands.append(
            (
                "public performance gate",
                ["pnpm", "--dir", "dashboard", "run", "test:perf:ci"],
            )
        )
    if include_visual:
        commands.append(
            (
                "public visual gate",
                ["pnpm", "--dir", "dashboard", "run", "test:visual"],
            )
        )
    return commands


def _build_environment(
    *,
    dashboard_url: str | None,
    skip_webserver: bool,
) -> dict[str, str]:
    env = os.environ.copy()
    env.pop("NO_COLOR", None)
    if dashboard_url:
        env["DASHBOARD_URL"] = dashboard_url
    if skip_webserver:
        env["PLAYWRIGHT_SKIP_WEBSERVER"] = "1"
    return env


def run_public_frontend_quality_gate(
    *,
    dashboard_url: str | None = None,
    skip_webserver: bool = False,
    include_a11y: bool = True,
    include_perf: bool = True,
    include_visual: bool = True,
    runner: CommandRunner = subprocess.run,
) -> None:
    env = _build_environment(
        dashboard_url=dashboard_url,
        skip_webserver=skip_webserver,
    )
    commands = build_public_quality_commands(
        include_a11y=include_a11y,
        include_perf=include_perf,
        include_visual=include_visual,
    )

    for label, cmd in commands:
        print(f"[public-quality] running {label}: {' '.join(cmd)}")
        runner(
            cmd,
            cwd=REPO_ROOT,
            env=env,
            check=True,
            text=True,
        )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Run the public browser smoke, accessibility, performance, and visual gates."
        )
    )
    parser.add_argument(
        "--dashboard-url",
        default=None,
        help=(
            "Existing dashboard URL to target (for example http://localhost:5174). "
            "When provided with --skip-webserver, the gate will reuse that running app."
        ),
    )
    parser.add_argument(
        "--skip-webserver",
        action="store_true",
        help="Do not let Playwright boot its own preview server.",
    )
    parser.add_argument(
        "--skip-a11y",
        action="store_true",
        help="Skip the accessibility suite.",
    )
    parser.add_argument(
        "--skip-perf",
        action="store_true",
        help="Skip the performance suite.",
    )
    parser.add_argument(
        "--skip-visual",
        action="store_true",
        help="Skip the visual suite.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    run_public_frontend_quality_gate(
        dashboard_url=args.dashboard_url,
        skip_webserver=bool(args.skip_webserver),
        include_a11y=not bool(args.skip_a11y),
        include_perf=not bool(args.skip_perf),
        include_visual=not bool(args.skip_visual),
    )
    print("[public-quality] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
