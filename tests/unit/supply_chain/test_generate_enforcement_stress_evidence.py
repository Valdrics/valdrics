from __future__ import annotations

import json
import math
import os
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

import scripts.generate_enforcement_stress_evidence as stress_generator
from scripts.generate_enforcement_stress_evidence import (
    ENFORCEMENT_ENDPOINTS,
    _configure_isolated_bootstrap_env,
    _extract_health_database_engine,
    _normalize_database_engine_name,
    _normalize_load_profile_args,
    _resolve_requested_database_url,
    _result_counts,
    _result_metrics,
    _result_to_payload,
)


def test_enforcement_endpoints_contract_contains_required_release_checks() -> None:
    assert "/api/v1/enforcement/policies" in ENFORCEMENT_ENDPOINTS
    assert "/api/v1/enforcement/ledger?limit=50" in ENFORCEMENT_ENDPOINTS
    assert "/api/v1/enforcement/exports/parity?limit=50" in ENFORCEMENT_ENDPOINTS


def test_normalize_database_engine_name_maps_known_dialects() -> None:
    assert _normalize_database_engine_name("postgresql+asyncpg://x") == "postgresql"
    assert _normalize_database_engine_name("sqlite+aiosqlite:///tmp/db.sqlite") == "sqlite"
    assert _normalize_database_engine_name("mysql+pymysql://x") == "mysql"


def test_resolve_requested_database_url_requires_release_backend_match() -> None:
    database_url = "postgresql+asyncpg://user:pass@db.example.com:5432/app"
    assert (
        _resolve_requested_database_url(
            database_url=database_url,
            required_database_engine="postgresql",
        )
        == database_url
    )

    try:
        _resolve_requested_database_url(
            database_url="sqlite+aiosqlite:///tmp/enforcement.sqlite3",
            required_database_engine="postgresql",
        )
    except ValueError as exc:
        assert "requires a postgresql runtime" in str(exc)
    else:
        raise AssertionError("expected sqlite release evidence to be rejected")


def test_configure_isolated_bootstrap_env_overrides_shell_database_url(
    monkeypatch,
) -> None:
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+asyncpg://user:pass@db.example.com:5432/app",
    )

    safe_database_url = "sqlite+aiosqlite:///tmp/enforcement-evidence.sqlite3"
    returned = _configure_isolated_bootstrap_env(database_url=safe_database_url)

    assert returned == safe_database_url
    assert os.environ["DATABASE_URL"] == safe_database_url
    assert os.environ["TESTING"] == "true"
    assert os.environ["DB_SSL_MODE"] == "disable"


