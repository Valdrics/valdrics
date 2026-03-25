from __future__ import annotations

import asyncio
import json
import math
import os
from pathlib import Path
from unittest.mock import patch

import pytest

import scripts.generate_valdrics_disposition_register as valdrics_generator
import scripts.generate_pricing_benchmark_register as pricing_generator
from scripts.generate_finance_telemetry_snapshot import (
    _generate_snapshot as generate_finance_telemetry_snapshot,
    _parse_date as parse_finance_telemetry_date,
    main as generate_finance_telemetry_snapshot_main,
)
from scripts.generate_finance_committee_packet import (
    main as generate_finance_committee_packet_main,
)
from scripts.generate_finance_committee_packet_assumptions import (
    main as generate_finance_committee_packet_assumptions_main,
)
from scripts.generate_key_rotation_drill_evidence import (
    _all_drill_checks,
    main as generate_key_rotation_drill_evidence_main,
)
from scripts.generate_pkg_fin_policy_decisions import (
    _build_payload as build_pkg_fin_policy_payload,
    main as generate_pkg_fin_policy_decisions_main,
)
from scripts.generate_pricing_benchmark_register import (
    main as generate_pricing_benchmark_register_main,
)
from scripts.generate_valdrics_disposition_register import (
    main as generate_valdrics_disposition_register_main,
)
from scripts.pkg_fin_policy_decisions_constants import REQUIRED_DECISION_BACKLOG_IDS
from scripts.pkg_fin_policy_decisions_constants import REQUIRED_TIERS
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


def test_generate_finance_telemetry_snapshot_does_not_leave_output_when_verification_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "finance_telemetry_snapshot.json"
    verify_calls: list[Path] = []

    async def _fake_generate_snapshot(**_: object) -> dict[str, object]:
        return {
            "captured_at": "2026-03-01T00:00:00+00:00",
            "window": {
                "start": "2026-02-01T00:00:00+00:00",
                "end": "2026-02-28T23:59:59+00:00",
            },
            "gate_results": {
                "telemetry_gate_required_tiers_present": True,
                "telemetry_gate_window_valid": True,
                "telemetry_gate_percentiles_valid": True,
                "telemetry_gate_artifact_fresh": True,
                "telemetry_gate_free_tier_guardrails_bounded": True,
                "telemetry_gate_free_tier_margin_guarded": True,
            },
        }

    def _fake_verify_snapshot(*, snapshot_path: Path, max_artifact_age_hours: float) -> int:
        verify_calls.append(snapshot_path)
        raise ValueError("snapshot verification failed")

    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._generate_snapshot",
        _fake_generate_snapshot,
    )
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot.verify_snapshot",
        _fake_verify_snapshot,
    )

    with pytest.raises(ValueError, match="snapshot verification failed"):
        generate_finance_telemetry_snapshot_main(["--output", str(output)])

    assert not output.exists()
    assert verify_calls
    assert all(path != output for path in verify_calls)


