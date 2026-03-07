from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from app.models.enforcement import (
    EnforcementApprovalRequest,
    EnforcementDecision,
    EnforcementSource,
)
from app.modules.enforcement.domain.approval_flow_ops import (
    approve_request as _approve_request_impl,
    consume_approval_token as _consume_approval_token_impl,
    create_or_get_approval_request as _create_or_get_approval_request_impl,
    deny_request as _deny_request_impl,
    list_pending_approvals as _list_pending_approvals_impl,
)
from app.modules.enforcement.domain.service_utils import (
    _as_utc,
    _normalize_environment,
    _quantize,
    _to_decimal,
    _utcnow,
)
from app.shared.core.auth import CurrentUser
from app.shared.core.ops_metrics import ENFORCEMENT_APPROVAL_TOKEN_EVENTS_TOTAL


class EnforcementServiceApprovalOps:
    db: Any

    async def create_or_get_approval_request(
        self,
        *,
        tenant_id: UUID,
        actor_id: UUID,
        decision_id: UUID,
        notes: str | None,
    ) -> EnforcementApprovalRequest:
        service = cast(Any, self)
        return await _create_or_get_approval_request_impl(
            db=service.db,
            tenant_id=tenant_id,
            actor_id=actor_id,
            decision_id=decision_id,
            notes=notes,
            get_or_create_policy_fn=service.get_or_create_policy,
            get_approval_by_decision_fn=service._get_approval_by_decision,
            resolve_approval_routing_trace_fn=service._resolve_approval_routing_trace,
            append_decision_ledger_entry_fn=service._append_decision_ledger_entry,
            utcnow_fn=_utcnow,
        )

    async def list_pending_approvals(
        self,
        *,
        tenant_id: UUID,
        reviewer: CurrentUser | None,
        limit: int,
    ) -> list[tuple[EnforcementApprovalRequest, EnforcementDecision]]:
        service = cast(Any, self)
        return await _list_pending_approvals_impl(
            db=service.db,
            tenant_id=tenant_id,
            reviewer=reviewer,
            limit=limit,
            get_or_create_policy_fn=service.get_or_create_policy,
            enforce_reviewer_authority_fn=service._enforce_reviewer_authority,
            utcnow_fn=_utcnow,
        )

    async def approve_request(
        self,
        *,
        tenant_id: UUID,
        approval_id: UUID,
        reviewer: CurrentUser,
        notes: str | None,
    ) -> tuple[EnforcementApprovalRequest, EnforcementDecision, str, datetime]:
        service = cast(Any, self)
        return await _approve_request_impl(
            db=service.db,
            tenant_id=tenant_id,
            approval_id=approval_id,
            reviewer=reviewer,
            notes=notes,
            load_approval_with_decision_fn=service._load_approval_with_decision,
            assert_pending_fn=service._assert_pending,
            settle_credit_reservations_for_decision_fn=(
                service._settle_credit_reservations_for_decision
            ),
            get_or_create_policy_fn=service.get_or_create_policy,
            enforce_reviewer_authority_fn=service._enforce_reviewer_authority,
            build_approval_token_fn=service._build_approval_token,
            append_decision_ledger_entry_fn=service._append_decision_ledger_entry,
            utcnow_fn=_utcnow,
            as_utc_fn=_as_utc,
        )

    async def deny_request(
        self,
        *,
        tenant_id: UUID,
        approval_id: UUID,
        reviewer: CurrentUser,
        notes: str | None,
    ) -> tuple[EnforcementApprovalRequest, EnforcementDecision]:
        service = cast(Any, self)
        return await _deny_request_impl(
            db=service.db,
            tenant_id=tenant_id,
            approval_id=approval_id,
            reviewer=reviewer,
            notes=notes,
            load_approval_with_decision_fn=service._load_approval_with_decision,
            assert_pending_fn=service._assert_pending,
            get_or_create_policy_fn=service.get_or_create_policy,
            enforce_reviewer_authority_fn=service._enforce_reviewer_authority,
            settle_credit_reservations_for_decision_fn=(
                service._settle_credit_reservations_for_decision
            ),
            append_decision_ledger_entry_fn=service._append_decision_ledger_entry,
            utcnow_fn=_utcnow,
        )

    async def consume_approval_token(
        self,
        *,
        tenant_id: UUID,
        approval_token: str,
        actor_id: UUID | None = None,
        expected_source: EnforcementSource | None = None,
        expected_project_id: str | None = None,
        expected_environment: str | None = None,
        expected_request_fingerprint: str | None = None,
        expected_resource_reference: str | None = None,
    ) -> tuple[EnforcementApprovalRequest, EnforcementDecision]:
        service = cast(Any, self)
        return await _consume_approval_token_impl(
            db=service.db,
            tenant_id=tenant_id,
            approval_token=approval_token,
            actor_id=actor_id,
            expected_source=expected_source,
            expected_project_id=expected_project_id,
            expected_environment=expected_environment,
            expected_request_fingerprint=expected_request_fingerprint,
            expected_resource_reference=expected_resource_reference,
            decode_approval_token_fn=service._decode_approval_token,
            extract_token_context_fn=service._extract_token_context,
            load_approval_with_decision_fn=service._load_approval_with_decision,
            utcnow_fn=_utcnow,
            as_utc_fn=_as_utc,
            normalize_environment_fn=_normalize_environment,
            quantize_fn=_quantize,
            to_decimal_fn=_to_decimal,
            approval_token_events_counter=ENFORCEMENT_APPROVAL_TOKEN_EVENTS_TOTAL,
        )
