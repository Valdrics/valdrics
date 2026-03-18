import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4, UUID
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.optimization.domain.remediation import RemediationService
from app.models.remediation import (
    RemediationRequest,
    RemediationStatus,
    RemediationAction,
)
from app.models.aws_connection import AWSConnection
from app.models.optimization import FindingSource, FindingStatus, OptimizationFinding
from app.shared.core.exceptions import ResourceNotFoundError, ValdricsException
from app.modules.optimization.domain.actions.base import ExecutionResult, ExecutionStatus
# Import all models to prevent mapper errors during Mock usage


@pytest.fixture
def db_session():
    """Mock database session."""
    session = MagicMock(spec=AsyncSession)
    session.bind = MagicMock()
    session.bind.url = "sqlite://"
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.info = {}
    session.connection = AsyncMock(return_value=MagicMock())
    return session


@pytest.fixture
def remediation_service(db_session):
    return RemediationService(db_session)


@pytest.mark.asyncio
async def test_create_request_success(remediation_service, db_session):
    tenant_id = uuid4()
    user_id = uuid4()
    connection_id = uuid4()

    mock_conn = MagicMock(spec=AWSConnection)
    mock_conn.id = connection_id
    mock_conn.tenant_id = tenant_id
    mock_conn.status = "active"

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_conn
    db_session.execute.return_value = mock_res

    request = await remediation_service.create_request(
        tenant_id=tenant_id,
        user_id=user_id,
        resource_id="vol-123",
        resource_type="ebs_volume",
        provider="aws",
        connection_id=connection_id,
        action=RemediationAction.DELETE_VOLUME,
        estimated_savings=50.0,
        create_backup=True,
    )

    assert request.resource_id == "vol-123"
    assert request.status == RemediationStatus.PENDING
    db_session.add.assert_called_once()


@pytest.mark.asyncio
async def test_create_request_unauthorized_connection(remediation_service, db_session):
    tenant_id = uuid4()
    connection_id = uuid4()

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db_session.execute.return_value = mock_res

    with pytest.raises(ResourceNotFoundError, match="Connection .* not found"):
        await remediation_service.create_request(
            tenant_id=tenant_id,
            user_id=uuid4(),
            resource_id="v-1",
            resource_type="type",
            action=RemediationAction.DELETE_VOLUME,
            estimated_savings=10.0,
            provider="aws",
            connection_id=connection_id,
        )


@pytest.mark.asyncio
async def test_create_request_does_not_swallow_base_exceptions(
    remediation_service, db_session
):
    class FatalConnectionScopeFailure(BaseException):
        pass

    tenant_id = uuid4()
    connection_id = uuid4()
    remediation_service.get_by_id = AsyncMock(
        side_effect=FatalConnectionScopeFailure("fatal")
    )

    with pytest.raises(FatalConnectionScopeFailure):
        await remediation_service.create_request(
            tenant_id=tenant_id,
            user_id=uuid4(),
            resource_id="v-1",
            resource_type="type",
            action=RemediationAction.DELETE_VOLUME,
            estimated_savings=10.0,
            provider="aws",
            connection_id=connection_id,
        )


