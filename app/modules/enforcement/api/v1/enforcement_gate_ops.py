from __future__ import annotations

from decimal import Decimal, InvalidOperation
import hashlib
import json
from typing import Any, Callable, Mapping

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enforcement import EnforcementSource
from app.modules.enforcement.api.v1.schemas import (
    CloudEventGateRequest,
    GateDecisionResponse,
    GateRequest,
)
from app.modules.enforcement.domain.service_models import GateInput
from app.shared.core.auth import CurrentUser


def _gate_timeout_seconds(*, get_settings_fn: Callable[[], Any]) -> float:
    raw = getattr(get_settings_fn(), "ENFORCEMENT_GATE_TIMEOUT_SECONDS", 2.0)
    try:
        timeout_seconds = float(raw)
    except (TypeError, ValueError):
        timeout_seconds = 2.0
    return max(0.05, min(timeout_seconds, 30.0))


def _enforcement_global_gate_limit(
    _: Request, *, get_settings_fn: Callable[[], Any]
) -> str:
    settings = get_settings_fn()
    if not bool(getattr(settings, "ENFORCEMENT_GLOBAL_ABUSE_GUARD_ENABLED", True)):
        return "1000000/minute"
    raw_cap = getattr(settings, "ENFORCEMENT_GLOBAL_GATE_PER_MINUTE_CAP", 1200)
    try:
        cap = int(raw_cap)
    except (TypeError, ValueError):
        cap = 1200
    cap = max(1, min(cap, 100000))
    return f"{cap}/minute"


def _metric_reason(value: str) -> str:
    normalized = str(value or "").strip().lower()
    if not normalized:
        return "unknown"
    safe = "".join(
        ch if (ch.isalnum() or ch in {"_", "-", "."}) else "_" for ch in normalized
    )
    return safe[:64] or "unknown"


def _http_detail_mapping(detail: Any) -> dict[str, Any]:
    if not isinstance(detail, dict):
        return {}
    return {str(key): detail[key] for key in detail if str(key).strip()}


def _lock_failure_reason_from_http_exception(exc: HTTPException) -> str | None:
    detail = _http_detail_mapping(exc.detail)
    code = str(detail.get("code") or "").strip().lower()
    if code in {"gate_lock_timeout", "gate_lock_contended"}:
        return code
    return None


def _build_gate_input(
    *,
    payload: GateRequest,
    idempotency_key: str | None,
) -> GateInput:
    return GateInput(
        project_id=str(payload.project_id).strip().lower() or "default",
        environment=payload.environment,
        action=str(payload.action).strip().lower(),
        resource_reference=str(payload.resource_reference).strip(),
        estimated_monthly_delta_usd=payload.estimated_monthly_delta_usd,
        estimated_hourly_delta_usd=payload.estimated_hourly_delta_usd,
        metadata=dict(payload.metadata or {}),
        idempotency_key=idempotency_key,
        dry_run=bool(payload.dry_run),
    )


def _annotation_decimal(
    annotations: dict[str, str],
    *,
    key: str,
    default: Decimal,
) -> Decimal:
    raw = str(annotations.get(key, "")).strip()
    if not raw:
        return default
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid admission annotation '{key}'",
        ) from exc


def _cloud_event_data_sha256(value: Any) -> str:
    serialized = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _build_cloud_event_gate_input(
    *,
    payload: CloudEventGateRequest,
    idempotency_key: str | None,
) -> GateInput:
    cloud_event = payload.cloud_event
    resource_reference = (
        str(payload.resource_reference or "").strip()
        or str(cloud_event.subject or "").strip()
        or str(cloud_event.source).strip()
    )
    if not resource_reference:
        raise HTTPException(
            status_code=422,
            detail="CloudEvent resource reference could not be derived",
        )
    metadata = {
        **dict(payload.metadata or {}),
        "cloud_event_id": cloud_event.id,
        "cloud_event_source": cloud_event.source,
        "cloud_event_type": cloud_event.type,
        "cloud_event_specversion": cloud_event.specversion,
        "cloud_event_subject": cloud_event.subject,
        "cloud_event_time": (
            cloud_event.time.isoformat() if cloud_event.time is not None else None
        ),
        "cloud_event_datacontenttype": cloud_event.datacontenttype,
        "cloud_event_dataschema": cloud_event.dataschema,
        "cloud_event_data_sha256": _cloud_event_data_sha256(cloud_event.data),
    }
    extra_attrs = dict(cloud_event.model_extra or {})
    if extra_attrs:
        metadata["cloud_event_extensions"] = {
            str(key): extra_attrs[key] for key in sorted(extra_attrs.keys())
        }

    return GateInput(
        project_id=str(payload.project_id).strip().lower() or "default",
        environment=payload.environment,
        action=str(payload.action).strip().lower(),
        resource_reference=resource_reference,
        estimated_monthly_delta_usd=payload.estimated_monthly_delta_usd,
        estimated_hourly_delta_usd=payload.estimated_hourly_delta_usd,
        metadata=metadata,
        idempotency_key=idempotency_key,
        dry_run=bool(payload.dry_run),
    )


