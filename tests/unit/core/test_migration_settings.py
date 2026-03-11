from __future__ import annotations

from unittest.mock import patch

import pytest

from app.shared.core.migration_settings import MigrationSettings


def test_migration_settings_accepts_minimal_database_contract() -> None:
    with patch.dict(
        "os.environ",
        {
            "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
        },
        clear=True,
    ):
        settings = MigrationSettings(_env_file=None)

    assert settings.DATABASE_URL.startswith("postgresql+asyncpg://postgres:")
    assert settings.DB_SSL_MODE == "require"
    assert settings.DB_SSL_CA_CERT_PATH is None


def test_migration_settings_requires_database_url() -> None:
    with patch.dict("os.environ", {}, clear=True):
        with pytest.raises(ValueError, match="DATABASE_URL is required for Alembic migrations."):
            MigrationSettings(_env_file=None)


def test_migration_settings_requires_ca_path_for_verified_ssl() -> None:
    with patch.dict(
        "os.environ",
        {
            "DATABASE_URL": "postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
            "DB_SSL_MODE": "verify-full",
        },
        clear=True,
    ):
        with pytest.raises(
            ValueError,
            match="DB_SSL_CA_CERT_PATH is required when DB_SSL_MODE is verify-ca or verify-full.",
        ):
            MigrationSettings(_env_file=None)


def test_migration_settings_rejects_placeholder_database_url() -> None:
    with patch.dict(
        "os.environ",
        {
            "DATABASE_URL": (
                "postgresql+asyncpg://REPLACE_WITH_DB_USER:"
                "REPLACE_WITH_DB_PASSWORD@REPLACE_WITH_DB_HOST:5432/postgres"
            ),
        },
        clear=True,
    ):
        with pytest.raises(
            ValueError,
            match="DATABASE_URL contains unresolved placeholder values.",
        ):
            MigrationSettings(_env_file=None)
