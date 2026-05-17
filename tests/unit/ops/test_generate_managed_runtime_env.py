from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch

import pytest

import scripts.generate_managed_runtime_env as managed_runtime_env_generator
from scripts.generate_managed_runtime_env import generate_managed_runtime_env
from scripts import validate_runtime_env


@pytest.fixture(autouse=True)
def _patch_supported_python_runtime() -> None:
    with patch(
        "app.shared.core.runtime_dependencies._is_supported_python_runtime",
        return_value=True,
    ):
        yield


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


_GCP_RUNTIME_ARGS = {
    "gcp_project_id": "valdrics-prod",
    "gcp_region": "us-central1",
    "gcp_cloud_tasks_queue": "valdrics-managed-work",
    "gcp_cloud_tasks_invoker_service_account_email": (
        "tasks-invoker@valdrics-prod.iam.gserviceaccount.com"
    ),
    "gcp_cloud_run_service_name": "valdrics-api",
    "gcp_cloud_run_batch_job_name": "valdrics-batch",
    "gcp_internal_allowed_service_accounts": [
        "tasks-invoker@valdrics-prod.iam.gserviceaccount.com",
        "scheduler-invoker@valdrics-prod.iam.gserviceaccount.com",
    ],
}


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
                "SUPABASE_URL=",
                "SUPABASE_ANON_KEY=",
                "SUPABASE_JWT_SECRET=",
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "KDF_SALT=",
                "ADMIN_API_KEY=",
                "INTERNAL_METRICS_AUTH_TOKEN=",
                "ENFORCEMENT_APPROVAL_TOKEN_SECRET=",
                "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
                "LLM_PROVIDER=groq",
                "GROQ_API_KEY=",
                "PAYSTACK_SECRET_KEY=",
                "PAYSTACK_PUBLIC_KEY=",
                "PAYSTACK_ACTIVATION_PENDING=false",
                "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY=NGN",
                "PAYSTACK_ENABLE_USD_CHECKOUT=false",
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
    assert values["PLATFORM_RUNTIME_PROFILE"] == "gcp"
    assert values["OBSERVABILITY_BACKEND"] == "gcp"
    assert values["PUBLIC_API_RATE_LIMITING_BACKEND"] == "cloudflare"
    assert values["RATELIMIT_ENABLED"] == "false"
    assert "WEB_CONCURRENCY" not in values
    assert values["DB_SSL_MODE"] == "require"
    assert values["SAAS_STRICT_INTEGRATIONS"] == "true"
    assert values["EXPOSE_API_DOCUMENTATION_PUBLICLY"] == "false"
    assert values["API_URL"] == "https://REPLACE_WITH_API_DOMAIN"
    assert values["DATABASE_URL"].startswith(
        "postgresql+asyncpg://REPLACE_WITH_DB_USER"
    )
    assert "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN" not in values
    assert values["PAYSTACK_ACTIVATION_PENDING"] == "true"
    assert values["PAYSTACK_SECRET_KEY"] == ""
    assert values["PAYSTACK_PUBLIC_KEY"] == ""
    assert values["GROQ_API_KEY"] == "REPLACE_WITH_GROQ_API_KEY"
    assert "SENTRY_DSN" not in values
    assert "OTEL_EXPORTER_OTLP_ENDPOINT" not in values
    assert len(values["CSRF_SECRET_KEY"]) >= 64
    assert len(values["ADMIN_API_KEY"]) >= 64
    assert len(base64.b64decode(values["KDF_SALT"])) == 32
    assert len(values["ENCRYPTION_KEY"]) >= 32

    assert report["environment"] == "production"
    assert (
        report_payload["resolved_public_runtime_values"]["API_URL"]
        == "https://REPLACE_WITH_API_DOMAIN"
    )
    assert (
        report_payload["resolved_public_runtime_values"]["FRONTEND_URL"]
        == "https://REPLACE_WITH_FRONTEND_DOMAIN"
    )
    assert report_payload["validation_ready"] is False
    assert "API_URL" in report_payload["required_operator_input_keys"]
    assert "GCP_PROJECT_ID" in report_payload["required_operator_input_keys"]
    assert "GROQ_API_KEY" in report_payload["required_operator_input_keys"]
    assert "DATABASE_URL" in report_payload["unresolved_external_keys"]
    assert "GCP_PROJECT_ID" in report_payload["unresolved_external_keys"]
    assert "GROQ_API_KEY" in report_payload["unresolved_external_keys"]
    assert "SUPABASE_URL" in report_payload["declared_external_placeholders"]
    assert "SUPABASE_ANON_KEY" in report_payload["declared_external_placeholders"]
    assert "SUPABASE_URL" in report_payload["declared_but_not_runtime_required"]
    assert "SUPABASE_ANON_KEY" in report_payload["declared_but_not_runtime_required"]
    assert "SUPABASE_URL" not in report_payload["runtime_validation_blockers"]
    assert "SUPABASE_ANON_KEY" not in report_payload["runtime_validation_blockers"]
    assert "DATABASE_URL" in report_payload["runtime_validation_blockers"]
    assert "GCP_PROJECT_ID" in report_payload["runtime_validation_blockers"]
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
                "SUPABASE_URL=",
                "SUPABASE_ANON_KEY=",
                "SUPABASE_JWT_SECRET=",
                "LLM_PROVIDER=groq",
                "OPENAI_API_KEY=",
                "PAYSTACK_SECRET_KEY=",
                "PAYSTACK_PUBLIC_KEY=",
                "PAYSTACK_ACTIVATION_PENDING=false",
                "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY=NGN",
                "PAYSTACK_ENABLE_USD_CHECKOUT=false",
                "TRUSTED_PROXY_CIDRS=[]",
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "KDF_SALT=",
                "ADMIN_API_KEY=",
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
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-key-for-dashboard",
        supabase_jwt_secret="x" * 40,
        llm_provider="openai",
        llm_api_key="sk-test-openai-key",
        paystack_secret_key="sk_live_test_paystack_key",
        paystack_public_key="pk_live_test_paystack_key",
        trusted_proxy_cidrs=["203.0.113.10/32"],
        **_GCP_RUNTIME_ARGS,
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
    assert values["PLATFORM_RUNTIME_PROFILE"] == "gcp"
    assert values["OBSERVABILITY_BACKEND"] == "gcp"
    assert "WEB_CONCURRENCY" not in values
    assert values["PUBLIC_API_RATE_LIMITING_BACKEND"] == "cloudflare"
    assert values["RATELIMIT_ENABLED"] == "false"
    assert values["GCP_PROJECT_ID"] == "valdrics-prod"
    assert values["GCP_REGION"] == "us-central1"
    assert values["GCP_CLOUD_TASKS_QUEUE"] == "valdrics-managed-work"
    assert (
        values["GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL"]
        == "tasks-invoker@valdrics-prod.iam.gserviceaccount.com"
    )
    assert values["GCP_CLOUD_RUN_SERVICE_NAME"] == "valdrics-api"
    assert values["GCP_CLOUD_RUN_BATCH_JOB_NAME"] == "valdrics-batch"
    assert values["GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS"] == (
        '["tasks-invoker@valdrics-prod.iam.gserviceaccount.com",'
        '"scheduler-invoker@valdrics-prod.iam.gserviceaccount.com"]'
    )
    assert (
        report_payload["resolved_public_runtime_values"]["FRONTEND_URL"]
        == "https://app.staging.example.com"
    )
    assert (
        report_payload["resolved_public_runtime_values"]["API_URL"]
        == "https://api.staging.example.com"
    )
    assert values["SUPABASE_ANON_KEY"] == "anon-key-for-dashboard"
    assert values["OPENAI_API_KEY"] == "sk-test-openai-key"
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
                "SUPABASE_URL=",
                "SUPABASE_ANON_KEY=",
                "SUPABASE_JWT_SECRET=",
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "KDF_SALT=",
                "ADMIN_API_KEY=",
                "INTERNAL_METRICS_AUTH_TOKEN=",
                "ENFORCEMENT_APPROVAL_TOKEN_SECRET=",
                "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
                "LLM_PROVIDER=groq",
                "GROQ_API_KEY=",
                "PAYSTACK_SECRET_KEY=",
                "PAYSTACK_PUBLIC_KEY=",
                "PAYSTACK_ACTIVATION_PENDING=false",
                "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY=NGN",
                "PAYSTACK_ENABLE_USD_CHECKOUT=false",
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
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-key-for-dashboard",
        supabase_jwt_secret="x" * 40,
        llm_provider="groq",
        llm_api_key="testing-groq-runtime-key",
        paystack_secret_key="sk_live_runtime_paystack_key",
        paystack_public_key="pk_live_runtime_paystack_key",
        trusted_proxy_cidrs=["203.0.113.10/32"],
        **_GCP_RUNTIME_ARGS,
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
    assert (
        "runtime_env_validation_passed environment=production testing=False"
        in capsys.readouterr().out
    )


