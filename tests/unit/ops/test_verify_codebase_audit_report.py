from __future__ import annotations

import json
from pathlib import Path

import scripts.verify_codebase_audit_report as codebase_audit_report
from scripts.verify_codebase_audit_report import (
    DEFAULT_REPORT,
    main,
    verify_audit_report,
)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _seed_dashboard_package_json(tmp_path: Path, *, include_chart_js: bool = False) -> None:
    dependencies: dict[str, str] = {
        "@sveltejs/kit": "^2.52.2",
        "svelte": "^5.51.5",
        "tailwindcss": "^4.1.18",
    }
    if include_chart_js:
        dependencies["chart.js"] = "^4.5.1"
    package_payload = {
        "name": "dashboard",
        "private": True,
        "devDependencies": {
            "playwright": "^1.58.0",
            "typescript": "^5.9.3",
            "vitest": "^4.0.15",
        },
        "dependencies": dependencies,
    }
    _write_json(tmp_path / "dashboard/package.json", package_payload)


def _valid_report_payload() -> dict[str, object]:
    return {
        "artifact_type": "codebase_audit_validation",
        "snapshot_date": "2026-04-02",
        "environment": "staging",
        "repository": "CloudSentinel-AI",
        "product_name": "Valdrics",
        "source_report_label": "User-provided Codebase Audit Summary",
        "validation_status": "partially_accurate",
        "validation_scope": [
            "Repository source inspection",
            "Package metadata inspection",
        ],
        "validation_commands": [
            "sed -n '1,240p' pyproject.toml",
            "timeout 120 env DEBUG=false uv run pytest --collect-only -q",
        ],
        "summary": {
            "overall": "Most core claims are real, but some counts are stale.",
            "high_confidence_findings": [
                "The repo uses Python 3.12 and FastAPI.",
                "The dashboard uses SvelteKit, Svelte 5, TypeScript, Tailwind CSS v4, Vitest, and Playwright.",
            ],
            "important_corrections": [
                "Backend tests collected currently total 6303, not 5358.",
                "Zombie detection plugin classes total 56 across providers, not 11.",
            ],
        },
        "measured_facts": {
            "python_requires": ">=3.12,<3.13",
            "fastapi_requirement": "~=0.128.0",
            "frontend_svelte_version": "^5.51.5",
            "frontend_sveltekit_version": "^2.52.2",
            "backend_tests_collected": 6303,
            "test_and_spec_files": 853,
            "zombie_plugin_classes": 56,
            "direct_audit_logger_call_sites": 42,
        },
        "confirmed_claims": [
            {
                "claim": "Backend stack includes FastAPI and Python 3.12.",
                "evidence": [
                    {
                        "path": "pyproject.toml",
                        "line": 8,
                    }
                ],
            },
            {
                "claim": "Frontend stack includes SvelteKit, Svelte 5, TypeScript, Tailwind CSS v4, Vitest, and Playwright.",
                "evidence": [
                    {
                        "path": "dashboard/package.json",
                        "line": 1,
                    }
                ],
            }
        ],
        "partial_or_overstated_claims": [
            {
                "claim": "Docker Compose for development, Koyeb for production",
                "status": "partial",
                "correction": "The dashboard is also configured for Cloudflare Pages/Workers.",
                "evidence": [
                    {
                        "path": "dashboard/svelte.config.js",
                        "line": 1,
                    }
                ],
            },
            {
                "claim": "Production-ready, enterprise-grade platform",
                "status": "overstated",
                "correction": "That is a qualitative judgment.",
            },
        ],
        "incorrect_claims": [
            {
                "claim": "Testing has 5,358 tests",
                "correction": "A fresh backend collection run reported 6303 tests collected.",
                "evidence": [
                    {
                        "path": "pytest --collect-only",
                        "line": 6303,
                    }
                ],
            },
            {
                "claim": "FinOps capabilities include 11 zombie detection plugins",
                "correction": "A structural scan found 56 ZombiePlugin subclasses across provider adapters.",
                "evidence": [
                    {
                        "path": "dashboard/svelte.config.js",
                        "line": 1,
                    }
                ],
            }
        ],
        "validation_runs": [
            {
                "report_label": "User-provided backend/middleware/dashboard security audit findings",
                "snapshot_date": "2026-04-02",
                "validation_status": "partially_accurate",
                "overall": (
                    "The report mixed correct middleware observations with two real "
                    "hardening findings that were subsequently fixed."
                ),
                "confirmed_findings": [
                    {
                        "finding": "API documentation routes are gated by configuration.",
                        "evidence": [
                            {
                                "path": "pyproject.toml",
                                "line": 1,
                            }
                        ],
                    }
                ],
                "watch_items": [
                    {
                        "finding": "The /api/v1/public CSRF exemption should stay limited to public flows.",
                        "evidence": [
                            {
                                "path": "dashboard/svelte.config.js",
                                "line": 1,
                            }
                        ],
                    }
                ],
                "incorrect_or_stale_findings": [
                    {
                        "finding": "Some file line references can go stale after refactors.",
                        "evidence": [
                            {
                                "path": "pyproject.toml",
                                "line": 1,
                            }
                        ],
                    }
                ],
                "remediations_applied": [
                    {
                        "finding": "Dashboard origin handling no longer trusts the raw Host header.",
                        "evidence": [
                            {
                                "path": "dashboard/svelte.config.js",
                                "line": 1,
                            }
                        ],
                    }
                ],
            }
        ],
        "deployment_notes": {
            "env_report_left_untouched": True,
            "reason": (
                ".runtime/staging.report.json remains the authoritative runtime "
                "environment blocker inventory used by deployment tooling."
            ),
        },
        "limitations": [
            "No live deployment health checks were executed for this validation pass.",
        ],
    }


