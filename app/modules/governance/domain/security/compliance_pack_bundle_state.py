from datetime import date, datetime, timedelta
from typing import Any, Awaitable, Callable

from app.modules.governance.domain.security.compliance_pack_support import (
    normalize_optional_provider,
    resolve_window,
)

PayloadEvidenceCollector = Callable[..., Awaitable[list[dict[str, Any]]]]


async def collect_payload_evidence_map(
    *,
    db: Any,
    tenant_id: Any,
    evidence_limit: int,
    payload_specs: tuple[tuple[str, str, str, bool], ...],
    collect_payload_evidence: PayloadEvidenceCollector,
) -> dict[str, list[dict[str, Any]]]:
    payload_evidence: dict[str, list[dict[str, Any]]] = {}
    for key, event_type, payload_key, include_thresholds in payload_specs:
        payload_evidence[key] = await collect_payload_evidence(
            db=db,
            tenant_id=tenant_id,
            event_type=event_type,
            payload_key=payload_key,
            limit=int(evidence_limit),
            include_thresholds=include_thresholds,
        )
    return payload_evidence


def default_included_files() -> list[str]:
    return [
        "audit_logs.csv",
        "notification_settings.json",
        "remediation_settings.json",
        "identity_settings.json",
        "integration_acceptance_evidence.json",
        "acceptance_kpis_evidence.json",
        "leadership_kpis_evidence.json",
        "quarterly_commercial_proof_evidence.json",
        "identity_smoke_evidence.json",
        "sso_federation_validation_evidence.json",
        "performance_load_test_evidence.json",
        "ingestion_persistence_benchmark_evidence.json",
        "ingestion_soak_evidence.json",
        "partitioning_evidence.json",
        "job_slo_evidence.json",
        "tenant_isolation_evidence.json",
        "carbon_assurance_evidence.json",
        "carbon_factor_sets.json",
        "carbon_factor_update_logs.json",
    ]


def build_doc_payloads(reference_docs: dict[str, Any]) -> dict[str, str | None]:
    return {
        "docs/integrations/scim.md": reference_docs.get("scim_doc"),
        "docs/integrations/idp_reference_configs.md": reference_docs.get(
            "idp_reference_doc"
        ),
        "docs/integrations/sso.md": reference_docs.get("sso_doc"),
        "docs/integrations/microsoft_teams.md": reference_docs.get("teams_doc"),
        "docs/compliance/compliance_pack.md": reference_docs.get("compliance_pack_doc"),
        "docs/compliance/focus_export.md": reference_docs.get("focus_doc"),
        "docs/ops/acceptance_evidence_capture.md": reference_docs.get("acceptance_doc"),
        "docs/runbooks/month_end_close.md": reference_docs.get("close_runbook_doc"),
        "docs/runbooks/tenant_data_lifecycle.md": reference_docs.get(
            "tenant_lifecycle_doc"
        ),
        "docs/runbooks/partition_maintenance.md": reference_docs.get(
            "partition_maintenance_doc"
        ),
        "docs/licensing.md": reference_docs.get("licensing_doc"),
        "LICENSE": reference_docs.get("license_text"),
        "TRADEMARK_POLICY.md": reference_docs.get("trademark_policy_doc"),
        "COMMERCIAL_LICENSE.md": reference_docs.get("commercial_license_doc"),
    }