@pytest.mark.asyncio
async def test_create_request_requires_explicit_connection_binding(
    remediation_service, db_session
):
    with pytest.raises(ValdricsException) as exc_info:
        await remediation_service.create_request(
            tenant_id=uuid4(),
            user_id=uuid4(),
            resource_id="vol-1",
            resource_type="ebs_volume",
            action=RemediationAction.DELETE_VOLUME,
            estimated_savings=10.0,
            provider="aws",
        )

    assert getattr(exc_info.value, "code", None) == "remediation_connection_required"
    db_session.add.assert_not_called()
    db_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_request_from_finding_binds_immutable_context(
    remediation_service, db_session
):
    tenant_id = uuid4()
    user_id = uuid4()
    finding_id = uuid4()
    connection_id = uuid4()
    finding = OptimizationFinding(
        id=finding_id,
        tenant_id=tenant_id,
        source=FindingSource.ZOMBIE_SCAN,
        status=FindingStatus.OPEN,
        fingerprint="f" * 64,
        provider="aws",
        category="unattached_volumes",
        connection_id=connection_id,
        connection_name="Prod AWS",
        resource_id="vol-123",
        resource_type="ebs_volume",
        region="us-east-1",
        estimated_monthly_savings=Decimal("50.0"),
        confidence_score=Decimal("0.95"),
        explainability_notes="Volume has been unattached for 30 days.",
        requires_manual_review=False,
        automated_action_allowed=True,
        decision_gate=None,
        payload={"resource_id": "vol-123"},
    )

    async def _get_by_id(model, entity_id, scope_tenant_id):
        if model is OptimizationFinding:
            assert entity_id == finding_id
            assert scope_tenant_id == tenant_id
            return finding
        return MagicMock(id=connection_id, tenant_id=tenant_id, status="active")

    remediation_service.get_by_id = AsyncMock(side_effect=_get_by_id)
    remediation_service._build_system_policy_context = AsyncMock(
        return_value={"source": "finding"}
    )

    request = await remediation_service.create_request_from_finding(
        tenant_id=tenant_id,
        user_id=user_id,
        finding_id=finding_id,
        action=RemediationAction.DELETE_VOLUME,
        create_backup=True,
    )

    assert request.finding_id == finding_id
    assert request.resource_id == "vol-123"
    assert request.connection_id == connection_id
    assert request.provider == "aws"
    assert request.finding_snapshot["finding_id"] == str(finding_id)
    assert request.finding_snapshot["category"] == "unattached_volumes"
    assert request.estimated_monthly_savings == Decimal("50.0")
    assert request.status == RemediationStatus.PENDING
    db_session.add.assert_called_once()
    db_session.commit.assert_awaited()