def test_generate_managed_runtime_env_preserves_existing_values_on_regeneration(
    tmp_path: Path,
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
                "SUPABASE_URL=",
                "SUPABASE_ANON_KEY=",
                "SUPABASE_JWT_SECRET=",
                "CSRF_SECRET_KEY=",
                "ENCRYPTION_KEY=",
                "KDF_SALT=",
                "ADMIN_API_KEY=",
                "INTERNAL_METRICS_AUTH_TOKEN=",
                "ENFORCEMENT_APPROVAL_TOKEN_SECRET=",
                "ENFORCEMENT_EXPORT_SIGNING_SECRET=",
                "LLM_PROVIDER=groq",
                "OPENAI_API_KEY=",
                "PAYSTACK_SECRET_KEY=",
                "PAYSTACK_PUBLIC_KEY=",
                "PAYSTACK_ACTIVATION_PENDING=false",
                "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY=NGN",
                "PAYSTACK_ENABLE_USD_CHECKOUT=false",
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
        supabase_url="https://example.supabase.co",
        supabase_anon_key="anon-key-for-dashboard",
        supabase_jwt_secret="x" * 40,
        llm_provider="openai",
        llm_api_key="sk-test-openai-key",
        paystack_secret_key="sk_live_test_paystack_key",
        paystack_public_key="pk_live_test_paystack_key",
        trusted_proxy_cidrs=["203.0.113.10/32"],
        **_GCP_RUNTIME_ARGS,
    )

    first_values = _parse_env(output)
    first_internal = {
        key: first_values[key]
        for key in (
            "CSRF_SECRET_KEY",
            "ENCRYPTION_KEY",
            "KDF_SALT",
            "ADMIN_API_KEY",
            "INTERNAL_METRICS_AUTH_TOKEN",
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET",
            "ENFORCEMENT_EXPORT_SIGNING_SECRET",
        )
    }

    generate_managed_runtime_env(
        template_path=template,
        output_path=output,
        report_path=report_path,
        environment="production",
    )

    second_values = _parse_env(output)
    second_report = json.loads(report_path.read_text(encoding="utf-8"))

    assert second_values["API_URL"] == "https://api.runtime.example"
    assert second_values["FRONTEND_URL"] == "https://app.runtime.example"
    assert second_values["PLATFORM_RUNTIME_PROFILE"] == "gcp"
    assert second_values["OBSERVABILITY_BACKEND"] == "gcp"
    assert second_values["PUBLIC_API_RATE_LIMITING_BACKEND"] == "cloudflare"
    assert second_values["RATELIMIT_ENABLED"] == "false"
    assert second_values["GCP_PROJECT_ID"] == "valdrics-prod"
    assert second_values["GCP_REGION"] == "us-central1"
    assert second_values["SUPABASE_ANON_KEY"] == "anon-key-for-dashboard"
    assert second_values["LLM_PROVIDER"] == "openai"
    assert second_values["OPENAI_API_KEY"] == "sk-test-openai-key"
    assert second_values["TRUSTED_PROXY_CIDRS"] == '["203.0.113.10/32"]'
    for key, value in first_internal.items():
        assert second_values[key] == value
    assert second_report["runtime_validation_blockers"] == []


