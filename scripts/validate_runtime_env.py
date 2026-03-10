#!/usr/bin/env python3
"""
Runtime environment preflight validator.

Validates:
- Settings contract (required secrets/env, security constraints)
- Runtime dependency contract (tiktoken, prophet fallback policy, sentry-sdk when DSN set)
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.env_generation_common import parse_env_file
from app.shared.core.config import Settings
from app.shared.core.runtime_dependencies import validate_runtime_dependencies


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate runtime env + dependency contract before deployment."
    )
    parser.add_argument(
        "--environment",
        choices=["local", "development", "staging", "production"],
        default=None,
        help="Override ENVIRONMENT for validation.",
    )
    parser.add_argument(
        "--allow-testing",
        action="store_true",
        help="Do not force TESTING=false (default forces production-style validation).",
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional shell-source-safe env file to load before validation.",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    if args.env_file is not None:
        for key, value in parse_env_file(args.env_file).items():
            os.environ[key] = value

    if args.environment:
        os.environ["ENVIRONMENT"] = args.environment
    if not args.allow_testing:
        os.environ["TESTING"] = "false"

    try:
        # Hermetic validation: never read repository-local `.env` during CI/runtime preflight.
        settings = Settings(_env_file=None)
        validate_runtime_dependencies(settings)
    except (ImportError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"runtime_env_validation_failed: {exc}", file=sys.stderr)
        return 1

    print(
        "runtime_env_validation_passed",
        f"environment={settings.ENVIRONMENT}",
        f"testing={settings.TESTING}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