@pytest.mark.asyncio
async def test_create_request_rejects_inactive_connection(remediation_service, db_session):
    tenant_id = uuid4()
    connection_id = uuid4()
    remediation_service.get_by_id = AsyncMock(
        return_value=MagicMock(id=connection_id, tenant_id=tenant_id, status="error")
    )

    with pytest.raises(ValdricsException) as exc_info:
        await remediation_service.create_request(
            tenant_id=tenant_id,
            user_id=uuid4(),
            resource_id="vol-1",
            resource_type="ebs_volume",
            action=RemediationAction.DELETE_VOLUME,
            estimated_savings=10.0,
            provider="aws",
            connection_id=connection_id,
        )

    assert getattr(exc_info.value, "code", None) == "remediation_connection_inactive"
    db_session.add.assert_not_called()
    db_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_create_request_from_finding_rejects_duplicate_open_request(
    remediation_service, db_session
):
    tenant_id = uuid4()
    user_id = uuid4()
    finding_id = uuid4()
    connection_id = uuid4()
    finding = OptimizationFinding(
        id=finding_id,
        tenant_id=tenant_id,
        source=FindingSource.ZOMBIE_SCAN,
        status=FindingStatus.OPEN,
        fingerprint="d" * 64,
        provider="aws",
        category="unattached_volumes",
        connection_id=connection_id,
        connection_name="Prod AWS",
        resource_id="vol-dup",
        resource_type="ebs_volume",
        region="us-east-1",
        estimated_monthly_savings=Decimal("11.0"),
        confidence_score=Decimal("0.91"),
        explainability_notes="Duplicate request guard.",
        requires_manual_review=False,
        automated_action_allowed=True,
        decision_gate=None,
        payload={"resource_id": "vol-dup"},
    )

    async def _get_by_id(model, entity_id, scope_tenant_id):
        if model is OptimizationFinding:
            assert entity_id == finding_id
            assert scope_tenant_id == tenant_id
            return finding
        return MagicMock(id=connection_id, tenant_id=tenant_id, status="active")

    db_session.scalar = AsyncMock(
        return_value=RemediationRequest(
            id=uuid4(),
            tenant_id=tenant_id,
            resource_id="vol-dup",
            resource_type="ebs_volume",
            provider="aws",
            connection_id=connection_id,
            region="us-east-1",
            action=RemediationAction.DELETE_VOLUME,
            status=RemediationStatus.PENDING,
            requested_by_user_id=uuid4(),
        )
    )
    remediation_service.get_by_id = AsyncMock(side_effect=_get_by_id)
    remediation_service._build_system_policy_context = AsyncMock(
        return_value={"source": "finding"}
    )

    with pytest.raises(ValdricsException) as exc_info:
        await remediation_service.create_request_from_finding(
            tenant_id=tenant_id,
            user_id=user_id,
            finding_id=finding_id,
            action=RemediationAction.DELETE_VOLUME,
        )

    assert getattr(exc_info.value, "code", None) == (
        "remediation_request_duplicate_open_finding"
    )
    db_session.add.assert_not_called()
    db_session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_preview_policy_for_finding_uses_bound_finding_context(
    remediation_service, db_session
):
    tenant_id = uuid4()
    user_id = uuid4()
    finding_id = uuid4()
    connection_id = uuid4()
    finding = OptimizationFinding(
        id=finding_id,
        tenant_id=tenant_id,
        source=FindingSource.ZOMBIE_SCAN,
        status=FindingStatus.OPEN,
        fingerprint="a" * 64,
        provider="aws",
        category="idle_instances",
        connection_id=connection_id,
        connection_name="Prod AWS",
        resource_id="i-123",
        resource_type="ec2_instance",
        region="us-east-1",
        estimated_monthly_savings=Decimal("20.0"),
        confidence_score=Decimal("0.88"),
        explainability_notes="Idle instance detected.",
        requires_manual_review=False,
        automated_action_allowed=True,
        decision_gate=None,
        payload={"resource_id": "i-123"},
    )

    async def _get_by_id(model, entity_id, scope_tenant_id):
        if model is OptimizationFinding:
            assert entity_id == finding_id
            assert scope_tenant_id == tenant_id
            return finding
        return MagicMock(id=connection_id, tenant_id=tenant_id, status="active")

    remediation_service.get_by_id = AsyncMock(side_effect=_get_by_id)
    remediation_service._build_system_policy_context = AsyncMock(
        return_value={"source": "finding"}
    )
    remediation_service.preview_policy = AsyncMock(
        return_value={"decision": "allow", "summary": "ok", "tier": "pro", "rule_hits": [], "config": {}}
    )

    result = await remediation_service.preview_policy_for_finding(
        tenant_id=tenant_id,
        user_id=user_id,
        finding_id=finding_id,
        action=RemediationAction.STOP_INSTANCE,
        review_notes="validate first",
    )

    preview_request = remediation_service.preview_policy.await_args.args[0]
    assert preview_request.finding_id == finding_id
    assert preview_request.resource_id == "i-123"
    assert preview_request.connection_id == connection_id
    assert preview_request.finding_snapshot["fingerprint"] == "a" * 64
    assert result["decision"] == "allow"


