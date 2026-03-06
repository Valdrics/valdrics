#!/usr/bin/env python3
"""Generate finance guardrails + committee packet artifacts from telemetry snapshots."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from scripts.finance_committee_packet_common import load_json, sanitize_label, write_csv
from scripts.finance_committee_packet_engine import build_finance_outputs
from scripts.verify_finance_guardrails_evidence import verify_evidence
from scripts.verify_finance_telemetry_snapshot import verify_snapshot


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


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    telemetry_path = Path(str(args.telemetry_path))
    assumptions_path = Path(str(args.assumptions_path))
    output_dir = Path(str(args.output_dir))
    output_dir.mkdir(parents=True, exist_ok=True)

    verify_snapshot(
        snapshot_path=telemetry_path,
        max_artifact_age_hours=(
            float(args.max_telemetry_age_hours)
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

    guardrails_path.write_text(
        json.dumps(finance_guardrails, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    committee_path.write_text(
        json.dumps(committee_packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    write_csv(tiers_csv_path, tier_rows)
    write_csv(scenarios_csv_path, scenario_rows)

    verify_evidence(evidence_path=guardrails_path, allow_failed_gates=True)

    _send_alert_if_needed(
        webhook_url=(str(args.alert_webhook_url).strip() if args.alert_webhook_url else None),
        webhook_timeout_seconds=float(args.alert_webhook_timeout_seconds),
        webhook_fail_on_error=bool(args.alert_webhook_fail_on_error),
        packet_summary=committee_packet["summary"],
        gate_results=committee_packet["gate_results"],
    )

    print(f"Generated finance guardrails: {guardrails_path}")
    print(f"Generated finance committee packet: {committee_path}")
    print(f"Generated tier economics CSV: {tiers_csv_path}")
    print(f"Generated scenarios CSV: {scenarios_csv_path}")

    if bool(args.require_all_gates_pass) and not all(committee_packet["gate_results"].values()):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
