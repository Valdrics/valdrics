from __future__ import annotations

import os
from types import SimpleNamespace

from scripts.generate_enforcement_stress_evidence import (
    ENFORCEMENT_ENDPOINTS,
    _configure_isolated_bootstrap_env,
    _extract_health_database_engine,
    _normalize_database_engine_name,
    _resolve_requested_database_url,
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