@pytest.mark.asyncio
async def test_list_pending_success(remediation_service, db_session):
    tenant_id = uuid4()
    req = RemediationRequest(
        id=uuid4(), tenant_id=tenant_id, status=RemediationStatus.PENDING
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [req]
    db_session.execute.return_value = mock_res

    res = await remediation_service.list_pending(tenant_id)
    assert len(res) == 1
    assert res[0].id == req.id


@pytest.mark.asyncio
async def test_approve_flow(remediation_service, db_session):
    request_id = uuid4()
    tenant_id = uuid4()
    reviewer_id = uuid4()

    # 1. Not found
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db_session.execute.return_value = mock_res
    with pytest.raises(ResourceNotFoundError, match="not found"):
        await remediation_service.approve(request_id, tenant_id, reviewer_id)

    # 2. Not pending
    # Important: Use MagicMock(spec=RemediationRequest) AND ensure .action is mocked if needed later
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    # Use a real enum value so .value works
    req.status = RemediationStatus.COMPLETED
    mock_res.scalar_one_or_none.return_value = req
    with pytest.raises(ValueError, match="not pending"):
        await remediation_service.approve(request_id, tenant_id, reviewer_id)

    # 3. Success
    req.status = RemediationStatus.PENDING
    res = await remediation_service.approve(
        request_id, tenant_id, reviewer_id, notes="OK"
    )
    assert res.status == RemediationStatus.APPROVED
    assert res.reviewed_by_user_id == reviewer_id
    assert res.review_notes == "OK"


@pytest.mark.asyncio
async def test_reject_flow(remediation_service, db_session):
    request_id = uuid4()
    tenant_id = uuid4()
    reviewer_id = uuid4()

    # 1. Not found
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db_session.execute.return_value = mock_res
    with pytest.raises(ResourceNotFoundError, match="not found"):
        await remediation_service.reject(request_id, tenant_id, reviewer_id)

    # 2. Success
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    req.status = RemediationStatus.PENDING
    mock_res.scalar_one_or_none.return_value = req
    res = await remediation_service.reject(
        request_id, tenant_id, reviewer_id, notes="NO"
    )
    assert res.status == RemediationStatus.REJECTED
    assert res.reviewed_by_user_id == reviewer_id


@pytest.mark.asyncio
async def test_reject_requires_pending_status(remediation_service, db_session):
    request_id = uuid4()
    tenant_id = uuid4()
    reviewer_id = uuid4()

    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    req.status = RemediationStatus.COMPLETED

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = req
    db_session.execute.return_value = mock_res

    with pytest.raises(ValueError, match="not pending"):
        await remediation_service.reject(request_id, tenant_id, reviewer_id)


@pytest.mark.asyncio
async def test_execute_errors(remediation_service, db_session):
    request_id = uuid4()
    tenant_id = uuid4()

    # 1. Not found
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    db_session.execute.return_value = mock_res

    with pytest.raises(ResourceNotFoundError, match="not found"):
        await remediation_service.execute(request_id, tenant_id)

    # 2. Invalid status
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    req.estimated_monthly_savings = Decimal("50.0")
    req.provider = "aws"
    req.action = RemediationAction.DELETE_VOLUME
    req.connection_id = None
    req.resource_id = "vol-1"
    req.resource_type = "ebs_volume"
    req.status = RemediationStatus.PENDING
    mock_res.scalar_one_or_none.return_value = req

    with patch(
        "app.modules.optimization.domain.remediation.SafetyGuardrailService"
    ) as mock_safety:
        mock_safety.return_value.check_all_guards = AsyncMock()
        res = await remediation_service.execute(request_id, tenant_id)
        assert res.status == RemediationStatus.FAILED
        assert "must be approved or scheduled" in (res.execution_error or "")


@pytest.mark.asyncio
async def test_execute_scheduled_successfully(remediation_service, db_session):
    request_id = uuid4()
    tenant_id = uuid4()
    reviewer_id = uuid4()
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    req.status = RemediationStatus.APPROVED
    req.resource_id = "v-1"
    req.action = RemediationAction.DELETE_VOLUME
    req.resource_type = "vol"
    req.estimated_monthly_savings = Decimal("50.0")
    req.provider = "aws"
    req.connection_id = None
    req.reviewed_by_user_id = reviewer_id
    req.create_backup = False

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = req
    db_session.execute.return_value = mock_res

    with (
        patch(
            "app.modules.optimization.domain.remediation.AuditLogger.log",
            return_value=AsyncMock(),
        ) as mock_audit,
        patch(
            "app.modules.governance.domain.jobs.processor.enqueue_job",
            return_value=AsyncMock(),
        ) as mock_job,
        patch(
            "app.modules.optimization.domain.remediation.SafetyGuardrailService"
        ) as mock_safety,
    ):
        mock_safety.return_value.check_all_guards = AsyncMock()

        res = await remediation_service.execute(
            request_id, tenant_id, bypass_grace_period=False
        )
        assert res.status == RemediationStatus.SCHEDULED
        mock_job.assert_called_once()
        assert mock_audit.called


@pytest.mark.asyncio
async def test_execute_grace_period_logic(remediation_service, db_session):
    request_id = uuid4()
    tenant_id = uuid4()

    # 1. Deferred
    future_time = datetime.now(timezone.utc) + timedelta(hours=10)
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    req.status = RemediationStatus.SCHEDULED
    req.scheduled_execution_at = future_time
    req.estimated_monthly_savings = Decimal("50.0")
    req.provider = "aws"  # Needed for service lookup
    req.action = RemediationAction.DELETE_VOLUME
    req.connection_id = None
    req.resource_id = "v-1"
    req.resource_type = "vol"

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = req
    db_session.execute.return_value = mock_res

    with patch(
        "app.modules.optimization.domain.remediation.SafetyGuardrailService"
    ) as mock_safety:
        mock_safety.return_value.check_all_guards = AsyncMock()
        res = await remediation_service.execute(request_id, tenant_id)
        assert res.status == RemediationStatus.SCHEDULED

    # 2. Passed
    past_time = datetime.now(timezone.utc) - timedelta(hours=1)
    # Reset status to APPROVED/SCHEDULED so it proceeds
    req.status = RemediationStatus.SCHEDULED
    req.scheduled_execution_at = past_time
    req.action = RemediationAction.DELETE_VOLUME
    req.create_backup = False
    req.resource_id = "v-1"
    req.resource_type = "vol"
    req.reviewed_by_user_id = uuid4()
    req.action_parameters = {}
    req.region = "us-east-1"

    with (
        patch(
            "app.modules.optimization.domain.remediation.RemediationActionFactory.get_strategy"
        ) as mock_get_strategy,
        patch(
            "app.modules.optimization.domain.remediation.AuditLogger.log",
            return_value=AsyncMock(),
        ),
        patch(
            "app.modules.optimization.domain.remediation.SafetyGuardrailService"
        ) as mock_safety,
    ):
        mock_safety.return_value.check_all_guards = AsyncMock()
        mock_strategy = MagicMock()
        mock_strategy.execute = AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                resource_id="v-1",
                action_taken=RemediationAction.DELETE_VOLUME.value,
            )
        )
        mock_get_strategy.return_value = mock_strategy
        res = await remediation_service.execute(request_id, tenant_id)
        assert res.status == RemediationStatus.COMPLETED


