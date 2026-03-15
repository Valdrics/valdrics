from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any


def _setting_value(data: Any, key: str, default: Any = None) -> Any:
    if isinstance(data, Mapping):
        return data.get(key, default)
    return getattr(data, key, default)


def enforce_incident_integrations_access(
    *,
    data: Any,
    current_tier: Any,
    normalize_tier_fn: Callable[[Any], Any],
    is_feature_enabled_fn: Callable[[Any, Any], bool],
    incident_integrations_feature: Any,
    raise_http_exception_fn: Callable[[int, str], None],
) -> None:
    needs_incident_integrations = bool(
        _setting_value(data, "teams_enabled", False)
        or _setting_value(data, "workflow_github_enabled", False)
        or _setting_value(data, "workflow_gitlab_enabled", False)
        or _setting_value(data, "workflow_webhook_enabled", False)
    )
    if not needs_incident_integrations:
        return

    tier = normalize_tier_fn(current_tier)
    if is_feature_enabled_fn(tier, incident_integrations_feature):
        return

    raise_http_exception_fn(
        403,
        (
            f"Feature '{incident_integrations_feature.value}' requires an upgrade. "
            f"Current tier: {tier.value}"
        ),
    )


def enforce_jira_integration_access(
    *,
    data: Any,
    current_tier: Any,
    normalize_tier_fn: Callable[[Any], Any],
    is_feature_enabled_fn: Callable[[Any, Any], bool],
    jira_integration_feature: Any,
    raise_http_exception_fn: Callable[[int, str], None],
) -> None:
    if not bool(_setting_value(data, "jira_enabled", False)):
        return

    tier = normalize_tier_fn(current_tier)
    if is_feature_enabled_fn(tier, jira_integration_feature):
        return

    raise_http_exception_fn(
        403,
        (
            f"Feature '{jira_integration_feature.value}' requires an upgrade. "
            f"Current tier: {tier.value}"
        ),
    )


def enforce_slack_integration_access(
    *,
    data: Any,
    current_tier: Any,
    normalize_tier_fn: Callable[[Any], Any],
    is_feature_enabled_fn: Callable[[Any, Any], bool],
    slack_integration_feature: Any,
    raise_http_exception_fn: Callable[[int, str], None],
) -> None:
    needs_slack_integration = bool(
        _setting_value(data, "slack_enabled", False)
        or _setting_value(data, "slack_channel_override", None)
    )
    if not needs_slack_integration:
        return

    tier = normalize_tier_fn(current_tier)
    if is_feature_enabled_fn(tier, slack_integration_feature):
        return

    raise_http_exception_fn(
        403,
        (
            f"Feature '{slack_integration_feature.value}' requires an upgrade. "
            f"Current tier: {tier.value}"
        ),
    )


def build_notification_settings_create_kwargs(
    *,
    data: Any,
    tenant_id: Any,
) -> dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "slack_enabled": data.slack_enabled,
        "slack_channel_override": data.slack_channel_override,
        "jira_enabled": data.jira_enabled,
        "jira_base_url": data.jira_base_url,
        "jira_email": str(data.jira_email) if data.jira_email else None,
        "jira_project_key": data.jira_project_key,
        "jira_issue_type": data.jira_issue_type,
        "jira_api_token": data.jira_api_token,
        "teams_enabled": data.teams_enabled,
        "teams_webhook_url": data.teams_webhook_url,
        "digest_schedule": data.digest_schedule,
        "digest_hour": data.digest_hour,
        "digest_minute": data.digest_minute,
        "alert_on_budget_warning": data.alert_on_budget_warning,
        "alert_on_budget_exceeded": data.alert_on_budget_exceeded,
        "alert_on_zombie_detected": data.alert_on_zombie_detected,
        "workflow_github_enabled": data.workflow_github_enabled,
        "workflow_github_owner": data.workflow_github_owner,
        "workflow_github_repo": data.workflow_github_repo,
        "workflow_github_workflow_id": data.workflow_github_workflow_id,
        "workflow_github_ref": data.workflow_github_ref,
        "workflow_github_token": data.workflow_github_token,
        "workflow_gitlab_enabled": data.workflow_gitlab_enabled,
        "workflow_gitlab_base_url": data.workflow_gitlab_base_url,
        "workflow_gitlab_project_id": data.workflow_gitlab_project_id,
        "workflow_gitlab_ref": data.workflow_gitlab_ref,
        "workflow_gitlab_trigger_token": data.workflow_gitlab_trigger_token,
        "workflow_webhook_enabled": data.workflow_webhook_enabled,
        "workflow_webhook_url": data.workflow_webhook_url,
        "workflow_webhook_bearer_token": data.workflow_webhook_bearer_token,
    }


