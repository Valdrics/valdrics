"""
Acceptance Suite Evidence Capture Job Handler

Runs on a schedule to capture audit-grade evidence that the system is healthy
enough for production sign-off (ingestion reliability, allocation coverage, etc).

Important: this handler must be non-invasive for tenant integrations. It should
avoid creating Jira issues or sending Slack/Teams messages during automated runs.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_job import BackgroundJob
from app.models.tenant import Tenant
from app.modules.governance.domain.jobs.handlers.acceptance_capture_ops import (
    build_system_user,
    capture_acceptance_artifacts,
    parse_capture_window,
    parse_kpi_thresholds,
)
from app.modules.governance.domain.jobs.handlers.acceptance_integration_ops import (
    run_passive_integration_checks,
)
from app.modules.governance.domain.jobs.handlers.acceptance_runtime_ops import (
    ACCEPTANCE_CAPTURE_RECOVERABLE_ERRORS,
    ACCEPTANCE_INTEGRATION_RECOVERABLE_ERRORS,
    ACCEPTANCE_PARSE_RECOVERABLE_ERRORS,
    _coerce_positive_int,
    _evaluate_tenancy_passive_check,
    _integration_event_type,
    _iso_date,
    _require_tenant_id,
    _tenant_tier,
)
from app.modules.governance.domain.jobs.handlers.base import BaseJobHandler
from app.modules.governance.domain.security.audit_log import AuditLogger
from app.modules.notifications.domain import (
    get_tenant_jira_service,
    get_tenant_slack_service,
    get_tenant_teams_service,
    get_tenant_workflow_dispatchers,
)
from app.shared.core.config import get_settings
from app.shared.core.pricing import is_feature_enabled

logger = structlog.get_logger()


class AcceptanceSuiteCaptureHandler(BaseJobHandler):
    """
    Captures acceptance KPI evidence and non-invasive integration health checks.

    Evidence is stored in immutable audit logs:
    - acceptance.kpis_captured
    - integration_test.* (in passive mode)
    """

    timeout_seconds = 300

    async def execute(self, job: BackgroundJob, db: AsyncSession) -> Dict[str, Any]:
        tenant_id = _require_tenant_id(job)
        payload = job.payload or {}

        start_date, end_date = parse_capture_window(payload, iso_date_parser=_iso_date)
        thresholds = parse_kpi_thresholds(payload)

        run_id = str(uuid4())
        captured_at = datetime.now(timezone.utc).isoformat()

        tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))
        tier = _tenant_tier(getattr(tenant, "plan", None))
        system_user = build_system_user(tenant_id=tenant_id, tier=tier)

        audit = AuditLogger(db=db, tenant_id=tenant_id, correlation_id=run_id)

        capture_result = await capture_acceptance_artifacts(
            db=db,
            tenant_id=tenant_id,
            tier=tier,
            start_date=start_date,
            end_date=end_date,
            thresholds=thresholds,
            payload=payload,
            run_id=run_id,
            captured_at=captured_at,
            system_user=system_user,
            audit=audit,
            is_feature_enabled_fn=is_feature_enabled,
            parse_recoverable_errors=ACCEPTANCE_PARSE_RECOVERABLE_ERRORS,
            capture_recoverable_errors=ACCEPTANCE_CAPTURE_RECOVERABLE_ERRORS,
            logger_obj=logger,
        )

        integration_summary = await run_passive_integration_checks(
            db=db,
            tenant_id=tenant_id,
            tier=tier,
            run_id=run_id,
            captured_at=captured_at,
            system_user_email=system_user.email,
            audit=audit,
            get_tenant_slack_service_fn=get_tenant_slack_service,
            get_tenant_jira_service_fn=get_tenant_jira_service,
            get_tenant_teams_service_fn=get_tenant_teams_service,
            get_tenant_workflow_dispatchers_fn=get_tenant_workflow_dispatchers,
            integration_event_type_fn=_integration_event_type,
            is_feature_enabled_fn=is_feature_enabled,
            integration_recoverable_errors=ACCEPTANCE_INTEGRATION_RECOVERABLE_ERRORS,
            evaluate_tenancy_passive_check_fn=_evaluate_tenancy_passive_check,
            coerce_positive_int_fn=lambda value, default: _coerce_positive_int(
                value, default=default
            ),
            get_settings_fn=get_settings,
            logger_obj=logger,
        )

        return {
            "status": "completed",
            "tenant_id": str(tenant_id),
            "run_id": run_id,
            "captured_at": captured_at,
            "tier": tier.value,
            "acceptance_kpis_captured": capture_result.kpi_success,
            "close_package_capture_requested": capture_result.close_capture_requested,
            "close_package_captured": capture_result.close_capture_success
            if capture_result.close_capture_requested
            else False,
            "close_package_error": capture_result.close_capture_error,
            "integrations": {
                "overall_status": integration_summary.overall_status,
                "passed": integration_summary.passed,
                "failed": integration_summary.failed,
                "results": integration_summary.results,
            },
        }