@pytest.mark.asyncio
async def test_execute_backup_routing(remediation_service, db_session):
    request_id = uuid4()
    tenant_id = uuid4()
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    # Reset status for each check
    req.status = RemediationStatus.APPROVED
    req.create_backup = True
    req.backup_retention_days = 7
    req.reviewed_by_user_id = uuid4()
    req.estimated_monthly_savings = Decimal("50.0")
    req.provider = "aws"
    req.connection_id = None
    req.resource_id = "r-1"
    req.resource_type = "type"
    req.action_parameters = {}
    req.region = "us-east-1"

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = req
    db_session.execute.return_value = mock_res

    with (
        patch(
            "app.modules.optimization.domain.remediation.RemediationActionFactory.get_strategy"
        ) as mock_get_strategy,
        patch(
            "app.modules.optimization.domain.remediation.AuditLogger.log",
            return_value=AsyncMock(),
        ),
        patch(
            "app.modules.optimization.domain.remediation.SafetyGuardrailService"
        ) as mock_safety,
    ):
        mock_safety.return_value.check_all_guards = AsyncMock()
        mock_strategy = MagicMock()
        mock_strategy.execute = AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                resource_id="r-1",
                action_taken=RemediationAction.DELETE_RDS_INSTANCE.value,
                backup_id="rds-snap-123",
            )
        )
        mock_get_strategy.return_value = mock_strategy

        req.status = RemediationStatus.APPROVED
        req.action = RemediationAction.DELETE_RDS_INSTANCE
        result = await remediation_service.execute(
            request_id, tenant_id, bypass_grace_period=True
        )

        assert result.status == RemediationStatus.COMPLETED
        assert result.backup_resource_id == "rds-snap-123"
        mock_strategy.execute.assert_awaited_once()
        _, context = mock_strategy.execute.await_args.args
        assert context.create_backup is True
        assert context.backup_retention_days == 7


