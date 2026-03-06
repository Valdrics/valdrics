from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from app.models.remediation import RemediationAction, RemediationRequest, RemediationStatus
from app.modules.governance.domain.security.remediation_policy import PolicyDecision
from app.modules.optimization.domain.actions.base import ExecutionResult, ExecutionStatus, RemediationContext
from app.shared.core.pricing import FeatureFlag, is_feature_enabled


def coerce_remediation_action(
    request: RemediationRequest,
    *,
    recoverable_errors: tuple[type[Exception], ...],
) -> RemediationAction:
    action_raw = getattr(request, "action", None)
    if isinstance(action_raw, RemediationAction):
        return action_raw

    try:
        action = RemediationAction(str(action_raw))
        request.action = action
    except recoverable_errors as exc:
        raise ValueError(f"Invalid remediation action on request: {action_raw}") from exc
    return action


def normalize_estimated_savings(value: Any) -> Decimal:
    savings_value = value if value is not None else Decimal("0")
    if isinstance(savings_value, Decimal):
        return savings_value
    return Decimal(str(savings_value))


def _policy_notification_flags(
    *,
    remediation_settings: Any,
    tenant_tier: Any,
) -> dict[str, bool]:
    incident_integrations_enabled = bool(
        is_feature_enabled(tenant_tier, FeatureFlag.INCIDENT_INTEGRATIONS)
    )
    notify_slack = bool(
        remediation_settings
        and bool(getattr(remediation_settings, "policy_violation_notify_slack", True))
        and is_feature_enabled(tenant_tier, FeatureFlag.SLACK_INTEGRATION)
    )
    notify_jira = bool(
        remediation_settings
        and bool(getattr(remediation_settings, "policy_violation_notify_jira", False))
        and incident_integrations_enabled
    )
    return {
        "notify_slack": notify_slack,
        "notify_jira": notify_jira,
        "notify_workflow": incident_integrations_enabled,
        "notify_teams": incident_integrations_enabled,
    }


async def maybe_notify_policy_event(
    *,
    tenant_id: UUID,
    policy_decision: PolicyDecision,
    summary: str,
    resource_id: str,
    action_value: str,
    request_id: UUID,
    remediation_settings: Any,
    tenant_tier: Any,
    db: Any,
) -> None:
    flags = _policy_notification_flags(
        remediation_settings=remediation_settings,
        tenant_tier=tenant_tier,
    )
    if not any(flags.values()):
        return

    from app.shared.core.notifications import NotificationDispatcher

    await NotificationDispatcher.notify_policy_event(
        tenant_id=str(tenant_id),
        decision=policy_decision.value,
        summary=summary,
        resource_id=resource_id,
        action=action_value,
        notify_slack=flags["notify_slack"],
        notify_jira=flags["notify_jira"],
        notify_teams=flags["notify_teams"],
        notify_workflow=flags["notify_workflow"],
        request_id=str(request_id),
        db=db,
    )


async def handle_policy_decision(
    *,
    request: RemediationRequest,
    policy_evaluation: Any,
    policy_details: dict[str, Any],
    request_id: UUID,
    actor_id: str,
    resource_id: str,
    resource_type: str,
    action_value: str,
    tenant_id: UUID,
    tenant_tier: Any,
    remediation_settings: Any,
    db: Any,
    audit_logger: Any,
    remediation_module: Any,
    logger: Any,
) -> bool:
    decision = policy_evaluation.decision
    if decision == PolicyDecision.WARN:
        logger.warning(
            "remediation_policy_warned",
            request_id=str(request_id),
            summary=policy_evaluation.summary,
        )
        await audit_logger.log(
            event_type=remediation_module.AuditEventType.POLICY_WARNED,
            actor_id=actor_id,
            resource_id=resource_id,
            resource_type=resource_type,
            success=True,
            details=policy_details,
        )
        return False

    if decision == PolicyDecision.BLOCK:
        request.status = RemediationStatus.FAILED
        request.execution_error = f"POLICY_BLOCK: {policy_evaluation.summary}"
        await audit_logger.log(
            event_type=remediation_module.AuditEventType.POLICY_BLOCKED,
            actor_id=actor_id,
            resource_id=resource_id,
            resource_type=resource_type,
            success=False,
            error_message=request.execution_error,
            details=policy_details,
        )
        await maybe_notify_policy_event(
            tenant_id=tenant_id,
            policy_decision=decision,
            summary=policy_evaluation.summary,
            resource_id=resource_id,
            action_value=action_value,
            request_id=request_id,
            remediation_settings=remediation_settings,
            tenant_tier=tenant_tier,
            db=db,
        )
        await db.commit()
        await db.refresh(request)
        return True

    if decision == PolicyDecision.ESCALATE:
        request.status = RemediationStatus.PENDING_APPROVAL
        request.escalation_required = True
        request.escalation_reason = policy_evaluation.summary
        request.escalated_at = datetime.now(timezone.utc)
        request.execution_error = None
        policy_details["escalation_workflow_feature_enabled"] = is_feature_enabled(
            tenant_tier, FeatureFlag.ESCALATION_WORKFLOW
        )
        await audit_logger.log(
            event_type=remediation_module.AuditEventType.POLICY_ESCALATED,
            actor_id=actor_id,
            resource_id=resource_id,
            resource_type=resource_type,
            success=False,
            error_message=policy_evaluation.summary,
            details=policy_details,
        )
        await maybe_notify_policy_event(
            tenant_id=tenant_id,
            policy_decision=decision,
            summary=policy_evaluation.summary,
            resource_id=resource_id,
            action_value=action_value,
            request_id=request_id,
            remediation_settings=remediation_settings,
            tenant_tier=tenant_tier,
            db=db,
        )
        await db.commit()
        await db.refresh(request)
        return True

    return False


