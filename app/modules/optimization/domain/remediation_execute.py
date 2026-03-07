from __future__ import annotations

import time
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.remediation import RemediationRequest, RemediationStatus
from app.modules.governance.domain.security.remediation_policy import PolicyDecision, RemediationPolicyEngine
from app.modules.optimization.domain.remediation_execute_helpers import (
    apply_execution_result,
    build_remediation_context,
    coerce_remediation_action,
    handle_policy_decision,
    maybe_schedule_grace_period_execution,
    normalize_estimated_savings,
    resolve_execution_region,
    should_notify_completion_workflow,
)
from app.shared.core.constants import SYSTEM_USER_ID
from app.shared.core.exceptions import (
    ExternalAPIError,
    KillSwitchTriggeredError,
    ResourceNotFoundError,
)
from app.shared.core.ops_metrics import REMEDIATION_DURATION_SECONDS
from app.shared.core.pricing import PricingTier
from app.shared.core.security_metrics import REMEDIATION_TOTAL
from app.shared.core.provider import normalize_provider

logger = structlog.get_logger()
_REMEDIATION_COMMON_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    ValueError,
    TypeError,
    KeyError,
    LookupError,
    AttributeError,
)
REMEDIATION_TIER_LOOKUP_RECOVERABLE_EXCEPTIONS = (
    _REMEDIATION_COMMON_RECOVERABLE_EXCEPTIONS
)
REMEDIATION_ACTION_PARSE_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (ValueError, TypeError, AttributeError)
REMEDIATION_EXECUTION_RECOVERABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    ExternalAPIError,
    KillSwitchTriggeredError,
    *_REMEDIATION_COMMON_RECOVERABLE_EXCEPTIONS,
)