def test_generate_finance_telemetry_snapshot_uses_unique_temp_database_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_database_paths: list[Path] = []

    async def _fake_generate_snapshot(**kwargs: object) -> dict[str, object]:
        database_path = kwargs["database_path"]
        assert isinstance(database_path, Path)
        seen_database_paths.append(database_path)
        database_path.write_text("seed", encoding="utf-8")
        return {
            "captured_at": "2026-03-01T00:00:00+00:00",
            "window": {
                "start": "2026-02-01T00:00:00+00:00",
                "end": "2026-02-28T23:59:59+00:00",
                "label": "2026-02",
            },
            "pricing_reference": {
                tier: {
                    "monthly_price_usd": 0.0,
                    "annual_price_usd": 0.0,
                    "annual_monthly_factor": 0.0,
                }
                for tier in ("free", "starter", "growth", "pro", "enterprise")
            },
            "tier_subscription_snapshot": [
                {
                    "tier": tier,
                    "total_tenants": 1,
                    "active_subscriptions": 0,
                    "dunning_events": 0,
                }
                for tier in ("free", "starter", "growth", "pro", "enterprise")
            ],
            "tier_revenue_inputs": [
                {
                    "tier": tier,
                    "monthly_price_usd": 0.0,
                    "active_subscriptions": 0,
                    "gross_mrr_usd": 0.0,
                }
                for tier in ("free", "starter", "growth", "pro", "enterprise")
            ],
            "tier_llm_usage": [
                {
                    "tier": tier,
                    "total_cost_usd": 0.0,
                    "tenant_monthly_cost_percentiles_usd": {"p50": 0.0, "p95": 0.0, "p99": 0.0},
                }
                for tier in ("free", "starter", "growth", "pro", "enterprise")
            ],
            "free_tier_compute_guardrails": {
                "tier": "free",
                "reference_tier": "starter",
                "limits": [
                    {
                        "limit_name": "llm_analyses_per_day",
                        "free_limit": 0,
                        "starter_limit": 0,
                        "free_le_starter": True,
                    }
                ],
                "bounded_against_starter": True,
            },
            "free_tier_margin_watch": {
                "free_total_tenants": 1,
                "free_active_subscriptions": 0,
                "free_total_llm_cost_usd": 0.0,
                "free_p95_tenant_monthly_cost_usd": 0.0,
                "starter_gross_mrr_usd": 0.0,
                "free_llm_cost_pct_of_starter_gross_mrr": 0.0,
                "max_allowed_pct_of_starter_gross_mrr": 100.0,
            },
            "gate_results": {
                "telemetry_gate_required_tiers_present": True,
                "telemetry_gate_window_valid": True,
                "telemetry_gate_percentiles_valid": True,
                "telemetry_gate_artifact_fresh": True,
                "telemetry_gate_free_tier_guardrails_bounded": True,
                "telemetry_gate_free_tier_margin_guarded": True,
            },
        }

    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._generate_snapshot",
        _fake_generate_snapshot,
    )
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot.verify_snapshot",
        lambda **_: 0,
    )

    first_output = tmp_path / "finance_telemetry_snapshot_first.json"
    second_output = tmp_path / "finance_telemetry_snapshot_second.json"

    assert generate_finance_telemetry_snapshot_main(["--output", str(first_output)]) == 0
    assert generate_finance_telemetry_snapshot_main(["--output", str(second_output)]) == 0

    assert len(seen_database_paths) == 2
    assert seen_database_paths[0] != seen_database_paths[1]
    assert all(not path.exists() for path in seen_database_paths)


def test_generate_finance_telemetry_snapshot_rejects_database_output_collision(
    tmp_path: Path,
) -> None:
    output = tmp_path / "finance_telemetry_snapshot.json"

    with pytest.raises(ValueError, match="output and database_path must be different files"):
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(output),
                "--database-path",
                str(output),
            ]
        )


def test_generate_finance_telemetry_snapshot_restores_environment_after_generation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_environment = {
        "DATABASE_URL": "postgresql+asyncpg://prod.example/app",
        "DB_SSL_MODE": "require",
        "TESTING": "false",
        "SUPABASE_JWT_SECRET": "original-supabase-jwt-secret-value",
    }

    async def _fake_seed_runtime_data(**_: object) -> None:
        return None

    async def _fake_collect_snapshot(**_: object) -> dict[str, object]:
        return {"runtime": {}}

    dispose_calls = 0

    async def _fake_dispose_db_runtime() -> None:
        nonlocal dispose_calls
        dispose_calls += 1
        return None

    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._register_models",
        lambda: None,
    )
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._seed_runtime_data",
        _fake_seed_runtime_data,
    )
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot.collect_snapshot",
        _fake_collect_snapshot,
    )
    monkeypatch.setattr(
        "app.shared.core.config.reload_settings_from_environment",
        lambda: None,
    )
    monkeypatch.setattr(
        "app.shared.db.session.dispose_db_runtime",
        _fake_dispose_db_runtime,
    )

    with patch.dict(os.environ, original_environment, clear=True):
        payload = asyncio.run(
            generate_finance_telemetry_snapshot(
                database_path=Path("/tmp/finance-telemetry.sqlite"),
                start_date=parse_finance_telemetry_date("2026-02-01", field="start_date"),
                end_date=parse_finance_telemetry_date("2026-02-28", field="end_date"),
                label="2026-02",
            )
        )

        assert payload["runtime"] == {
            "collector": "scripts/generate_finance_telemetry_snapshot.py",
            "database_seed_mode": "orm_seed_live_query",
        }
        assert dict(os.environ) == original_environment
        assert "ENCRYPTION_KEY" not in os.environ
        assert "CSRF_SECRET_KEY" not in os.environ
        assert "KDF_SALT" not in os.environ
        assert dispose_calls == 2


