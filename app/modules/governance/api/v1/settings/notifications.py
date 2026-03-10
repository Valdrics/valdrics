"""
Notification Settings API

Manages Slack/Jira/Teams and alert notification preferences for tenants.
"""
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification_settings import NotificationSettings
from app.models.remediation_settings import RemediationSettings
from app.modules.governance.api.v1.settings.notification_diagnostics_ops import (
    to_jira_policy_diagnostics as _to_jira_policy_diagnostics_impl,
    to_notification_response as _to_notification_response_impl,
    to_slack_policy_diagnostics as _to_slack_policy_diagnostics_impl,
)
from app.modules.governance.api.v1.settings.notification_settings_ops import (
    apply_notification_settings_update as _apply_notification_settings_update_impl,
    build_notification_settings_audit_payload as _build_notification_settings_audit_payload_impl,
    build_notification_settings_create_kwargs as _build_notification_settings_create_kwargs_impl,
    enforce_incident_integrations_access as _enforce_incident_integrations_access_impl,
    enforce_jira_integration_access as _enforce_jira_integration_access_impl,
    enforce_slack_integration_access as _enforce_slack_integration_access_impl,
    validate_notification_settings_requirements as _validate_notification_settings_requirements_impl,
)
from app.modules.governance.api.v1.settings.notifications_acceptance_ops import (
    coerce_status_code as _coerce_status_code_impl,
    normalize_acceptance_details as _normalize_acceptance_details_impl,
    record_acceptance_evidence as _record_acceptance_evidence_impl,
    run_jira_connectivity_test as _run_jira_connectivity_test_impl,
    run_slack_connectivity_test as _run_slack_connectivity_test_impl,
    run_teams_connectivity_test as _run_teams_connectivity_test_impl,
    run_workflow_connectivity_test as _run_workflow_connectivity_test_impl,
)
from app.modules.governance.api.v1.settings.notifications_models import (
    IntegrationAcceptanceCaptureRequest,
    IntegrationAcceptanceCaptureResponse,
    IntegrationAcceptanceEvidenceItem,
    IntegrationAcceptanceEvidenceListResponse,
    IntegrationAcceptanceResult,
    NotificationSettingsResponse,
    NotificationSettingsUpdate,
    PolicyNotificationDiagnosticsResponse,
)
from app.modules.governance.domain.security.audit_log import AuditEventType, AuditLog
from app.shared.core.auth import (
    CurrentUser,
    get_current_user_with_db_context,
    requires_role_with_db_context,
)
from app.shared.core.async_utils import maybe_await
from app.shared.core.logging import audit_log_async as audit_log
from app.shared.core.pricing import FeatureFlag, is_feature_enabled, normalize_tier
from app.shared.db.session import get_db

logger = structlog.get_logger()
router = APIRouter(tags=["Notifications"])


def _raise_http_exception(status_code: int, detail: str) -> None:
    raise HTTPException(status_code=status_code, detail=detail)


_coerce_status_code = _coerce_status_code_impl
_normalize_acceptance_details = _normalize_acceptance_details_impl
_record_acceptance_evidence = _record_acceptance_evidence_impl
_run_slack_connectivity_test = _run_slack_connectivity_test_impl
_run_jira_connectivity_test = _run_jira_connectivity_test_impl
_run_teams_connectivity_test = _run_teams_connectivity_test_impl
_run_workflow_connectivity_test = _run_workflow_connectivity_test_impl


async def _execute_notification_channel_test(
    *,
    channel: str,
    request_path: str,
    runner: Callable[..., Awaitable[IntegrationAcceptanceResult]],
    current_user: CurrentUser,
    db: AsyncSession,
) -> dict[str, str]:
    run_id = str(uuid4())
    result = await runner(current_user=current_user, db=db)
    await _record_acceptance_evidence(
        db=db,
        user=current_user,
        run_id=run_id,
        channel=channel,
        success=result.success,
        status_code=result.status_code,
        message=result.message,
        details=result.details,
        request_path=request_path,
    )
    await db.commit()
    if not result.success:
        raise HTTPException(status_code=result.status_code, detail=result.message)
    return {"status": "success", "message": result.message}


