from __future__ import annotations

import os
from pathlib import Path
import tempfile


_ISOLATED_TEST_ENV = {
    "CSRF_SECRET_KEY": "test-csrf-secret-key-at-least-32-bytes",
    "DB_SSL_MODE": "disable",
    "DEBUG": "false",
    "ENCRYPTION_KEY": "32-byte-long-test-encryption-key",
    "ENVIRONMENT": "local",
    "KDF_SALT": "S0RGX1NBTFRfRk9SX1RFU1RJTkdfMzJfQllURVNfT0s=",
    "PGSSLMODE": "disable",
    "SUPABASE_JWT_SECRET": "test-jwt-secret-for-testing-at-least-32-bytes",
    "TESTING": "true",
}


def configure_isolated_test_environment(*, database_url: str) -> None:
    resolved_database_url = str(database_url or "").strip()
    if not resolved_database_url:
        raise ValueError("database_url must be provided for isolated in-process runtime")

    env_values = dict(_ISOLATED_TEST_ENV)
    env_values["DATABASE_URL"] = resolved_database_url
    for key, value in env_values.items():
        os.environ[key] = value


def build_unique_sqlite_database_url(*, prefix: str) -> tuple[str, Path]:
    normalized_prefix = str(prefix or "valdrics-runtime").strip().replace("_", "-")
    database_root = Path(tempfile.mkdtemp(prefix=f"{normalized_prefix}-"))
    database_path = database_root / f"{normalized_prefix}.sqlite3"
    database_url = f"sqlite+aiosqlite:///{database_path.as_posix()}"
    return database_url, database_path