def test_extract_and_result_payload_helpers_are_deterministic() -> None:
    payload = {
        "database": {
            "engine": "postgresql+asyncpg",
        }
    }
    assert _extract_health_database_engine(payload) == "postgresql"

    raw = SimpleNamespace(
        total_requests=42,
        successful_requests=40,
        failed_requests=2,
        throughput_rps=1.2,
        avg_response_time=0.2,
        median_response_time=0.1,
        p95_response_time=0.3,
        p99_response_time=0.5,
        min_response_time=0.05,
        max_response_time=0.9,
        errors=["err-1", "err-2"],
    )
    rendered = _result_to_payload(raw)
    assert rendered["total_requests"] == 42
    assert rendered["successful_requests"] == 40
    assert rendered["failed_requests"] == 2
    assert rendered["errors_sample"] == ["err-1", "err-2"]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("total_requests", -1, "result.total_requests must be >= 0"),
        ("successful_requests", -1, "result.successful_requests must be >= 0"),
        ("failed_requests", -1, "result.failed_requests must be >= 0"),
        (
            "failed_requests",
            50,
            "result.successful_requests \\+ result.failed_requests must be <= result.total_requests",
        ),
    ],
)
def test_result_count_helpers_reject_invalid_runtime_counts(
    field: str,
    value: object,
    message: str,
) -> None:
    raw = SimpleNamespace(
        total_requests=42,
        successful_requests=40,
        failed_requests=2,
        throughput_rps=1.2,
        avg_response_time=0.2,
        median_response_time=0.1,
        p95_response_time=0.3,
        p99_response_time=0.5,
        min_response_time=0.05,
        max_response_time=0.9,
    )
    setattr(raw, field, value)

    with pytest.raises(ValueError, match=message):
        _result_counts(raw)

    with pytest.raises(ValueError, match=message):
        _result_to_payload(raw)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("throughput_rps", math.nan, "result.throughput_rps must be finite"),
        ("avg_response_time", math.inf, "result.avg_response_time must be finite"),
        ("median_response_time", -1.0, "result.median_response_time must be >= 0"),
        ("p95_response_time", "oops", "result.p95_response_time must be numeric"),
    ],
)
def test_result_metric_helpers_reject_invalid_runtime_metrics(
    field: str,
    value: object,
    message: str,
) -> None:
    raw = SimpleNamespace(
        throughput_rps=1.2,
        avg_response_time=0.2,
        median_response_time=0.1,
        p95_response_time=0.3,
        p99_response_time=0.5,
        min_response_time=0.05,
        max_response_time=0.9,
    )
    setattr(raw, field, value)

    with pytest.raises(ValueError, match=message):
        _result_metrics(raw)

    with pytest.raises(ValueError, match=message):
        _result_to_payload(raw)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("rounds", 0, "rounds must be > 0"),
        ("duration_seconds", 0, "duration_seconds must be > 0"),
        ("concurrent_users", 0, "concurrent_users must be > 0"),
        ("ramp_seconds", -1, "ramp_seconds must be >= 0"),
        ("pause_seconds", -0.1, "pause_seconds must be >= 0"),
        ("max_p95_seconds", 0, "max_p95_seconds must be > 0"),
        ("max_error_rate_percent", -1, "max_error_rate_percent must be >= 0"),
        ("min_throughput_rps", 0, "min_throughput_rps must be > 0"),
    ],
)
def test_normalize_load_profile_args_rejects_invalid_thresholds(
    field: str,
    value: int | float,
    message: str,
) -> None:
    args = Namespace(
        duration_seconds=30,
        concurrent_users=10,
        ramp_seconds=5,
        rounds=3,
        pause_seconds=0.0,
        max_p95_seconds=2.0,
        max_error_rate_percent=1.0,
        min_throughput_rps=0.5,
    )
    setattr(args, field, value)

    with pytest.raises(ValueError, match=message):
        _normalize_load_profile_args(args)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("pause_seconds", math.nan),
        ("pause_seconds", math.inf),
        ("max_p95_seconds", math.nan),
        ("max_p95_seconds", math.inf),
        ("max_error_rate_percent", math.nan),
        ("max_error_rate_percent", -math.inf),
        ("min_throughput_rps", math.nan),
        ("min_throughput_rps", math.inf),
    ],
)
def test_normalize_load_profile_args_rejects_non_finite_floats(
    field: str,
    value: float,
) -> None:
    args = Namespace(
        duration_seconds=30,
        concurrent_users=10,
        ramp_seconds=5,
        rounds=3,
        pause_seconds=0.0,
        max_p95_seconds=2.0,
        max_error_rate_percent=1.0,
        min_throughput_rps=0.5,
    )
    setattr(args, field, value)

    with pytest.raises(ValueError, match=rf"{field} must be finite"):
        _normalize_load_profile_args(args)


def test_normalize_load_profile_args_preserves_valid_explicit_values() -> None:
    args = Namespace(
        duration_seconds=45,
        concurrent_users=12,
        ramp_seconds=6,
        rounds=4,
        pause_seconds=1.5,
        max_p95_seconds=2.5,
        max_error_rate_percent=0.5,
        min_throughput_rps=0.75,
    )

    normalized = _normalize_load_profile_args(args)

    assert normalized == {
        "duration_seconds": 45,
        "concurrent_users": 12,
        "ramp_seconds": 6,
        "rounds": 4,
        "pause_seconds": 1.5,
        "max_p95_seconds": 2.5,
        "max_error_rate_percent": 0.5,
        "min_throughput_rps": 0.75,
    }