def _to_acceptance_evidence_item(row: AuditLog) -> IntegrationAcceptanceEvidenceItem:
    details = row.details or {}
    message_value = details.get("result_message", row.error_message)
    return IntegrationAcceptanceEvidenceItem(
        event_id=str(row.id),
        run_id=row.correlation_id,
        event_type=row.event_type,
        channel=str(details.get("channel", row.resource_id or "unknown")),
        success=bool(row.success),
        status_code=_coerce_status_code(details.get("status_code")),
        message=str(message_value) if message_value is not None else None,
        actor_id=str(row.actor_id) if row.actor_id else None,
        actor_email=row.actor_email,
        event_timestamp=row.event_timestamp.isoformat(),
        details=_normalize_acceptance_details(details),
    )

@router.get("/notifications", response_model=NotificationSettingsResponse)
async def get_notification_settings(
    current_user: CurrentUser = Depends(get_current_user_with_db_context),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsResponse:
    result = await db.execute(
        select(NotificationSettings).where(
            NotificationSettings.tenant_id == current_user.tenant_id
        )
    )
    settings = result.scalar_one_or_none()
    tier = normalize_tier(current_user.tier)
    slack_feature_allowed_by_tier = is_feature_enabled(
        tier, FeatureFlag.SLACK_INTEGRATION
    )

    # Create default settings if not exists
    if not settings:
        settings = NotificationSettings(
            tenant_id=current_user.tenant_id,
            slack_enabled=slack_feature_allowed_by_tier,
            jira_enabled=False,
            jira_issue_type="Task",
            digest_schedule="daily",
            digest_hour=9,
            digest_minute=0,
            alert_on_budget_warning=True,
            alert_on_budget_exceeded=True,
            alert_on_zombie_detected=True,
        )
        db.add(settings)
        await db.commit()
        await db.refresh(settings)

        logger.info(
            "notification_settings_created",
            tenant_id=str(current_user.tenant_id),
        )

    return _to_notification_response_impl(
        settings, slack_feature_allowed_by_tier=slack_feature_allowed_by_tier
    )


@router.put("/notifications", response_model=NotificationSettingsResponse)
async def update_notification_settings(
    data: NotificationSettingsUpdate,
    current_user: CurrentUser = Depends(requires_role_with_db_context("admin")),
    db: AsyncSession = Depends(get_db),
) -> NotificationSettingsResponse:
    result = await db.execute(
        select(NotificationSettings).where(
            NotificationSettings.tenant_id == current_user.tenant_id
        )
    )
    settings = result.scalar_one_or_none()
    tier = normalize_tier(current_user.tier)
    slack_feature_allowed_by_tier = is_feature_enabled(
        tier, FeatureFlag.SLACK_INTEGRATION
    )
    _enforce_slack_integration_access_impl(
        data=data,
        current_tier=current_user.tier,
        normalize_tier_fn=normalize_tier,
        is_feature_enabled_fn=is_feature_enabled,
        slack_integration_feature=FeatureFlag.SLACK_INTEGRATION,
        raise_http_exception_fn=_raise_http_exception,
    )
    _enforce_jira_integration_access_impl(
        data=data,
        current_tier=current_user.tier,
        normalize_tier_fn=normalize_tier,
        is_feature_enabled_fn=is_feature_enabled,
        jira_integration_feature=FeatureFlag.JIRA_INTEGRATION,
        raise_http_exception_fn=_raise_http_exception,
    )
    _enforce_incident_integrations_access_impl(
        data=data,
        current_tier=current_user.tier,
        normalize_tier_fn=normalize_tier,
        is_feature_enabled_fn=is_feature_enabled,
        incident_integrations_feature=FeatureFlag.INCIDENT_INTEGRATIONS,
        raise_http_exception_fn=_raise_http_exception,
    )

    if not settings:
        settings = NotificationSettings(
            **_build_notification_settings_create_kwargs_impl(
                data=data,
                tenant_id=current_user.tenant_id,
            )
        )
        db.add(settings)
    else:
        _apply_notification_settings_update_impl(
            settings=settings,
            updates=data.model_dump(),
        )

    _validate_notification_settings_requirements_impl(
        settings=settings,
        raise_http_exception_fn=_raise_http_exception,
    )

    await maybe_await(
        audit_log(
            "settings.notifications_updated",
            str(current_user.id),
            str(current_user.tenant_id),
            _build_notification_settings_audit_payload_impl(settings),
            db=db,
            resource_type="notification_settings",
            resource_id=str(current_user.tenant_id),
            request_method="PUT",
            request_path="/api/v1/settings/notifications",
        )
    )
    await db.commit()
    await db.refresh(settings)

    logger.info(
        "notification_settings_updated",
        tenant_id=str(current_user.tenant_id),
        digest_schedule=settings.digest_schedule,
    )

    return _to_notification_response_impl(
        settings, slack_feature_allowed_by_tier=slack_feature_allowed_by_tier
    )


@router.get(
    "/notifications/policy-diagnostics",
    response_model=PolicyNotificationDiagnosticsResponse,
)
async def get_policy_notification_diagnostics(
    current_user: CurrentUser = Depends(requires_role_with_db_context("admin")),
    db: AsyncSession = Depends(get_db),
) -> PolicyNotificationDiagnosticsResponse:
    from app.shared.core.config import get_settings

    notification_result = await db.execute(
        select(NotificationSettings).where(
            NotificationSettings.tenant_id == current_user.tenant_id
        )
    )
    notification_settings = notification_result.scalar_one_or_none()

    remediation_result = await db.execute(
        select(RemediationSettings).where(
            RemediationSettings.tenant_id == current_user.tenant_id
        )
    )
    remediation_settings = remediation_result.scalar_one_or_none()

    tier = normalize_tier(current_user.tier)
    slack_feature_allowed_by_tier = is_feature_enabled(
        tier, FeatureFlag.SLACK_INTEGRATION
    )
    jira_feature_allowed_by_tier = is_feature_enabled(
        tier, FeatureFlag.JIRA_INTEGRATION
    )

    app_settings = get_settings()
    slack = _to_slack_policy_diagnostics_impl(
        remediation_settings,
        notification_settings,
        feature_allowed_by_tier=slack_feature_allowed_by_tier,
        has_bot_token=bool(app_settings.SLACK_BOT_TOKEN),
        has_default_channel=bool(app_settings.SLACK_CHANNEL_ID),
    )
    jira = _to_jira_policy_diagnostics_impl(
        remediation_settings,
        notification_settings,
        feature_allowed_by_tier=jira_feature_allowed_by_tier,
    )

    return PolicyNotificationDiagnosticsResponse(
        tier=tier.value,
        has_activeops_settings=remediation_settings is not None,
        has_notification_settings=notification_settings is not None,
        policy_enabled=bool(getattr(remediation_settings, "policy_enabled", True)),
        slack=slack,
        jira=jira,
    )


@router.post("/notifications/test-slack")
async def test_slack_notification(
    current_user: CurrentUser = Depends(requires_role_with_db_context("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    return await _execute_notification_channel_test(
        channel="slack",
        request_path="/api/v1/settings/notifications/test-slack",
        runner=_run_slack_connectivity_test,
        current_user=current_user,
        db=db,
    )


@router.post("/notifications/test-jira")
async def test_jira_notification(
    current_user: CurrentUser = Depends(requires_role_with_db_context("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Send a test Jira issue using tenant-scoped Jira notification settings.
    """
    return await _execute_notification_channel_test(
        channel="jira",
        request_path="/api/v1/settings/notifications/test-jira",
        runner=_run_jira_connectivity_test,
        current_user=current_user,
        db=db,
    )


@router.post("/notifications/test-teams")
async def test_teams_notification(
    current_user: CurrentUser = Depends(requires_role_with_db_context("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Send a test notification to Microsoft Teams using tenant-scoped settings.
    """
    return await _execute_notification_channel_test(
        channel="teams",
        request_path="/api/v1/settings/notifications/test-teams",
        runner=_run_teams_connectivity_test,
        current_user=current_user,
        db=db,
    )


@router.post("/notifications/test-workflow")
async def test_workflow_notification(
    current_user: CurrentUser = Depends(requires_role_with_db_context("admin")),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """
    Send a test workflow automation event using tenant-scoped workflow settings.
    """
    return await _execute_notification_channel_test(
        channel="workflow",
        request_path="/api/v1/settings/notifications/test-workflow",
        runner=_run_workflow_connectivity_test,
        current_user=current_user,
        db=db,
    )


@router.post(
    "/notifications/acceptance-evidence/capture",
    response_model=IntegrationAcceptanceCaptureResponse,
)
async def capture_notification_acceptance_evidence(
    payload: IntegrationAcceptanceCaptureRequest | None = None,
    current_user: CurrentUser = Depends(requires_role_with_db_context("admin")),
    db: AsyncSession = Depends(get_db),
) -> IntegrationAcceptanceCaptureResponse:
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context required. Please complete onboarding.",
        )
    payload = payload or IntegrationAcceptanceCaptureRequest()

    run_id = str(uuid4())
    captured_at = datetime.now(timezone.utc)
    checks: list[
        tuple[
            str,
            Callable[..., Awaitable[IntegrationAcceptanceResult]],
        ]
    ] = []
    if payload.include_slack:
        checks.append(("slack", _run_slack_connectivity_test))
    if payload.include_jira:
        checks.append(("jira", _run_jira_connectivity_test))
    if payload.include_teams:
        checks.append(("teams", _run_teams_connectivity_test))
    if payload.include_workflow:
        checks.append(("workflow", _run_workflow_connectivity_test))
    if not checks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one integration check must be enabled.",
        )

    results: list[IntegrationAcceptanceResult] = []
    for channel, runner in checks:
        channel_result = await runner(current_user=current_user, db=db)
        results.append(channel_result)
        await _record_acceptance_evidence(
            db=db,
            user=current_user,
            run_id=run_id,
            channel=channel,
            success=channel_result.success,
            status_code=channel_result.status_code,
            message=channel_result.message,
            details=channel_result.details,
            request_path="/api/v1/settings/notifications/acceptance-evidence/capture",
        )
        if payload.fail_fast and not channel_result.success:
            break

    passed = sum(1 for item in results if item.success)
    failed = len(results) - passed
    overall_status = (
        "success" if failed == 0 else "partial_failure" if passed > 0 else "failed"
    )

    await _record_acceptance_evidence(
        db=db,
        user=current_user,
        run_id=run_id,
        channel="suite",
        success=(failed == 0),
        status_code=status.HTTP_200_OK if failed == 0 else status.HTTP_207_MULTI_STATUS,
        message=f"Acceptance suite completed ({passed} passed, {failed} failed).",
        details={
            "overall_status": overall_status,
            "passed": passed,
            "failed": failed,
            "checked_channels": [item.channel for item in results],
        },
        request_path="/api/v1/settings/notifications/acceptance-evidence/capture",
    )
    await db.commit()

    return IntegrationAcceptanceCaptureResponse(
        run_id=run_id,
        tenant_id=str(current_user.tenant_id),
        captured_at=captured_at.isoformat(),
        overall_status=overall_status,
        passed=passed,
        failed=failed,
        results=results,
    )


@router.get(
    "/notifications/acceptance-evidence",
    response_model=IntegrationAcceptanceEvidenceListResponse,
)
async def list_notification_acceptance_evidence(
    current_user: CurrentUser = Depends(requires_role_with_db_context("admin")),
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    run_id: str | None = None,
) -> IntegrationAcceptanceEvidenceListResponse:
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant context required. Please complete onboarding.",
        )
    safe_limit = max(1, min(int(limit), 200))
    accepted_event_types = [
        AuditEventType.INTEGRATION_TEST_SLACK.value,
        AuditEventType.INTEGRATION_TEST_JIRA.value,
        AuditEventType.INTEGRATION_TEST_TEAMS.value,
        AuditEventType.INTEGRATION_TEST_WORKFLOW.value,
        AuditEventType.INTEGRATION_TEST_SUITE.value,
    ]
    stmt = (
        select(AuditLog)
        .where(AuditLog.tenant_id == current_user.tenant_id)
        .where(AuditLog.event_type.in_(accepted_event_types))
        .order_by(desc(AuditLog.event_timestamp))
        .limit(safe_limit)
    )
    if run_id:
        stmt = stmt.where(AuditLog.correlation_id == run_id)
    rows = (await db.execute(stmt)).scalars().all()
    items = [_to_acceptance_evidence_item(row) for row in rows]
    return IntegrationAcceptanceEvidenceListResponse(total=len(items), items=items)
