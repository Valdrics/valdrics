from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from unittest.mock import patch

from scripts import validate_runtime_env


def _set_strict_env() -> None:
    os.environ["DATABASE_URL"] = "postgresql+asyncpg://postgres:postgres@127.0.0.1:5432/valdrics"
    os.environ["CSRF_SECRET_KEY"] = "ci-csrf-secret-key-32-chars-min-000000"
    os.environ["ENCRYPTION_KEY"] = "ci-encryption-key-32-chars-min-00000000"
    os.environ["KDF_SALT"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
    os.environ["SUPABASE_JWT_SECRET"] = "ci-supabase-jwt-secret-32-chars-0000"
    os.environ["ADMIN_API_KEY"] = "ci-admin-api-key-32-chars-min-0000000"
    os.environ["GROQ_API_KEY"] = "testing"
    os.environ["LLM_PROVIDER"] = "groq"
    os.environ["PAYSTACK_SECRET_KEY"] = "example_paystack_secret_ci_validation_only"
    os.environ["PAYSTACK_PUBLIC_KEY"] = "example_paystack_public_ci_validation_only"
    os.environ["ALLOW_SYNTHETIC_BILLING_KEYS_FOR_VALIDATION"] = "true"
    os.environ["REDIS_URL"] = "redis://localhost:6379/0"
    os.environ["SENTRY_DSN"] = "https://example@sentry.io/1"
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = "http://otel-collector:4317"
    os.environ["FORECASTER_ALLOW_HOLT_WINTERS_FALLBACK"] = "true"
    os.environ["FORECASTER_BREAK_GLASS_REASON"] = "Hermetic validator test without prophet wheel."
    os.environ["FORECASTER_BREAK_GLASS_EXPIRES_AT"] = (
        datetime.now(timezone.utc) + timedelta(hours=4)
    ).isoformat()


def test_validate_runtime_env_ignores_repo_local_dotenv(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "API_URL=https://api.from-dotenv.example",
                "FRONTEND_URL=https://app.from-dotenv.example",
            ]
        ),
        encoding="utf-8",
    )

    with patch.dict(os.environ, {}, clear=True):
        _set_strict_env()
        monkeypatch.setattr(
            sys,
            "argv",
            ["validate_runtime_env.py", "--environment", "production"],
        )

        result = validate_runtime_env.main()

    assert result == 1
    stderr = capsys.readouterr().err
    assert "api.from-dotenv.example" not in stderr
    assert "app.from-dotenv.example" not in stderr
    assert "API_URL" in stderr


def test_validate_runtime_env_passes_with_explicit_environment_values(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "API_URL=https://api.from-dotenv.example\nFRONTEND_URL=https://app.from-dotenv.example\n",
        encoding="utf-8",
    )

    with patch.dict(os.environ, {}, clear=True):
        _set_strict_env()
        os.environ["API_URL"] = "https://api.runtime.example"
        os.environ["FRONTEND_URL"] = "https://app.runtime.example"
        with patch(
            "app.shared.core.runtime_dependencies._module_available",
            return_value=True,
        ):
            monkeypatch.setattr(
                sys,
                "argv",
                ["validate_runtime_env.py", "--environment", "production"],
            )

            result = validate_runtime_env.main()

    assert result == 0
    assert "runtime_env_validation_passed environment=production testing=False" in capsys.readouterr().out


def test_validate_runtime_env_rejects_insecure_cors_origin(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    monkeypatch.chdir(tmp_path)

    with patch.dict(os.environ, {}, clear=True):
        _set_strict_env()
        os.environ["API_URL"] = "https://api.runtime.example"
        os.environ["FRONTEND_URL"] = "https://app.runtime.example"
        os.environ["CORS_ORIGINS"] = '["http://localhost:4173"]'
        with patch(
            "app.shared.core.runtime_dependencies._module_available",
            return_value=True,
        ):
            monkeypatch.setattr(
                sys,
                "argv",
                ["validate_runtime_env.py", "--environment", "production"],
            )

            result = validate_runtime_env.main()

    assert result == 1
    assert "CORS_ORIGINS" in capsys.readouterr().err