def test_generate_managed_runtime_env_rejects_shared_output_and_report_path(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    combined = tmp_path / "staging.env"
    _write(template, "API_URL=\nFRONTEND_URL=\nDATABASE_URL=\n")

    with pytest.raises(
        ValueError,
        match="template_path, output_path, and report_path must be different files",
    ):
        generate_managed_runtime_env(
            template_path=template,
            output_path=combined,
            report_path=combined,
            environment="staging",
        )


def test_generate_managed_runtime_env_rejects_invalid_trusted_proxy_cidrs(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "staging.env"
    report_path = tmp_path / "staging.report.json"
    _write(template, "API_URL=\nFRONTEND_URL=\nDATABASE_URL=\nTRUSTED_PROXY_CIDRS=[]\n")

    with pytest.raises(
        ValueError,
        match="trusted_proxy_cidrs contains invalid CIDR: not-a-cidr",
    ):
        generate_managed_runtime_env(
            template_path=template,
            output_path=output,
            report_path=report_path,
            environment="staging",
            trusted_proxy_cidrs=["not-a-cidr"],
        )


def test_generate_managed_runtime_env_rejects_non_https_public_urls(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "staging.env"
    report_path = tmp_path / "staging.report.json"
    _write(template, "API_URL=\nFRONTEND_URL=\nDATABASE_URL=\nTRUSTED_PROXY_CIDRS=[]\n")

    with pytest.raises(
        ValueError,
        match="API_URL must use an explicit https:// URL in staging/production.",
    ):
        generate_managed_runtime_env(
            template_path=template,
            output_path=output,
            report_path=report_path,
            environment="staging",
            api_url="http://api.staging.example.com",
        )


@pytest.mark.parametrize(
    ("field_name", "kwargs", "message"),
    [
        (
            "PAYSTACK_SECRET_KEY",
            {"paystack_secret_key": "sk_test_not_live"},
            "PAYSTACK_SECRET_KEY must be a live key \\(sk_live_\\.\\.\\.\\) in production.",
        ),
        (
            "PAYSTACK_PUBLIC_KEY",
            {"paystack_public_key": "pk_test_not_live"},
            "PAYSTACK_PUBLIC_KEY must be a live key \\(pk_live_\\.\\.\\.\\) in production.",
        ),
    ],
)
def test_generate_managed_runtime_env_rejects_invalid_production_paystack_keys(
    tmp_path: Path,
    field_name: str,
    kwargs: dict[str, str],
    message: str,
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "production.env"
    report_path = tmp_path / "production.report.json"
    _write(template, "API_URL=\nFRONTEND_URL=\nDATABASE_URL=\nTRUSTED_PROXY_CIDRS=[]\n")
    _write(output, "PAYSTACK_ACTIVATION_PENDING=false\n")

    with pytest.raises(ValueError, match=message):
        generate_managed_runtime_env(
            template_path=template,
            output_path=output,
            report_path=report_path,
            environment="production",
            **kwargs,
        )


def test_generate_managed_runtime_env_infers_pending_paystack_activation(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "production.env"
    report_path = tmp_path / "production.report.json"
    _write(
        template,
        "\n".join(
            [
                "PAYSTACK_SECRET_KEY=",
                "PAYSTACK_PUBLIC_KEY=",
                "PAYSTACK_ACTIVATION_PENDING=false",
                "TRUSTED_PROXY_CIDRS=[]",
            ]
        ),
    )

    report = generate_managed_runtime_env(
        template_path=template,
        output_path=output,
        report_path=report_path,
        environment="production",
        paystack_secret_key="sk_test_activation_pending",
        paystack_public_key="pk_test_activation_pending",
    )
    values = _parse_env(output)

    assert values["PAYSTACK_ACTIVATION_PENDING"] == "true"
    assert values["PAYSTACK_SECRET_KEY"] == ""
    assert values["PAYSTACK_PUBLIC_KEY"] == ""
    assert "PAYSTACK_SECRET_KEY" not in report["runtime_validation_blockers"]
    assert "PAYSTACK_PUBLIC_KEY" not in report["runtime_validation_blockers"]


def test_generate_managed_runtime_env_ignores_provider_specific_aws_contract_keys(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "production.env"
    report_path = tmp_path / "production.report.json"
    _write(
        template,
        "API_URL=\nFRONTEND_URL=\nDATABASE_URL=\nAWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN=\nTRUSTED_PROXY_CIDRS=[]\n",
    )

    generate_managed_runtime_env(
        template_path=template,
        output_path=output,
        report_path=report_path,
        environment="production",
    )

    values = _parse_env(output)
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))

    assert values["AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN"] == ""
    assert (
        "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN"
        not in report_payload["required_operator_input_keys"]
    )
    assert (
        "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN"
        not in report_payload["runtime_validation_blockers"]
    )


def test_generate_managed_runtime_env_does_not_leave_outputs_when_report_staging_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    template = tmp_path / ".env.example"
    output = tmp_path / "staging.env"
    report_path = tmp_path / "staging.report.json"
    _write(template, "API_URL=\nFRONTEND_URL=\nDATABASE_URL=\n")
    original_stage = managed_runtime_env_generator._stage_text_file

    def _failing_stage(path: Path, content: str) -> Path:
        if path == report_path:
            raise RuntimeError("report staging failed")
        return original_stage(path, content)

    monkeypatch.setattr(
        managed_runtime_env_generator,
        "_stage_text_file",
        _failing_stage,
    )

    with pytest.raises(RuntimeError, match="report staging failed"):
        generate_managed_runtime_env(
            template_path=template,
            output_path=output,
            report_path=report_path,
            environment="staging",
        )

    assert not output.exists()
    assert not report_path.exists()


def test_generate_managed_runtime_env_rejects_template_path_collisions(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    report_path = tmp_path / "staging.report.json"
    _write(template, "API_URL=\nFRONTEND_URL=\nDATABASE_URL=\n")

    with pytest.raises(
        ValueError,
        match="template_path, output_path, and report_path must be different files",
    ):
        generate_managed_runtime_env(
            template_path=template,
            output_path=template,
            report_path=report_path,
            environment="staging",
        )


def test_generate_managed_runtime_env_rejects_non_file_template_path(
    tmp_path: Path,
) -> None:
    template_dir = tmp_path / "template-dir"
    template_dir.mkdir()
    output = tmp_path / "staging.env"
    report_path = tmp_path / "staging.report.json"

    with pytest.raises(ValueError, match="template_path must be a file"):
        generate_managed_runtime_env(
            template_path=template_dir,
            output_path=output,
            report_path=report_path,
            environment="staging",
        )


@pytest.mark.parametrize(
    ("field_name", "relative_target"),
    [
        ("output_path", ".env.example"),
        ("report_path", "scripts/validate_runtime_env.py"),
        ("output_path", "docs/ops/evidence/finance_guardrails_TEMPLATE.json"),
        ("report_path", "docs/ops/key-rotation-drill-2026-02-27.md"),
        ("output_path", "docs/ops/evidence/README.md"),
    ],
)
def test_generate_managed_runtime_env_rejects_protected_output_targets(
    tmp_path: Path,
    field_name: str,
    relative_target: str,
) -> None:
    repo_root = Path(__file__).resolve().parents[3]
    template = tmp_path / ".env.example"
    _write(template, "API_URL=\nFRONTEND_URL=\nDATABASE_URL=\n")
    output = tmp_path / "staging.env"
    report_path = tmp_path / "staging.report.json"
    kwargs = {
        "template_path": template,
        "output_path": output,
        "report_path": report_path,
        "environment": "staging",
    }
    kwargs[field_name] = repo_root / relative_target

    with pytest.raises(
        ValueError,
        match=rf"{field_name} must not overwrite runtime source, template, or validator files",
    ):
        generate_managed_runtime_env(**kwargs)


@pytest.mark.parametrize("field_name", ["output_path", "report_path"])
def test_generate_managed_runtime_env_rejects_directory_output_targets(
    tmp_path: Path,
    field_name: str,
) -> None:
    template = tmp_path / ".env.example"
    _write(template, "API_URL=\nFRONTEND_URL=\nDATABASE_URL=\n")
    output = tmp_path / "staging.env"
    report_path = tmp_path / "staging.report.json"
    bad_target = tmp_path / field_name
    bad_target.mkdir()

    kwargs = {
        "template_path": template,
        "output_path": output,
        "report_path": report_path,
        "environment": "staging",
    }
    kwargs[field_name] = bad_target

    with pytest.raises(ValueError, match=rf"{field_name} must be a file path"):
        generate_managed_runtime_env(**kwargs)


@pytest.mark.parametrize("field_name", ["output_path", "report_path"])
def test_generate_managed_runtime_env_rejects_blocked_parent_dirs(
    tmp_path: Path,
    field_name: str,
) -> None:
    template = tmp_path / ".env.example"
    _write(template, "API_URL=\nFRONTEND_URL=\nDATABASE_URL=\n")
    blocked_parent = tmp_path / f"blocked-{field_name}"
    blocked_parent.write_text("not-a-directory", encoding="utf-8")
    safe_parent = tmp_path / "safe-parent"
    output = safe_parent / "staging.env"
    report_path = safe_parent / "staging.report.json"

    kwargs = {
        "template_path": template,
        "output_path": output,
        "report_path": report_path,
        "environment": "staging",
    }
    kwargs[field_name] = blocked_parent / Path(kwargs[field_name]).name

    with pytest.raises(
        ValueError, match=rf"{field_name} parent must be a directory path"
    ):
        generate_managed_runtime_env(**kwargs)


def test_main_resolves_default_paths_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_generate_managed_runtime_env(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        output_path = kwargs["output_path"]
        return {
            "environment": kwargs["environment"],
            "output_path": output_path.as_posix(),
            "validation_ready": False,
            "runtime_validation_blockers": [],
            "declared_external_placeholders": [],
        }

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        managed_runtime_env_generator,
        "generate_managed_runtime_env",
        _fake_generate_managed_runtime_env,
    )

    assert managed_runtime_env_generator.main(["--environment", "staging"]) == 0
    assert (
        captured["template_path"]
        == (
            managed_runtime_env_generator._repo_root()
            / managed_runtime_env_generator.DEFAULT_TEMPLATE_PATH
        ).resolve()
    )
    assert (
        captured["output_path"]
        == (
            managed_runtime_env_generator._repo_root()
            / managed_runtime_env_generator.DEFAULT_OUTPUT_DIR
            / "staging.env"
        ).resolve()
    )
    assert (
        captured["report_path"]
        == (
            managed_runtime_env_generator._repo_root()
            / managed_runtime_env_generator.DEFAULT_OUTPUT_DIR
            / "staging.report.json"
        ).resolve()
    )


def test_main_resolves_explicit_relative_paths_from_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    captured: dict[str, object] = {}

    def _fake_generate_managed_runtime_env(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {
            "environment": kwargs["environment"],
            "output_path": kwargs["output_path"].as_posix(),  # type: ignore[index]
            "validation_ready": False,
            "runtime_validation_blockers": [],
            "declared_external_placeholders": [],
        }

    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(managed_runtime_env_generator, "_repo_root", lambda: repo_root)
    monkeypatch.setattr(
        managed_runtime_env_generator,
        "generate_managed_runtime_env",
        _fake_generate_managed_runtime_env,
    )

    assert (
        managed_runtime_env_generator.main(
            [
                "--environment",
                "staging",
                "--template-path",
                ".env.example",
                "--output-path",
                ".runtime/staging.env",
                "--report-path",
                ".runtime/staging.report.json",
            ]
        )
        == 0
    )
    assert captured["template_path"] == (repo_root / ".env.example").resolve()
    assert captured["output_path"] == (repo_root / ".runtime" / "staging.env").resolve()
    assert (
        captured["report_path"]
        == (repo_root / ".runtime" / "staging.report.json").resolve()
    )


def test_main_rejects_relative_paths_that_escape_repo_root(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    outside_cwd = tmp_path / "outside"
    outside_cwd.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(outside_cwd)
    monkeypatch.setattr(managed_runtime_env_generator, "_repo_root", lambda: repo_root)

    with pytest.raises(
        ValueError, match="output_path must stay within repo root when relative"
    ):
        managed_runtime_env_generator.main(
            [
                "--environment",
                "staging",
                "--template-path",
                ".env.example",
                "--output-path",
                "../escape/staging.env",
            ]
        )
