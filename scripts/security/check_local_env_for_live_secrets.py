#!/usr/bin/env python3
"""
Fail-fast local scanner for accidental live secrets in .env.

This script is intentionally conservative and only prints key names, never values.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path


PATTERNS: dict[str, re.Pattern[str]] = {
    "PAYSTACK_SECRET_KEY": re.compile(r"^sk_live_[A-Za-z0-9_]+$"),
    "PAYSTACK_PUBLIC_KEY": re.compile(r"^pk_live_[A-Za-z0-9_]+$"),
    "SLACK_BOT_TOKEN": re.compile(r"^xox[baprs]-[A-Za-z0-9-]+$"),
    "GROQ_API_KEY": re.compile(r"^gsk_[A-Za-z0-9]+$"),
    "OPENAI_API_KEY": re.compile(
        r"^(?:sk-[A-Za-z0-9]{20,}|sk-(?:proj|svcacct)-[A-Za-z0-9_-]{6,})$"
    ),
    "AWS_ACCESS_KEY_ID": re.compile(r"^(?:AKIA|ASIA)[0-9A-Z]{16}$"),
    "AWS_SECRET_ACCESS_KEY": re.compile(r"^[A-Za-z0-9/+=]{40}$"),
    "DATABASE_URL": re.compile(r"^postgres(?:ql(?:\+asyncpg)?)://[^:]+:[^@]+@.+$"),
}


def is_live_secret_value(key: str, value: str) -> bool:
    pattern = PATTERNS.get(str(key or "").strip())
    if pattern is None:
        return False
    return bool(pattern.match(str(value or "").strip()))


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan a local env file for known live-secret patterns."
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        default=Path(".env"),
        help="Env file to scan. Relative paths are resolved from the repo root.",
    )
    return parser


def _resolve_env_path(path: Path) -> Path:
    raw = Path(path).expanduser()
    repo_root = _repo_root()
    if raw.is_absolute():
        resolved = raw.resolve()
    else:
        resolved = (repo_root / raw).resolve()
        try:
            resolved.relative_to(repo_root)
        except ValueError as exc:
            raise ValueError(
                "--env-file must stay within repo root when relative"
            ) from exc

    if resolved.exists() and not resolved.is_file():
        raise ValueError(f"--env-file must be a file path: {resolved.as_posix()}")
    return resolved


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        env_path = _resolve_env_path(args.env_file)
    except ValueError as exc:
        print(str(exc))
        return 2

    if not env_path.exists():
        print("No .env file found.")
        return 0

    risky_keys: list[str] = []
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue
        is_commented = line.startswith("#")
        content = line[1:].strip() if is_commented else line
        if "=" not in content:
            continue
        key, _, raw_value = content.partition("=")
        key = key.strip()
        value = raw_value.strip().strip('"').strip("'")

        if is_live_secret_value(key, value):
            suffix = " (commented)" if is_commented else ""
            risky_keys.append(f"{key}{suffix}")

    if risky_keys:
        deduped = sorted(set(risky_keys))
        print("Potential live secrets detected in .env:")
        for key in deduped:
            print(f"- {key}")
        print("Rotate these secrets and replace .env with non-live placeholders.")
        return 1

    print("No known live-secret patterns detected in .env.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
