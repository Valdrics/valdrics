from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.modules.governance.api.v1.settings.notification_diagnostics_ops import (
    to_notification_response,
    to_slack_policy_diagnostics,
)
from app.modules.governance.api.v1.settings.notification_settings_ops import (
    enforce_slack_integration_access,
)


class _CapturedHttpError(RuntimeError):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _raise_http_error(status_code: int, detail: str) -> None:
    raise _CapturedHttpError(status_code, detail)


def test_enforce_slack_integration_access_requires_growth_or_higher() -> None:
    with pytest.raises(_CapturedHttpError) as exc_info:
        enforce_slack_integration_access(
            data=SimpleNamespace(slack_enabled=True, slack_channel_override=None),
            current_tier=SimpleNamespace(value="starter"),
            normalize_tier_fn=lambda tier: tier,
            is_feature_enabled_fn=lambda tier, feature: False,
            slack_integration_feature=SimpleNamespace(value="slack_integration"),
            raise_http_exception_fn=_raise_http_error,
        )

    assert exc_info.value.status_code == 403
    assert "slack_integration" in exc_info.value.detail
    assert "starter" in exc_info.value.detail


def test_enforce_slack_integration_access_allows_growth_when_enabled() -> None:
    enforce_slack_integration_access(
        data=SimpleNamespace(slack_enabled=True, slack_channel_override="#alerts"),
        current_tier=SimpleNamespace(value="growth"),
        normalize_tier_fn=lambda tier: tier,
        is_feature_enabled_fn=lambda tier, feature: True,
        slack_integration_feature=SimpleNamespace(value="slack_integration"),
        raise_http_exception_fn=_raise_http_error,
    )


def test_to_notification_response_masks_slack_fields_when_tier_disallows_feature() -> None:
    response = to_notification_response(
        SimpleNamespace(
            slack_enabled=True,
            slack_channel_override="#alerts",
            jira_enabled=False,
            teams_enabled=False,
            digest_schedule="daily",
            digest_hour=9,
            digest_minute=0,
            alert_on_budget_warning=True,
            alert_on_budget_exceeded=True,
            alert_on_zombie_detected=True,
        ),
        slack_feature_allowed_by_tier=False,
    )

    assert response.slack_enabled is False
    assert response.slack_channel_override is None


def test_to_slack_policy_diagnostics_flags_tier_block_and_masks_readiness() -> None:
    diagnostics = to_slack_policy_diagnostics(
        remediation_settings=SimpleNamespace(
            policy_enabled=True,
            policy_violation_notify_slack=True,
        ),
        notification_settings=SimpleNamespace(
            slack_enabled=True,
            slack_channel_override="#alerts",
        ),
        feature_allowed_by_tier=False,
        has_bot_token=True,
        has_default_channel=True,
    )

    assert diagnostics.feature_allowed_by_tier is False
    assert diagnostics.ready is False
    assert "tier_missing_slack_integration_feature" in diagnostics.reasons
    assert diagnostics.selected_channel == "#alerts"
    assert diagnostics.channel_source == "tenant_override"
