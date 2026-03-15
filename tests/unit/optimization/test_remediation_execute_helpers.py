from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.models.remediation import RemediationAction, RemediationStatus
from app.modules.optimization.domain.remediation_execute_helpers import (
    maybe_schedule_grace_period_execution,
)


@pytest.mark.asyncio
async def test_maybe_schedule_grace_period_execution_rolls_back_and_restores_request_on_enqueue_failure() -> None:
    request = SimpleNamespace(
        status=RemediationStatus.APPROVED,
        scheduled_execution_at=None,
    )
    db = AsyncMock()
    audit_logger = SimpleNamespace(log=AsyncMock())

    with patch(
        "app.modules.governance.domain.jobs.processor.enqueue_job",
        new=AsyncMock(side_effect=RuntimeError("boom")),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            await maybe_schedule_grace_period_execution(
                request=request,
                action=RemediationAction.DELETE_VOLUME,
                remediation_settings=SimpleNamespace(),
                request_id=uuid4(),
                tenant_id=uuid4(),
                action_value="delete_volume",
                actor_id=str(uuid4()),
                resource_id="vol-1",
                resource_type="volume",
                db=db,
                audit_logger=audit_logger,
                remediation_module=SimpleNamespace(
                    AuditEventType=SimpleNamespace(
                        REMEDIATION_EXECUTION_STARTED="remediation.execution_started"
                    )
                ),
                logger=SimpleNamespace(info=lambda *args, **kwargs: None),
                bypass_grace_period=False,
            )

    assert request.status == RemediationStatus.APPROVED
    assert request.scheduled_execution_at is None
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
    audit_logger.log.assert_not_awaited()
