from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timezone

from fastapi import status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.modules.governance.api.v1.settings.notifications_models import (
    IntegrationAcceptanceResult,
)
from app.modules.governance.domain.security.audit_log import (
    AuditEventType,
    AuditLogger,
)
from app.shared.core.auth import CurrentUser
from app.shared.core.pricing import FeatureFlag, is_feature_enabled, normalize_tier

logger = structlog.get_logger()

NOTIFICATION_CONNECTIVITY_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    ValueError,
    TypeError,
    AttributeError,
    KeyError,
)


def integration_event_type(channel: str) -> AuditEventType:
    normalized = channel.strip().lower()
    if normalized == "slack":
        return AuditEventType.INTEGRATION_TEST_SLACK
    if normalized == "jira":
        return AuditEventType.INTEGRATION_TEST_JIRA
    if normalized == "teams":
        return AuditEventType.INTEGRATION_TEST_TEAMS
    if normalized == "workflow":
        return AuditEventType.INTEGRATION_TEST_WORKFLOW
    return AuditEventType.INTEGRATION_TEST_SUITE


def normalize_acceptance_details(
    details: Mapping[str, object] | None,
) -> dict[str, str | int | float | bool | list[str]]:
    normalized: dict[str, str | int | float | bool | list[str]] = {}
    for key, value in (details or {}).items():
        if isinstance(value, (str, int, float, bool)):
            normalized[str(key)] = value
        elif isinstance(value, list):
            normalized[str(key)] = [str(item) for item in value]
        elif value is not None:
            normalized[str(key)] = str(value)
    return normalized


