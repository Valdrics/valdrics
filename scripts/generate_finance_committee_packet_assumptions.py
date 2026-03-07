#!/usr/bin/env python3
"""Generate finance committee packet assumptions from runtime telemetry."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

from scripts.finance_committee_packet_assumptions_engine import (
    derive_assumptions_inputs,
)
from scripts.finance_committee_packet_common import load_json
from scripts.generate_finance_telemetry_snapshot import (
    main as generate_finance_telemetry_snapshot_main,
)
from scripts.verify_finance_telemetry_snapshot import verify_snapshot


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate finance committee packet assumptions JSON from a telemetry snapshot."
        ),
    )
    parser.add_argument("--output", required=True, help="Output assumptions JSON path.")
    parser.add_argument(
        "--telemetry-path",
        default=None,
        help=(
            "Optional telemetry snapshot path. "
            "When omitted, a runtime telemetry snapshot is generated first."
        ),
    )
    return parser.parse_args(argv)


def _resolve_telemetry_payload(
    *,
    telemetry_path: Path | None,
) -> tuple[dict[str, Any], str]:
    if telemetry_path is not None:
        verify_snapshot(snapshot_path=telemetry_path, max_artifact_age_hours=24.0)
        return load_json(telemetry_path, field="telemetry_path"), str(telemetry_path.resolve())

    with tempfile.TemporaryDirectory(prefix="finance-assumptions-") as tmp_dir:
        generated = Path(tmp_dir) / "finance_telemetry_snapshot.json"
        exit_code = generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(generated),
            ]
        )
        if exit_code != 0:
            raise RuntimeError(
                "failed to generate runtime telemetry snapshot for assumptions"
            )
        verify_snapshot(snapshot_path=generated, max_artifact_age_hours=24.0)
        return load_json(generated, field="generated_telemetry_path"), "runtime://generated"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    telemetry_path = Path(str(args.telemetry_path)) if args.telemetry_path else None
    telemetry, source_telemetry = _resolve_telemetry_payload(telemetry_path=telemetry_path)

    assumptions = derive_assumptions_inputs(telemetry=telemetry)
    assumptions["source_telemetry_path"] = source_telemetry

    output_path = Path(str(args.output))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(assumptions, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Generated finance committee packet assumptions: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
