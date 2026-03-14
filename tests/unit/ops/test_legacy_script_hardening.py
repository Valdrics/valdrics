from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.shared.db.base import Base
from scripts import (
    deactivate_aws,
    delete_cloudfront,
    dev_bearer_token,
    disable_cloudfront,
    emergency_disconnect,
    purge_simulation_data,
    rls_tooling,
    update_exchange_rates,
)


@pytest.mark.parametrize(
    "module",
    [
        deactivate_aws,
        emergency_disconnect,
        disable_cloudfront,
        delete_cloudfront,
        purge_simulation_data,
    ],
)
def test_legacy_destructive_scripts_accept_explicit_confirmation(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv(module.NONINTERACTIVE_BYPASS_ENV, "true")  # type: ignore[attr-defined]

    module._validate_request(  # type: ignore[attr-defined]
        force=True,
        phrase=module.CONFIRM_PHRASE,  # type: ignore[attr-defined]
        confirm_environment="development",
        no_prompt=True,
        operator="ops@valdrics.io",
        reason="Emergency maintenance during an approved drill.",
    )


@pytest.mark.parametrize(
    "module",
    [
        deactivate_aws,
        emergency_disconnect,
        disable_cloudfront,
        delete_cloudfront,
        purge_simulation_data,
    ],
)
def test_legacy_destructive_scripts_require_environment_match(
    monkeypatch: pytest.MonkeyPatch,
    module: object,
) -> None:
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv(module.NONINTERACTIVE_BYPASS_ENV, "true")  # type: ignore[attr-defined]

    with pytest.raises(RuntimeError, match="confirm-environment"):
        module._validate_request(  # type: ignore[attr-defined]
            force=True,
            phrase=module.CONFIRM_PHRASE,  # type: ignore[attr-defined]
            confirm_environment="staging",
            no_prompt=True,
            operator="ops@valdrics.io",
            reason="Emergency maintenance during an approved drill.",
        )


def test_dev_bearer_token_is_retired(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = dev_bearer_token.main()

    assert exit_code == 2
    assert "retired" in capsys.readouterr().err.lower()


def test_collect_purge_targets_covers_tenant_and_user_scoped_tables() -> None:
    targets = purge_simulation_data.collect_purge_targets(Base.metadata)
    table_names = {target.table_name for target in targets}

    assert {"license_connections", "audit_logs", "system_audit_logs", "remediation_requests"} <= table_names


def test_rls_candidate_filter_excludes_rls_exempt_tables() -> None:
    filtered = rls_tooling.filter_rls_candidate_tables(
        [
            "users",
            "tenant_identity_settings",
            "tenant_subscriptions",
            "background_jobs",
            "cloud_accounts",
        ]
    )

    assert filtered == ("cloud_accounts",)


def test_purge_main_requires_explicit_tenant_ids() -> None:
    exit_code = purge_simulation_data.main([])
    assert exit_code == 2


def test_disable_cloudfront_main_returns_failure_when_action_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(disable_cloudfront, "disable_cloudfront", lambda **_: False)
    assert disable_cloudfront.main(["--distribution-id", "dist-123"]) == 1


def test_delete_cloudfront_main_returns_failure_when_action_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(delete_cloudfront, "delete_cloudfront", lambda **_: False)
    assert delete_cloudfront.main(["--distribution-id", "dist-123"]) == 1


def test_update_exchange_rates_main_returns_failure_on_runtime_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        update_exchange_rates,
        "update_exchange_rates",
        AsyncMock(side_effect=RuntimeError("boom")),
    )
    assert update_exchange_rates.main() == 1