@pytest.mark.asyncio
async def test_execute_backup_failure_aborts(remediation_service, db_session):
    request_id = uuid4()
    tenant_id = uuid4()
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    req.status = RemediationStatus.APPROVED
    req.resource_id = "v-1"
    req.resource_type = "vol"
    req.action = RemediationAction.DELETE_VOLUME
    req.create_backup = True
    req.reviewed_by_user_id = uuid4()
    req.estimated_monthly_savings = Decimal("40.0")
    req.provider = "aws"
    req.connection_id = None
    req.action_parameters = {}
    req.region = "us-east-1"

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = req
    db_session.execute.return_value = mock_res

    with (
        patch(
            "app.modules.optimization.domain.remediation.RemediationActionFactory.get_strategy"
        ) as mock_get_strategy,
        patch(
            "app.modules.optimization.domain.remediation.AuditLogger.log",
            return_value=AsyncMock(),
        ),
        patch(
            "app.modules.optimization.domain.remediation.SafetyGuardrailService"
        ) as mock_safety,
    ):
        mock_safety.return_value.check_all_guards = AsyncMock()
        mock_strategy = MagicMock()
        mock_strategy.execute = AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.FAILED,
                resource_id="v-1",
                action_taken=RemediationAction.DELETE_VOLUME.value,
                error_message="BACKUP_FAILED: AWS Error",
            )
        )
        mock_get_strategy.return_value = mock_strategy

        res = await remediation_service.execute(
            request_id, tenant_id, bypass_grace_period=True
        )
        assert res.status == RemediationStatus.FAILED


@pytest.mark.asyncio
async def test_execute_fails_closed_when_finding_binding_mismatches(
    remediation_service, db_session
):
    request_id = uuid4()
    tenant_id = uuid4()
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    req.status = RemediationStatus.APPROVED
    req.resource_id = "vol-actual"
    req.resource_type = "ebs_volume"
    req.action = RemediationAction.DELETE_VOLUME
    req.create_backup = False
    req.reviewed_by_user_id = uuid4()
    req.estimated_monthly_savings = Decimal("15.0")
    req.provider = "aws"
    req.connection_id = uuid4()
    req.finding_id = uuid4()
    req.finding_snapshot = {
        "provider": "aws",
        "connection_id": str(req.connection_id),
        "region": "us-east-1",
        "resource_id": "vol-expected",
        "resource_type": "ebs_volume",
        "fingerprint": "b" * 64,
    }
    req.region = "us-east-1"
    req.action_parameters = {}

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = req
    db_session.execute.return_value = mock_res

    with (
        patch(
            "app.modules.optimization.domain.remediation.AuditLogger.log",
            new=AsyncMock(),
        ) as mock_audit_log,
        patch(
            "app.modules.optimization.domain.remediation.SafetyGuardrailService"
        ) as mock_safety,
    ):
        mock_safety.return_value.check_all_guards = AsyncMock()
        result = await remediation_service.execute(
            request_id, tenant_id, bypass_grace_period=True
        )

    assert result.status == RemediationStatus.FAILED
    assert "bound finding context" in (result.execution_error or "")
    mock_safety.return_value.check_all_guards.assert_not_awaited()
    assert mock_audit_log.await_count >= 1


