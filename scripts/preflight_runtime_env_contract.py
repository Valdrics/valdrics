#!/usr/bin/env python3
"""Fail fast when GitHub managed-runtime JSON cannot produce a release-ready env."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shlex
import sys
import tempfile
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.generate_managed_runtime_env import generate_managed_runtime_env
from scripts.managed_deployment_contract import runtime_json_classification_errors


DEFAULT_PLAIN_ENV_NAME = "RUNTIME_PLAIN_ENV_JSON"
DEFAULT_SECRET_ENV_NAME = "RUNTIME_SECRET_ENV_JSON"


def _load_payload_from_env(name: str) -> dict[str, str]:
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        raise ValueError(f"{name} must be set to a JSON object")

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{name} must be valid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{name} must be a JSON object")

    normalized: dict[str, str] = {}
    for raw_key, raw_value in payload.items():
        key = str(raw_key or "").strip()
        if not key:
            raise ValueError(f"{name} contains an empty key")
        if not isinstance(raw_value, str):
            raise ValueError(f"{name}.{key} must be a string")
        normalized[key] = raw_value
    return normalized


def _render_env_payload(values: dict[str, str]) -> str:
    lines = []
    for key in sorted(values):
        value = values[key]
        rendered = "" if value == "" else shlex.quote(value)
        lines.append(f"{key}={rendered}")
    return "\n".join(lines) + "\n"


def preflight_runtime_env_contract(
    *,
    environment: str,
    plain: dict[str, str],
    secret: dict[str, str],
    template_path: Path,
) -> dict[str, Any]:
    normalized_environment = environment.strip().lower()
    overlap = sorted(set(plain) & set(secret))
    if overlap:
        raise ValueError(
            "RUNTIME_PLAIN_ENV_JSON and RUNTIME_SECRET_ENV_JSON must not share keys: "
            + ", ".join(overlap)
        )

    classification_errors = runtime_json_classification_errors(plain, secret)
    if classification_errors:
        raise ValueError("\n".join(classification_errors))

    with tempfile.TemporaryDirectory(
        prefix=f"valdrics-{normalized_environment}-runtime-contract-"
    ) as temp_dir:
        temp_root = Path(temp_dir)
        output_path = temp_root / f"{normalized_environment}.env"
        report_path = temp_root / f"{normalized_environment}.report.json"
        output_path.write_text(_render_env_payload({**plain, **secret}), encoding="utf-8")

        report = generate_managed_runtime_env(
            template_path=template_path,
            output_path=output_path,
            report_path=report_path,
            environment=normalized_environment,
        )

    blockers = [
        str(key)
        for key in report.get("runtime_validation_blockers", [])
        if str(key).strip()
    ]
    if blockers:
        raise ValueError(
            "managed runtime contract has unresolved operator inputs: "
            + ", ".join(sorted(blockers))
        )

    return report


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--environment",
        required=True,
        choices=("staging", "production"),
        help="Managed release environment to validate.",
    )
    parser.add_argument(
        "--runtime-plain-env-name",
        default=DEFAULT_PLAIN_ENV_NAME,
        help="Environment variable containing the plain managed runtime JSON.",
    )
    parser.add_argument(
        "--runtime-secret-env-name",
        default=DEFAULT_SECRET_ENV_NAME,
        help="Environment variable containing the secret managed runtime JSON.",
    )
    parser.add_argument(
        "--template-path",
        type=Path,
        default=Path(".env.example"),
        help="Runtime env template used by managed runtime generation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = preflight_runtime_env_contract(
            environment=args.environment,
            plain=_load_payload_from_env(args.runtime_plain_env_name),
            secret=_load_payload_from_env(args.runtime_secret_env_name),
            template_path=args.template_path,
        )
    except Exception as exc:
        print(f"::error title=Managed runtime contract preflight failed::{exc}")
        return 1

    required_keys = report.get("required_operator_input_keys", [])
    print(
        "[managed-runtime-contract-preflight] ok "
        f"environment={args.environment} required_operator_input_keys={len(required_keys)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
