"""Acceptance-suite passive integration verification operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.governance.domain.security.audit_log import AuditEventType, AuditLogger
from app.shared.core.pricing import FeatureFlag, PricingTier


@dataclass(slots=True)
class IntegrationSuiteResult:
    """Integration suite summary payload returned by acceptance handler."""

    overall_status: str
    passed: int
    failed: int
    results: list[dict[str, Any]]


async def run_passive_integration_checks(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    tier: PricingTier,
    run_id: str,
    captured_at: str,
    system_user_email: str,
    audit: AuditLogger,
    get_tenant_slack_service_fn: Any,
    get_tenant_jira_service_fn: Any,
    get_tenant_teams_service_fn: Any,
    get_tenant_workflow_dispatchers_fn: Any,
    integration_event_type_fn: Callable[[str], AuditEventType],
    is_feature_enabled_fn: Callable[[PricingTier, FeatureFlag], bool],
    integration_recoverable_errors: tuple[type[Exception], ...],
    evaluate_tenancy_passive_check_fn: Any,
    coerce_positive_int_fn: Callable[[object, int], int],
    get_settings_fn: Callable[[], Any],
    logger_obj: Any,
) -> IntegrationSuiteResult:
    """Run non-invasive integration checks and persist audit events."""
    integration_results: list[dict[str, Any]] = []

    async def record_integration(
        *,
        channel: str,
        success: bool,
        status_code: int,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        integration_results.append(
            {
                "channel": channel,
                "success": success,
                "status_code": status_code,
                "message": message,
                "details": details or {},
            }
        )
        await audit.log(
            event_type=integration_event_type_fn(channel),
            actor_id=None,
            actor_email=system_user_email,
            resource_type="notification_integration",
            resource_id=channel,
            details={
                "channel": channel,
                "mode": "passive",
                "status_code": status_code,
                "result_message": message,
                "run_id": run_id,
                "captured_at": captured_at,
                **(details or {}),
            },
            success=success,
            error_message=None if success else message,
            request_method="JOB",
            request_path="/jobs/acceptance-suite-capture",
        )

    slack = await get_tenant_slack_service_fn(db, tenant_id)
    if slack is None:
        await record_integration(
            channel="slack",
            success=True,
            status_code=204,
            message="Slack not configured for this tenant (skipped).",
            details={"skipped": True, "reason": "not_configured"},
        )
    else:
        try:
            ok = await slack.health_check()
        except integration_recoverable_errors as exc:
            ok = False
            logger_obj.warning(
                "slack_passive_health_check_exception",
                error=str(exc),
                tenant_id=str(tenant_id),
            )
        await record_integration(
            channel="slack",
            success=bool(ok),
            status_code=200 if ok else 502,
            message="Slack passive health check OK."
            if ok
            else "Slack passive health check failed.",
        )

    jira_allowed = is_feature_enabled_fn(tier, FeatureFlag.JIRA_INTEGRATION)
    incident_integrations_allowed = is_feature_enabled_fn(
        tier, FeatureFlag.INCIDENT_INTEGRATIONS
    )

    jira = await get_tenant_jira_service_fn(db, tenant_id)
    if jira is None:
        await record_integration(
            channel="jira",
            success=True,
            status_code=204,
            message="Jira not configured for this tenant (skipped).",
            details={"skipped": True, "reason": "not_configured"},
        )
    elif not jira_allowed:
        await record_integration(
            channel="jira",
            success=True,
            status_code=204,
            message="Jira configured but Jira integration is not enabled for this tier (skipped).",
            details={
                "skipped": True,
                "reason": "tier_not_allowed",
                "tier": tier.value,
                "feature": FeatureFlag.JIRA_INTEGRATION.value,
            },
        )
    else:
        ok, status_code, error = await jira.health_check()
        await record_integration(
            channel="jira",
            success=bool(ok),
            status_code=int(status_code or (200 if ok else 502)),
            message="Jira passive health check OK."
            if ok
            else "Jira passive health check failed.",
            details={"error": error} if error else None,
        )

    teams = await get_tenant_teams_service_fn(db, tenant_id)
    if teams is None:
        await record_integration(
            channel="teams",
            success=True,
            status_code=204,
            message="Teams not configured for this tenant (skipped).",
            details={"skipped": True, "reason": "not_configured"},
        )
    elif not incident_integrations_allowed:
        await record_integration(
            channel="teams",
            success=True,
            status_code=204,
            message="Teams configured but incident integrations are not enabled for this tier (skipped).",
            details={
                "skipped": True,
                "reason": "tier_not_allowed",
                "tier": tier.value,
                "feature": FeatureFlag.INCIDENT_INTEGRATIONS.value,
            },
        )
    else:
        ok, status_code, error = await teams.health_check()
        await record_integration(
            channel="teams",
            success=bool(ok),
            status_code=int(status_code or (200 if ok else 502)),
            message="Teams passive health check OK."
            if ok
            else "Teams passive health check failed.",
            details={"error": error} if error else None,
        )

    dispatchers = await get_tenant_workflow_dispatchers_fn(db, tenant_id)
    providers = [str(getattr(item, "provider", "unknown")) for item in dispatchers]
    if not dispatchers:
        await record_integration(
            channel="workflow",
            success=True,
            status_code=204,
            message="Workflow automation not configured for this tenant (skipped).",
            details={"skipped": True, "reason": "not_configured"},
        )
    elif not incident_integrations_allowed:
        await record_integration(
            channel="workflow",
            success=True,
            status_code=204,
            message="Workflow configured but incident integrations are not enabled for this tier (skipped).",
            details={
                "skipped": True,
                "reason": "tier_not_allowed",
                "tier": tier.value,
                "providers": providers,
                "feature": FeatureFlag.INCIDENT_INTEGRATIONS.value,
            },
        )
    else:
        await record_integration(
            channel="workflow",
            success=True,
            status_code=200,
            message=f"Workflow dispatchers configured ({len(dispatchers)}). Passive check skipped.",
            details={"providers": providers, "checked": False},
        )

    runtime_settings = get_settings_fn()
    environment = str(getattr(runtime_settings, "ENVIRONMENT", "") or "").strip().lower()
    if environment in {"staging", "production"}:
        max_age_hours = coerce_positive_int_fn(
            getattr(runtime_settings, "TENANT_ISOLATION_EVIDENCE_MAX_AGE_HOURS", 168),
            168,
        )
        tenancy_check = await evaluate_tenancy_passive_check_fn(
            db,
            tenant_id=tenant_id,
            max_age_hours=max_age_hours,
            now_utc=datetime.now(timezone.utc),
        )
        await record_integration(
            channel="tenancy",
            success=bool(tenancy_check["success"]),
            status_code=int(tenancy_check["status_code"]),
            message=str(tenancy_check["message"]),
            details=tenancy_check.get("details"),
        )

    passed = sum(1 for item in integration_results if item.get("success"))
    failed = len(integration_results) - passed
    overall_status = (
        "success" if failed == 0 else "partial_failure" if passed > 0 else "failed"
    )

    await audit.log(
        event_type=AuditEventType.INTEGRATION_TEST_SUITE,
        actor_id=None,
        actor_email=system_user_email,
        resource_type="notification_integration",
        resource_id="suite",
        details={
            "channel": "suite",
            "mode": "passive",
            "overall_status": overall_status,
            "passed": passed,
            "failed": failed,
            "checked_channels": [item.get("channel") for item in integration_results],
            "run_id": run_id,
            "captured_at": captured_at,
        },
        success=(failed == 0),
        error_message=None if failed == 0 else f"{failed} integrations failed",
        request_method="JOB",
        request_path="/jobs/acceptance-suite-capture",
    )

    return IntegrationSuiteResult(
        overall_status=overall_status,
        passed=passed,
        failed=failed,
        results=integration_results,
    )


__all__ = ["IntegrationSuiteResult", "run_passive_integration_checks"]