def apply_notification_settings_update(
    *,
    settings: Any,
    updates: dict[str, Any],
) -> None:
    if "slack_enabled" in updates:
        settings.slack_enabled = updates["slack_enabled"]
    if "slack_channel_override" in updates:
        settings.slack_channel_override = updates["slack_channel_override"]
    if "jira_enabled" in updates:
        settings.jira_enabled = updates["jira_enabled"]
    if "jira_base_url" in updates:
        settings.jira_base_url = updates["jira_base_url"]
    if "jira_email" in updates:
        settings.jira_email = (
            str(updates["jira_email"]) if updates["jira_email"] else None
        )
    if "jira_project_key" in updates:
        settings.jira_project_key = updates["jira_project_key"]
    if "jira_issue_type" in updates:
        settings.jira_issue_type = updates["jira_issue_type"]
    if updates.get("jira_api_token"):
        settings.jira_api_token = updates["jira_api_token"]
    elif updates.get("clear_jira_api_token"):
        settings.jira_api_token = None
    elif not hasattr(settings, "jira_api_token"):
        settings.jira_api_token = None

    if "teams_enabled" in updates:
        settings.teams_enabled = updates["teams_enabled"]
    if "teams_webhook_url" in updates:
        settings.teams_webhook_url = updates["teams_webhook_url"]
    if updates.get("teams_webhook_url"):
        settings.teams_webhook_url = updates["teams_webhook_url"]
    elif updates.get("clear_teams_webhook_url"):
        settings.teams_webhook_url = None
    elif not hasattr(settings, "teams_webhook_url"):
        settings.teams_webhook_url = None

    if "digest_schedule" in updates:
        settings.digest_schedule = updates["digest_schedule"]
    if "digest_hour" in updates:
        settings.digest_hour = updates["digest_hour"]
    if "digest_minute" in updates:
        settings.digest_minute = updates["digest_minute"]
    if "alert_on_budget_warning" in updates:
        settings.alert_on_budget_warning = updates["alert_on_budget_warning"]
    if "alert_on_budget_exceeded" in updates:
        settings.alert_on_budget_exceeded = updates["alert_on_budget_exceeded"]
    if "alert_on_zombie_detected" in updates:
        settings.alert_on_zombie_detected = updates["alert_on_zombie_detected"]

    if "workflow_github_enabled" in updates:
        settings.workflow_github_enabled = updates["workflow_github_enabled"]
    if "workflow_github_owner" in updates:
        settings.workflow_github_owner = updates["workflow_github_owner"]
    if "workflow_github_repo" in updates:
        settings.workflow_github_repo = updates["workflow_github_repo"]
    if "workflow_github_workflow_id" in updates:
        settings.workflow_github_workflow_id = updates["workflow_github_workflow_id"]
    if "workflow_github_ref" in updates:
        settings.workflow_github_ref = updates["workflow_github_ref"]
    if updates.get("workflow_github_token"):
        settings.workflow_github_token = updates["workflow_github_token"]
    elif updates.get("clear_workflow_github_token"):
        settings.workflow_github_token = None

    if "workflow_gitlab_enabled" in updates:
        settings.workflow_gitlab_enabled = updates["workflow_gitlab_enabled"]
    if "workflow_gitlab_base_url" in updates:
        settings.workflow_gitlab_base_url = updates["workflow_gitlab_base_url"]
    if "workflow_gitlab_project_id" in updates:
        settings.workflow_gitlab_project_id = updates["workflow_gitlab_project_id"]
    if "workflow_gitlab_ref" in updates:
        settings.workflow_gitlab_ref = updates["workflow_gitlab_ref"]
    if updates.get("workflow_gitlab_trigger_token"):
        settings.workflow_gitlab_trigger_token = updates["workflow_gitlab_trigger_token"]
    elif updates.get("clear_workflow_gitlab_trigger_token"):
        settings.workflow_gitlab_trigger_token = None

    if "workflow_webhook_enabled" in updates:
        settings.workflow_webhook_enabled = updates["workflow_webhook_enabled"]
    if "workflow_webhook_url" in updates:
        settings.workflow_webhook_url = updates["workflow_webhook_url"]
    if updates.get("workflow_webhook_bearer_token"):
        settings.workflow_webhook_bearer_token = updates["workflow_webhook_bearer_token"]
    elif updates.get("clear_workflow_webhook_bearer_token"):
        settings.workflow_webhook_bearer_token = None