def test_generate_finance_telemetry_snapshot_rejects_blank_label_before_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._generate_snapshot",
        lambda **_: (_ for _ in ()).throw(AssertionError("snapshot generation should not run")),
    )

    with pytest.raises(ValueError, match="label must be a non-empty string"):
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(tmp_path / "finance_telemetry_snapshot.json"),
                "--database-path",
                str(tmp_path / "finance.sqlite"),
                "--label",
                "   ",
            ]
        )


def test_generate_finance_telemetry_snapshot_does_not_create_database_parent_on_label_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "nested" / "telemetry.sqlite"
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._generate_snapshot",
        lambda **_: (_ for _ in ()).throw(AssertionError("snapshot generation should not run")),
    )

    with pytest.raises(ValueError, match="label must be a non-empty string"):
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(tmp_path / "finance_telemetry_snapshot.json"),
                "--database-path",
                str(database_path),
                "--label",
                "   ",
            ]
        )

    assert not database_path.parent.exists()


@pytest.mark.parametrize(
    "relative_output",
    [
        "scripts/verify_finance_telemetry_snapshot.py",
        "scripts/collect_finance_telemetry_snapshot.py",
        "docs/ops/evidence/finance_telemetry_snapshot_TEMPLATE.json",
        "docs/ops/evidence/finance_telemetry_snapshot_2026-02-28.json",
        "docs/ops/evidence/finance_committee_packet_assumptions_TEMPLATE.json",
        "docs/ops/evidence/finance_committee_packet_assumptions_2026-02-28.json",
        "docs/ops/evidence/finance_guardrails_TEMPLATE.json",
        "docs/ops/evidence/finance_guardrails_2026-02-27.json",
        "docs/ops/evidence/pkg_fin_policy_decisions_TEMPLATE.json",
        "docs/ops/evidence/pkg_fin_policy_decisions_2026-02-28.json",
        "docs/ops/evidence/README.md",
    ],
)
def test_generate_finance_telemetry_snapshot_rejects_protected_output_collisions(
    monkeypatch: pytest.MonkeyPatch,
    relative_output: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    output = repo_root / relative_output
    called = {"generate": False}

    async def _unexpected_generate_snapshot(**_: object) -> dict[str, object]:
        called["generate"] = True
        raise AssertionError("snapshot generation should not run for protected output paths")

    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._generate_snapshot",
        _unexpected_generate_snapshot,
    )

    with pytest.raises(ValueError, match="output must not overwrite finance telemetry"):
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(output),
                "--database-path",
                str(repo_root / ".runtime" / "tmp" / "finance.sqlite"),
            ]
        )

    assert called["generate"] is False


def test_generate_finance_telemetry_snapshot_rejects_output_parent_file(
    tmp_path: Path,
) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="output parent must be a directory path"):
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(blocked_parent / "finance_telemetry_snapshot.json"),
                "--database-path",
                str(tmp_path / "finance.sqlite"),
            ]
        )


def test_generate_finance_telemetry_snapshot_rejects_directory_output_path(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "telemetry-output"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="output must be a file path"):
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(output_dir),
                "--database-path",
                str(tmp_path / "finance.sqlite"),
            ]
        )


def test_generate_finance_telemetry_snapshot_rejects_relative_protected_output_from_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._repo_root",
        lambda: repo_root,
    )

    with pytest.raises(ValueError, match="output must not overwrite finance telemetry"):
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                "docs/ops/evidence/finance_telemetry_snapshot_TEMPLATE.json",
                "--database-path",
                "runtime/finance.sqlite",
            ]
        )