async def maybe_schedule_grace_period_execution(
    *,
    request: RemediationRequest,
    action: RemediationAction,
    remediation_settings: Any,
    request_id: UUID,
    tenant_id: UUID,
    action_value: str,
    actor_id: str,
    resource_id: str,
    resource_type: str,
    db: Any,
    audit_logger: Any,
    remediation_module: Any,
    logger: Any,
    bypass_grace_period: bool,
) -> bool:
    if request.status != RemediationStatus.APPROVED or bypass_grace_period:
        return False

    hours = 24
    if action == RemediationAction.RECLAIM_LICENSE_SEAT:
        hours = (
            getattr(remediation_settings, "license_reclaim_grace_period_days", 1) or 1
        ) * 24

    scheduled_at = datetime.now(timezone.utc) + timedelta(hours=hours)
    request.status = RemediationStatus.SCHEDULED
    request.scheduled_execution_at = scheduled_at
    await db.commit()

    logger.info(
        "remediation_scheduled_grace_period",
        request_id=str(request_id),
        scheduled_at=scheduled_at.isoformat(),
        grace_hours=hours,
    )
    await audit_logger.log(
        event_type=remediation_module.AuditEventType.REMEDIATION_EXECUTION_STARTED,
        actor_id=actor_id,
        resource_id=resource_id,
        resource_type=resource_type,
        success=True,
        details={
            "request_id": str(request_id),
            "action": action_value,
            "scheduled_execution_at": scheduled_at.isoformat(),
            "note": f"Resource scheduled for execution after {hours}h grace period.",
        },
    )

    from app.models.background_job import JobType
    from app.modules.governance.domain.jobs.processor import enqueue_job

    await enqueue_job(
        db=db,
        job_type=JobType.REMEDIATION,
        tenant_id=tenant_id,
        payload={"request_id": str(request_id)},
        scheduled_for=scheduled_at,
    )
    return True


async def resolve_execution_region(
    *,
    service: Any,
    request: RemediationRequest,
    provider: str,
    tenant_id: UUID,
    credentials: dict[str, Any],
) -> Any:
    execution_region = getattr(request, "region", None) or service.region
    if str(execution_region or "").strip().lower() in {"", "global"}:
        credential_region = str((credentials or {}).get("region") or "").strip()
        if credential_region and credential_region.lower() != "global":
            execution_region = credential_region
    if provider == "aws" and str(execution_region or "").strip().lower() in {"", "global"}:
        execution_region = await service._resolve_aws_region_hint(
            tenant_id=tenant_id,
            connection_id=getattr(request, "connection_id", None),
        )
    return execution_region


def build_remediation_context(
    *,
    service: Any,
    tenant_id: UUID,
    tier_value: str,
    execution_region: Any,
    credentials: dict[str, Any],
    request: RemediationRequest,
) -> RemediationContext:
    return RemediationContext(
        db_session=service.db,
        tenant_id=tenant_id,
        tier=tier_value,
        region=execution_region,
        credentials=credentials,
        create_backup=bool(getattr(request, "create_backup", False)),
        backup_retention_days=int(getattr(request, "backup_retention_days", 30) or 30),
        parameters=service._strip_system_policy_context(
            getattr(request, "action_parameters", None)
        ),
    )


def apply_execution_result(
    *,
    request: RemediationRequest,
    execution_result: ExecutionResult,
) -> None:
    if execution_result.status == ExecutionStatus.SUCCESS:
        request.status = RemediationStatus.COMPLETED
        request.executed_at = datetime.now(timezone.utc)
        request.backup_resource_id = execution_result.backup_id
        request.execution_error = None
        return

    request.status = RemediationStatus.FAILED
    if execution_result.status == ExecutionStatus.SKIPPED:
        request.execution_error = (
            execution_result.error_message
            or "Action skipped by validation or tier policy."
        )
        return
    request.execution_error = execution_result.error_message or "Action failed."


def should_notify_completion_workflow(tenant_tier: Any) -> bool:
    return bool(
        is_feature_enabled(tenant_tier, FeatureFlag.GITOPS_REMEDIATION)
        or is_feature_enabled(tenant_tier, FeatureFlag.INCIDENT_INTEGRATIONS)
    )
