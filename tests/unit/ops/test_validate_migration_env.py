from __future__ import annotations

import os
from pathlib import Path
import sys
from unittest.mock import patch

from scripts import validate_migration_env


def test_validate_migration_env_passes_with_minimal_env_file(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    env_file = tmp_path / "production.migrate.env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
                "DB_SSL_MODE=require",
            ]
        ),
        encoding="utf-8",
    )

    with patch.dict(os.environ, {}, clear=True):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "validate_migration_env.py",
                "--env-file",
                str(env_file),
            ],
        )
        result = validate_migration_env.main()

    assert result == 0
    assert "migration_env_validation_passed db_ssl_mode=require" in capsys.readouterr().out


def test_validate_migration_env_rejects_verified_ssl_without_ca_path(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    env_file = tmp_path / "production.migrate.env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
                "DB_SSL_MODE=verify-full",
            ]
        ),
        encoding="utf-8",
    )

    with patch.dict(os.environ, {}, clear=True):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "validate_migration_env.py",
                "--env-file",
                str(env_file),
            ],
        )
        result = validate_migration_env.main()

    assert result == 1
    assert "DB_SSL_CA_CERT_PATH is required" in capsys.readouterr().err


def test_validate_migration_env_rejects_placeholder_database_url(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    env_file = tmp_path / "production.migrate.env"
    env_file.write_text(
        "\n".join(
            [
                "DATABASE_URL=postgresql+asyncpg://REPLACE_WITH_DB_USER:REPLACE_WITH_DB_PASSWORD@REPLACE_WITH_DB_HOST:5432/postgres",
                "DB_SSL_MODE=require",
            ]
        ),
        encoding="utf-8",
    )

    with patch.dict(os.environ, {}, clear=True):
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "validate_migration_env.py",
                "--env-file",
                str(env_file),
            ],
        )
        result = validate_migration_env.main()

    assert result == 1
    assert "DATABASE_URL contains unresolved placeholder values." in capsys.readouterr().err
