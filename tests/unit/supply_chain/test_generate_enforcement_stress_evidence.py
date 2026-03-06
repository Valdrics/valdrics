from __future__ import annotations

from types import SimpleNamespace

from scripts.generate_enforcement_stress_evidence import (
    ENFORCEMENT_ENDPOINTS,
    _extract_health_database_engine,
    _normalize_database_engine_name,
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