def test_generate_finance_telemetry_snapshot_resolves_relative_paths_from_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    output = repo_root / "artifacts" / "finance_telemetry_snapshot.json"
    database_path = repo_root / "runtime" / "finance.sqlite"
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._repo_root",
        lambda: repo_root,
    )

    async def _fake_generate_snapshot(**kwargs: object) -> dict[str, object]:
        assert kwargs["database_path"] == database_path
        return {
            "captured_at": "2026-03-01T00:00:00+00:00",
            "window": {"start": "2026-02-01T00:00:00+00:00", "end": "2026-02-28T23:59:59+00:00"},
            "gate_results": {
                "telemetry_gate_required_tiers_present": True,
                "telemetry_gate_window_valid": True,
                "telemetry_gate_percentiles_valid": True,
                "telemetry_gate_artifact_fresh": True,
                "telemetry_gate_free_tier_guardrails_bounded": True,
                "telemetry_gate_free_tier_margin_guarded": True,
            },
        }

    verify_calls: list[dict[str, object]] = []

    def _fake_verify_snapshot(**kwargs: object) -> int:
        verify_calls.append(kwargs)
        return 0

    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._generate_snapshot",
        _fake_generate_snapshot,
    )
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot.verify_snapshot",
        _fake_verify_snapshot,
    )

    assert (
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                "artifacts/finance_telemetry_snapshot.json",
                "--database-path",
                "runtime/finance.sqlite",
            ]
        )
        == 0
    )
    assert output.exists()
    assert len(verify_calls) == 1
    assert verify_calls[0]["max_artifact_age_hours"] == 4.0
    assert verify_calls[0]["snapshot_path"].parent == output.parent
    assert verify_calls[0]["snapshot_path"] != output


def test_generate_finance_telemetry_snapshot_rejects_relative_database_path_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._repo_root",
        lambda: repo_root,
    )
    monkeypatch.setattr(
        "scripts.generate_finance_telemetry_snapshot._generate_snapshot",
        lambda **_: (_ for _ in ()).throw(AssertionError("snapshot generation should not run")),
    )

    with pytest.raises(
        ValueError,
        match="database_path must stay within repo root when relative",
    ):
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                "artifacts/finance_telemetry_snapshot.json",
                "--database-path",
                "../escape/finance.sqlite",
            ]
        )


def test_generate_finance_telemetry_snapshot_rejects_directory_database_path(
    tmp_path: Path,
) -> None:
    database_dir = tmp_path / "database-dir"
    database_dir.mkdir()

    with pytest.raises(ValueError, match="database_path must be a file path"):
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(tmp_path / "finance_telemetry_snapshot.json"),
                "--database-path",
                str(database_dir),
            ]
        )


def test_generate_finance_telemetry_snapshot_rejects_blocked_database_parent(
    tmp_path: Path,
) -> None:
    blocked_parent = tmp_path / "blocked-database-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="database_path parent must be a directory path"):
        generate_finance_telemetry_snapshot_main(
            [
                "--output",
                str(tmp_path / "finance_telemetry_snapshot.json"),
                "--database-path",
                str(blocked_parent / "finance.sqlite"),
            ]
        )


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


def test_generate_pricing_benchmark_register_rejects_invalid_source_age_threshold(
    tmp_path: Path,
) -> None:
    output = tmp_path / "pricing_benchmark_register.json"

    with pytest.raises(ValueError, match="max_source_age_days must be >= 1.0"):
        generate_pricing_benchmark_register_main(
            [
                "--output",
                str(output),
                "--max-source-age-days",
                "0",
            ]
        )


@pytest.mark.parametrize(
    "relative_output",
    [
        "scripts/verify_pricing_benchmark_register.py",
        "docs/ops/evidence/pricing_benchmark_register_TEMPLATE.json",
        "docs/ops/evidence/finance_guardrails_TEMPLATE.json",
        "docs/ops/evidence/valdrics_disposition_register_2026-02-28.json",
        "docs/ops/evidence/README.md",
    ],
)
def test_generate_pricing_benchmark_register_rejects_protected_output_collisions(
    monkeypatch: pytest.MonkeyPatch,
    relative_output: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    output = repo_root / relative_output
    called = {"build": False}

    def _unexpected_build_payload(**_: object) -> dict[str, object]:
        called["build"] = True
        raise AssertionError("payload generation should not run for protected output paths")

    monkeypatch.setattr(pricing_generator, "_build_payload", _unexpected_build_payload)

    with pytest.raises(ValueError, match="output must not overwrite pricing benchmark"):
        generate_pricing_benchmark_register_main(
            [
                "--output",
                str(output),
                "--max-source-age-days",
                "120",
            ]
        )

    assert called["build"] is False


def test_generate_pricing_benchmark_register_rejects_output_parent_file(
    tmp_path: Path,
) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="output parent must be a directory path"):
        generate_pricing_benchmark_register_main(
            [
                "--output",
                str(blocked_parent / "pricing_benchmark_register.json"),
                "--max-source-age-days",
                "120",
            ]
        )