@pytest.mark.asyncio
async def test_execute_resolves_bound_finding_on_success(remediation_service, db_session):
    request_id = uuid4()
    tenant_id = uuid4()
    connection_id = uuid4()
    finding_id = uuid4()
    finding = OptimizationFinding(
        id=finding_id,
        tenant_id=tenant_id,
        source=FindingSource.ZOMBIE_SCAN,
        status=FindingStatus.OPEN,
        fingerprint="c" * 64,
        provider="aws",
        category="idle_instances",
        connection_id=connection_id,
        connection_name="Prod AWS",
        resource_id="i-123",
        resource_type="ec2_instance",
        region="us-east-1",
        estimated_monthly_savings=Decimal("20.0"),
        confidence_score=Decimal("0.88"),
        explainability_notes="Idle instance detected.",
        requires_manual_review=False,
        automated_action_allowed=True,
        decision_gate=None,
        payload={"resource_id": "i-123"},
    )
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    req.status = RemediationStatus.APPROVED
    req.resource_id = "i-123"
    req.resource_type = "ec2_instance"
    req.action = RemediationAction.STOP_INSTANCE
    req.create_backup = False
    req.reviewed_by_user_id = uuid4()
    req.estimated_monthly_savings = Decimal("20.0")
    req.provider = "aws"
    req.connection_id = connection_id
    req.finding_id = finding_id
    req.finding_snapshot = {
        "provider": "aws",
        "connection_id": str(connection_id),
        "region": "us-east-1",
        "resource_id": "i-123",
        "resource_type": "ec2_instance",
        "fingerprint": "c" * 64,
    }
    req.region = "us-east-1"
    req.action_parameters = {}

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = req
    db_session.execute.return_value = mock_res
    remediation_service.get_by_id = AsyncMock(return_value=finding)
    remediation_service._resolve_credentials = AsyncMock(
        return_value={"region": "us-east-1"}
    )

    with (
        patch(
            "app.modules.optimization.domain.remediation.RemediationActionFactory.get_strategy"
        ) as mock_get_strategy,
        patch(
            "app.modules.optimization.domain.remediation.AuditLogger.log",
            new=AsyncMock(),
        ),
        patch(
            "app.modules.optimization.domain.remediation.SafetyGuardrailService"
        ) as mock_safety,
    ):
        mock_safety.return_value.check_all_guards = AsyncMock()
        mock_strategy = MagicMock()
        mock_strategy.execute = AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                resource_id="i-123",
                action_taken=RemediationAction.STOP_INSTANCE.value,
            )
        )
        mock_get_strategy.return_value = mock_strategy

        result = await remediation_service.execute(
            request_id, tenant_id, bypass_grace_period=True
        )

    assert result.status == RemediationStatus.COMPLETED
    assert finding.status == FindingStatus.RESOLVED
    assert finding.resolved_at is not None


@pytest.mark.asyncio
async def test_get_client_credential_mapping(remediation_service):
    # Test with CamelCase credentials
    remediation_service.credentials = {
        "AccessKeyId": "AK",
        "SecretAccessKey": "SK",
        "SessionToken": "ST",
    }
    mock_session = MagicMock()
    remediation_service.session = mock_session
    with patch(
        "app.modules.optimization.domain.remediation.get_settings"
    ) as mock_settings:
        mock_settings.return_value.AWS_ENDPOINT_URL = "http://localhost"
        await remediation_service._get_client("ec2")
        args, kwargs = mock_session.client.call_args
        assert kwargs["aws_access_key_id"] == "AK"
        assert kwargs["endpoint_url"] == "http://localhost"


