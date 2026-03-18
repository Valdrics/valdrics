from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, cast
from uuid import UUID, uuid4

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.optimization import (
    FindingSource,
    FindingStatus,
    OptimizationFinding,
)
from app.shared.core.exceptions import ResourceNotFoundError, ValdricsException
from app.shared.core.provider import normalize_provider

logger = structlog.get_logger()

FINDING_PERSISTENCE_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    KeyError,
    LookupError,
    AttributeError,
)
_NON_ACTIONABLE_BUCKETS = {
    "errors",
    "scan_completeness",
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _coerce_uuid(value: Any) -> UUID | None:
    if isinstance(value, UUID):
        return value
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        try:
            return UUID(raw)
        except ValueError:
            return None
    return None


def _coerce_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (ValueError, TypeError, ArithmeticError):
        return None


def _normalize_region(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return normalized or "global"


def _snapshot_payload(item: dict[str, Any]) -> dict[str, Any]:
    payload = dict(item)
    payload.pop("finding_id", None)
    payload.pop("finding_status", None)
    return payload


def build_finding_fingerprint(
    *,
    source: str,
    provider: str,
    connection_id: UUID,
    category: str,
    region: str,
    resource_id: str,
    resource_type: str,
) -> str:
    canonical = json.dumps(
        {
            "source": source,
            "provider": provider,
            "connection_id": str(connection_id),
            "category": category,
            "region": region,
            "resource_id": resource_id,
            "resource_type": resource_type,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_request_finding_snapshot(finding: OptimizationFinding) -> dict[str, Any]:
    return {
        "finding_id": str(finding.id),
        "source": (
            finding.source.value
            if hasattr(finding.source, "value")
            else str(finding.source or "")
        ),
        "status": (
            finding.status.value
            if hasattr(finding.status, "value")
            else str(finding.status or "")
        ),
        "fingerprint": str(finding.fingerprint or ""),
        "provider": str(finding.provider or ""),
        "category": str(finding.category or ""),
        "connection_id": str(finding.connection_id),
        "connection_name": str(finding.connection_name or ""),
        "resource_id": str(finding.resource_id or ""),
        "resource_type": str(finding.resource_type or ""),
        "region": str(finding.region or "global"),
        "estimated_monthly_savings": (
            str(finding.estimated_monthly_savings)
            if finding.estimated_monthly_savings is not None
            else None
        ),
        "confidence_score": (
            float(finding.confidence_score)
            if finding.confidence_score is not None
            else None
        ),
        "explainability_notes": str(finding.explainability_notes or "")
        if finding.explainability_notes is not None
        else None,
        "requires_manual_review": bool(finding.requires_manual_review),
        "automated_action_allowed": bool(finding.automated_action_allowed),
        "decision_gate": str(finding.decision_gate or "")
        if finding.decision_gate is not None
        else None,
        "payload": dict(finding.payload or {}),
        "first_detected_at": (
            finding.first_detected_at.isoformat()
            if finding.first_detected_at is not None
            else None
        ),
        "last_detected_at": (
            finding.last_detected_at.isoformat()
            if finding.last_detected_at is not None
            else None
        ),
    }


async def get_open_finding_for_tenant(
    service: Any,
    *,
    tenant_id: UUID,
    finding_id: UUID,
    source: FindingSource = FindingSource.ZOMBIE_SCAN,
) -> OptimizationFinding:
    try:
        finding = cast(
            OptimizationFinding,
            await service.get_by_id(OptimizationFinding, finding_id, tenant_id),
        )
    except ResourceNotFoundError as exc:
        raise ResourceNotFoundError(
            f"Finding {finding_id} not found for this tenant.",
            code="optimization_finding_not_found",
        ) from exc

    if finding.source != source:
        raise ValdricsException(
            message="Finding source is not valid for this remediation flow.",
            code="optimization_finding_invalid_source",
            status_code=400,
            details={"finding_id": str(finding_id)},
        )
    if finding.status != FindingStatus.OPEN:
        raise ValdricsException(
            message="Finding is no longer open for remediation.",
            code="optimization_finding_resolved",
            status_code=409,
            details={"finding_id": str(finding_id)},
        )
    return finding


async def validate_request_finding_binding(
    service: Any,
    *,
    tenant_id: UUID,
    request: Any,
) -> OptimizationFinding | None:
    finding_id = _coerce_uuid(getattr(request, "finding_id", None))
    snapshot_candidate = getattr(request, "finding_snapshot", None)
    snapshot_raw = (
        snapshot_candidate if isinstance(snapshot_candidate, dict) else None
    )
    if finding_id is None and snapshot_raw is None:
        return None

    if snapshot_raw is None:
        raise ValdricsException(
            message="Remediation request is missing its immutable finding snapshot.",
            code="remediation_finding_snapshot_missing",
            status_code=409,
        )

    expected_provider = normalize_provider(snapshot_raw.get("provider"))
    current_provider = normalize_provider(getattr(request, "provider", None))
    expected_connection_id = _coerce_uuid(snapshot_raw.get("connection_id"))
    current_connection_id = getattr(request, "connection_id", None)
    expected_region = _normalize_region(snapshot_raw.get("region"))
    current_region = _normalize_region(getattr(request, "region", None))
    expected_resource_id = str(snapshot_raw.get("resource_id") or "").strip()
    current_resource_id = str(getattr(request, "resource_id", "") or "").strip()
    expected_resource_type = str(snapshot_raw.get("resource_type") or "").strip()
    current_resource_type = str(getattr(request, "resource_type", "") or "").strip()

    mismatches: dict[str, dict[str, Any]] = {}
    if expected_provider != current_provider:
        mismatches["provider"] = {"expected": expected_provider, "actual": current_provider}
    if expected_connection_id != current_connection_id:
        mismatches["connection_id"] = {
            "expected": str(expected_connection_id) if expected_connection_id else None,
            "actual": str(current_connection_id) if current_connection_id else None,
        }
    if expected_region != current_region:
        mismatches["region"] = {"expected": expected_region, "actual": current_region}
    if expected_resource_id != current_resource_id:
        mismatches["resource_id"] = {
            "expected": expected_resource_id,
            "actual": current_resource_id,
        }
    if expected_resource_type != current_resource_type:
        mismatches["resource_type"] = {
            "expected": expected_resource_type,
            "actual": current_resource_type,
        }
    if mismatches:
        raise ValdricsException(
            message="Remediation request no longer matches its bound finding context.",
            code="remediation_finding_context_mismatch",
            status_code=409,
            details={"mismatches": mismatches},
        )

    if finding_id is None:
        return None

    finding = await get_open_finding_for_tenant(
        service,
        tenant_id=tenant_id,
        finding_id=finding_id,
    )

    snapshot_fingerprint = str(snapshot_raw.get("fingerprint") or "").strip()
    if snapshot_fingerprint and snapshot_fingerprint != str(finding.fingerprint or ""):
        raise ValdricsException(
            message="Remediation finding has drifted from the approved snapshot.",
            code="remediation_finding_drifted",
            status_code=409,
            details={
                "finding_id": str(finding_id),
                "snapshot_fingerprint": snapshot_fingerprint,
                "current_fingerprint": str(finding.fingerprint or ""),
            },
        )
    return finding


async def persist_scan_findings(
    service: Any,
    *,
    tenant_id: UUID,
    scan_payload: dict[str, Any],
) -> None:
    now = _utcnow()
    scopes: set[tuple[str, UUID, str]] = set()
    normalized_items: list[tuple[str, dict[str, Any], dict[str, Any]]] = []

    completeness_rows = scan_payload.get("scan_completeness")
    if isinstance(completeness_rows, list):
        for summary in completeness_rows:
            if not isinstance(summary, dict):
                continue
            provider = normalize_provider(summary.get("provider"))
            connection_id = _coerce_uuid(summary.get("connection_id"))
            if not provider or connection_id is None:
                continue
            scopes.add((provider, connection_id, _normalize_region(summary.get("region"))))

    for category, bucket in scan_payload.items():
        if category in _NON_ACTIONABLE_BUCKETS or not isinstance(bucket, list):
            continue
        for item in bucket:
            if not isinstance(item, dict):
                continue
            provider = normalize_provider(item.get("provider"))
            connection_id = _coerce_uuid(item.get("connection_id"))
            resource_id = str(item.get("resource_id") or item.get("id") or "").strip()
            if not provider or connection_id is None or not resource_id:
                continue
            resource_type = str(item.get("resource_type") or category).strip() or category
            region = _normalize_region(item.get("region"))
            fingerprint = build_finding_fingerprint(
                source=FindingSource.ZOMBIE_SCAN.value,
                provider=provider,
                connection_id=connection_id,
                category=category,
                region=region,
                resource_id=resource_id,
                resource_type=resource_type,
            )
            scopes.add((provider, connection_id, region))
            normalized: dict[str, Any] = {
                "provider": provider,
                "connection_id": connection_id,
                "connection_name": str(item.get("connection_name") or "").strip() or None,
                "category": category,
                "resource_id": resource_id,
                "resource_type": resource_type,
                "region": region,
                "estimated_monthly_savings": _coerce_decimal(
                    item.get("estimated_monthly_savings", item.get("monthly_cost"))
                ),
                "confidence_score": _coerce_decimal(item.get("confidence_score")),
                "explainability_notes": (
                    str(item.get("explainability_notes")).strip()
                    if item.get("explainability_notes") is not None
                    else None
                ),
                "requires_manual_review": bool(item.get("requires_manual_review", False)),
                "automated_action_allowed": bool(
                    item.get("automated_action_allowed", True)
                ),
                "decision_gate": (
                    str(item.get("decision_gate")).strip()
                    if item.get("decision_gate") is not None
                    else None
                ),
                "payload": _snapshot_payload(item),
                "fingerprint": fingerprint,
            }
            normalized_items.append((category, item, normalized))

    connection_ids = {connection_id for _provider, connection_id, _region in scopes}
    existing_rows: list[OptimizationFinding] = []
    if connection_ids:
        query_result = await service.db.execute(
            select(OptimizationFinding).where(
                OptimizationFinding.tenant_id == tenant_id,
                OptimizationFinding.source == FindingSource.ZOMBIE_SCAN,
                OptimizationFinding.connection_id.in_(list(connection_ids)),
            )
        )
        scalar_result = query_result.scalars()
        existing_rows = [
            row
            for row in list(
                scalar_result.all() if hasattr(scalar_result, "all") else scalar_result
            )
            if isinstance(row, OptimizationFinding)
        ]

    existing_by_fingerprint = {
        str(row.fingerprint): row for row in existing_rows if row.fingerprint
    }
    seen_fingerprints: set[str] = set()

    for _category, item, normalized in normalized_items:
        fingerprint = str(normalized["fingerprint"])
        finding = existing_by_fingerprint.get(fingerprint)
        connection_id = cast(UUID, normalized["connection_id"])
        connection_name = cast(str | None, normalized["connection_name"])
        estimated_monthly_savings = cast(
            Decimal | None,
            normalized["estimated_monthly_savings"],
        )
        confidence_score = cast(Decimal | None, normalized["confidence_score"])
        explainability_notes = cast(str | None, normalized["explainability_notes"])
        decision_gate = cast(str | None, normalized["decision_gate"])
        payload = cast(dict[str, Any], normalized["payload"])
        if finding is None:
            finding = OptimizationFinding(
                id=uuid4(),
                tenant_id=tenant_id,
                source=FindingSource.ZOMBIE_SCAN,
                status=FindingStatus.OPEN,
                fingerprint=fingerprint,
                provider=str(normalized["provider"]),
                category=str(normalized["category"]),
                connection_id=connection_id,
                connection_name=connection_name,
                resource_id=str(normalized["resource_id"]),
                resource_type=str(normalized["resource_type"]),
                region=str(normalized["region"]),
                estimated_monthly_savings=estimated_monthly_savings,
                confidence_score=confidence_score,
                explainability_notes=explainability_notes,
                requires_manual_review=bool(normalized["requires_manual_review"]),
                automated_action_allowed=bool(normalized["automated_action_allowed"]),
                decision_gate=decision_gate,
                payload=dict(payload),
                first_detected_at=now,
                last_detected_at=now,
                resolved_at=None,
            )
            service.db.add(finding)
            existing_by_fingerprint[fingerprint] = finding
        else:
            finding.status = FindingStatus.OPEN
            finding.provider = str(normalized["provider"])
            finding.category = str(normalized["category"])
            finding.connection_id = connection_id
            finding.connection_name = connection_name
            finding.resource_id = str(normalized["resource_id"])
            finding.resource_type = str(normalized["resource_type"])
            finding.region = str(normalized["region"])
            finding.estimated_monthly_savings = estimated_monthly_savings
            finding.confidence_score = confidence_score
            finding.explainability_notes = explainability_notes
            finding.requires_manual_review = bool(normalized["requires_manual_review"])
            finding.automated_action_allowed = bool(
                normalized["automated_action_allowed"]
            )
            finding.decision_gate = decision_gate
            finding.payload = dict(payload)
            finding.last_detected_at = now
            finding.resolved_at = None

        seen_fingerprints.add(fingerprint)
        item["finding_id"] = str(finding.id)
        item["finding_status"] = FindingStatus.OPEN.value

    if not bool(scan_payload.get("partial_results")):
        for row in existing_rows:
            scope = (
                normalize_provider(row.provider) or str(row.provider),
                row.connection_id,
                _normalize_region(row.region),
            )
            if scope not in scopes:
                continue
            if row.fingerprint in seen_fingerprints:
                continue
            if row.status == FindingStatus.RESOLVED:
                continue
            row.status = FindingStatus.RESOLVED
            row.resolved_at = now


async def persist_scan_findings_with_guard(
    service: Any,
    *,
    tenant_id: UUID,
    scan_payload: dict[str, Any],
) -> None:
    try:
        await persist_scan_findings(
            service,
            tenant_id=tenant_id,
            scan_payload=scan_payload,
        )
        await service.db.commit()
    except FINDING_PERSISTENCE_RECOVERABLE_EXCEPTIONS as exc:
        await service.db.rollback()
        logger.exception(
            "optimization_finding_persistence_failed",
            tenant_id=str(tenant_id),
            error=str(exc),
        )
        raise ValdricsException(
            message="Failed to persist actionable findings for this scan.",
            code="optimization_finding_persistence_failed",
            status_code=500,
        ) from exc
