#!/usr/bin/env python3
"""Validate the minimal Alembic migration env contract."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys
from unittest.mock import patch

from pydantic import ValidationError

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.shared.core.migration_settings import MigrationSettings
from scripts.env_generation_common import parse_env_file


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate the Alembic migration env contract."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=None,
        help="Optional shell-source-safe env file to load before validation.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    env_overrides: dict[str, str] = {}
    if args.env_file is not None:
        if args.env_file.exists() and not args.env_file.is_file():
            print(
                f"migration_env_validation_failed: env-file must be a file path: {args.env_file}",
                file=sys.stderr,
            )
            return 1
        try:
            env_overrides.update(parse_env_file(args.env_file))
        except OSError as exc:
            print(f"migration_env_validation_failed: {exc}", file=sys.stderr)
            return 1

    try:
        with patch.dict(os.environ, env_overrides, clear=False):
            settings = MigrationSettings(_env_file=None)
    except (ValidationError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"migration_env_validation_failed: {exc}", file=sys.stderr)
        return 1

    print(
        "migration_env_validation_passed",
        f"db_ssl_mode={settings.DB_SSL_MODE}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