def initialize_optional_export_state(
    *,
    include_focus_export: bool,
    focus_include_preliminary: bool,
    focus_max_rows: int,
    include_savings_proof: bool,
    include_realized_savings: bool,
    realized_limit: int,
    include_close_package: bool,
    close_enforce_finalized: bool,
    close_max_restatements: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    focus_export_info: dict[str, Any] = {
        "included": bool(include_focus_export),
        "provider": None,
        "include_preliminary": bool(focus_include_preliminary),
        "max_rows": int(focus_max_rows),
        "rows_written": 0,
        "truncated": False,
        "window": {"start_date": None, "end_date": None},
        "status": "skipped" if not include_focus_export else "pending",
        "error": None,
    }
    savings_proof_info: dict[str, Any] = {
        "included": bool(include_savings_proof),
        "provider": None,
        "window": {"start_date": None, "end_date": None},
        "status": "skipped" if not include_savings_proof else "pending",
        "error": None,
    }
    realized_savings_info: dict[str, Any] = {
        "included": bool(include_realized_savings),
        "provider": None,
        "limit": int(realized_limit),
        "window": {"start_date": None, "end_date": None},
        "status": "skipped" if not include_realized_savings else "pending",
        "error": None,
        "rows_written": 0,
    }
    close_package_info: dict[str, Any] = {
        "included": bool(include_close_package),
        "provider": None,
        "enforce_finalized": bool(close_enforce_finalized),
        "max_restatements": int(close_max_restatements),
        "window": {"start_date": None, "end_date": None},
        "status": "skipped" if not include_close_package else "pending",
        "error": None,
    }
    return (
        focus_export_info,
        savings_proof_info,
        realized_savings_info,
        close_package_info,
    )


def resolve_optional_export_scopes(
    *,
    focus_export_info: dict[str, Any],
    savings_proof_info: dict[str, Any],
    realized_savings_info: dict[str, Any],
    close_package_info: dict[str, Any],
    focus_provider: str | None,
    savings_provider: str | None,
    realized_provider: str | None,
    close_provider: str | None,
    focus_start_date: date | None,
    focus_end_date: date | None,
    savings_start_date: date | None,
    savings_end_date: date | None,
    realized_start_date: date | None,
    realized_end_date: date | None,
    close_start_date: date | None,
    close_end_date: date | None,
    default_start_date: datetime | None,
    default_end_date: datetime | None,
    exported_at: datetime,
) -> dict[str, Any]:
    normalized_focus_provider = normalize_optional_provider(
        provider=focus_provider,
        provider_name="focus_provider",
    )
    focus_export_info["provider"] = normalized_focus_provider

    focus_window_start, focus_window_end = resolve_window(
        start=focus_start_date,
        end=focus_end_date,
        default_start=(default_start_date or (exported_at - timedelta(days=30))).date(),
        default_end=(default_end_date or exported_at).date(),
        error_detail="start_date must be <= end_date",
    )
    focus_export_info["window"] = {
        "start_date": focus_window_start.isoformat(),
        "end_date": focus_window_end.isoformat(),
    }

    normalized_savings_provider = normalize_optional_provider(
        provider=savings_provider,
        provider_name="savings_provider",
    )
    savings_window_start, savings_window_end = resolve_window(
        start=savings_start_date,
        end=savings_end_date,
        default_start=focus_window_start,
        default_end=focus_window_end,
        error_detail="savings_start_date must be <= savings_end_date",
    )
    savings_proof_info["provider"] = normalized_savings_provider
    savings_proof_info["window"] = {
        "start_date": savings_window_start.isoformat(),
        "end_date": savings_window_end.isoformat(),
    }

    normalized_realized_provider = normalize_optional_provider(
        provider=realized_provider,
        provider_name="realized_provider",
    )
    realized_window_start, realized_window_end = resolve_window(
        start=realized_start_date,
        end=realized_end_date,
        default_start=savings_window_start,
        default_end=savings_window_end,
        error_detail="realized_start_date must be <= realized_end_date",
    )
    realized_savings_info["provider"] = normalized_realized_provider
    realized_savings_info["window"] = {
        "start_date": realized_window_start.isoformat(),
        "end_date": realized_window_end.isoformat(),
    }

    normalized_close_provider = normalize_optional_provider(
        provider=close_provider,
        provider_name="close_provider",
    )
    close_window_start, close_window_end = resolve_window(
        start=close_start_date,
        end=close_end_date,
        default_start=focus_window_start,
        default_end=focus_window_end,
        error_detail="close_start_date must be <= close_end_date",
    )
    close_package_info["provider"] = normalized_close_provider
    close_package_info["window"] = {
        "start_date": close_window_start.isoformat(),
        "end_date": close_window_end.isoformat(),
    }
    return {
        "normalized_focus_provider": normalized_focus_provider,
        "normalized_savings_provider": normalized_savings_provider,
        "normalized_realized_provider": normalized_realized_provider,
        "normalized_close_provider": normalized_close_provider,
        "focus_window_start": focus_window_start,
        "focus_window_end": focus_window_end,
        "savings_window_start": savings_window_start,
        "savings_window_end": savings_window_end,
        "realized_window_start": realized_window_start,
        "realized_window_end": realized_window_end,
        "close_window_start": close_window_start,
        "close_window_end": close_window_end,
    }