def test_main_self_verifies_generated_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "enforcement_stress.json"
    payload = {
        "profile": "enforcement",
        "runner": "scripts/load_test_api.py",
        "runtime": {"database_engine": "postgresql"},
        "captured_at": "2026-03-18T12:00:00+00:00",
        "endpoints": list(ENFORCEMENT_ENDPOINTS),
        "duration_seconds": 30,
        "concurrent_users": 10,
        "rounds": 3,
        "runs": [{}, {}, {}],
        "results": {
            "total_requests": 300,
            "successful_requests": 300,
            "failed_requests": 0,
            "throughput_rps": 1.0,
            "avg_response_time": 0.2,
            "median_response_time": 0.2,
            "p95_response_time": 0.4,
            "p99_response_time": 0.5,
            "min_response_time": 0.1,
            "max_response_time": 0.6,
            "errors_sample": [],
        },
        "min_throughput_rps": 1.0,
        "preflight": {"enabled": True, "passed": True, "failures": []},
        "thresholds": {
            "max_p95_seconds": 2.0,
            "max_error_rate_percent": 1.0,
            "min_throughput_rps": 0.5,
        },
        "evaluation": {
            "rounds": [],
            "overall_meets_targets": True,
            "worst_p95_seconds": 0.4,
            "min_throughput_rps": 1.0,
        },
        "meets_targets": True,
    }

    async def _fake_generate_evidence(args: Namespace) -> dict[str, object]:
        assert args.output == str(output)
        return payload

    verify_calls: list[dict[str, object]] = []

    def _fake_verify(**kwargs: object) -> int:
        verify_calls.append(kwargs)
        return 0

    monkeypatch.setattr(stress_generator, "generate_evidence", _fake_generate_evidence)
    monkeypatch.setattr(stress_generator, "verify_evidence", _fake_verify)

    exit_code = stress_generator.main(
        [
            "--output",
            str(output),
            "--database-url",
            "postgresql+asyncpg://user:pass@db.example.com:5432/app",
        ]
    )

    assert exit_code == 0
    assert json.loads(output.read_text(encoding="utf-8")) == payload
    assert len(verify_calls) == 1
    assert verify_calls[0]["expected_profile"] == "enforcement"
    assert verify_calls[0]["min_rounds"] == 3
    assert verify_calls[0]["min_duration_seconds"] == 30
    assert verify_calls[0]["min_concurrent_users"] == 10
    assert verify_calls[0]["required_database_engine"] == "postgresql"
    assert verify_calls[0]["max_p95_seconds"] == 2.0
    assert verify_calls[0]["max_error_rate_percent"] == 1.0
    assert verify_calls[0]["min_throughput_rps"] == 0.5
    assert verify_calls[0]["max_artifact_age_hours"] == 4.0
    assert verify_calls[0]["evidence_path"].parent == output.parent
    assert verify_calls[0]["evidence_path"] != output


def test_main_does_not_leave_output_when_verification_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output = tmp_path / "enforcement_stress.json"
    payload = {
        "profile": "enforcement",
        "runner": "scripts/load_test_api.py",
        "runtime": {"database_engine": "postgresql"},
        "captured_at": "2026-03-18T12:00:00+00:00",
        "endpoints": list(ENFORCEMENT_ENDPOINTS),
        "duration_seconds": 30,
        "concurrent_users": 10,
        "rounds": 3,
        "runs": [{}, {}, {}],
        "results": {
            "total_requests": 300,
            "successful_requests": 300,
            "failed_requests": 0,
            "throughput_rps": 1.0,
            "avg_response_time": 0.2,
            "median_response_time": 0.2,
            "p95_response_time": 0.4,
            "p99_response_time": 0.5,
            "min_response_time": 0.1,
            "max_response_time": 0.6,
            "errors_sample": [],
        },
        "min_throughput_rps": 1.0,
        "preflight": {"enabled": True, "passed": True, "failures": []},
        "thresholds": {
            "max_p95_seconds": 2.0,
            "max_error_rate_percent": 1.0,
            "min_throughput_rps": 0.5,
        },
        "evaluation": {
            "rounds": [],
            "overall_meets_targets": True,
            "worst_p95_seconds": 0.4,
            "min_throughput_rps": 1.0,
        },
        "meets_targets": True,
    }
    verify_calls: list[Path] = []

    async def _fake_generate_evidence(args: Namespace) -> dict[str, object]:
        assert args.output == str(output)
        return payload

    def _fake_verify(**kwargs: object) -> int:
        verify_calls.append(kwargs["evidence_path"])
        raise ValueError("stress verification failed")

    monkeypatch.setattr(stress_generator, "generate_evidence", _fake_generate_evidence)
    monkeypatch.setattr(stress_generator, "verify_evidence", _fake_verify)

    with pytest.raises(ValueError, match="stress verification failed"):
        stress_generator.main(
            [
                "--output",
                str(output),
                "--database-url",
                "postgresql+asyncpg://user:pass@db.example.com:5432/app",
            ]
        )

    assert not output.exists()
    assert verify_calls
    assert all(path != output for path in verify_calls)


