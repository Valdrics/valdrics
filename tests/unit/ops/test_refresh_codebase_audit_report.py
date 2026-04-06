from __future__ import annotations

import json
from pathlib import Path

from scripts.refresh_codebase_audit_report import refresh_audit_report


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _base_payload() -> dict[str, object]:
    return {
        "artifact_type": "codebase_audit_validation",
        "snapshot_date": "2026-04-01",
        "environment": "staging",
        "repository": "CloudSentinel-AI",
        "product_name": "Valdrics",
        "source_report_label": "User-provided Codebase Audit Summary",
        "validation_status": "partially_accurate",
        "validation_scope": ["Repository source inspection"],
        "validation_commands": ["uv run pytest --collect-only -q"],
        "summary": {
            "overall": "Summary",
            "high_confidence_findings": [
                "The dashboard uses old stack text.",
            ],
            "important_corrections": [
                "Backend tests collected currently total 1, not 5358.",
                "Zombie detection plugin classes total 1 across providers, not 11.",
            ],
        },
        "measured_facts": {
            "python_requires": ">=3.12,<3.13",
            "fastapi_requirement": "~=0.128.0",
            "frontend_svelte_version": "^5.51.5",
            "frontend_sveltekit_version": "^2.52.2",
            "backend_tests_collected": 1,
            "test_and_spec_files": 2,
            "zombie_plugin_classes": 1,
            "direct_audit_logger_call_sites": 3,
        },
        "confirmed_claims": [
            {
                "claim": "Frontend stack includes SvelteKit, Svelte 5, TypeScript, Tailwind CSS v4, Vitest, and Playwright.",
                "evidence": [{"path": "dashboard/package.json", "line": 1}],
            }
        ],
        "partial_or_overstated_claims": [],
        "incorrect_claims": [
            {
                "claim": "Testing has 5,358 tests",
                "correction": "wrong",
                "evidence": [{"path": "pytest --collect-only", "line": 1}],
            },
            {
                "claim": "FinOps capabilities include 11 zombie detection plugins",
                "correction": "wrong",
                "evidence": [{"path": "dashboard/svelte.config.js", "line": 1}],
            },
        ],
        "validation_runs": [],
        "deployment_notes": {
            "env_report_left_untouched": True,
            "reason": ".runtime/staging.report.json remains untouched.",
        },
        "limitations": ["None"],
    }


def test_refresh_audit_report_updates_live_fact_dependent_fields(tmp_path: Path) -> None:
    report_path = tmp_path / ".runtime/staging.audit.report.json"
    payload = _base_payload()
    _write_json(report_path, payload)

    refreshed = refresh_audit_report(
        root=tmp_path,
        report_path=report_path,
        snapshot_date="2026-04-06",
        live_facts={
            "python_requires": ">=3.12,<3.13",
            "fastapi_requirement": "~=0.128.0",
            "frontend_svelte_version": "^5.51.5",
            "frontend_sveltekit_version": "^2.52.2",
            "backend_tests_collected": 6367,
            "test_and_spec_files": 964,
            "zombie_plugin_classes": 56,
            "direct_audit_logger_call_sites": 33,
        },
        frontend_stack_phrase="SvelteKit, Svelte 5, TypeScript, Tailwind CSS v4, Vitest, and Playwright",
    )

    written = json.loads(report_path.read_text(encoding="utf-8"))

    assert refreshed["snapshot_date"] == "2026-04-06"
    assert written["measured_facts"]["backend_tests_collected"] == 6367
    assert (
        "Backend tests collected currently total 6367, not 5358."
        in written["summary"]["important_corrections"]
    )
    assert (
        "Zombie detection plugin classes total 56 across providers, not 11."
        in written["summary"]["important_corrections"]
    )
    assert (
        "The dashboard uses SvelteKit, Svelte 5, TypeScript, Tailwind CSS v4, Vitest, and Playwright."
        in written["summary"]["high_confidence_findings"]
    )
    assert written["confirmed_claims"][0]["claim"] == (
        "Frontend stack includes SvelteKit, Svelte 5, TypeScript, Tailwind CSS v4, Vitest, and Playwright."
    )
    assert written["incorrect_claims"][0]["correction"] == (
        "A fresh backend collection run reported 6367 tests collected."
    )
    assert written["incorrect_claims"][0]["evidence"][0]["line"] == 6367
    assert written["incorrect_claims"][1]["correction"] == (
        "A structural scan found 56 ZombiePlugin subclasses across provider adapters."
    )