def validate_notification_settings_requirements(
    *,
    settings: Any,
    raise_http_exception_fn: Callable[[int, str], None],
) -> None:
    if settings.jira_enabled:
        from app.modules.notifications.domain.jira import validate_jira_base_url

        jira_requirements = [
            ("jira_base_url", settings.jira_base_url),
            ("jira_email", settings.jira_email),
            ("jira_project_key", settings.jira_project_key),
            ("jira_api_token", settings.jira_api_token),
        ]
        missing = [name for name, value in jira_requirements if not value]
        if missing:
            raise_http_exception_fn(
                422,
                "Jira is enabled but missing required fields: " + ", ".join(missing),
            )
        try:
            validate_jira_base_url(str(settings.jira_base_url))
        except ValueError as exc:
            raise_http_exception_fn(422, f"jira_base_url is invalid: {exc}")
    if settings.teams_enabled and not settings.teams_webhook_url:
        raise_http_exception_fn(
            422,
            "Teams is enabled but missing required field: teams_webhook_url",
        )
    if settings.workflow_github_enabled:
        github_requirements = [
            ("workflow_github_owner", settings.workflow_github_owner),
            ("workflow_github_repo", settings.workflow_github_repo),
            ("workflow_github_workflow_id", settings.workflow_github_workflow_id),
            ("workflow_github_token", settings.workflow_github_token),
        ]
        missing = [name for name, value in github_requirements if not value]
        if missing:
            raise_http_exception_fn(
                422,
                "GitHub workflow dispatch is enabled but missing required fields: "
                + ", ".join(missing),
            )

    if settings.workflow_gitlab_enabled:
        gitlab_requirements = [
            ("workflow_gitlab_base_url", settings.workflow_gitlab_base_url),
            ("workflow_gitlab_project_id", settings.workflow_gitlab_project_id),
            ("workflow_gitlab_trigger_token", settings.workflow_gitlab_trigger_token),
        ]
        missing = [name for name, value in gitlab_requirements if not value]
        if missing:
            raise_http_exception_fn(
                422,
                "GitLab workflow dispatch is enabled but missing required fields: "
                + ", ".join(missing),
            )

    if settings.workflow_webhook_enabled and not settings.workflow_webhook_url:
        raise_http_exception_fn(
            422,
            "Webhook workflow dispatch is enabled but missing required field: "
            "workflow_webhook_url",
        )


def build_notification_settings_audit_payload(settings: Any) -> dict[str, Any]:
    return {
        "slack_enabled": settings.slack_enabled,
        "digest": settings.digest_schedule,
        "slack_override": bool(settings.slack_channel_override),
        "jira_enabled": bool(getattr(settings, "jira_enabled", False)),
        "jira_base_url": bool(getattr(settings, "jira_base_url", None)),
        "jira_project_key": getattr(settings, "jira_project_key", None),
        "has_jira_api_token": bool(getattr(settings, "jira_api_token", None)),
        "teams_enabled": bool(getattr(settings, "teams_enabled", False)),
        "has_teams_webhook_url": bool(getattr(settings, "teams_webhook_url", None)),
        "workflow_github_enabled": bool(
            getattr(settings, "workflow_github_enabled", False)
        ),
        "workflow_has_github_token": bool(
            getattr(settings, "workflow_github_token", None)
        ),
        "workflow_gitlab_enabled": bool(
            getattr(settings, "workflow_gitlab_enabled", False)
        ),
        "workflow_has_gitlab_trigger_token": bool(
            getattr(settings, "workflow_gitlab_trigger_token", None)
        ),
        "workflow_webhook_enabled": bool(
            getattr(settings, "workflow_webhook_enabled", False)
        ),
        "workflow_has_webhook_bearer_token": bool(
            getattr(settings, "workflow_webhook_bearer_token", None)
        ),
    }