def test_verify_audit_report_accepts_valid_report(tmp_path: Path) -> None:
    payload = _valid_report_payload()
    _write_json(tmp_path / ".runtime/staging.audit.report.json", payload)

    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "dashboard").mkdir(parents=True, exist_ok=True)
    (tmp_path / "dashboard/svelte.config.js").write_text(
        "export default {};\n", encoding="utf-8"
    )
    _seed_dashboard_package_json(tmp_path)

    errors = verify_audit_report(
        root=tmp_path,
        report_path=tmp_path / ".runtime/staging.audit.report.json",
    )
    assert errors == []


def test_verify_audit_report_flags_schema_drift(tmp_path: Path) -> None:
    payload = _valid_report_payload()
    payload["validation_status"] = "maybe"
    payload["measured_facts"] = {
        **payload["measured_facts"],  # type: ignore[index]
        "backend_tests_collected": 0,
    }
    payload["confirmed_claims"] = [
        {
            "claim": "Backend stack includes FastAPI and Python 3.12.",
            "evidence": [
                {
                    "path": "missing-file.py",
                    "line": 0,
                }
            ],
        }
    ]
    payload["deployment_notes"] = {
        "env_report_left_untouched": False,
        "reason": "left untouched",
    }
    _write_json(tmp_path / ".runtime/staging.audit.report.json", payload)
    _seed_dashboard_package_json(tmp_path)

    errors = verify_audit_report(
        root=tmp_path,
        report_path=tmp_path / ".runtime/staging.audit.report.json",
    )

    assert (
        "validation_status must be one of: accurate, inaccurate, partially_accurate"
        in errors
    )
    assert "measured_facts.backend_tests_collected must be a positive integer" in errors
    assert "confirmed_claims[0].evidence[0].path must exist: missing-file.py" in errors
    assert (
        "confirmed_claims[0].evidence[0].line must be a positive integer when present"
        in errors
    )
    assert "deployment_notes.env_report_left_untouched must be true" in errors
    assert (
        "deployment_notes.reason must explain why the reserved managed runtime report remains untouched: .runtime/staging.report.json"
        in errors
    )


def test_verify_audit_report_flags_invalid_validation_runs(tmp_path: Path) -> None:
    payload = _valid_report_payload()
    payload["validation_runs"] = [
        {
            "report_label": "",
            "snapshot_date": "2026-13-40",
            "validation_status": "maybe",
            "overall": "",
            "confirmed_findings": [
                {
                    "finding": "",
                    "evidence": [],
                }
            ],
            "watch_items": "not-a-list",
            "incorrect_or_stale_findings": [],
            "remediations_applied": [],
        }
    ]
    _write_json(tmp_path / ".runtime/staging.audit.report.json", payload)

    (tmp_path / "pyproject.toml").write_text("[project]\n", encoding="utf-8")
    (tmp_path / "dashboard").mkdir(parents=True, exist_ok=True)
    (tmp_path / "dashboard/svelte.config.js").write_text(
        "export default {};\n", encoding="utf-8"
    )
    _seed_dashboard_package_json(tmp_path)

    errors = verify_audit_report(
        root=tmp_path,
        report_path=tmp_path / ".runtime/staging.audit.report.json",
    )

    assert "validation_runs[0].report_label must be a non-empty string" in errors
    assert (
        "validation_runs[0].snapshot_date must be an ISO-8601 date (YYYY-MM-DD)"
        in errors
    )
    assert (
        "validation_runs[0].validation_status must be one of: accurate, inaccurate, partially_accurate"
        in errors
    )
    assert "validation_runs[0].overall must be a non-empty string" in errors
    assert (
        "validation_runs[0].confirmed_findings[0].finding must be a non-empty string"
        in errors
    )
    assert (
        "validation_runs[0].confirmed_findings[0].evidence must be a non-empty list"
        in errors
    )
    assert "validation_runs[0].watch_items must be a list" in errors


