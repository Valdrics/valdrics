"""Acceptance-suite evidence capture operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.governance.domain.security.audit_log import AuditEventType, AuditLogger
from app.shared.core.auth import CurrentUser
from app.shared.core.pricing import FeatureFlag, PricingTier


@dataclass(slots=True)
class AcceptanceArtifactCaptureResult:
    """Outcome summary for evidence artifacts captured during a job run."""

    kpi_success: bool
    close_capture_requested: bool
    close_capture_success: bool
    close_capture_error: str | None


@dataclass(slots=True)
class AcceptanceKpiThresholds:
    """Configurable threshold inputs used for KPI capture."""

    ingestion_window_hours: int
    ingestion_target_success_rate_percent: float
    recency_target_hours: int
    chargeback_target_percent: float
    max_unit_anomalies: int


def parse_capture_window(
    payload: dict[str, Any],
    *,
    iso_date_parser: Callable[[object], date],
) -> tuple[date, date]:
    """Resolve capture date window from payload with sane defaults."""
    end_date = (
        iso_date_parser(payload.get("end_date"))
        if payload.get("end_date")
        else date.today()
    )
    start_date = (
        iso_date_parser(payload.get("start_date"))
        if payload.get("start_date")
        else end_date - timedelta(days=30)
    )
    return start_date, end_date


def parse_kpi_thresholds(payload: dict[str, Any]) -> AcceptanceKpiThresholds:
    """Parse KPI thresholds from payload with deterministic defaults."""
    return AcceptanceKpiThresholds(
        ingestion_window_hours=int(payload.get("ingestion_window_hours", 24 * 7)),
        ingestion_target_success_rate_percent=float(
            payload.get("ingestion_target_success_rate_percent", 95.0)
        ),
        recency_target_hours=int(payload.get("recency_target_hours", 48)),
        chargeback_target_percent=float(payload.get("chargeback_target_percent", 90.0)),
        max_unit_anomalies=int(payload.get("max_unit_anomalies", 0)),
    )


def build_system_user(tenant_id: UUID, tier: PricingTier) -> CurrentUser:
    """Construct a synthetic admin principal for tier-aware service computations."""
    from app.models.tenant import UserPersona, UserRole

    return CurrentUser(
        id=uuid4(),
        email="system@valdrics.local",
        tenant_id=tenant_id,
        role=UserRole.ADMIN,
        tier=tier,
        persona=UserPersona.PLATFORM,
    )


def parse_requested_flag(value: object) -> bool:
    """Parse boolean-like payload flags from API and scheduler inputs."""
    return value is True or str(value).strip().lower() in {"1", "true", "yes", "y"}


async def capture_acceptance_artifacts(
    *,
    db: AsyncSession,
    tenant_id: UUID,
    tier: PricingTier,
    start_date: date,
    end_date: date,
    thresholds: AcceptanceKpiThresholds,
    payload: dict[str, Any],
    run_id: str,
    captured_at: str,
    system_user: CurrentUser,
    audit: AuditLogger,
    is_feature_enabled_fn: Callable[[PricingTier, FeatureFlag], bool],
    parse_recoverable_errors: tuple[type[Exception], ...],
    capture_recoverable_errors: tuple[type[Exception], ...],
    logger_obj: Any,
) -> AcceptanceArtifactCaptureResult:
    """Capture KPI/leadership/quarterly/close evidence and persist audit records."""
    kpi_success = True
    kpi_error: str | None = None
    acceptance_payload: Any | None = None
    try:
        from app.modules.reporting.api.v1.costs import _compute_acceptance_kpis_payload

        acceptance_payload = await _compute_acceptance_kpis_payload(
            start_date=start_date,
            end_date=end_date,
            ingestion_window_hours=thresholds.ingestion_window_hours,
            ingestion_target_success_rate_percent=thresholds.ingestion_target_success_rate_percent,
            recency_target_hours=thresholds.recency_target_hours,
            chargeback_target_percent=thresholds.chargeback_target_percent,
            max_unit_anomalies=thresholds.max_unit_anomalies,
            current_user=system_user,
            db=db,
        )
    except capture_recoverable_errors as exc:
        kpi_success = False
        kpi_error = str(exc)
        logger_obj.warning(
            "acceptance_kpi_capture_failed",
            tenant_id=str(tenant_id),
            error=kpi_error,
        )

    await audit.log(
        event_type=AuditEventType.ACCEPTANCE_KPIS_CAPTURED,
        actor_id=None,
        actor_email=system_user.email,
        resource_type="acceptance_kpis",
        resource_id=f"{start_date.isoformat()}:{end_date.isoformat()}",
        details={
            "run_id": run_id,
            "captured_at": captured_at,
            "thresholds": {
                "ingestion_window_hours": thresholds.ingestion_window_hours,
                "ingestion_target_success_rate_percent": thresholds.ingestion_target_success_rate_percent,
                "recency_target_hours": thresholds.recency_target_hours,
                "chargeback_target_percent": thresholds.chargeback_target_percent,
                "max_unit_anomalies": thresholds.max_unit_anomalies,
            },
            "tier": tier.value,
            "acceptance_kpis": acceptance_payload.model_dump()
            if acceptance_payload is not None and hasattr(acceptance_payload, "model_dump")
            else acceptance_payload,
            "error": kpi_error,
        },
        success=kpi_success,
        error_message=None if kpi_success else (kpi_error or "KPI capture failed"),
        request_method="JOB",
        request_path="/jobs/acceptance-suite-capture",
    )

    if is_feature_enabled_fn(tier, FeatureFlag.COMPLIANCE_EXPORTS):
        leadership_success = True
        leadership_error: str | None = None
        leadership_payload: Any | None = None
        try:
            from app.modules.reporting.domain.leadership_kpis import LeadershipKpiService

            leadership_payload = await LeadershipKpiService(db).compute(
                tenant_id=tenant_id,
                tier=tier,
                start_date=start_date,
                end_date=end_date,
                provider=None,
                include_preliminary=False,
                top_services_limit=10,
            )
        except capture_recoverable_errors as exc:
            leadership_success = False
            leadership_error = str(exc)
            logger_obj.warning(
                "leadership_kpi_capture_failed",
                tenant_id=str(tenant_id),
                error=leadership_error,
            )

        await audit.log(
            event_type=AuditEventType.LEADERSHIP_KPIS_CAPTURED,
            actor_id=None,
            actor_email=system_user.email,
            resource_type="leadership_kpis",
            resource_id=f"{start_date.isoformat()}:{end_date.isoformat()}",
            details={
                "run_id": run_id,
                "captured_at": captured_at,
                "tier": tier.value,
                "leadership_kpis": leadership_payload.model_dump()
                if leadership_payload is not None and hasattr(leadership_payload, "model_dump")
                else leadership_payload,
                "error": leadership_error,
            },
            success=leadership_success,
            error_message=None
            if leadership_success
            else (leadership_error or "Leadership KPI capture failed"),
            request_method="JOB",
            request_path="/jobs/acceptance-suite-capture",
        )

    quarterly_capture_requested = parse_requested_flag(
        payload.get("capture_quarterly_report", False)
    )
    if quarterly_capture_requested:
        if not is_feature_enabled_fn(tier, FeatureFlag.COMPLIANCE_EXPORTS):
            await audit.log(
                event_type=AuditEventType.COMMERCIAL_QUARTERLY_REPORT_CAPTURED,
                actor_id=None,
                actor_email=system_user.email,
                resource_type="commercial_quarterly_report",
                resource_id="previous_quarter",
                details={
                    "run_id": run_id,
                    "captured_at": captured_at,
                    "skipped": True,
                    "reason": "feature_not_enabled",
                    "tier": tier.value,
                },
                success=True,
                request_method="JOB",
                request_path="/jobs/acceptance-suite-capture",
            )
        else:
            quarterly_success = True
            quarterly_error: str | None = None
            quarterly_payload: Any | None = None
            try:
                from app.modules.reporting.domain.commercial_reports import (
                    CommercialProofReportService,
                )

                quarterly_payload = await CommercialProofReportService(db).quarterly_report(
                    tenant_id=tenant_id,
                    tier=tier,
                    period="previous",
                    as_of=end_date,
                    provider=None,
                )
            except capture_recoverable_errors as exc:
                quarterly_success = False
                quarterly_error = str(exc)
                logger_obj.warning(
                    "commercial_quarterly_report_capture_failed",
                    tenant_id=str(tenant_id),
                    error=quarterly_error,
                )

            resource_id = None
            if quarterly_payload is not None and isinstance(
                getattr(quarterly_payload, "year", None), int
            ):
                resource_id = (
                    f"{getattr(quarterly_payload, 'year', 'unknown')}-Q"
                    f"{getattr(quarterly_payload, 'quarter', 'unknown')}"
                )

            await audit.log(
                event_type=AuditEventType.COMMERCIAL_QUARTERLY_REPORT_CAPTURED,
                actor_id=None,
                actor_email=system_user.email,
                resource_type="commercial_quarterly_report",
                resource_id=resource_id or "previous_quarter",
                details={
                    "run_id": run_id,
                    "captured_at": captured_at,
                    "tier": tier.value,
                    "quarterly_report": quarterly_payload.model_dump()
                    if quarterly_payload is not None
                    and hasattr(quarterly_payload, "model_dump")
                    else quarterly_payload,
                    "error": quarterly_error,
                },
                success=quarterly_success,
                error_message=None
                if quarterly_success
                else (
                    quarterly_error
                    or "Quarterly commercial proof report capture failed"
                ),
                request_method="JOB",
                request_path="/jobs/acceptance-suite-capture",
            )

    close_capture_requested = parse_requested_flag(payload.get("capture_close_package", False))
    close_capture_success = False
    close_capture_error: str | None = None
    close_capture_payload: dict[str, Any] | None = None

    if close_capture_requested:
        if not is_feature_enabled_fn(tier, FeatureFlag.CLOSE_WORKFLOW):
            close_capture_payload = {
                "skipped": True,
                "reason": "feature_not_enabled",
                "tier": tier.value,
            }
            close_capture_success = True
        else:
            window_anchor = end_date
            close_end = window_anchor.replace(day=1) - timedelta(days=1)
            close_start = close_end.replace(day=1)
            close_provider = payload.get("close_provider")
            max_restatements_raw = payload.get("close_max_restatement_entries", 25)
            try:
                max_restatements = int(max_restatements_raw)
            except parse_recoverable_errors:
                max_restatements = 25
            if max_restatements < 0:
                max_restatements = 0

            try:
                from app.modules.reporting.domain.reconciliation import (
                    CostReconciliationService,
                )

                service = CostReconciliationService(db)
                package = await service.generate_close_package(
                    tenant_id=tenant_id,
                    start_date=close_start,
                    end_date=close_end,
                    enforce_finalized=False,
                    provider=str(close_provider).strip().lower()
                    if isinstance(close_provider, str) and close_provider
                    else None,
                    max_restatement_entries=max_restatements,
                )
                package.pop("csv", None)
                close_capture_payload = package
                close_capture_success = True
            except capture_recoverable_errors as exc:
                close_capture_error = str(exc)
                logger_obj.warning(
                    "acceptance_close_package_capture_failed",
                    tenant_id=str(tenant_id),
                    error=close_capture_error,
                )

        await audit.log(
            event_type=AuditEventType.ACCEPTANCE_CLOSE_PACKAGE_CAPTURED,
            actor_id=None,
            actor_email=system_user.email,
            resource_type="close_package",
            resource_id="previous_month",
            details={
                "run_id": run_id,
                "captured_at": captured_at,
                "requested": True,
                "payload": close_capture_payload,
                "error": close_capture_error,
            },
            success=close_capture_success,
            error_message=None
            if close_capture_success
            else (close_capture_error or "Close package capture failed"),
            request_method="JOB",
            request_path="/jobs/acceptance-suite-capture",
        )

    return AcceptanceArtifactCaptureResult(
        kpi_success=kpi_success,
        close_capture_requested=close_capture_requested,
        close_capture_success=close_capture_success,
        close_capture_error=close_capture_error,
    )


__all__ = [
    "AcceptanceArtifactCaptureResult",
    "AcceptanceKpiThresholds",
    "build_system_user",
    "capture_acceptance_artifacts",
    "parse_capture_window",
    "parse_kpi_thresholds",
]
