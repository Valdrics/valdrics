from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.shared.core.config_validation_placeholders import require_no_managed_placeholder


_ALLOWED_DB_SSL_MODES = {"disable", "require", "verify-ca", "verify-full"}


class MigrationSettings(BaseSettings):
    """Minimal settings contract for Alembic migrations."""

    DATABASE_URL: Optional[str] = None
    DB_SSL_MODE: str = "require"
    DB_SSL_CA_CERT_PATH: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", env_ignore_empty=True)

    @model_validator(mode="after")
    def validate_migration_config(self) -> "MigrationSettings":
        database_url = str(self.DATABASE_URL or "").strip()
        if not database_url:
            raise ValueError("DATABASE_URL is required for Alembic migrations.")
        require_no_managed_placeholder(database_url, name="DATABASE_URL")

        normalized_ssl_mode = str(self.DB_SSL_MODE or "require").strip().lower()
        if normalized_ssl_mode not in _ALLOWED_DB_SSL_MODES:
            raise ValueError(
                "DB_SSL_MODE must be one of: disable, require, verify-ca, verify-full."
            )

        self.DB_SSL_MODE = normalized_ssl_mode
        require_no_managed_placeholder(
            self.DB_SSL_CA_CERT_PATH,
            name="DB_SSL_CA_CERT_PATH",
        )
        if normalized_ssl_mode in {"verify-ca", "verify-full"} and not str(
            self.DB_SSL_CA_CERT_PATH or ""
        ).strip():
            raise ValueError(
                "DB_SSL_CA_CERT_PATH is required when DB_SSL_MODE is verify-ca or verify-full."
            )

        return self


@lru_cache
def get_migration_settings() -> MigrationSettings:
    return MigrationSettings()
