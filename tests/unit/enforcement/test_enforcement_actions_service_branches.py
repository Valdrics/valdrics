from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.enforcement import EnforcementActionStatus, EnforcementDecisionType
from app.modules.enforcement.domain.action_errors import EnforcementActionError
from app.modules.enforcement.domain.actions import EnforcementActionOrchestrator
from tests.unit.enforcement.enforcement_actions_orchestrator_support import (
    _QueueDB,
    _RowCountResult,
    _RowsResult,
    _ScalarResult,
)


@pytest.mark.asyncio
async def test_action_orchestrator_create_auto_idempotency_and_integrity_dedup_paths() -> None:
    tenant_id = uuid4()
    actor_id = uuid4()
    decision = SimpleNamespace(
        id=uuid4(),
        decision=EnforcementDecisionType.ALLOW,
        approval_required=False,
    )

    auto_db = _QueueDB([_ScalarResult(None)])
    auto_orchestrator = EnforcementActionOrchestrator(auto_db)  # type: ignore[arg-type]
    auto_orchestrator._resolve_decision_and_approval = AsyncMock(return_value=(decision, None))
    auto_orchestrator._assert_action_request_allowed = AsyncMock(return_value=None)
    auto_orchestrator._resolve_policy_execution_controls = AsyncMock(return_value=(3, 60, 300))

    auto_action = await auto_orchestrator.create_action_request(
        tenant_id=tenant_id,
        actor_id=actor_id,
        decision_id=decision.id,
        action_type="terraform.apply.execute",
        target_reference="module.app.aws_instance.auto-idem",
        request_payload={"k": "v"},
        idempotency_key=None,
    )
    assert len(auto_action.idempotency_key) == 40

    deduped = SimpleNamespace(id=uuid4())
    dedupe_db = _QueueDB([_ScalarResult(None), _ScalarResult(deduped)])
    dedupe_db.commit = AsyncMock(
        side_effect=IntegrityError("insert", {"x": 1}, RuntimeError("duplicate"))
    )
    dedupe_orchestrator = EnforcementActionOrchestrator(dedupe_db)  # type: ignore[arg-type]
    dedupe_orchestrator._resolve_decision_and_approval = AsyncMock(return_value=(decision, None))
    dedupe_orchestrator._assert_action_request_allowed = AsyncMock(return_value=None)
    dedupe_orchestrator._resolve_policy_execution_controls = AsyncMock(return_value=(3, 60, 300))

    deduped_action = await dedupe_orchestrator.create_action_request(
        tenant_id=tenant_id,
        actor_id=actor_id,
        decision_id=decision.id,
        action_type="terraform.apply.execute",
        target_reference="module.app.aws_instance.dedupe",
        request_payload={"k": "v"},
        idempotency_key="dedupe-key",
    )
    assert deduped_action is deduped
    dedupe_db.rollback.assert_awaited()

    no_dedupe_db = _QueueDB([_ScalarResult(None), _ScalarResult(None)])
    duplicate_error = IntegrityError("insert", {"x": 1}, RuntimeError("duplicate"))
    no_dedupe_db.commit = AsyncMock(side_effect=duplicate_error)
    no_dedupe_orchestrator = EnforcementActionOrchestrator(no_dedupe_db)  # type: ignore[arg-type]
    no_dedupe_orchestrator._resolve_decision_and_approval = AsyncMock(
        return_value=(decision, None)
    )
    no_dedupe_orchestrator._assert_action_request_allowed = AsyncMock(return_value=None)
    no_dedupe_orchestrator._resolve_policy_execution_controls = AsyncMock(
        return_value=(3, 60, 300)
    )

    with pytest.raises(IntegrityError):
        await no_dedupe_orchestrator.create_action_request(
            tenant_id=tenant_id,
            actor_id=actor_id,
            decision_id=decision.id,
            action_type="terraform.apply.execute",
            target_reference="module.app.aws_instance.dedupe-miss",
            request_payload={"k": "v"},
            idempotency_key="dedupe-key-miss",
        )
    no_dedupe_db.rollback.assert_awaited()


@pytest.mark.asyncio
async def test_action_orchestrator_get_list_lease_and_cancel_missing_branches() -> None:
    tenant_id = uuid4()
    decision_id = uuid4()
    action_id = uuid4()

    not_found_db = _QueueDB([_ScalarResult(None)])
    not_found_orchestrator = EnforcementActionOrchestrator(not_found_db)  # type: ignore[arg-type]
    with pytest.raises(EnforcementActionError, match="not found"):
        await not_found_orchestrator.get_action(tenant_id=tenant_id, action_id=action_id)

    listed_row = SimpleNamespace(id=action_id)
    list_db = _QueueDB([_RowsResult([listed_row])])
    list_orchestrator = EnforcementActionOrchestrator(list_db)  # type: ignore[arg-type]
    listed = await list_orchestrator.list_actions(
        tenant_id=tenant_id,
        status=EnforcementActionStatus.QUEUED,
        decision_id=decision_id,
        limit=10,
    )
    assert listed == [listed_row]

    no_status_row = SimpleNamespace(id=uuid4())
    no_status_db = _QueueDB([_RowsResult([no_status_row])])
    no_status_orchestrator = EnforcementActionOrchestrator(no_status_db)  # type: ignore[arg-type]
    no_status_listed = await no_status_orchestrator.list_actions(
        tenant_id=tenant_id,
        status=None,
        decision_id=None,
        limit=10,
    )
    assert no_status_listed == [no_status_row]

    empty_candidate_db = _QueueDB([_ScalarResult(None)])
    empty_candidate_orchestrator = EnforcementActionOrchestrator(
        empty_candidate_db
    )  # type: ignore[arg-type]
    assert (
        await empty_candidate_orchestrator.lease_next_action(
            tenant_id=tenant_id,
            worker_id=uuid4(),
            action_type="terraform.apply.execute",
            now=datetime.now(timezone.utc),
        )
        is None
    )

    candidate = SimpleNamespace(
        id=uuid4(),
        lease_ttl_seconds=300,
        attempt_count=0,
        started_at=None,
    )
    execute_results: list[object] = []
    for _ in range(5):
        execute_results.append(_ScalarResult(candidate))
        execute_results.append(_RowCountResult(0))
    contention_db = _QueueDB(execute_results)
    contention_orchestrator = EnforcementActionOrchestrator(contention_db)  # type: ignore[arg-type]
    leased = await contention_orchestrator.lease_next_action(
        tenant_id=tenant_id,
        worker_id=uuid4(),
        action_type="terraform.apply.execute",
        now=datetime.now(timezone.utc),
    )
    assert leased is None
    assert contention_db.rollback.await_count == 5

    cancel_db = _QueueDB([])
    cancel_orchestrator = EnforcementActionOrchestrator(cancel_db)  # type: ignore[arg-type]
    cancellable = SimpleNamespace(
        status=EnforcementActionStatus.QUEUED,
        locked_by_worker_id=uuid4(),
        lease_expires_at=datetime.now(timezone.utc),
        completed_at=None,
        next_retry_at=datetime.now(timezone.utc),
        result_payload=None,
        result_payload_sha256=None,
        last_error_code=None,
        last_error_message=None,
    )
    cancel_orchestrator.get_action = AsyncMock(return_value=cancellable)
    cancelled = await cancel_orchestrator.cancel_action(
        tenant_id=tenant_id,
        action_id=uuid4(),
        actor_id=uuid4(),
        reason="  operator cancelled request  ",
    )
    assert cancelled.last_error_code == "cancelled"
    assert cancelled.result_payload is not None
    assert "operator cancelled request" in str(cancelled.result_payload["reason"])