def test_generate_pricing_benchmark_register_rejects_directory_output_path(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "pricing-output"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="output must be a file path"):
        generate_pricing_benchmark_register_main(
            [
                "--output",
                str(output_dir),
                "--max-source-age-days",
                "120",
            ]
        )


def test_generate_pricing_benchmark_register_rejects_relative_protected_output_from_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(pricing_generator, "_repo_root", lambda: repo_root)

    with pytest.raises(ValueError, match="output must not overwrite pricing benchmark"):
        generate_pricing_benchmark_register_main(
            [
                "--output",
                "docs/ops/evidence/pricing_benchmark_register_TEMPLATE.json",
                "--max-source-age-days",
                "120",
            ]
        )


def test_generate_pricing_benchmark_register_resolves_relative_output_from_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(pricing_generator, "_repo_root", lambda: repo_root)

    assert (
        generate_pricing_benchmark_register_main(
            [
                "--output",
                "artifacts/pricing_benchmark_register.json",
                "--max-source-age-days",
                "120",
            ]
        )
        == 0
    )
    assert (repo_root / "artifacts" / "pricing_benchmark_register.json").exists()


def test_generate_pricing_benchmark_register_does_not_leave_output_when_verification_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "pricing_benchmark_register.json"
    verify_calls: list[Path] = []

    def _fake_verify_register(*, register_path: Path, max_source_age_days: float) -> int:
        del max_source_age_days
        verify_calls.append(register_path)
        raise ValueError("pricing verification failed")

    monkeypatch.setattr(pricing_generator, "verify_register", _fake_verify_register)

    with pytest.raises(ValueError, match="pricing verification failed"):
        generate_pricing_benchmark_register_main(
            [
                "--output",
                str(output),
                "--max-source-age-days",
                "120",
            ]
        )

    assert not output.exists()
    assert verify_calls
    assert all(path != output for path in verify_calls)


def test_generate_pricing_benchmark_register_rejects_relative_output_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(pricing_generator, "_repo_root", lambda: repo_root)

    with pytest.raises(
        ValueError,
        match="output must stay within repo root when relative",
    ):
        generate_pricing_benchmark_register_main(
            [
                "--output",
                "../escape/pricing_benchmark_register.json",
                "--max-source-age-days",
                "120",
            ]
        )


@pytest.mark.parametrize(
    ("value", "expected_message"),
    [
        (math.nan, r"sources\[0\]\.confidence_score must be finite"),
        (math.inf, r"sources\[0\]\.confidence_score must be finite"),
        (-0.1, r"sources\[0\]\.confidence_score must be >= 0"),
        (1.1, r"sources\[0\]\.confidence_score must be <= 1"),
        ("oops", r"sources\[0\]\.confidence_score must be numeric"),
    ],
)
def test_generate_pricing_benchmark_register_rejects_invalid_confidence_scores(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    value: object,
    expected_message: str,
) -> None:
    output = tmp_path / "pricing_benchmark_register.json"
    original_sources = pricing_generator._build_sources

    def _build_sources_with_invalid_score(*, captured_at):
        sources = original_sources(captured_at=captured_at)
        sources[0]["confidence_score"] = value
        return sources

    monkeypatch.setattr(pricing_generator, "_build_sources", _build_sources_with_invalid_score)

    with pytest.raises(ValueError, match=expected_message):
        generate_pricing_benchmark_register_main(
            [
                "--output",
                str(output),
                "--max-source-age-days",
                "120",
            ]
        )


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


def test_generate_pkg_fin_policy_decisions_rejects_duplicate_tier_rows() -> None:
    tiers = sorted(REQUIRED_TIERS)
    telemetry_payload = {
        "window": {
            "start": "2026-01-01",
            "end": "2026-01-31",
            "label": "2026-01",
        },
        "pricing_reference": {
            tier: {"annual_monthly_factor": 1.0}
            for tier in tiers
        },
        "tier_revenue_inputs": [
            {"tier": tier, "gross_mrr_usd": 1000.0}
            for tier in tiers
        ]
        + [{"tier": tiers[0], "gross_mrr_usd": 1500.0}],
        "tier_llm_usage": [
            {"tier": tier, "total_cost_usd": 100.0}
            for tier in tiers
        ],
        "tier_subscription_snapshot": [
            {"tier": tier, "active_subscriptions": 10}
            for tier in tiers
        ],
    }

    try:
        build_pkg_fin_policy_payload(
            telemetry_payload=telemetry_payload,
            months_observed=2,
        )
    except ValueError as exc:
        assert "duplicate tier" in str(exc)
    else:
        raise AssertionError("expected duplicate tier rows to be rejected")


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


