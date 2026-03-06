from __future__ import annotations

from collections.abc import Callable
import csv
from datetime import datetime
from decimal import Decimal
import io
import json
from typing import Any

from app.models.enforcement import EnforcementApprovalRequest, EnforcementDecision


def render_decisions_csv(
    decisions: list[EnforcementDecision],
    *,
    computed_context_snapshot_fn: Callable[[dict[str, Any] | None], dict[str, Any]],
    sanitize_csv_cell_fn: Callable[[Any], str],
    normalize_policy_document_schema_version_fn: Callable[[str | None], str],
    normalize_policy_document_sha256_fn: Callable[[str | None], str],
    to_decimal_fn: Callable[[Any], Decimal],
    iso_or_empty_fn: Callable[[datetime | None], str],
    json_default_fn: Callable[[Any], Any],
) -> str:
    headers = [
        "decision_id",
        "source",
        "environment",
        "project_id",
        "action",
        "resource_reference",
        "decision",
        "reason_codes",
        "policy_version",
        "policy_document_schema_version",
        "policy_document_sha256",
        "computed_context_version",
        "computed_context_generated_at",
        "computed_context_month_start",
        "computed_context_month_end",
        "computed_context_month_elapsed_days",
        "computed_context_month_total_days",
        "computed_context_observed_cost_days",
        "computed_context_latest_cost_date",
        "computed_context_data_source_mode",
        "request_fingerprint",
        "idempotency_key",
        "estimated_monthly_delta_usd",
        "estimated_hourly_delta_usd",
        "allocation_available_usd",
        "credits_available_usd",
        "reserved_allocation_usd",
        "reserved_credit_usd",
        "reservation_active",
        "approval_required",
        "approval_token_issued",
        "token_expires_at",
        "created_by_user_id",
        "created_at",
        "request_payload",
        "response_payload",
    ]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)
    for decision in decisions:
        context_snapshot = computed_context_snapshot_fn(decision.response_payload)
        writer.writerow(
            [
                sanitize_csv_cell_fn(decision.id),
                sanitize_csv_cell_fn(decision.source.value),
                sanitize_csv_cell_fn(decision.environment),
                sanitize_csv_cell_fn(decision.project_id),
                sanitize_csv_cell_fn(decision.action),
                sanitize_csv_cell_fn(decision.resource_reference),
                sanitize_csv_cell_fn(decision.decision.value),
                sanitize_csv_cell_fn(
                    json.dumps(
                        list(decision.reason_codes or []),
                        separators=(",", ":"),
                    )
                ),
                sanitize_csv_cell_fn(int(decision.policy_version)),
                sanitize_csv_cell_fn(
                    normalize_policy_document_schema_version_fn(
                        decision.policy_document_schema_version
                    )
                ),
                sanitize_csv_cell_fn(
                    normalize_policy_document_sha256_fn(decision.policy_document_sha256)
                ),
                sanitize_csv_cell_fn(context_snapshot["context_version"]),
                sanitize_csv_cell_fn(context_snapshot["generated_at"]),
                sanitize_csv_cell_fn(context_snapshot["month_start"]),
                sanitize_csv_cell_fn(context_snapshot["month_end"]),
                sanitize_csv_cell_fn(context_snapshot["month_elapsed_days"]),
                sanitize_csv_cell_fn(context_snapshot["month_total_days"]),
                sanitize_csv_cell_fn(context_snapshot["observed_cost_days"]),
                sanitize_csv_cell_fn(context_snapshot["latest_cost_date"]),
                sanitize_csv_cell_fn(context_snapshot["data_source_mode"]),
                sanitize_csv_cell_fn(decision.request_fingerprint),
                sanitize_csv_cell_fn(decision.idempotency_key),
                sanitize_csv_cell_fn(to_decimal_fn(decision.estimated_monthly_delta_usd)),
                sanitize_csv_cell_fn(to_decimal_fn(decision.estimated_hourly_delta_usd)),
                sanitize_csv_cell_fn(
                    to_decimal_fn(decision.allocation_available_usd)
                    if decision.allocation_available_usd is not None
                    else ""
                ),
                sanitize_csv_cell_fn(
                    to_decimal_fn(decision.credits_available_usd)
                    if decision.credits_available_usd is not None
                    else ""
                ),
                sanitize_csv_cell_fn(to_decimal_fn(decision.reserved_allocation_usd)),
                sanitize_csv_cell_fn(to_decimal_fn(decision.reserved_credit_usd)),
                sanitize_csv_cell_fn(bool(decision.reservation_active)),
                sanitize_csv_cell_fn(bool(decision.approval_required)),
                sanitize_csv_cell_fn(bool(decision.approval_token_issued)),
                sanitize_csv_cell_fn(iso_or_empty_fn(decision.token_expires_at)),
                sanitize_csv_cell_fn(decision.created_by_user_id or ""),
                sanitize_csv_cell_fn(iso_or_empty_fn(decision.created_at)),
                sanitize_csv_cell_fn(
                    json.dumps(
                        decision.request_payload or {},
                        sort_keys=True,
                        separators=(",", ":"),
                        default=json_default_fn,
                    )
                ),
                sanitize_csv_cell_fn(
                    json.dumps(
                        decision.response_payload or {},
                        sort_keys=True,
                        separators=(",", ":"),
                        default=json_default_fn,
                    )
                ),
            ]
        )
    return out.getvalue()


