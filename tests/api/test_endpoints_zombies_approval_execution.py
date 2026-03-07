"""Zombie API endpoint tests: approval and execution flows."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
from httpx import AsyncClient

class TestZombieAPIApprovalAndExecution:
    """Tests for remediation approval and execution endpoints."""

    @pytest.mark.asyncio
    async def test_approve_remediation_success(
        self, ac: AsyncClient, db, test_tenant, mock_user, test_remediation_request
    ):
        """Test successful remediation approval."""
        approval_data = {"notes": "Approved for cost savings"}

        # Mock authentication by overriding the app's dependency
        from app.shared.core.auth import (
            get_current_user,
            require_tenant_access,
            requires_role,
        )

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        async def mock_requires_role(role: str):
            return mock_user

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[requires_role] = mock_requires_role

        # Mock service response
        with patch(
            "app.modules.optimization.api.v1.zombies.RemediationService"
        ) as mock_service_cls:
            mock_service = mock_service_cls.return_value
            mock_result = MagicMock()
            mock_result.id = test_remediation_request.id
            mock_service.approve = AsyncMock(return_value=mock_result)

            response = await ac.post(
                f"/api/v1/zombies/approve/{test_remediation_request.id}",
                json=approval_data,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "approved"

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(requires_role, None)

    @pytest.mark.asyncio
    async def test_approve_remediation_not_found(
        self, ac: AsyncClient, mock_user, test_tenant
    ):
        """Test remediation approval with non-existent request."""
        approval_data = {"notes": "Approved"}

        # Mock authentication by overriding the app's dependency
        from app.shared.core.auth import (
            get_current_user,
            require_tenant_access,
            requires_role,
        )

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        async def mock_requires_role(role: str):
            return mock_user

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[requires_role] = mock_requires_role

        # Mock service to raise ValueError
        with patch(
            "app.modules.optimization.api.v1.zombies.RemediationService"
        ) as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.approve.side_effect = ValueError("Request not found")
            mock_service_cls.return_value = mock_service

            response = await ac.post(
                f"/api/v1/zombies/approve/{uuid4()}", json=approval_data
            )

            assert response.status_code == 404

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(requires_role, None)

    @pytest.mark.asyncio
    async def test_execute_remediation_success(
        self, ac: AsyncClient, db, test_tenant, mock_user, test_remediation_request
    ):
        """Test successful remediation execution."""
        # Mock AWS connection
        from app.models.aws_connection import AWSConnection

        aws_conn = AWSConnection(
            id=test_tenant.id,  # SEC: API uses tenant_id as PK for lookup here
            tenant_id=test_tenant.id,
            region="us-east-1",
            role_arn="arn:aws:iam::123456789012:role/ValdricsReadOnly",
            external_id="vx-test-id",
            aws_account_id="123456789012",
        )
        db.add(aws_conn)
        await db.commit()

        # Mock authentication by overriding the app's dependency
        from app.shared.core.auth import (
            get_current_user,
            require_tenant_access,
            requires_role,
        )
        from app.shared.core.pricing import FeatureFlag

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        async def mock_requires_role(role: str):
            return mock_user

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[requires_role] = mock_requires_role
        ac.app.dependency_overrides[FeatureFlag.AUTO_REMEDIATION] = lambda: True

        # Mock service response
        with (
            patch(
                "app.modules.optimization.api.v1.zombies.RemediationService"
            ) as mock_service_cls,
            patch(
                "app.shared.adapters.aws_multitenant.MultiTenantAWSAdapter"
            ) as mock_adapter_cls,
        ):
            mock_service = mock_service_cls.return_value
            mock_executed_request = MagicMock()
            mock_executed_request.status.value = "completed"
            mock_executed_request.id = test_remediation_request.id
            mock_service.execute = AsyncMock(return_value=mock_executed_request)
            mock_service.get_by_id = AsyncMock(return_value=aws_conn)

            mock_adapter = AsyncMock()
            mock_credentials = MagicMock()
            mock_adapter.get_credentials.return_value = mock_credentials
            mock_adapter_cls.return_value = mock_adapter

            response = await ac.post(
                f"/api/v1/zombies/execute/{test_remediation_request.id}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(requires_role, None)
        ac.app.dependency_overrides.pop(FeatureFlag.AUTO_REMEDIATION, None)

    @pytest.mark.asyncio
    async def test_execute_remediation_no_aws_connection(
        self,
        ac: AsyncClient,
        mock_user,
        test_tenant,
        test_remediation_request,
    ):
        """Test remediation execution surfaces aws_connection_missing from service."""
        from app.shared.core.exceptions import ValdricsException

        # Mock authentication by overriding the app's dependency
        from app.shared.core.auth import (
            get_current_user,
            require_tenant_access,
            requires_role,
        )
        from app.shared.core.pricing import FeatureFlag

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        async def mock_requires_role(role: str):
            return mock_user

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[requires_role] = mock_requires_role
        ac.app.dependency_overrides[FeatureFlag.AUTO_REMEDIATION] = lambda: True

        with patch(
            "app.modules.optimization.api.v1.zombies.RemediationService"
        ) as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.execute.side_effect = ValdricsException(
                message="No AWS connection found for this tenant",
                code="aws_connection_missing",
                status_code=400,
            )
            mock_service_cls.return_value = mock_service

            response = await ac.post(
                f"/api/v1/zombies/execute/{test_remediation_request.id}?bypass_grace_period=true"
            )

        assert response.status_code == 400
        data = response.json()
        assert "aws_connection_missing" in data.get("error", {}).get("code", "")

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(requires_role, None)
        ac.app.dependency_overrides.pop(FeatureFlag.AUTO_REMEDIATION, None)

    @pytest.mark.asyncio
    async def test_execute_remediation_escalation_without_aws_connection(
        self,
        ac: AsyncClient,
        db,
        mock_user,
        test_tenant,
        test_remediation_request,
    ):
        """Escalation policy can be evaluated/executed without AWS credentials lookup."""
        from app.models.remediation import RemediationStatus
        from app.shared.core.auth import (
            get_current_user,
            require_tenant_access,
            requires_role,
        )
        from app.shared.core.pricing import FeatureFlag

        test_remediation_request.status = RemediationStatus.APPROVED
        db.add(test_remediation_request)
        # Keep changes inside the shared test transaction to avoid session deadlocks.
        await db.flush()

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        async def mock_requires_role(role: str):
            return mock_user

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[requires_role] = mock_requires_role
        ac.app.dependency_overrides[FeatureFlag.AUTO_REMEDIATION] = lambda: True

        with patch(
            "app.modules.optimization.api.v1.zombies.RemediationService"
        ) as mock_service_cls:
            mock_service = mock_service_cls.return_value
            mock_service.preview_policy = AsyncMock(return_value={"decision": "escalate"})
            mock_result = MagicMock()
            mock_result.status.value = "pending_approval"
            mock_result.id = test_remediation_request.id
            mock_service.execute = AsyncMock(return_value=mock_result)

            response = await ac.post(
                f"/api/v1/zombies/execute/{test_remediation_request.id}"
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "pending_approval"

        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(requires_role, None)
        ac.app.dependency_overrides.pop(FeatureFlag.AUTO_REMEDIATION, None)