def _extract_k8s_labels_annotations(
    obj: dict[str, Any] | None,
) -> tuple[dict[str, str], dict[str, str], str, str]:
    metadata = obj.get("metadata") if isinstance(obj, dict) else {}
    metadata = metadata if isinstance(metadata, dict) else {}
    labels_raw = metadata.get("labels")
    annotations_raw = metadata.get("annotations")
    labels = labels_raw if isinstance(labels_raw, dict) else {}
    annotations = annotations_raw if isinstance(annotations_raw, dict) else {}
    name = str(metadata.get("name") or "").strip()
    namespace = str(metadata.get("namespace") or "").strip()
    return (
        {str(k): str(v) for k, v in labels.items()},
        {str(k): str(v) for k, v in annotations.items()},
        name,
        namespace,
    )


async def _run_gate_input_impl(
    *,
    source: EnforcementSource,
    gate_input: GateInput,
    expected_request_fingerprint: str | None,
    current_user: CurrentUser,
    db: AsyncSession,
    tenant_or_403_fn: Callable[[CurrentUser], Any],
    enforcement_service_cls: type[Any],
    gate_result_to_response_fn: Callable[[Any], Mapping[str, Any]],
    gate_timeout_seconds_fn: Callable[[], float],
    lock_failure_reason_from_http_exception_fn: Callable[[HTTPException], str | None],
    http_detail_mapping_fn: Callable[[Any], dict[str, Any]],
    metric_reason_fn: Callable[[str], str],
    gate_evaluation_recoverable_exceptions: tuple[type[Exception], ...],
    gate_decisions_total_metric: Any,
    gate_decision_reasons_total_metric: Any,
    gate_failures_total_metric: Any,
    gate_latency_seconds_metric: Any,
    logger_obj: Any,
    wait_for_fn: Callable[..., Any],
    perf_counter_fn: Callable[[], float],
) -> GateDecisionResponse:
    tenant_id = tenant_or_403_fn(current_user)
    started_at = perf_counter_fn()
    metric_path = "normal"

    service = enforcement_service_cls(db)
    normalized_expected_fingerprint = str(expected_request_fingerprint or "").strip().lower()
    if normalized_expected_fingerprint:
        computed_fingerprint = service.compute_request_fingerprint(
            source=source,
            gate_input=gate_input,
        )
        if normalized_expected_fingerprint != computed_fingerprint:
            raise HTTPException(
                status_code=409,
                detail=(
                    "Terraform preflight fingerprint mismatch; "
                    "retry payload does not match expected request fingerprint"
                ),
            )

    timeout_seconds = gate_timeout_seconds_fn()
    try:
        result = await wait_for_fn(
            service.evaluate_gate(
                tenant_id=tenant_id,
                actor_id=current_user.id,
                source=source,
                gate_input=gate_input,
            ),
            timeout=timeout_seconds,
        )
    except TimeoutError:
        metric_path = "failsafe"
        gate_failures_total_metric.labels(
            source=source.value,
            failure_type="timeout",
        ).inc()
        logger_obj.warning(
            "enforcement_gate_timeout_fallback",
            tenant_id=str(tenant_id),
            source=source.value,
            timeout_seconds=timeout_seconds,
        )
        result = await service.resolve_fail_safe_gate(
            tenant_id=tenant_id,
            actor_id=current_user.id,
            source=source,
            gate_input=gate_input,
            failure_reason_code="gate_timeout",
            failure_metadata={"timeout_seconds": f"{timeout_seconds:.3f}"},
        )
    except HTTPException as exc:
        lock_reason_code = lock_failure_reason_from_http_exception_fn(exc)
        if lock_reason_code is None:
            raise

        metric_path = "failsafe"
        gate_failures_total_metric.labels(
            source=source.value,
            failure_type=(
                "lock_timeout"
                if lock_reason_code == "gate_lock_timeout"
                else "lock_contended"
            ),
        ).inc()
        detail = http_detail_mapping_fn(exc.detail)
        logger_obj.warning(
            "enforcement_gate_lock_fallback",
            tenant_id=str(tenant_id),
            source=source.value,
            reason=lock_reason_code,
            http_status_code=int(exc.status_code),
            lock_timeout_seconds=detail.get("lock_timeout_seconds"),
            lock_wait_seconds=detail.get("lock_wait_seconds"),
        )
        result = await service.resolve_fail_safe_gate(
            tenant_id=tenant_id,
            actor_id=current_user.id,
            source=source,
            gate_input=gate_input,
            failure_reason_code=lock_reason_code,
            failure_metadata={
                "http_status_code": int(exc.status_code),
                **detail,
            },
        )
    except gate_evaluation_recoverable_exceptions as exc:
        metric_path = "failsafe"
        gate_failures_total_metric.labels(
            source=source.value,
            failure_type="evaluation_error",
        ).inc()
        logger_obj.exception(
            "enforcement_gate_failure_fallback",
            tenant_id=str(tenant_id),
            source=source.value,
            error_type=type(exc).__name__,
        )
        result = await service.resolve_fail_safe_gate(
            tenant_id=tenant_id,
            actor_id=current_user.id,
            source=source,
            gate_input=gate_input,
            failure_reason_code="gate_evaluation_error",
            failure_metadata={"error_type": type(exc).__name__},
        )

    gate_decisions_total_metric.labels(
        source=source.value,
        decision=result.decision.decision.value,
        path=metric_path,
    ).inc()
    for reason in list(result.decision.reason_codes or [])[:8]:
        gate_decision_reasons_total_metric.labels(
            source=source.value,
            reason=metric_reason_fn(reason),
        ).inc()
    gate_latency_seconds_metric.labels(
        source=source.value,
        path=metric_path,
    ).observe(max(0.0, perf_counter_fn() - started_at))

    return GateDecisionResponse(**gate_result_to_response_fn(result))
