from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_managed_migration_env import generate_managed_migration_env


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def test_generate_managed_migration_env_defaults_to_database_url_blocker(
    tmp_path: Path,
) -> None:
    output = tmp_path / "production.migrate.env"
    report_path = tmp_path / "production.migrate.report.json"

    report = generate_managed_migration_env(
        output_path=output,
        report_path=report_path,
        environment="production",
    )
    values = _parse_env(output)
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert values["ENVIRONMENT"] == "production"
    assert values["DB_SSL_MODE"] == "require"
    assert values["DATABASE_URL"].startswith("postgresql+asyncpg://REPLACE_WITH_DB_USER")
    assert report["migration_ready"] is False
    assert report_payload["required_operator_input_keys"] == ["DATABASE_URL"]
    assert report_payload["migration_validation_blockers"] == ["DATABASE_URL"]


def test_generate_managed_migration_env_requires_ca_path_for_verified_ssl(
    tmp_path: Path,
) -> None:
    output = tmp_path / "staging.migrate.env"
    report_path = tmp_path / "staging.migrate.report.json"

    generate_managed_migration_env(
        output_path=output,
        report_path=report_path,
        environment="staging",
        database_url="postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
        db_ssl_mode="verify-full",
    )
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert report_payload["required_operator_input_keys"] == [
        "DATABASE_URL",
        "DB_SSL_CA_CERT_PATH",
    ]
    assert report_payload["migration_validation_blockers"] == ["DB_SSL_CA_CERT_PATH"]
