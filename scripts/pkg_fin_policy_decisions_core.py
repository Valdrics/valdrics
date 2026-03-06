"""Core validation logic for PKG/FIN policy decision evidence."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from scripts.pkg_fin_policy_decisions_constants import (
    ALLOWED_APPROVAL_GOVERNANCE_MODES,
    ALLOWED_DECISION_OWNER_FUNCTIONS,
    ALLOWED_DECISION_RESOLUTIONS,
    ALLOWED_ENTERPRISE_PRICING_MODELS,
    ALLOWED_GROWTH_AUTO_REMEDIATION_SCOPES,
    ALLOWED_MIGRATION_STRATEGIES,
    ALLOWED_PRO_ENFORCEMENT_BOUNDARY,
    ALLOWED_TELEMETRY_SOURCE_TYPES,
    PLACEHOLDER_TOKEN_RE,
    REQUIRED_DECISION_BACKLOG_IDS,
    REQUIRED_TIERS,
)


def parse_iso_utc(value: Any, *, field: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(f"{field} must be a non-empty ISO-8601 datetime")
    if raw.endswith("Z"):
        raw = f"{raw[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"{field} must be a valid ISO-8601 datetime") from exc
    if parsed.tzinfo is None:
        raise ValueError(f"{field} must include timezone information")
    return parsed.astimezone(timezone.utc)


def parse_float(
    value: Any,
    *,
    field: str,
    min_value: float | None = None,
    max_value: float | None = None,
) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"{field} must be finite")
    if min_value is not None and parsed < min_value:
        raise ValueError(f"{field} must be >= {min_value}")
    if max_value is not None and parsed > max_value:
        raise ValueError(f"{field} must be <= {max_value}")
    return parsed


def parse_int(value: Any, *, field: str, min_value: int | None = None) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be integer-like") from exc
    if min_value is not None and parsed < min_value:
        raise ValueError(f"{field} must be >= {min_value}")
    return parsed


def parse_bool(value: Any, *, field: str) -> bool:
    if isinstance(value, bool):
        return value
    raise ValueError(f"{field} must be boolean")


def parse_non_empty_str(value: Any, *, field: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field} must be a non-empty string")
    if PLACEHOLDER_TOKEN_RE.search(normalized):
        raise ValueError(f"{field} must not contain placeholder tokens")
    return normalized


def parse_date(value: Any, *, field: str) -> datetime:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError(f"{field} must be a non-empty YYYY-MM-DD date")
    try:
        parsed = datetime.fromisoformat(f"{raw}T00:00:00+00:00")
    except ValueError as exc:
        raise ValueError(f"{field} must be YYYY-MM-DD") from exc
    return parsed


def load_payload(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"PKG/FIN policy decision evidence file not found: {path}")
    raw = path.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"PKG/FIN policy decision evidence JSON is invalid: {path}"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError("PKG/FIN policy decision payload must be a JSON object")
    return payload


def validate_telemetry(telemetry: dict[str, Any]) -> tuple[bool, str]:
    months_observed = parse_int(
        telemetry.get("months_observed"),
        field="telemetry.months_observed",
        min_value=1,
    )
    source_type = parse_non_empty_str(
        telemetry.get("source_type"),
        field="telemetry.source_type",
    )
    if source_type not in ALLOWED_TELEMETRY_SOURCE_TYPES:
        raise ValueError(
            "telemetry.source_type must be one of "
            f"{sorted(ALLOWED_TELEMETRY_SOURCE_TYPES)}"
        )
    tier_unit_economics = telemetry.get("tier_unit_economics")
    if not isinstance(tier_unit_economics, list) or not tier_unit_economics:
        raise ValueError("telemetry.tier_unit_economics must be a non-empty array")

    seen_tiers: set[str] = set()
    for idx, item in enumerate(tier_unit_economics):
        if not isinstance(item, dict):
            raise ValueError(f"telemetry.tier_unit_economics[{idx}] must be an object")
        tier = parse_non_empty_str(
            item.get("tier"),
            field=f"telemetry.tier_unit_economics[{idx}].tier",
        ).lower()
        seen_tiers.add(tier)

        mrr_usd = parse_float(
            item.get("mrr_usd"),
            field=f"telemetry.tier_unit_economics[{idx}].mrr_usd",
            min_value=0.0,
        )
        effective_mrr_usd = parse_float(
            item.get("effective_mrr_usd"),
            field=f"telemetry.tier_unit_economics[{idx}].effective_mrr_usd",
            min_value=0.0,
        )
        if effective_mrr_usd > mrr_usd:
            raise ValueError(
                "telemetry.tier_unit_economics[{idx}].effective_mrr_usd cannot exceed "
                "mrr_usd".format(idx=idx)
            )
        parse_float(
            item.get("llm_cogs_usd"),
            field=f"telemetry.tier_unit_economics[{idx}].llm_cogs_usd",
            min_value=0.0,
        )
        parse_float(
            item.get("infra_cogs_usd"),
            field=f"telemetry.tier_unit_economics[{idx}].infra_cogs_usd",
            min_value=0.0,
        )
        parse_float(
            item.get("support_cogs_usd"),
            field=f"telemetry.tier_unit_economics[{idx}].support_cogs_usd",
            min_value=0.0,
        )

    missing_tiers = REQUIRED_TIERS.difference(seen_tiers)
    if missing_tiers:
        raise ValueError(
            "telemetry.tier_unit_economics missing required tiers: "
            + ", ".join(sorted(missing_tiers))
        )
    return months_observed >= 2, source_type


def validate_policy_decisions(
    policy_decisions: dict[str, Any],
    *,
    telemetry_window_sufficient: bool,
    telemetry_source_type: str,
) -> tuple[bool, bool]:
    enterprise_pricing_model = parse_non_empty_str(
        policy_decisions.get("enterprise_pricing_model"),
        field="policy_decisions.enterprise_pricing_model",
    )
    if enterprise_pricing_model not in ALLOWED_ENTERPRISE_PRICING_MODELS:
        raise ValueError(
            "policy_decisions.enterprise_pricing_model must be one of "
            f"{sorted(ALLOWED_ENTERPRISE_PRICING_MODELS)}"
        )

    parse_float(
        policy_decisions.get("max_annual_discount_percent"),
        field="policy_decisions.max_annual_discount_percent",
        min_value=0.0,
        max_value=100.0,
    )

    growth_scope = parse_non_empty_str(
        policy_decisions.get("growth_auto_remediation_scope"),
        field="policy_decisions.growth_auto_remediation_scope",
    )
    if growth_scope not in ALLOWED_GROWTH_AUTO_REMEDIATION_SCOPES:
        raise ValueError(
            "policy_decisions.growth_auto_remediation_scope must be one of "
            f"{sorted(ALLOWED_GROWTH_AUTO_REMEDIATION_SCOPES)}"
        )

    pro_boundary = parse_non_empty_str(
        policy_decisions.get("pro_enforcement_boundary"),
        field="policy_decisions.pro_enforcement_boundary",
    )
    if pro_boundary not in ALLOWED_PRO_ENFORCEMENT_BOUNDARY:
        raise ValueError(
            "policy_decisions.pro_enforcement_boundary must be one of "
            f"{sorted(ALLOWED_PRO_ENFORCEMENT_BOUNDARY)}"
        )

    migration_strategy = parse_non_empty_str(
        policy_decisions.get("migration_strategy"),
        field="policy_decisions.migration_strategy",
    )
    if migration_strategy not in ALLOWED_MIGRATION_STRATEGIES:
        raise ValueError(
            "policy_decisions.migration_strategy must be one of "
            f"{sorted(ALLOWED_MIGRATION_STRATEGIES)}"
        )

    migration_window_days = parse_int(
        policy_decisions.get("migration_window_days"),
        field="policy_decisions.migration_window_days",
        min_value=0,
    )
    if migration_strategy == "grandfather_timeboxed" and migration_window_days <= 0:
        raise ValueError(
            "policy_decisions.migration_window_days must be > 0 when "
            "migration_strategy=grandfather_timeboxed"
        )

    floor_value_raw = policy_decisions.get("enterprise_floor_usd_monthly")
    if enterprise_pricing_model in {"flat_floor", "hybrid"}:
        parse_float(
            floor_value_raw,
            field="policy_decisions.enterprise_floor_usd_monthly",
            min_value=1.0,
        )
    elif floor_value_raw is not None:
        parse_float(
            floor_value_raw,
            field="policy_decisions.enterprise_floor_usd_monthly",
            min_value=0.0,
        )

    pricing_motion_allowed = parse_bool(
        policy_decisions.get("pricing_motion_allowed"),
        field="policy_decisions.pricing_motion_allowed",
    )

    pricing_motion_guarded = (
        telemetry_window_sufficient
        and telemetry_source_type == "production_observed"
        and pricing_motion_allowed
    ) or (
        (not pricing_motion_allowed) and telemetry_source_type == "synthetic_prelaunch"
    )

    return True, pricing_motion_guarded


def validate_approvals(approvals: dict[str, Any], *, captured_at: datetime) -> bool:
    finance_owner = parse_non_empty_str(
        approvals.get("finance_owner"),
        field="approvals.finance_owner",
    )
    product_owner = parse_non_empty_str(
        approvals.get("product_owner"),
        field="approvals.product_owner",
    )
    go_to_market_owner = parse_non_empty_str(
        approvals.get("go_to_market_owner"),
        field="approvals.go_to_market_owner",
    )
    governance_mode = parse_non_empty_str(
        approvals.get("governance_mode"),
        field="approvals.governance_mode",
    )
    if governance_mode not in ALLOWED_APPROVAL_GOVERNANCE_MODES:
        raise ValueError(
            "approvals.governance_mode must be one of "
            f"{sorted(ALLOWED_APPROVAL_GOVERNANCE_MODES)}"
        )
    if governance_mode == "segregated_owners":
        unique_owners = {
            finance_owner.lower(),
            product_owner.lower(),
            go_to_market_owner.lower(),
        }
        if len(unique_owners) != 3:
            raise ValueError(
                "approvals.governance_mode=segregated_owners requires distinct "
                "finance/product/go-to-market owners"
            )
    parse_non_empty_str(
        approvals.get("approval_record_ref"),
        field="approvals.approval_record_ref",
    )
    approved_at = parse_iso_utc(
        approvals.get("approved_at"),
        field="approvals.approved_at",
    )
    if approved_at > captured_at:
        raise ValueError("approvals.approved_at must be <= captured_at")
    return True


def validate_decision_backlog(
    decision_backlog: dict[str, Any],
    *,
    captured_at: datetime,
) -> tuple[bool, bool, bool]:
    required_ids = decision_backlog.get("required_decision_ids")
    if not isinstance(required_ids, list) or not required_ids:
        raise ValueError("decision_backlog.required_decision_ids must be a non-empty array")

    required_ids_norm: list[str] = []
    for idx, item in enumerate(required_ids):
        item_id = parse_non_empty_str(
            item,
            field=f"decision_backlog.required_decision_ids[{idx}]",
        ).upper()
        required_ids_norm.append(item_id)

    required_ids_set = set(required_ids_norm)
    canonical_required_ids = set(REQUIRED_DECISION_BACKLOG_IDS)
    if required_ids_set != canonical_required_ids:
        missing = sorted(canonical_required_ids.difference(required_ids_set))
        extra = sorted(required_ids_set.difference(canonical_required_ids))
        raise ValueError(
            "decision_backlog.required_decision_ids must match canonical PKG/FIN decision set. "
            f"missing={missing} extra={extra}"
        )

    items = decision_backlog.get("decision_items")
    if not isinstance(items, list) or not items:
        raise ValueError("decision_backlog.decision_items must be a non-empty array")

    seen_ids: set[str] = set()
    launch_blockers_resolved = True
    postlaunch_commitments_scheduled = True
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"decision_backlog.decision_items[{idx}] must be an object")

        item_id = parse_non_empty_str(
            item.get("id"),
            field=f"decision_backlog.decision_items[{idx}].id",
        ).upper()
        if item_id in seen_ids:
            raise ValueError(f"decision_backlog.decision_items[{idx}].id duplicates {item_id}")
        seen_ids.add(item_id)
        if item_id not in canonical_required_ids:
            raise ValueError(
                f"decision_backlog.decision_items[{idx}].id is not in canonical set: {item_id}"
            )

        owner_function = parse_non_empty_str(
            item.get("owner_function"),
            field=f"decision_backlog.decision_items[{idx}].owner_function",
        ).lower()
        if owner_function not in ALLOWED_DECISION_OWNER_FUNCTIONS:
            raise ValueError(
                f"decision_backlog.decision_items[{idx}].owner_function must be one of "
                f"{sorted(ALLOWED_DECISION_OWNER_FUNCTIONS)}"
            )
        parse_non_empty_str(
            item.get("owner"),
            field=f"decision_backlog.decision_items[{idx}].owner",
        )
        parse_non_empty_str(
            item.get("decision_summary"),
            field=f"decision_backlog.decision_items[{idx}].decision_summary",
        )

        resolution = parse_non_empty_str(
            item.get("resolution"),
            field=f"decision_backlog.decision_items[{idx}].resolution",
        ).lower()
        if resolution not in ALLOWED_DECISION_RESOLUTIONS:
            raise ValueError(
                f"decision_backlog.decision_items[{idx}].resolution must be one of "
                f"{sorted(ALLOWED_DECISION_RESOLUTIONS)}"
            )

        launch_blocking = parse_bool(
            item.get("launch_blocking"),
            field=f"decision_backlog.decision_items[{idx}].launch_blocking",
        )
        parse_non_empty_str(
            item.get("approval_record_ref"),
            field=f"decision_backlog.decision_items[{idx}].approval_record_ref",
        )
        approved_at = parse_iso_utc(
            item.get("approved_at"),
            field=f"decision_backlog.decision_items[{idx}].approved_at",
        )
        if approved_at > captured_at:
            raise ValueError(
                f"decision_backlog.decision_items[{idx}].approved_at must be <= captured_at"
            )

        if launch_blocking and resolution != "locked_prelaunch":
            launch_blockers_resolved = False

        if resolution == "scheduled_postlaunch":
            target_date = parse_date(
                item.get("target_date"),
                field=f"decision_backlog.decision_items[{idx}].target_date",
            )
            parse_non_empty_str(
                item.get("success_criteria"),
                field=f"decision_backlog.decision_items[{idx}].success_criteria",
            )
            if target_date.date() < captured_at.date():
                raise ValueError(
                    f"decision_backlog.decision_items[{idx}].target_date must be >= captured_at date"
                )
        else:
            if item.get("target_date") is not None:
                parse_date(
                    item.get("target_date"),
                    field=f"decision_backlog.decision_items[{idx}].target_date",
                )

        if resolution == "scheduled_postlaunch" and not str(
            item.get("success_criteria") or ""
        ).strip():
            postlaunch_commitments_scheduled = False

    backlog_coverage_complete = canonical_required_ids.issubset(seen_ids)
    if not backlog_coverage_complete:
        missing = sorted(canonical_required_ids.difference(seen_ids))
        raise ValueError(
            "decision_backlog.decision_items missing required decisions: "
            + ", ".join(missing)
        )

    return (
        backlog_coverage_complete,
        launch_blockers_resolved,
        postlaunch_commitments_scheduled,
    )


def verify_evidence(
    *,
    evidence_path: Path,
    max_artifact_age_hours: float | None = None,
) -> int:
    payload = load_payload(evidence_path)
    captured_at = parse_iso_utc(payload.get("captured_at"), field="captured_at")

    if max_artifact_age_hours is not None:
        max_age = parse_float(
            max_artifact_age_hours,
            field="max_artifact_age_hours",
            min_value=0.01,
        )
        age_hours = (datetime.now(timezone.utc) - captured_at).total_seconds() / 3600.0
        if age_hours > max_age:
            raise ValueError(
                f"captured_at is too old ({age_hours:.2f}h > max {max_age:.2f}h)"
            )

    window = payload.get("window")
    if not isinstance(window, dict):
        raise ValueError("window must be an object")
    window_start = parse_iso_utc(window.get("start"), field="window.start")
    window_end = parse_iso_utc(window.get("end"), field="window.end")
    if window_end < window_start:
        raise ValueError("window.end must be >= window.start")

    telemetry = payload.get("telemetry")
    if not isinstance(telemetry, dict):
        raise ValueError("telemetry must be an object")
    telemetry_window_sufficient, telemetry_source_type = validate_telemetry(telemetry)

    policy_decisions = payload.get("policy_decisions")
    if not isinstance(policy_decisions, dict):
        raise ValueError("policy_decisions must be an object")
    policy_decisions_complete, pricing_motion_guarded = validate_policy_decisions(
        policy_decisions,
        telemetry_window_sufficient=telemetry_window_sufficient,
        telemetry_source_type=telemetry_source_type,
    )

    approvals = payload.get("approvals")
    if not isinstance(approvals, dict):
        raise ValueError("approvals must be an object")
    approvals_complete = validate_approvals(approvals, captured_at=captured_at)

    decision_backlog = payload.get("decision_backlog")
    if not isinstance(decision_backlog, dict):
        raise ValueError("decision_backlog must be an object")
    (
        backlog_coverage_complete,
        launch_blockers_resolved,
        postlaunch_commitments_scheduled,
    ) = validate_decision_backlog(decision_backlog, captured_at=captured_at)

    gate_results = payload.get("gate_results")
    if not isinstance(gate_results, dict):
        raise ValueError("gate_results must be an object")

    computed_gates = {
        "pkg_fin_gate_policy_decisions_complete": policy_decisions_complete,
        "pkg_fin_gate_telemetry_window_sufficient": telemetry_window_sufficient,
        "pkg_fin_gate_approvals_complete": approvals_complete,
        "pkg_fin_gate_pricing_motion_guarded": pricing_motion_guarded,
        "pkg_fin_gate_backlog_coverage_complete": backlog_coverage_complete,
        "pkg_fin_gate_launch_blockers_resolved": launch_blockers_resolved,
        "pkg_fin_gate_postlaunch_commitments_scheduled": postlaunch_commitments_scheduled,
    }
    for gate, expected in computed_gates.items():
        actual = parse_bool(gate_results.get(gate), field=f"gate_results.{gate}")
        if actual is not expected:
            raise ValueError(
                f"gate_results.{gate} mismatch: payload={actual} computed={expected}"
            )

    if not all(computed_gates.values()):
        failed = [name for name, ok in computed_gates.items() if not ok]
        raise ValueError(
            "PKG/FIN policy decision verification failed for gates: "
            + ", ".join(failed)
        )
    return 0