def render_approvals_csv(
    approvals: list[EnforcementApprovalRequest],
    *,
    sanitize_csv_cell_fn: Callable[[Any], str],
    iso_or_empty_fn: Callable[[datetime | None], str],
) -> str:
    headers = [
        "approval_id",
        "decision_id",
        "status",
        "requested_by_user_id",
        "reviewed_by_user_id",
        "review_notes",
        "routing_rule_id",
        "routing_required_permission",
        "routing_allowed_reviewer_roles",
        "routing_require_requester_reviewer_separation",
        "approval_token_expires_at",
        "approval_token_consumed_at",
        "expires_at",
        "approved_at",
        "denied_at",
        "created_at",
        "updated_at",
    ]
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)
    for approval in approvals:
        routing_trace = (
            approval.routing_trace if isinstance(approval.routing_trace, dict) else {}
        )
        routing_roles = routing_trace.get("allowed_reviewer_roles")
        if not isinstance(routing_roles, list):
            routing_roles = []
        writer.writerow(
            [
                sanitize_csv_cell_fn(approval.id),
                sanitize_csv_cell_fn(approval.decision_id),
                sanitize_csv_cell_fn(approval.status.value),
                sanitize_csv_cell_fn(approval.requested_by_user_id or ""),
                sanitize_csv_cell_fn(approval.reviewed_by_user_id or ""),
                sanitize_csv_cell_fn(approval.review_notes or ""),
                sanitize_csv_cell_fn(approval.routing_rule_id or ""),
                sanitize_csv_cell_fn(routing_trace.get("required_permission") or ""),
                sanitize_csv_cell_fn(",".join(str(role) for role in routing_roles)),
                sanitize_csv_cell_fn(
                    bool(routing_trace.get("require_requester_reviewer_separation"))
                ),
                sanitize_csv_cell_fn(iso_or_empty_fn(approval.approval_token_expires_at)),
                sanitize_csv_cell_fn(
                    iso_or_empty_fn(approval.approval_token_consumed_at)
                ),
                sanitize_csv_cell_fn(iso_or_empty_fn(approval.expires_at)),
                sanitize_csv_cell_fn(iso_or_empty_fn(approval.approved_at)),
                sanitize_csv_cell_fn(iso_or_empty_fn(approval.denied_at)),
                sanitize_csv_cell_fn(iso_or_empty_fn(approval.created_at)),
                sanitize_csv_cell_fn(iso_or_empty_fn(approval.updated_at)),
            ]
        )
    return out.getvalue()