def test_key_rotation_drill_checks_use_distinct_selectors() -> None:
    selectors = [check.selector for check in _all_drill_checks()]

    assert len(selectors) == len(set(selectors))


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
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["runtime_probe_results"]
    assert all(item["control_probe_ids"] for item in payload["dispositions"])
    assert (
        verify_disposition_register(
            register_path=output,
            max_artifact_age_days=45.0,
            max_review_window_days=120.0,
        )
        == 0
    )


def test_generate_valdrics_disposition_register_rejects_blank_source_audit_path(
    tmp_path: Path,
) -> None:
    output = tmp_path / "valdrics_disposition_register.json"

    with pytest.raises(ValueError, match="source_audit_path must be a non-empty string"):
        generate_valdrics_disposition_register_main(
            [
                "--output",
                str(output),
                "--source-audit-path",
                "   ",
            ]
        )


def test_generate_valdrics_disposition_register_rejects_missing_local_source_audit_path(
    tmp_path: Path,
) -> None:
    output = tmp_path / "valdrics_disposition_register.json"
    missing_audit = tmp_path / "missing_audit.md"

    with pytest.raises(
        FileNotFoundError,
        match="source_audit_path local file does not exist",
    ):
        generate_valdrics_disposition_register_main(
            [
                "--output",
                str(output),
                "--source-audit-path",
                str(missing_audit),
            ]
        )


def test_generate_valdrics_disposition_register_rejects_source_audit_output_collision(
    tmp_path: Path,
) -> None:
    output = tmp_path / "valdrics_disposition_register.json"
    output.write_text("audit source", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="source_audit_path and output must be different files",
    ):
        generate_valdrics_disposition_register_main(
            [
                "--output",
                str(output),
                "--source-audit-path",
                str(output),
            ]
        )


@pytest.mark.parametrize(
    "relative_output",
    [
        "scripts/verify_valdrics_disposition_freshness.py",
        "docs/ops/evidence/valdrics_disposition_register_TEMPLATE.json",
        "docs/ops/evidence/valdrics_disposition_register_2026-02-28.json",
        "docs/ops/evidence/finance_telemetry_snapshot_TEMPLATE.json",
        "docs/ops/evidence/enforcement_stress_artifact_2026-02-27.json",
        "docs/ops/evidence/README.md",
    ],
)
def test_generate_valdrics_disposition_register_rejects_protected_output_collisions(
    monkeypatch: pytest.MonkeyPatch,
    relative_output: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    output = repo_root / relative_output

    monkeypatch.setattr(
        "scripts.generate_valdrics_disposition_register._collect_probe_results",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("probe collection should not run for protected output paths")
        ),
    )

    with pytest.raises(ValueError, match="output must not overwrite Valdrics"):
        generate_valdrics_disposition_register_main(
            [
                "--output",
                str(output),
            ]
        )


def test_generate_valdrics_disposition_register_rejects_relative_protected_output_from_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(valdrics_generator, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        "scripts.generate_valdrics_disposition_register._collect_probe_results",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("probe collection should not run for protected output paths")
        ),
    )

    with pytest.raises(ValueError, match="output must not overwrite Valdrics"):
        generate_valdrics_disposition_register_main(
            [
                "--output",
                "docs/ops/evidence/valdrics_disposition_register_TEMPLATE.json",
            ]
        )