@pytest.mark.asyncio
async def test_execute_uses_registered_strategy(remediation_service, db_session):
    request_id = uuid4()
    tenant_id = uuid4()
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    req.status = RemediationStatus.APPROVED
    req.resource_id = "i-123"
    req.resource_type = "instance"
    req.action = RemediationAction.STOP_INSTANCE
    req.create_backup = False
    req.reviewed_by_user_id = uuid4()
    req.estimated_monthly_savings = Decimal("25.0")
    req.provider = "aws"
    req.connection_id = None
    req.region = "us-east-1"
    req.action_parameters = {"reason": "test"}

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = req
    db_session.execute.return_value = mock_res

    with (
        patch(
            "app.modules.optimization.domain.remediation.RemediationActionFactory.get_strategy"
        ) as mock_get_strategy,
        patch(
            "app.modules.optimization.domain.remediation.AuditLogger.log",
            return_value=AsyncMock(),
        ),
        patch(
            "app.modules.optimization.domain.remediation.SafetyGuardrailService"
        ) as mock_safety,
    ):
        mock_safety.return_value.check_all_guards = AsyncMock()
        mock_strategy = MagicMock()
        mock_strategy.execute = AsyncMock(
            return_value=ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                resource_id="i-123",
                action_taken=RemediationAction.STOP_INSTANCE.value,
            )
        )
        mock_get_strategy.return_value = mock_strategy

        result = await remediation_service.execute(
            request_id, tenant_id, bypass_grace_period=True
        )

        assert result.status == RemediationStatus.COMPLETED
        mock_get_strategy.assert_called_once_with("aws", RemediationAction.STOP_INSTANCE)


@pytest.mark.asyncio
async def test_execute_does_not_swallow_base_exceptions(
    remediation_service, db_session
):
    class FatalExecutionFailure(BaseException):
        pass

    request_id = uuid4()
    tenant_id = uuid4()
    req = MagicMock(spec=RemediationRequest)
    req.id = request_id
    req.tenant_id = tenant_id
    req.status = RemediationStatus.APPROVED
    req.resource_id = "i-123"
    req.resource_type = "instance"
    req.action = RemediationAction.STOP_INSTANCE
    req.create_backup = False
    req.reviewed_by_user_id = uuid4()
    req.estimated_monthly_savings = Decimal("25.0")
    req.provider = "aws"
    req.connection_id = None
    req.region = "us-east-1"
    req.action_parameters = {"reason": "test"}

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = req
    db_session.execute.return_value = mock_res

    with (
        patch(
            "app.modules.optimization.domain.remediation.RemediationActionFactory.get_strategy"
        ) as mock_get_strategy,
        patch(
            "app.modules.optimization.domain.remediation.AuditLogger.log",
            return_value=AsyncMock(),
        ),
        patch(
            "app.modules.optimization.domain.remediation.SafetyGuardrailService"
        ) as mock_safety,
    ):
        mock_safety.return_value.check_all_guards = AsyncMock()
        mock_strategy = MagicMock()
        mock_strategy.execute = AsyncMock(side_effect=FatalExecutionFailure("fatal"))
        mock_get_strategy.return_value = mock_strategy

        with pytest.raises(FatalExecutionFailure):
            await remediation_service.execute(
                request_id, tenant_id, bypass_grace_period=True
            )


@pytest.mark.asyncio
async def test_enforce_hard_limit_success(remediation_service, db_session):
    tenant_id = uuid4()
    req = MagicMock(spec=RemediationRequest)
    req.id = uuid4()
    req.tenant_id = tenant_id
    req.action = RemediationAction.STOP_INSTANCE
    req.status = RemediationStatus.PENDING
    req.confidence_score = Decimal("0.99")
    req.estimated_monthly_savings = Decimal("10.0")

    with patch(
        "app.shared.llm.usage_tracker.UsageTracker.check_budget",
        return_value="hard_limit",
    ):
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = [req]
        db_session.execute.return_value = mock_res

        with patch.object(
            remediation_service, "execute", return_value=AsyncMock()
        ) as mock_execute:
            ids = await remediation_service.enforce_hard_limit(tenant_id)
            assert len(ids) == 1
            assert req.status == RemediationStatus.APPROVED
            assert req.reviewed_by_user_id == UUID(
                "00000000-0000-0000-0000-000000000000"
            )
            mock_execute.assert_called_once_with(
                req.id, tenant_id, bypass_grace_period=False
            )