@pytest.mark.parametrize(
    "relative_output",
    [
        "scripts/verify_enforcement_stress_evidence.py",
        "scripts/load_test_api.py",
        "docs/ops/evidence/enforcement_stress_artifact_TEMPLATE.json",
        "docs/ops/evidence/enforcement_stress_artifact_2026-02-27.json",
        "docs/ops/evidence/finance_guardrails_TEMPLATE.json",
        "docs/ops/evidence/pricing_benchmark_register_2026-02-27.json",
    ],
)
def test_main_rejects_protected_output_collisions(
    monkeypatch: pytest.MonkeyPatch,
    relative_output: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    output = repo_root / relative_output

    async def _unexpected_generate_evidence(args: Namespace) -> dict[str, object]:
        raise AssertionError("stress generation should not run for protected output paths")

    monkeypatch.setattr(stress_generator, "generate_evidence", _unexpected_generate_evidence)

    with pytest.raises(ValueError, match="output must not overwrite enforcement stress"):
        stress_generator.main(
            [
                "--output",
                str(output),
                "--database-url",
                "postgresql+asyncpg://user:pass@db.example.com:5432/app",
            ]
        )


def test_main_rejects_relative_protected_output_from_outside_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(stress_generator, "_repo_root", lambda: repo_root)

    async def _unexpected_generate_evidence(args: Namespace) -> dict[str, object]:
        del args
        raise AssertionError("stress generation should not run for protected output paths")

    monkeypatch.setattr(stress_generator, "generate_evidence", _unexpected_generate_evidence)

    with pytest.raises(ValueError, match="output must not overwrite enforcement stress"):
        stress_generator.main(
            [
                "--output",
                "docs/ops/evidence/enforcement_stress_artifact_2026-02-27.json",
                "--database-url",
                "postgresql+asyncpg://user:pass@db.example.com:5432/app",
            ]
        )


def test_main_rejects_relative_output_that_escapes_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(stress_generator, "_repo_root", lambda: repo_root)

    async def _unexpected_generate_evidence(args: Namespace) -> dict[str, object]:
        del args
        raise AssertionError("stress generation should not run for escaping output paths")

    monkeypatch.setattr(stress_generator, "generate_evidence", _unexpected_generate_evidence)

    with pytest.raises(
        ValueError,
        match="output must stay within repo root when relative",
    ):
        stress_generator.main(
            [
                "--output",
                "../escape/enforcement_stress.json",
                "--database-url",
                "postgresql+asyncpg://user:pass@db.example.com:5432/app",
            ]
        )


def test_main_resolves_relative_output_from_repo_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(stress_generator, "_repo_root", lambda: repo_root)

    payload = {
        "profile": "enforcement",
        "meets_targets": True,
        "results": {"total_requests": 1},
    }

    async def _fake_generate_evidence(args: Namespace) -> dict[str, object]:
        del args
        return payload

    verify_calls: list[dict[str, object]] = []

    def _fake_verify(**kwargs: object) -> int:
        verify_calls.append(kwargs)
        return 0

    monkeypatch.setattr(stress_generator, "generate_evidence", _fake_generate_evidence)
    monkeypatch.setattr(stress_generator, "verify_evidence", _fake_verify)

    assert (
        stress_generator.main(
            [
                "--output",
                "artifacts/enforcement_stress.json",
                "--database-url",
                "postgresql+asyncpg://user:pass@db.example.com:5432/app",
            ]
        )
        == 0
    )
    expected_output = repo_root / "artifacts" / "enforcement_stress.json"
    assert expected_output.exists()
    assert verify_calls == [
        {
            "evidence_path": expected_output,
            "expected_profile": "enforcement",
            "min_rounds": 3,
            "min_duration_seconds": 30,
            "min_concurrent_users": 10,
            "required_database_engine": "postgresql",
            "max_p95_seconds": 2.0,
            "max_error_rate_percent": 1.0,
            "min_throughput_rps": 0.5,
            "max_artifact_age_hours": 4.0,
        }
    ]


def test_main_rejects_output_parent_file(
    tmp_path: Path,
) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")

    with pytest.raises(ValueError, match="output parent must be a directory path"):
        stress_generator.main(
            [
                "--output",
                str(blocked_parent / "enforcement_stress.json"),
                "--database-url",
                "postgresql+asyncpg://user:pass@db.example.com:5432/app",
            ]
        )


def test_main_rejects_directory_output_path(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "stress-output"
    output_dir.mkdir()

    with pytest.raises(ValueError, match="output must be a file path"):
        stress_generator.main(
            [
                "--output",
                str(output_dir),
                "--database-url",
                "postgresql+asyncpg://user:pass@db.example.com:5432/app",
            ]
        )