def test_verify_audit_report_rejects_missing_root(tmp_path: Path) -> None:
    missing_root = tmp_path / "missing-root"
    assert verify_audit_report(
        root=missing_root, report_path=missing_root / "report.json"
    ) == [f"root not found: {missing_root}"]


def test_verify_audit_report_rejects_non_directory_root(tmp_path: Path) -> None:
    root_file = tmp_path / "root.txt"
    root_file.write_text("not-a-directory\n", encoding="utf-8")
    assert verify_audit_report(
        root=root_file, report_path=tmp_path / "report.json"
    ) == [f"root must be a directory: {root_file}"]


def test_main_accepts_root_override(monkeypatch) -> None:
    seen: list[tuple[Path, Path, bool]] = []

    def _fake_verify_audit_report(
        *,
        root: Path,
        report_path: Path,
        enforce_live_measured_facts: bool = False,
    ) -> list[str]:
        seen.append((root, report_path, enforce_live_measured_facts))
        return []

    monkeypatch.setattr(
        codebase_audit_report,
        "verify_audit_report",
        _fake_verify_audit_report,
    )

    assert main(["--root", "."]) == 0
    assert seen == [
        (
            codebase_audit_report.DEFAULT_ROOT,
            codebase_audit_report.DEFAULT_ROOT / DEFAULT_REPORT,
            True,
        )
    ]


def test_main_rejects_relative_root_escape(capsys) -> None:
    assert main(["--root", "../outside"]) == 2
    assert "root must stay within repo root when relative" in capsys.readouterr().out


def test_main_rejects_relative_report_escape(capsys) -> None:
    assert main(["--report", "../outside.json"]) == 2
    assert "report must resolve inside the repository root" in capsys.readouterr().out


def test_repo_staging_audit_report_passes() -> None:
    errors = verify_audit_report(
        root=codebase_audit_report.DEFAULT_ROOT,
        report_path=codebase_audit_report.DEFAULT_ROOT / DEFAULT_REPORT,
    )
    assert errors == []


def test_verify_audit_report_flags_live_measured_fact_drift(
    tmp_path: Path, monkeypatch
) -> None:
    payload = _valid_report_payload()
    _write_json(tmp_path / ".runtime/staging.audit.report.json", payload)
    _seed_dashboard_package_json(tmp_path)

    monkeypatch.setattr(
        codebase_audit_report,
        "collect_live_measured_facts",
        lambda *, root: {
            "python_requires": ">=3.12,<3.13",
            "fastapi_requirement": "~=0.128.0",
            "frontend_svelte_version": "^5.51.5",
            "frontend_sveltekit_version": "^2.52.2",
            "backend_tests_collected": 7777,
            "test_and_spec_files": 854,
            "zombie_plugin_classes": 57,
            "direct_audit_logger_call_sites": 42,
        },
    )

    errors = verify_audit_report(
        root=tmp_path,
        report_path=tmp_path / ".runtime/staging.audit.report.json",
        enforce_live_measured_facts=True,
    )

    assert (
        "measured_facts.backend_tests_collected must match live repo fact: "
        "recorded=6303 live=7777"
    ) in errors
    assert (
        "measured_facts.test_and_spec_files must match live repo fact: "
        "recorded=853 live=854"
    ) in errors
    assert (
        "measured_facts.zombie_plugin_classes must match live repo fact: "
        "recorded=56 live=57"
    ) in errors
    assert (
        "measured_facts.python_requires must match live repo fact: "
        "recorded='>=3.12,<3.13' live='>=3.12,<3.13'"
    ) not in errors


def test_verify_audit_report_flags_claim_consistency_drift(tmp_path: Path) -> None:
    payload = _valid_report_payload()
    payload["summary"] = {
        **payload["summary"],  # type: ignore[index]
        "high_confidence_findings": ["wrong"],
        "important_corrections": ["wrong"],
    }
    payload["confirmed_claims"] = [
        {
            "claim": "Backend stack includes FastAPI and Python 3.12.",
            "evidence": [{"path": "pyproject.toml", "line": 1}],
        }
    ]
    payload["incorrect_claims"] = [
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
    ]
    _write_json(tmp_path / ".runtime/staging.audit.report.json", payload)
    _seed_dashboard_package_json(tmp_path)

    errors = verify_audit_report(
        root=tmp_path,
        report_path=tmp_path / ".runtime/staging.audit.report.json",
    )

    assert (
        "summary.important_corrections must include the live backend test count correction"
        in errors
    )
    assert (
        "summary.important_corrections must include the live zombie plugin correction"
        in errors
    )
    assert (
        "incorrect_claims testing correction must include the live backend test count"
        in errors
    )
    assert (
        "incorrect_claims testing evidence line must match the live backend test count"
        in errors
    )
    assert (
        "incorrect_claims zombie plugin correction must include the live plugin count"
        in errors
    )
    assert (
        "summary.high_confidence_findings must include the live frontend stack summary"
        in errors
    )
    assert "confirmed_claims must include the live frontend stack claim" in errors
