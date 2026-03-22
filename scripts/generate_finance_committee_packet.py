#!/usr/bin/env python3
"""Generate finance guardrails + committee packet artifacts from telemetry snapshots."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from scripts.env_generation_common import (
    ensure_directory_path as _ensure_directory_path_shared,
    protected_output_paths_from_root as _protected_output_paths_from_root,
    repo_root_for as _repo_root_for,
    resolve_repo_relative_path_from_root as _resolve_repo_relative_path_from_root,
)
from scripts.finance_committee_packet_common import load_json, sanitize_label, write_csv
from scripts.finance_committee_packet_engine import build_finance_outputs
from scripts.verify_finance_guardrails_evidence import verify_evidence
from scripts.verify_finance_telemetry_snapshot import verify_snapshot


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _protected_output_paths() -> set[Path]:
    return _protected_output_paths_from_root(
        _repo_root(),
        __file__,
        "docs/ops/evidence/finance_guardrails_TEMPLATE.json",
        "docs/ops/evidence/finance_guardrails_2026-02-27.json",
    )


def _resolve_repo_relative_path(value: str, *, field_name: str) -> Path:
    return _resolve_repo_relative_path_from_root(
        _repo_root(),
        value,
        field_name=field_name,
    )


def _ensure_output_dir_parent(output_dir: Path) -> None:
    _ensure_directory_path_shared(output_dir, field_name="output_dir")


def _send_alert_if_needed(
    *,
    webhook_url: str | None,
    webhook_timeout_seconds: float,
    webhook_fail_on_error: bool,
    packet_summary: dict[str, Any],
    gate_results: dict[str, bool],
) -> None:
    if not webhook_url:
        return
    if all(gate_results.values()):
        return

    payload = {
        "event": "finance_gate_failure",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "summary": packet_summary,
        "gate_results": gate_results,
    }
    try:
        response = httpx.post(
            webhook_url,
            json=payload,
            timeout=webhook_timeout_seconds,
        )
        if response.status_code >= 400:
            raise RuntimeError(
                f"alert webhook rejected payload with status={response.status_code}"
            )
    except (httpx.HTTPError, OSError, RuntimeError, TypeError, ValueError) as exc:
        if webhook_fail_on_error:
            raise RuntimeError(f"failed to send finance alert webhook: {exc}") from exc


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate finance guardrail + committee packet artifacts from telemetry.",
    )
    parser.add_argument("--telemetry-path", required=True, help="Telemetry snapshot JSON path.")
    parser.add_argument("--assumptions-path", required=True, help="Packet assumptions JSON path.")
    parser.add_argument("--output-dir", required=True, help="Output directory for generated artifacts.")
    parser.add_argument(
        "--max-telemetry-age-hours",
        type=float,
        default=None,
        help="Optional max allowed age for telemetry artifact.",
    )
    parser.add_argument(
        "--require-all-gates-pass",
        action="store_true",
        help="Return non-zero when any FIN gate fails.",
    )
    parser.add_argument(
        "--alert-webhook-url",
        default=None,
        help="Optional webhook URL for finance gate failure alerts.",
    )
    parser.add_argument(
        "--alert-webhook-timeout-seconds",
        type=float,
        default=10.0,
        help="Webhook timeout in seconds.",
    )
    parser.add_argument(
        "--alert-webhook-fail-on-error",
        action="store_true",
        help="Fail generation if alert webhook call fails.",
    )
    return parser.parse_args(argv)


def _parse_positive_float_arg(value: float, *, field: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    if parsed <= 0:
        raise ValueError(f"{field} must be > 0")
    return parsed


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    telemetry_path = _resolve_repo_relative_path(
        str(args.telemetry_path),
        field_name="telemetry_path",
    )
    assumptions_path = _resolve_repo_relative_path(
        str(args.assumptions_path),
        field_name="assumptions_path",
    )
    output_dir = _resolve_repo_relative_path(
        str(args.output_dir),
        field_name="output_dir",
    )
    telemetry_resolved = telemetry_path.resolve()
    assumptions_resolved = assumptions_path.resolve()
    if telemetry_resolved == assumptions_resolved:
        raise ValueError("telemetry_path and assumptions_path must be different files")
    _ensure_output_dir_parent(output_dir)

    verify_snapshot(
        snapshot_path=telemetry_path,
        max_artifact_age_hours=(
            _parse_positive_float_arg(
                float(args.max_telemetry_age_hours),
                field="max_telemetry_age_hours",
            )
            if args.max_telemetry_age_hours is not None
            else None
        ),
    )
    telemetry = load_json(telemetry_path, field="telemetry_path")
    assumptions = load_json(assumptions_path, field="assumptions_path")

    finance_guardrails, committee_packet, tier_rows, scenario_rows = build_finance_outputs(
        telemetry=telemetry,
        assumptions=assumptions,
    )
    label = sanitize_label(str(finance_guardrails["window"]["label"]))

    guardrails_path = output_dir / f"finance_guardrails_{label}.json"
    committee_path = output_dir / f"finance_committee_packet_{label}.json"
    tiers_csv_path = output_dir / f"finance_committee_tier_unit_economics_{label}.csv"
    scenarios_csv_path = output_dir / f"finance_committee_scenarios_{label}.csv"
    input_paths = {
        telemetry_resolved: "telemetry_path",
        assumptions_resolved: "assumptions_path",
    }
    for output_path in (
        guardrails_path,
        committee_path,
        tiers_csv_path,
        scenarios_csv_path,
    ):
        output_resolved = output_path.resolve()
        if output_resolved in input_paths:
            raise ValueError(
                "output_dir would overwrite "
                f"{input_paths[output_resolved]}: {output_path.as_posix()}"
            )
        if output_resolved in _protected_output_paths():
            raise ValueError(
                "output_dir would overwrite checked-in finance evidence: "
                f"{output_path.as_posix()}"
            )

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    guardrails_text = json.dumps(finance_guardrails, indent=2, sort_keys=True)
    committee_text = json.dumps(committee_packet, indent=2, sort_keys=True)
    staging_dir = Path(
        tempfile.mkdtemp(prefix=f".{output_dir.name}-", dir=output_dir.parent)
    )
    temp_guardrails_path = staging_dir / guardrails_path.name
    temp_committee_path = staging_dir / committee_path.name
    temp_tiers_csv_path = staging_dir / tiers_csv_path.name
    temp_scenarios_csv_path = staging_dir / scenarios_csv_path.name
    temp_guardrails_path.write_text(guardrails_text, encoding="utf-8")
    temp_committee_path.write_text(
        committee_text,
        encoding="utf-8",
    )
    write_csv(temp_tiers_csv_path, tier_rows)
    write_csv(temp_scenarios_csv_path, scenario_rows)
    verify_evidence(evidence_path=temp_guardrails_path, allow_failed_gates=True)
    _send_alert_if_needed(
        webhook_url=(str(args.alert_webhook_url).strip() if args.alert_webhook_url else None),
        webhook_timeout_seconds=_parse_positive_float_arg(
            float(args.alert_webhook_timeout_seconds),
            field="alert_webhook_timeout_seconds",
        ),
        webhook_fail_on_error=bool(args.alert_webhook_fail_on_error),
        packet_summary=committee_packet["summary"],
        gate_results=committee_packet["gate_results"],
    )
    promoted_paths: list[Path] = []
    output_dir.mkdir(parents=True, exist_ok=True)
    promotion_completed = False
    try:
        for staged_path, final_path in (
            (temp_guardrails_path, guardrails_path),
            (temp_committee_path, committee_path),
            (temp_tiers_csv_path, tiers_csv_path),
            (temp_scenarios_csv_path, scenarios_csv_path),
        ):
            staged_path.replace(final_path)
            promoted_paths.append(final_path)
        promotion_completed = True
    finally:
        if not promotion_completed:
            for final_path in promoted_paths:
                final_path.unlink(missing_ok=True)
        shutil.rmtree(staging_dir, ignore_errors=True)

    print(f"Generated finance guardrails: {guardrails_path}")
    print(f"Generated finance committee packet: {committee_path}")
    print(f"Generated tier economics CSV: {tiers_csv_path}")
    print(f"Generated scenarios CSV: {scenarios_csv_path}")

    if bool(args.require_all_gates_pass) and not all(committee_packet["gate_results"].values()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
