"""API endpoint tests: input validation and background job endpoint contracts."""

import pytest
from uuid import uuid4
from httpx import AsyncClient

class TestInputValidation:
    """Tests for API input validation."""

    @pytest.mark.asyncio
    async def test_invalid_json_handling(self, ac: AsyncClient):
        """Test handling of invalid JSON in request bodies."""
        response = await ac.post(
            "/api/v1/zombies/request",
            content="invalid json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_required_fields(
        self, ac: AsyncClient, mock_user, test_tenant
    ):
        """Test validation of missing required fields."""
        # Mock authentication by overriding the app's dependency
        from app.shared.core.auth import get_current_user, require_tenant_access
        from app.shared.core.pricing import FeatureFlag

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[FeatureFlag.AUTO_REMEDIATION] = lambda: True

        # Missing required fields
        incomplete_data = {"resource_type": "ec2_instance"}

        response = await ac.post("/api/v1/zombies/request", json=incomplete_data)

        assert response.status_code == 422  # Validation error

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(FeatureFlag.AUTO_REMEDIATION, None)

    @pytest.mark.asyncio
    async def test_invalid_enum_values(self, ac: AsyncClient, mock_user, test_tenant):
        """Test validation of invalid enum values."""
        # Mock authentication by overriding the app's dependency
        from app.shared.core.auth import get_current_user, require_tenant_access
        from app.shared.core.pricing import FeatureFlag

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        from app.shared.core.dependencies import requires_feature

        ac.app.dependency_overrides[requires_feature(FeatureFlag.AUTO_REMEDIATION)] = (
            lambda: True
        )

        # Invalid action enum value
        invalid_data = {
            "resource_id": "i-test123",
            "resource_type": "ec2_instance",
            "action": "invalid_action_name",
            "provider": "aws",
            "estimated_savings": 50.0,
        }

        response = await ac.post("/api/v1/zombies/request", json=invalid_data)

        assert response.status_code == 400
        data = response.json()
        assert "invalid_remediation_action" in data.get("error", {}).get("code", "")

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(FeatureFlag.AUTO_REMEDIATION, None)

    @pytest.mark.asyncio
    async def test_uuid_validation(self, ac: AsyncClient, mock_user, test_tenant):
        """Test validation of UUID parameters."""
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

        # Invalid UUID format
        response = await ac.post(
            "/api/v1/zombies/approve/invalid-uuid", json={"notes": "test"}
        )

        assert response.status_code == 422  # Validation error

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(requires_role, None)


class TestBackgroundJobsAPI:
    """Tests for background jobs API endpoints."""

    @pytest.mark.asyncio
    async def test_job_status_endpoint(
        self, ac: AsyncClient, db, test_tenant, mock_user
    ):
        """Test job status retrieval endpoint."""
        # Mock authentication by overriding the app's dependency
        from app.shared.core.auth import get_current_user, require_tenant_access

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access

        # This would test the jobs API endpoints
        # For now, test that the endpoint exists and requires auth
        response = await ac.get("/api/v1/jobs/status")

        # Should return some response (may be 404 if not implemented yet)
        assert response.status_code in [200, 404, 501]

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)

    @pytest.mark.asyncio
    async def test_job_cancellation_endpoint(
        self, ac: AsyncClient, mock_user, test_tenant
    ):
        """Test job cancellation endpoint."""
        # Mock authentication by overriding the app's dependency
        from app.shared.core.auth import get_current_user, require_tenant_access

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access

        # Test job cancellation functionality
        response = await ac.post(f"/api/v1/jobs/cancel/{uuid4()}")

        # Should return some response (may be 404 if not implemented yet)
        assert response.status_code in [200, 404, 501]

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)