def coerce_status_code(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.isdigit():
            return int(candidate)
    return None


async def record_acceptance_evidence(
    *,
    db: AsyncSession,
    user: CurrentUser,
    run_id: str,
    channel: str,
    success: bool,
    status_code: int,
    message: str,
    details: Mapping[str, object] | None = None,
    request_path: str,
) -> None:
    if user.tenant_id is None:
        return
    audit = AuditLogger(db=db, tenant_id=user.tenant_id, correlation_id=run_id)
    await audit.log(
        event_type=integration_event_type(channel),
        actor_id=None,
        actor_email=user.email,
        resource_type="notification_integration",
        resource_id=channel,
        details={
            "channel": channel,
            "status_code": status_code,
            "result_message": message,
            "run_id": run_id,
            "captured_at": datetime.now(timezone.utc).isoformat(),
            **normalize_acceptance_details(details),
        },
        success=success,
        error_message=None if success else message,
        request_method="POST",
        request_path=request_path,
    )


async def run_slack_connectivity_test(
    *,
    current_user: CurrentUser,
    db: AsyncSession,
) -> IntegrationAcceptanceResult:
    from app.modules.notifications.domain import get_tenant_slack_service

    if current_user.tenant_id is None:
        return IntegrationAcceptanceResult(
            channel="slack",
            event_type=AuditEventType.INTEGRATION_TEST_SLACK.value,
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Tenant context required. Please complete onboarding.",
        )

    tier = normalize_tier(current_user.tier)
    if not is_feature_enabled(tier, FeatureFlag.SLACK_INTEGRATION):
        return IntegrationAcceptanceResult(
            channel="slack",
            event_type=AuditEventType.INTEGRATION_TEST_SLACK.value,
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message=(
                "Slack integration requires the Growth plan or higher. "
                f"Current tier: {tier.value}"
            ),
        )

    slack = await get_tenant_slack_service(db, current_user.tenant_id)
    if slack is None:
        return IntegrationAcceptanceResult(
            channel="slack",
            event_type=AuditEventType.INTEGRATION_TEST_SLACK.value,
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message=(
                "Slack is not configured for this tenant. "
                "Ensure Slack is enabled and channel settings are set."
            ),
        )

    try:
        ok = await slack.send_alert(
            title="Valdrics Slack Connectivity Test",
            message=f"This is a test alert from Valdrics.\n\nUser: {current_user.email}",
            severity="info",
        )
    except NOTIFICATION_CONNECTIVITY_RECOVERABLE_ERRORS as exc:
        logger.error("slack_test_failed", error=str(exc))
        return IntegrationAcceptanceResult(
            channel="slack",
            event_type=AuditEventType.INTEGRATION_TEST_SLACK.value,
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Slack test failed: {str(exc)}",
        )

    if not ok:
        return IntegrationAcceptanceResult(
            channel="slack",
            event_type=AuditEventType.INTEGRATION_TEST_SLACK.value,
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to send Slack notification",
        )

    return IntegrationAcceptanceResult(
        channel="slack",
        event_type=AuditEventType.INTEGRATION_TEST_SLACK.value,
        success=True,
        status_code=status.HTTP_200_OK,
        message="Test notification sent to Slack",
    )


async def run_jira_connectivity_test(
    *,
    current_user: CurrentUser,
    db: AsyncSession,
) -> IntegrationAcceptanceResult:
    from app.modules.notifications.domain import get_tenant_jira_service

    if current_user.tenant_id is None:
        return IntegrationAcceptanceResult(
            channel="jira",
            event_type=AuditEventType.INTEGRATION_TEST_JIRA.value,
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Tenant context required. Please complete onboarding.",
        )

    jira = await get_tenant_jira_service(db, current_user.tenant_id)
    if jira is None:
        return IntegrationAcceptanceResult(
            channel="jira",
            event_type=AuditEventType.INTEGRATION_TEST_JIRA.value,
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message=(
                "Jira is not configured for this tenant. "
                "Set Jira fields in notification settings and keep Jira enabled."
            ),
        )

    try:
        success = await jira.create_issue(
            summary="Valdrics Jira Connectivity Test",
            description=(
                "h2. Connectivity test\n"
                "This issue verifies Valdrics can create Jira incidents for policy events."
            ),
            labels=["valdrics", "connectivity-test"],
        )
    except NOTIFICATION_CONNECTIVITY_RECOVERABLE_ERRORS as exc:
        logger.error("jira_test_failed", error=str(exc))
        return IntegrationAcceptanceResult(
            channel="jira",
            event_type=AuditEventType.INTEGRATION_TEST_JIRA.value,
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Jira test failed: {str(exc)}",
        )

    if not success:
        return IntegrationAcceptanceResult(
            channel="jira",
            event_type=AuditEventType.INTEGRATION_TEST_JIRA.value,
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to create Jira test issue",
        )

    return IntegrationAcceptanceResult(
        channel="jira",
        event_type=AuditEventType.INTEGRATION_TEST_JIRA.value,
        success=True,
        status_code=status.HTTP_200_OK,
        message="Test issue created in Jira",
    )


async def run_teams_connectivity_test(
    *,
    current_user: CurrentUser,
    db: AsyncSession,
) -> IntegrationAcceptanceResult:
    from app.modules.notifications.domain import get_tenant_teams_service

    if current_user.tenant_id is None:
        return IntegrationAcceptanceResult(
            channel="teams",
            event_type=AuditEventType.INTEGRATION_TEST_TEAMS.value,
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Tenant context required. Please complete onboarding.",
        )

    tier = normalize_tier(current_user.tier)
    if not is_feature_enabled(tier, FeatureFlag.INCIDENT_INTEGRATIONS):
        return IntegrationAcceptanceResult(
            channel="teams",
            event_type=AuditEventType.INTEGRATION_TEST_TEAMS.value,
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message=(
                f"Feature '{FeatureFlag.INCIDENT_INTEGRATIONS.value}' requires an upgrade. "
                f"Current tier: {tier.value}"
            ),
        )

    teams = await get_tenant_teams_service(db, current_user.tenant_id)
    if teams is None:
        return IntegrationAcceptanceResult(
            channel="teams",
            event_type=AuditEventType.INTEGRATION_TEST_TEAMS.value,
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message=(
                "Teams is not configured for this tenant. "
                "Set Teams webhook URL in notification settings and keep Teams enabled."
            ),
        )

    try:
        ok = await teams.send_alert(
            title="Valdrics Teams Connectivity Test",
            message=f"This is a test alert from Valdrics.\n\nUser: {current_user.email}",
            severity="info",
        )
    except NOTIFICATION_CONNECTIVITY_RECOVERABLE_ERRORS as exc:
        logger.error("teams_test_failed", error=str(exc))
        return IntegrationAcceptanceResult(
            channel="teams",
            event_type=AuditEventType.INTEGRATION_TEST_TEAMS.value,
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=f"Teams test failed: {str(exc)}",
        )

    if not ok:
        return IntegrationAcceptanceResult(
            channel="teams",
            event_type=AuditEventType.INTEGRATION_TEST_TEAMS.value,
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Failed to send Teams notification",
        )

    return IntegrationAcceptanceResult(
        channel="teams",
        event_type=AuditEventType.INTEGRATION_TEST_TEAMS.value,
        success=True,
        status_code=status.HTTP_200_OK,
        message="Test notification sent to Teams",
    )


async def run_workflow_connectivity_test(
    *,
    current_user: CurrentUser,
    db: AsyncSession,
) -> IntegrationAcceptanceResult:
    from app.modules.notifications.domain import get_tenant_workflow_dispatchers
    from app.shared.core.notifications import NotificationDispatcher

    if current_user.tenant_id is None:
        return IntegrationAcceptanceResult(
            channel="workflow",
            event_type=AuditEventType.INTEGRATION_TEST_WORKFLOW.value,
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message="Tenant context required. Please complete onboarding.",
        )

    tier = normalize_tier(current_user.tier)
    if not is_feature_enabled(tier, FeatureFlag.INCIDENT_INTEGRATIONS):
        return IntegrationAcceptanceResult(
            channel="workflow",
            event_type=AuditEventType.INTEGRATION_TEST_WORKFLOW.value,
            success=False,
            status_code=status.HTTP_403_FORBIDDEN,
            message=(
                f"Feature '{FeatureFlag.INCIDENT_INTEGRATIONS.value}' requires an upgrade. "
                f"Current tier: {tier.value}"
            ),
        )

    dispatchers = await get_tenant_workflow_dispatchers(db, current_user.tenant_id)
    if not dispatchers:
        return IntegrationAcceptanceResult(
            channel="workflow",
            event_type=AuditEventType.INTEGRATION_TEST_WORKFLOW.value,
            success=False,
            status_code=status.HTTP_400_BAD_REQUEST,
            message=(
                "No workflow integration is configured for this tenant. "
                "Configure GitHub, GitLab, or webhook workflow settings first."
            ),
        )

    payload = {
        "tenant_id": str(current_user.tenant_id),
        "request_id": None,
        "decision": "warn",
        "summary": "Valdrics workflow connectivity test event",
        "resource_id": "workflow-connectivity-check",
        "action": "test_dispatch",
        "severity": "info",
        "evidence_links": NotificationDispatcher._build_remediation_evidence_links(
            None
        ),
    }

    ok_count = 0
    provider_results: list[str] = []
    for dispatcher in dispatchers:
        provider = str(getattr(dispatcher, "provider", "unknown"))
        try:
            ok = await dispatcher.dispatch("workflow.connectivity_test", payload)
        except NOTIFICATION_CONNECTIVITY_RECOVERABLE_ERRORS as exc:
            logger.warning(
                "workflow_test_dispatch_exception", provider=provider, error=str(exc)
            )
            ok = False
        if ok:
            ok_count += 1
            provider_results.append(f"{provider}:ok")
        else:
            provider_results.append(f"{provider}:failed")

    if ok_count == 0:
        return IntegrationAcceptanceResult(
            channel="workflow",
            event_type=AuditEventType.INTEGRATION_TEST_WORKFLOW.value,
            success=False,
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message="Workflow test failed for all configured integrations",
            details={
                "total_targets": len(dispatchers),
                "successful_targets": 0,
                "provider_results": provider_results,
            },
        )

    return IntegrationAcceptanceResult(
        channel="workflow",
        event_type=AuditEventType.INTEGRATION_TEST_WORKFLOW.value,
        success=True,
        status_code=status.HTTP_200_OK,
        message=f"Workflow test dispatched successfully ({ok_count}/{len(dispatchers)} targets).",
        details={
            "total_targets": len(dispatchers),
            "successful_targets": ok_count,
            "provider_results": provider_results,
        },
    )