def test_generate_valdrics_disposition_register_resolves_relative_paths_from_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    source_audit = repo_root / "docs" / "ops" / "source_audit.md"
    source_audit.parent.mkdir(parents=True, exist_ok=True)
    source_audit.write_text("audit source", encoding="utf-8")
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(valdrics_generator, "_repo_root", lambda: repo_root)

    probe_results = {
        probe.probe_id: {
            "probe_id": probe.probe_id,
            "command": " ".join(probe.command),
            "passed": True,
            "output_excerpt": "ok",
        }
        for probe in valdrics_generator.RUNTIME_PROBES
    }
    monkeypatch.setattr(
        "scripts.generate_valdrics_disposition_register._collect_probe_results",
        lambda **_: probe_results,
    )
    verify_calls: list[dict[str, object]] = []

    def _fake_verify(**kwargs: object) -> int:
        verify_calls.append(kwargs)
        return 0

    monkeypatch.setattr(valdrics_generator, "verify_disposition_register", _fake_verify)

    assert (
        generate_valdrics_disposition_register_main(
            [
                "--output",
                "artifacts/valdrics_disposition_register.json",
                "--source-audit-path",
                "docs/ops/source_audit.md",
            ]
        )
        == 0
    )

    expected_output = repo_root / "artifacts" / "valdrics_disposition_register.json"
    assert expected_output.exists()
    payload = json.loads(expected_output.read_text(encoding="utf-8"))
    assert payload["source_audit_path"] == source_audit.as_posix()
    assert len(verify_calls) == 1
    assert verify_calls[0]["max_artifact_age_days"] == 45.0
    assert verify_calls[0]["max_review_window_days"] == 120.0
    assert verify_calls[0]["register_path"].parent == expected_output.parent
    assert verify_calls[0]["register_path"] != expected_output


def test_generate_valdrics_disposition_register_does_not_leave_output_when_verification_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "valdrics_disposition_register.json"
    verify_calls: list[Path] = []

    probe_results = {
        probe.probe_id: {
            "probe_id": probe.probe_id,
            "command": " ".join(probe.command),
            "passed": True,
            "output_excerpt": "ok",
        }
        for probe in valdrics_generator.RUNTIME_PROBES
    }
    monkeypatch.setattr(
        "scripts.generate_valdrics_disposition_register._collect_probe_results",
        lambda **_: probe_results,
    )

    def _fake_verify(*, register_path: Path, max_artifact_age_days: float, max_review_window_days: float) -> int:
        del max_artifact_age_days, max_review_window_days
        verify_calls.append(register_path)
        raise ValueError("valdrics verification failed")

    monkeypatch.setattr(valdrics_generator, "verify_disposition_register", _fake_verify)

    with pytest.raises(ValueError, match="valdrics verification failed"):
        generate_valdrics_disposition_register_main(
            [
                "--output",
                str(output),
                "--source-audit-path",
                "runtime://ci/deep_debt_audit_2026-03-05",
            ]
        )

    assert not output.exists()
    assert verify_calls
    assert all(path != output for path in verify_calls)


def test_generate_valdrics_disposition_register_rejects_relative_paths_that_escape_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(valdrics_generator, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        "scripts.generate_valdrics_disposition_register._collect_probe_results",
        lambda **_: (_ for _ in ()).throw(
            AssertionError("probe collection should not run for escaping paths")
        ),
    )

    with pytest.raises(
        ValueError,
        match="relative path must stay within repo root",
    ):
        generate_valdrics_disposition_register_main(
            [
                "--output",
                "artifacts/valdrics_disposition_register.json",
                "--source-audit-path",
                "../escape/source_audit.md",
            ]
        )


def test_generate_valdrics_disposition_register_rejects_output_parent_file(
    tmp_path: Path,
) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="output parent must be a directory path"):
        generate_valdrics_disposition_register_main(
            [
                "--output",
                str(blocked_parent / "valdrics_disposition_register.json"),
            ]
        )


def test_generate_valdrics_disposition_register_rejects_directory_output_path(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "valdrics-output"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="output must be a file path"):
        generate_valdrics_disposition_register_main(
            [
                "--output",
                str(output_dir),
            ]
        )


def test_generate_valdrics_disposition_register_rejects_non_positive_probe_timeout(
    tmp_path: Path,
) -> None:
    output = tmp_path / "valdrics_disposition_register.json"

    with pytest.raises(ValueError, match="probe_timeout_seconds must be > 0"):
        generate_valdrics_disposition_register_main(
            [
                "--output",
                str(output),
                "--probe-timeout-seconds",
                "0",
            ]
        )


def test_generate_valdrics_disposition_register_runs_probes_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cwd_calls: list[Path] = []

    class _Completed:
        returncode = 0
        stdout = "ok\n"
        stderr = ""

    def _fake_run(*args, **kwargs):  # type: ignore[no-untyped-def]
        del args
        cwd_calls.append(kwargs["cwd"])
        return _Completed()

    monkeypatch.setattr(valdrics_generator.subprocess, "run", _fake_run)

    probe_results = valdrics_generator._collect_probe_results(timeout_seconds=1.0)

    assert probe_results
    assert cwd_calls
    assert all(cwd == valdrics_generator._repo_root() for cwd in cwd_calls)
