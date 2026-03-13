from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

from scripts.generate_managed_runtime_env import generate_managed_runtime_env
from scripts import validate_runtime_env


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def test_generate_managed_runtime_env_generates_internal_secrets_and_reports_unresolved_keys(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "production.env"
    report_path = tmp_path / "production.report.json"
    _write(
        template,
        "\n".join(
            [
                "ENVIRONMENT=development",
                "API_URL=http://localhost:8000",
                "FRONTEND_URL=http://localhost:5174",
                "DATABASE_URL=",
                "REDIS_URL=",
                "SUPABASE_URL=",
                "SUPABASE_JWT_SECRET=",
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "KDF_SALT=",
                "ADMIN_API_KEY=",
                "INTERNAL_JOB_SECRET=",
                "INTERNAL_METRICS_AUTH_TOKEN=",
                "ENFORCEMENT_APPROVAL_TOKEN_SECRET=",
                "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
                "LLM_PROVIDER=groq",
                "GROQ_API_KEY=",
                "PAYSTACK_SECRET_KEY=",
                "PAYSTACK_PUBLIC_KEY=",
                "SENTRY_DSN=",
                "OTEL_EXPORTER_OTLP_ENDPOINT=",
                "TRUSTED_PROXY_CIDRS=[]",
            ]
        ),
    )

    report = generate_managed_runtime_env(
        template_path=template,
        output_path=output,
        report_path=report_path,
        environment="production",
    )
    values = _parse_env(output)
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert values["ENVIRONMENT"] == "production"
    assert values["DEBUG"] == "false"
    assert values["TESTING"] == "false"
    assert values["DB_SSL_MODE"] == "require"
    assert values["SAAS_STRICT_INTEGRATIONS"] == "true"
    assert values["EXPOSE_API_DOCUMENTATION_PUBLICLY"] == "false"
    assert values["API_URL"] == "https://REPLACE_WITH_API_DOMAIN"
    assert values["DATABASE_URL"].startswith("postgresql+asyncpg://REPLACE_WITH_DB_USER")
    assert values["AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN"].startswith(
        "arn:aws:iam::123456789012:role/REPLACE_WITH_"
    )
    assert values["PAYSTACK_SECRET_KEY"].startswith("sk_live_")
    assert values["PAYSTACK_PUBLIC_KEY"].startswith("pk_live_")
    assert values["GROQ_API_KEY"] == "REPLACE_WITH_GROQ_API_KEY"
    assert len(values["CSRF_SECRET_KEY"]) >= 64
    assert len(values["ADMIN_API_KEY"]) >= 64
    assert len(values["INTERNAL_JOB_SECRET"]) >= 64
    assert len(base64.b64decode(values["KDF_SALT"])) == 32
    assert len(values["ENCRYPTION_KEY"]) >= 32

    assert report["environment"] == "production"
    assert report_payload["validation_ready"] is False
    assert "API_URL" in report_payload["required_operator_input_keys"]
    assert "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN" in report_payload["required_operator_input_keys"]
    assert "GROQ_API_KEY" in report_payload["required_operator_input_keys"]
    assert "DATABASE_URL" in report_payload["unresolved_external_keys"]
    assert "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN" in report_payload["unresolved_external_keys"]
    assert "GROQ_API_KEY" in report_payload["unresolved_external_keys"]
    assert "SUPABASE_URL" in report_payload["declared_external_placeholders"]
    assert "SUPABASE_URL" in report_payload["declared_but_not_runtime_required"]
    assert "SUPABASE_URL" not in report_payload["runtime_validation_blockers"]
    assert "DATABASE_URL" in report_payload["runtime_validation_blockers"]
    assert report_payload["generated_internal_secret_keys"]


def test_generate_managed_runtime_env_respects_overrides_and_is_shell_source_safe(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "staging.env"
    report_path = tmp_path / "staging.report.json"
    _write(
        template,
        "\n".join(
            [
                "API_URL=",
                "FRONTEND_URL=",
                "CORS_ORIGINS=[]",
                "DATABASE_URL=",
                "REDIS_URL=",
                "SUPABASE_URL=",
                "SUPABASE_JWT_SECRET=",
                "LLM_PROVIDER=groq",
                "OPENAI_API_KEY=",
                "PAYSTACK_SECRET_KEY=",
                "PAYSTACK_PUBLIC_KEY=",
                "TRUSTED_PROXY_CIDRS=[]",
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "KDF_SALT=",
                "ADMIN_API_KEY=",
                "INTERNAL_JOB_SECRET=",
                "INTERNAL_METRICS_AUTH_TOKEN=",
                "ENFORCEMENT_APPROVAL_TOKEN_SECRET=",
                "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
            ]
        ),
    )

    generate_managed_runtime_env(
        template_path=template,
        output_path=output,
        report_path=report_path,
        environment="staging",
        api_url="https://api.staging.example.com",
        frontend_url="https://app.staging.example.com",
        database_url="postgresql+asyncpg://user:pass@db.example.com:5432/postgres",
        redis_url="redis://redis.example.com:6379/0",
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret="x" * 40,
        aws_assume_role_trust_principal_arn=(
            "arn:aws:iam::123456789012:role/ValdricsControlPlane"
        ),
        llm_provider="openai",
        llm_api_key="sk-test-openai-key",
        paystack_secret_key="sk_live_test_paystack_key",
        paystack_public_key="pk_live_test_paystack_key",
        sentry_dsn="https://key@example.com/1",
        otel_endpoint="https://otel.example.com:4317",
        trusted_proxy_cidrs=["203.0.113.10/32"],
    )

    sourced = subprocess.run(
        ["bash", "-lc", f"set -a && source {output} && printf '%s' \"$CORS_ORIGINS\""],
        check=True,
        capture_output=True,
        text=True,
    )
    values = _parse_env(output)
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert values["LLM_PROVIDER"] == "openai"
    assert values["OPENAI_API_KEY"] == "sk-test-openai-key"
    assert (
        values["AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN"]
        == "arn:aws:iam::123456789012:role/ValdricsControlPlane"
    )
    assert sourced.stdout == '["https://app.staging.example.com"]'
    assert values["TRUSTED_PROXY_CIDRS"] == '["203.0.113.10/32"]'
    assert "OPENAI_API_KEY" in report_payload["required_operator_input_keys"]
    assert "OPENAI_API_KEY" not in report_payload["unresolved_external_keys"]
    assert "DATABASE_URL" not in report_payload["unresolved_external_keys"]
    assert report_payload["runtime_validation_blockers"] == []


def test_generate_managed_runtime_env_can_satisfy_strict_runtime_validator(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "production.env"
    report_path = tmp_path / "production.report.json"
    _write(
        template,
        "\n".join(
            [
                "API_URL=",
                "FRONTEND_URL=",
                "CORS_ORIGINS=[]",
                "DATABASE_URL=",
                "REDIS_URL=",
                "SUPABASE_URL=",
                "SUPABASE_JWT_SECRET=",
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "KDF_SALT=",
                "ADMIN_API_KEY=",
                "INTERNAL_JOB_SECRET=",
                "INTERNAL_METRICS_AUTH_TOKEN=",
                "ENFORCEMENT_APPROVAL_TOKEN_SECRET=",
                "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
                "LLM_PROVIDER=groq",
                "GROQ_API_KEY=",
                "PAYSTACK_SECRET_KEY=",
                "PAYSTACK_PUBLIC_KEY=",
                "SENTRY_DSN=",
                "OTEL_EXPORTER_OTLP_ENDPOINT=",
                "TRUSTED_PROXY_CIDRS=[]",
            ]
        ),
    )

    generate_managed_runtime_env(
        template_path=template,
        output_path=output,
        report_path=report_path,
        environment="production",
        api_url="https://api.runtime.example",
        frontend_url="https://app.runtime.example",
        database_url="postgresql+asyncpg://postgres:postgres@db.example.com:5432/postgres",
        redis_url="redis://redis.example.com:6379/0",
        supabase_url="https://example.supabase.co",
        supabase_jwt_secret="x" * 40,
        aws_assume_role_trust_principal_arn=(
            "arn:aws:iam::123456789012:role/ValdricsControlPlane"
        ),
        llm_provider="groq",
        llm_api_key="testing-groq-runtime-key",
        paystack_secret_key="sk_live_runtime_paystack_key",
        paystack_public_key="pk_live_runtime_paystack_key",
        sentry_dsn="https://key@example.com/1",
        otel_endpoint="https://otel.example.com:4317",
        trusted_proxy_cidrs=["203.0.113.10/32"],
    )

    with patch.dict("os.environ", {}, clear=True):
        with patch(
            "app.shared.core.runtime_dependencies._module_available",
            return_value=True,
        ):
            monkeypatch.setattr(
                sys,
                "argv",
                [
                    "validate_runtime_env.py",
                    "--environment",
                    "production",
                    "--env-file",
                    str(output),
                ],
            )
            result = validate_runtime_env.main()

    assert result == 0
    assert "runtime_env_validation_passed environment=production testing=False" in capsys.readouterr().out
