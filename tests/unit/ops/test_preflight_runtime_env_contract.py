from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.preflight_runtime_env_contract import (
    main,
    preflight_runtime_env_contract,
)


def _write_template(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "API_URL=",
                "FRONTEND_URL=",
                "DATABASE_URL=",
                "SUPABASE_JWT_SECRET=",
                "PAYSTACK_SECRET_KEY=",
                "PAYSTACK_PUBLIC_KEY=",
                "PAYSTACK_ACTIVATION_PENDING=false",
                "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY=NGN",
                "PAYSTACK_ENABLE_USD_CHECKOUT=false",
                "GROQ_API_KEY=",
                "TRUSTED_PROXY_CIDRS=[]",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _plain_payload() -> dict[str, str]:
    return {
        "ENVIRONMENT": "production",
        "API_URL": "https://api.example.com",
        "FRONTEND_URL": "https://app.example.com",
        "GCP_PROJECT_ID": "valdrics-production-001",
        "GCP_REGION": "europe-west2",
        "GCP_CLOUD_TASKS_QUEUE": "valdrics-managed-work",
        "GCP_CLOUD_TASKS_INVOKER_SERVICE_ACCOUNT_EMAIL": (
            "production-valdrics-internal@valdrics-production-001.iam.gserviceaccount.com"
        ),
        "GCP_CLOUD_RUN_SERVICE_NAME": "valdrics-api",
        "GCP_CLOUD_RUN_BATCH_JOB_NAME": "valdrics-batch",
        "GCP_INTERNAL_ALLOWED_SERVICE_ACCOUNTS": (
            '["production-valdrics-internal@valdrics-production-001.iam.gserviceaccount.com",'
            '"production-valdrics-scheduler@valdrics-production-001.iam.gserviceaccount.com"]'
        ),
        "TRUSTED_PROXY_CIDRS": '["173.245.48.0/20"]',
        "SUPABASE_URL": "https://example.supabase.co",
        "SUPABASE_ANON_KEY": "sb_publishable_example",
        "LLM_PROVIDER": "groq",
    }


def _secret_payload() -> dict[str, str]:
    return {
        "DATABASE_URL": "postgresql+asyncpg://user:pass@db.example.com:5432/postgres",
        "SUPABASE_JWT_SECRET": "supabase-jwt-secret-minimum-32-chars",
        "PAYSTACK_SECRET_KEY": "sk_live_paystack_secret",
        "PAYSTACK_PUBLIC_KEY": "pk_live_paystack_public",
        "GROQ_API_KEY": "gsk_live_provider_key",
    }


def test_preflight_runtime_env_contract_accepts_release_ready_payload(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    _write_template(template)

    report = preflight_runtime_env_contract(
        environment="production",
        plain=_plain_payload(),
        secret=_secret_payload(),
        template_path=template,
    )

    assert report["validation_ready"] is True
    assert report["runtime_validation_blockers"] == []


def test_preflight_runtime_env_contract_rejects_invalid_production_paystack_key(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    _write_template(template)
    plain = _plain_payload()
    plain["PAYSTACK_ACTIVATION_PENDING"] = "false"
    secret = _secret_payload()
    secret["PAYSTACK_SECRET_KEY"] = "sk_test_not_live"

    with pytest.raises(ValueError, match="PAYSTACK_SECRET_KEY must be a live key"):
        preflight_runtime_env_contract(
            environment="production",
            plain=plain,
            secret=secret,
            template_path=template,
        )


def test_preflight_runtime_env_contract_accepts_pending_paystack_activation(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    _write_template(template)
    plain = _plain_payload()
    plain["PAYSTACK_ACTIVATION_PENDING"] = "true"
    secret = _secret_payload()
    secret["PAYSTACK_SECRET_KEY"] = "sk_test_activation_pending"
    secret["PAYSTACK_PUBLIC_KEY"] = "pk_test_activation_pending"

    report = preflight_runtime_env_contract(
        environment="production",
        plain=plain,
        secret=secret,
        template_path=template,
    )

    assert report["validation_ready"] is True
    assert report["runtime_validation_blockers"] == []
    assert "PAYSTACK_SECRET_KEY" not in report["required_operator_input_keys"]
    assert "PAYSTACK_PUBLIC_KEY" not in report["required_operator_input_keys"]


def test_preflight_runtime_env_contract_rejects_unresolved_secret_inputs(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    _write_template(template)

    with pytest.raises(ValueError, match="managed runtime contract has unresolved"):
        preflight_runtime_env_contract(
            environment="production",
            plain=_plain_payload(),
            secret={},
            template_path=template,
        )


def test_preflight_runtime_env_contract_rejects_classification_errors(
    tmp_path: Path,
) -> None:
    template = tmp_path / ".env.example"
    _write_template(template)
    plain = _plain_payload()
    plain["DATABASE_URL"] = "postgresql+asyncpg://user:pass@db.example.com/postgres"
    secret = _secret_payload()
    secret.pop("DATABASE_URL")

    with pytest.raises(ValueError, match="secret-classified keys"):
        preflight_runtime_env_contract(
            environment="production",
            plain=plain,
            secret=secret,
            template_path=template,
        )


def test_preflight_runtime_env_contract_cli_uses_github_annotation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    template = tmp_path / ".env.example"
    _write_template(template)
    plain = _plain_payload()
    plain["PAYSTACK_ACTIVATION_PENDING"] = "false"
    secret = _secret_payload()
    secret["PAYSTACK_SECRET_KEY"] = "sk_test_not_live"
    monkeypatch.setenv("RUNTIME_PLAIN_ENV_JSON", json.dumps(plain))
    monkeypatch.setenv("RUNTIME_SECRET_ENV_JSON", json.dumps(secret))

    exit_code = main(
        [
            "--environment",
            "production",
            "--template-path",
            template.as_posix(),
        ]
    )

    assert exit_code == 1
    assert (
        "::error title=Managed runtime contract preflight failed::"
        in capsys.readouterr().out
    )
