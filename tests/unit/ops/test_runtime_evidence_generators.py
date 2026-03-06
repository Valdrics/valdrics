from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_finance_telemetry_snapshot import (
    main as generate_finance_telemetry_snapshot_main,
)
from scripts.generate_finance_committee_packet import (
    main as generate_finance_committee_packet_main,
)
from scripts.generate_finance_committee_packet_assumptions import (
    main as generate_finance_committee_packet_assumptions_main,
)
from scripts.generate_key_rotation_drill_evidence import (
    main as generate_key_rotation_drill_evidence_main,
)
from scripts.generate_pkg_fin_policy_decisions import (
    main as generate_pkg_fin_policy_decisions_main,
)
from scripts.generate_pricing_benchmark_register import (
    main as generate_pricing_benchmark_register_main,
)
from scripts.generate_valdrics_disposition_register import (
    main as generate_valdrics_disposition_register_main,
)
from scripts.pkg_fin_policy_decisions_constants import REQUIRED_DECISION_BACKLOG_IDS
from scripts.verify_finance_telemetry_snapshot import verify_snapshot
from scripts.verify_key_rotation_drill_evidence import verify_key_rotation_drill_evidence
from scripts.verify_pkg_fin_policy_decisions import verify_evidence
from scripts.verify_pricing_benchmark_register import verify_register
from scripts.verify_valdrics_disposition_freshness import verify_disposition_register


def test_generate_finance_telemetry_snapshot_emits_verifiable_artifact(
    tmp_path: Path,
) -> None:
    output = tmp_path / "finance_telemetry_snapshot.json"
    assert generate_finance_telemetry_snapshot_main(["--output", str(output)]) == 0
    assert verify_snapshot(snapshot_path=output, max_artifact_age_hours=4.0) == 0


def test_generate_pricing_benchmark_register_emits_verifiable_artifact(
    tmp_path: Path,
) -> None:
    output = tmp_path / "pricing_benchmark_register.json"
    assert (
        generate_pricing_benchmark_register_main(
            [
                "--output",
                str(output),
                "--max-source-age-days",
                "120",
            ]
        )
        == 0
    )
    assert verify_register(register_path=output, max_source_age_days=120.0) == 0


def test_generate_pkg_fin_policy_decisions_emits_verifiable_artifact(
    tmp_path: Path,
) -> None:
    telemetry_output = tmp_path / "finance_telemetry_snapshot.json"
    pkg_fin_output = tmp_path / "pkg_fin_policy_decisions.json"

    assert (
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(telemetry_output),
            ]
        )
        == 0
    )
    assert (
        generate_pkg_fin_policy_decisions_main(
            [
                "--output",
                str(pkg_fin_output),
                "--telemetry-snapshot-path",
                str(telemetry_output),
            ]
        )
        == 0
    )

    assert verify_evidence(evidence_path=pkg_fin_output, max_artifact_age_hours=4.0) == 0
    payload = json.loads(pkg_fin_output.read_text(encoding="utf-8"))
    decision_ids = {
        str(item.get("id")).strip().upper()
        for item in payload["decision_backlog"]["decision_items"]
    }
    assert decision_ids == set(REQUIRED_DECISION_BACKLOG_IDS)


def test_generate_finance_committee_assumptions_integrates_with_packet_generation(
    tmp_path: Path,
) -> None:
    telemetry_output = tmp_path / "finance_telemetry_snapshot.json"
    assumptions_output = tmp_path / "finance_committee_packet_assumptions.json"
    output_dir = tmp_path / "committee-output"
    assert generate_finance_telemetry_snapshot_main(["--output", str(telemetry_output)]) == 0
    assert (
        generate_finance_committee_packet_assumptions_main(
            [
                "--output",
                str(assumptions_output),
                "--telemetry-path",
                str(telemetry_output),
            ]
        )
        == 0
    )
    assert (
        generate_finance_committee_packet_main(
            [
                "--telemetry-path",
                str(telemetry_output),
                "--assumptions-path",
                str(assumptions_output),
                "--output-dir",
                str(output_dir),
            ]
        )
        == 0
    )
    assert list(output_dir.glob("finance_guardrails_*.json"))


def test_generate_finance_committee_assumptions_self_generates_telemetry(
    tmp_path: Path,
) -> None:
    assumptions_output = tmp_path / "finance_committee_packet_assumptions.json"
    assert (
        generate_finance_committee_packet_assumptions_main(
            [
                "--output",
                str(assumptions_output),
            ]
        )
        == 0
    )
    payload = json.loads(assumptions_output.read_text(encoding="utf-8"))
    assert payload["source_telemetry_path"] == "runtime://generated"


def test_generate_key_rotation_drill_evidence_emits_verifiable_artifact(
    tmp_path: Path,
) -> None:
    output = tmp_path / "key_rotation_drill.md"
    assert (
        generate_key_rotation_drill_evidence_main(
            [
                "--output",
                str(output),
                "--max-drill-age-days",
                "120",
            ]
        )
        == 0
    )
    assert verify_key_rotation_drill_evidence(drill_path=output, max_drill_age_days=120.0) == 0


def test_generate_valdrics_disposition_register_emits_verifiable_artifact(
    tmp_path: Path,
) -> None:
    output = tmp_path / "valdrics_disposition_register.json"
    assert (
        generate_valdrics_disposition_register_main(
            [
                "--output",
                str(output),
                "--max-artifact-age-days",
                "45",
                "--max-review-window-days",
                "120",
            ]
        )
        == 0
    )
    assert (
        verify_disposition_register(
            register_path=output,
            max_artifact_age_days=45.0,
            max_review_window_days=120.0,
        )
        == 0
    )
