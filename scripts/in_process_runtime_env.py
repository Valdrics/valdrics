from __future__ import annotations

import os
from pathlib import Path
import tempfile


def _build_synthetic_secret(label: str, *, minimum_length: int = 32) -> str:
    normalized = str(label or "fixture").strip().replace("_", "-")
    seed = f"valdrics-{normalized}-fixture-"
    value = seed
    while len(value) < minimum_length:
        value += seed
    return value[:minimum_length]


def build_isolated_test_environment_values(*, database_url: str) -> dict[str, str]:
    resolved_database_url = str(database_url or "").strip()
    if not resolved_database_url:
        raise ValueError("database_url must be provided for isolated in-process runtime")

    return {
        "CSRF_SECRET_KEY": _build_synthetic_secret("csrf-secret"),
        "DATABASE_URL": resolved_database_url,
        "DB_SSL_MODE": "disable",
        "DEBUG": "false",
        "ENCRYPTION_KEY": _build_synthetic_secret("encryption-key"),
        "ENVIRONMENT": "local",
        "KDF_SALT": "S0RGX1NBTFRfRk9SX1RFU1RJTkdfMzJfQllURVNfT0s=",
        "PGSSLMODE": "disable",
        "SUPABASE_JWT_SECRET": _build_synthetic_secret("supabase-jwt-secret"),
        "TESTING": "true",
    }


def configure_isolated_test_environment(*, database_url: str) -> None:
    for key, value in build_isolated_test_environment_values(
        database_url=database_url
    ).items():
        os.environ[key] = value


def build_unique_sqlite_database_url(*, prefix: str) -> tuple[str, Path]:
    normalized_prefix = str(prefix or "valdrics-runtime").strip().replace("_", "-")
    database_root = Path(tempfile.mkdtemp(prefix=f"{normalized_prefix}-"))
    database_path = database_root / f"{normalized_prefix}.sqlite3"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    return database_url, database_path