async def execute_remediation_request(
    service: Any,
    request_id: UUID,
    tenant_id: UUID,
    *,
    bypass_grace_period: bool = False,
) -> RemediationRequest:
    start_time = time.time()
    from app.modules.optimization.domain import remediation as remediation_module

    result = await service.db.execute(
        select(RemediationRequest)
        .where(RemediationRequest.id == request_id)
        .where(RemediationRequest.tenant_id == tenant_id)
        .with_for_update()
    )
    request = cast(RemediationRequest | None, await service._scalar_one_or_none(result))

    if not request:
        raise ResourceNotFoundError(f"Request {request_id} not found")

    try:
        tenant_tier = await remediation_module.get_tenant_tier(tenant_id, service.db)
    except REMEDIATION_TIER_LOOKUP_RECOVERABLE_EXCEPTIONS as exc:
        logger.warning(
            "tenant_tier_lookup_failed_in_execute",
            tenant_id=str(tenant_id),
            error=str(exc),
        )
        tenant_tier = PricingTier.FREE

    tier_value = (
        tenant_tier.value if isinstance(tenant_tier, PricingTier) else str(tenant_tier)
    )
    resource_id = str(getattr(request, "resource_id", "") or "")
    resource_type = str(getattr(request, "resource_type", "unknown") or "unknown")
    provider = normalize_provider(getattr(request, "provider", None))
    if not provider:
        raise ValueError("Invalid or missing provider on remediation request")
    actor_id = str(getattr(request, "reviewed_by_user_id", None) or SYSTEM_USER_ID)

    action = coerce_remediation_action(
        request,
        recoverable_errors=REMEDIATION_ACTION_PARSE_RECOVERABLE_EXCEPTIONS,
    )
    action_value = action.value

    savings_value = normalize_estimated_savings(
        getattr(request, "estimated_monthly_savings", Decimal("0"))
    )

    audit_logger = remediation_module.AuditLogger(
        db=service.db, tenant_id=str(tenant_id)
    )
    grace_period_bypassed = False

    try:
        safety = remediation_module.SafetyGuardrailService(service.db)
        await safety.check_all_guards(tenant_id, savings_value)

        if request.status != RemediationStatus.APPROVED:
            if request.status == RemediationStatus.SCHEDULED:
                now = datetime.now(timezone.utc)
                scheduled_execution_at = getattr(request, "scheduled_execution_at", None)
                if scheduled_execution_at and now < scheduled_execution_at:
                    if not bypass_grace_period:
                        logger.info(
                            "remediation_execution_deferred_grace_period",
                            request_id=str(request_id),
                            remaining_minutes=(scheduled_execution_at - now).total_seconds() / 60,
                        )
                        return request
                    grace_period_bypassed = True
                    logger.warning(
                        "remediation_grace_period_bypassed",
                        request_id=str(request_id),
                        scheduled_execution_at=scheduled_execution_at.isoformat(),
                    )
            else:
                raise ValueError(
                    f"Request must be approved or scheduled (current: {request.status.value})"
                )

        policy_config, remediation_settings = await service._build_policy_config(
            tenant_id
        )

        system_policy_context = await service._apply_system_policy_context(
            request,
            tenant_id=tenant_id,
            provider=provider,
            connection_id=getattr(request, "connection_id", None),
        )
        policy_evaluation = RemediationPolicyEngine().evaluate(request, policy_config)
        policy_details: dict[str, Any] = {
            "request_id": str(request_id),
            "action": action_value,
            "stage": "pre_execution",
            "tier": tier_value,
            "policy": policy_evaluation.to_dict(),
            "policy_context_source": (
                system_policy_context.get("source")
                if system_policy_context
                else None
            ),
        }
        await audit_logger.log(
            event_type=remediation_module.AuditEventType.POLICY_EVALUATED,
            actor_id=actor_id,
            resource_id=resource_id,
            resource_type=resource_type,
            success=True,
            details=policy_details,
        )

        if policy_evaluation.decision in {
            PolicyDecision.WARN,
            PolicyDecision.BLOCK,
            PolicyDecision.ESCALATE,
        }:
            handled = await handle_policy_decision(
                request=request,
                policy_evaluation=policy_evaluation,
                policy_details=policy_details,
                request_id=request_id,
                actor_id=actor_id,
                resource_id=resource_id,
                resource_type=resource_type,
                action_value=action_value,
                tenant_id=tenant_id,
                tenant_tier=tenant_tier,
                remediation_settings=remediation_settings,
                db=service.db,
                audit_logger=audit_logger,
                remediation_module=remediation_module,
                logger=logger,
            )
            if handled:
                return request

        if await maybe_schedule_grace_period_execution(
            request=request,
            action=action,
            remediation_settings=remediation_settings,
            request_id=request_id,
            tenant_id=tenant_id,
            action_value=action_value,
            actor_id=actor_id,
            resource_id=resource_id,
            resource_type=resource_type,
            db=service.db,
            audit_logger=audit_logger,
            remediation_module=remediation_module,
            logger=logger,
            bypass_grace_period=bypass_grace_period,
        ):
            return request

        request.status = RemediationStatus.EXECUTING
        await service.db.commit()

        await audit_logger.log(
            event_type=remediation_module.AuditEventType.REMEDIATION_EXECUTION_STARTED,
            actor_id=actor_id,
            resource_id=resource_id,
            resource_type=resource_type,
            success=True,
            details={
                "request_id": str(request_id),
                "action": action_value,
                "triggered_by": "background_worker",
                "grace_period_bypassed": grace_period_bypassed,
            },
        )

        credentials = await service._resolve_credentials(request)
        execution_region = await resolve_execution_region(
            service=service,
            request=request,
            provider=provider,
            tenant_id=tenant_id,
            credentials=credentials,
        )
        context = build_remediation_context(
            service=service,
            tenant_id=tenant_id,
            tier_value=tier_value,
            execution_region=execution_region,
            credentials=credentials,
            request=request,
        )

        strategy = remediation_module.RemediationActionFactory.get_strategy(
            provider, action
        )
        execution_result = await strategy.execute(resource_id, context)

        apply_execution_result(request=request, execution_result=execution_result)

        logger.info(
            "remediation_executed",
            request_id=str(request_id),
            resource=resource_id,
            status=request.status.value,
        )

        await audit_logger.log(
            event_type=remediation_module.AuditEventType.REMEDIATION_EXECUTED,
            actor_id=actor_id,
            resource_id=resource_id,
            resource_type=resource_type,
            success=request.status == RemediationStatus.COMPLETED,
            error_message=request.execution_error,
            details={
                "request_id": str(request_id),
                "action": action_value,
                "execution_status": execution_result.status.value,
                "backup_id": request.backup_resource_id,
                "savings": float(savings_value),
            },
        )

        duration = time.time() - start_time
        REMEDIATION_DURATION_SECONDS.labels(
            action=action_value, provider=provider
        ).observe(duration)

    except REMEDIATION_EXECUTION_RECOVERABLE_EXCEPTIONS as exc:
        request.status = RemediationStatus.FAILED
        request.execution_error = str(exc)[:500]

        await audit_logger.log(
            event_type=remediation_module.AuditEventType.REMEDIATION_FAILED,
            actor_id=actor_id,
            resource_id=resource_id,
            resource_type=resource_type,
            success=False,
            error_message=str(exc),
            details={"request_id": str(request_id), "action": action_value},
        )

        logger.error(
            "remediation_failed",
            request_id=str(request_id),
            error=str(exc),
        )

    await service.db.commit()
    await service.db.refresh(request)

    if request.status == RemediationStatus.COMPLETED:
        REMEDIATION_TOTAL.labels(
            status="success",
            resource_type=resource_type,
            action=action_value,
        ).inc()

        from app.shared.core.notifications import NotificationDispatcher

        await NotificationDispatcher.notify_remediation_completed(
            tenant_id=str(tenant_id),
            resource_id=resource_id,
            action=action_value,
            savings=float(savings_value),
            request_id=str(request_id),
            provider=provider,
            notify_workflow=should_notify_completion_workflow(tenant_tier),
            db=service.db,
        )

    return request
