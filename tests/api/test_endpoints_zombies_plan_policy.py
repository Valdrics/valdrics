"""Zombie API endpoint tests: plan generation and policy preview flows."""

import pytest
from uuid import uuid4
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient

class TestZombieAPIPlanAndPolicyPreview:
    """Tests for remediation planning and policy preview endpoints."""

    @pytest.mark.asyncio
    async def test_get_remediation_plan_success(
        self, ac: AsyncClient, db, test_tenant, mock_user, test_remediation_request
    ):
        """Test successful retrieval of remediation plan."""
        # Mock authentication by overriding the app's dependency
        from app.shared.core.auth import get_current_user, require_tenant_access
        from app.shared.core.pricing import FeatureFlag

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[FeatureFlag.GITOPS_REMEDIATION] = lambda: True

        # Mock service response
        with patch(
            "app.modules.optimization.api.v1.zombies.RemediationService"
        ) as mock_service_cls:
            mock_service = mock_service_cls.return_value
            mock_service.get_by_id = AsyncMock(return_value=test_remediation_request)
            mock_service.generate_iac_plan = AsyncMock(return_value="# Valdrics GitOps Remediation Plan\n# Resource: i-test123 (ec2_instance)\n# Savings: $50.00/mo\n# Action: stop_instance\n\n# Option 1: Manual State Removal\nterraform state rm cloud_resource.i_test123\n\n# Option 2: Terraform 'removed' block (Recommended for TF 1.7+)\nremoved {\n  from = cloud_resource.i_test123\n  lifecycle {\n    destroy = true\n  }\n}")

            response = await ac.get(
                f"/api/v1/zombies/plan/{test_remediation_request.id}"
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
            assert "Valdrics GitOps Remediation Plan" in data["plan"]
            assert data["resource_id"] == "i-test123"

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(FeatureFlag.GITOPS_REMEDIATION, None)

    @pytest.mark.asyncio
    async def test_get_remediation_plan_not_found(
        self, ac: AsyncClient, mock_user, test_tenant
    ):
        """Test remediation plan retrieval for non-existent request."""
        # Mock authentication by overriding the app's dependency
        from app.shared.core.auth import get_current_user, require_tenant_access
        from app.shared.core.pricing import FeatureFlag

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[FeatureFlag.GITOPS_REMEDIATION] = lambda: True

        # Mock service to return None for request
        with patch(
            "app.modules.optimization.api.v1.zombies.RemediationService"
        ) as mock_service_cls:
            mock_service = AsyncMock()
            mock_service.get_by_id.return_value = None  # Request not found
            mock_service_cls.return_value = mock_service

            response = await ac.get(f"/api/v1/zombies/plan/{uuid4()}")

            assert response.status_code == 404

        # Clean up overrides
        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(FeatureFlag.GITOPS_REMEDIATION, None)

    @pytest.mark.asyncio
    async def test_preview_remediation_policy_success(
        self, ac: AsyncClient, mock_user, test_tenant, test_remediation_request
    ):
        """Test policy preview endpoint returns deterministic preview payload."""
        from app.shared.core.auth import get_current_user, require_tenant_access
        from app.shared.core.pricing import FeatureFlag

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[FeatureFlag.POLICY_PREVIEW] = lambda: True

        with patch(
            "app.modules.optimization.api.v1.zombies.RemediationService"
        ) as mock_service_cls:
            mock_service = mock_service_cls.return_value
            mock_service.get_by_id = AsyncMock(return_value=test_remediation_request)
            mock_service.preview_policy = AsyncMock(return_value={
                "decision": "allow",
                "summary": "No policy rules triggered.",
                "tier": "pro",
                "rule_hits": [],
                "config": {
                    "enabled": True,
                    "block_production_destructive": True,
                    "require_gpu_override": True,
                    "low_confidence_warn_threshold": 0.9,
                },
            })

            response = await ac.get(
                f"/api/v1/zombies/policy-preview/{test_remediation_request.id}"
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["decision"] == "allow"
            assert payload["tier"] == "pro"

        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(FeatureFlag.POLICY_PREVIEW, None)

    @pytest.mark.asyncio
    async def test_preview_remediation_policy_payload_success(
        self, ac: AsyncClient, mock_user, test_tenant
    ):
        """Test payload-based policy preview endpoint before request creation."""
        from app.shared.core.auth import get_current_user, require_tenant_access
        from app.shared.core.pricing import FeatureFlag

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[FeatureFlag.POLICY_PREVIEW] = lambda: True

        with patch(
            "app.modules.optimization.api.v1.zombies.RemediationService"
        ) as mock_service_cls:
            mock_service = mock_service_cls.return_value
            mock_service.preview_policy_input = AsyncMock(return_value={
                "decision": "escalate",
                "summary": "GPU-related remediation requires explicit GPU approval override.",
                "tier": "pro",
                "rule_hits": [{"rule_id": "gpu-change-requires-explicit-override"}],
                "config": {
                    "enabled": True,
                    "block_production_destructive": True,
                    "require_gpu_override": True,
                    "low_confidence_warn_threshold": 0.9,
                },
            })

            response = await ac.post(
                "/api/v1/zombies/policy-preview",
                json={
                    "resource_id": "i-gpu-smoke",
                    "resource_type": "GPU Compute",
                    "action": "terminate_instance",
                    "provider": "aws",
                    "confidence_score": 0.88,
                    "explainability_notes": "gpu workload",
                },
            )
            assert response.status_code == 200
            payload = response.json()
            assert payload["decision"] == "escalate"
            assert payload["tier"] == "pro"

        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(FeatureFlag.POLICY_PREVIEW, None)

    @pytest.mark.asyncio
    async def test_preview_remediation_policy_payload_invalid_action(
        self, ac: AsyncClient, mock_user, test_tenant
    ):
        """Invalid action on payload preview should return deterministic validation error."""
        from app.shared.core.auth import get_current_user, require_tenant_access
        from app.shared.core.pricing import FeatureFlag

        async def mock_get_current_user():
            return mock_user

        async def mock_require_tenant_access():
            return test_tenant.id

        ac.app.dependency_overrides[get_current_user] = mock_get_current_user
        ac.app.dependency_overrides[require_tenant_access] = mock_require_tenant_access
        ac.app.dependency_overrides[FeatureFlag.POLICY_PREVIEW] = lambda: True

        response = await ac.post(
            "/api/v1/zombies/policy-preview",
            json={
                "resource_id": "i-gpu-smoke",
                "resource_type": "GPU Compute",
                "action": "invalid_action",
                "provider": "aws",
            },
        )
        assert response.status_code == 400
        payload = response.json()
        assert "invalid_remediation_action" in payload.get("error", {}).get("code", "")

        ac.app.dependency_overrides.pop(get_current_user, None)
        ac.app.dependency_overrides.pop(require_tenant_access, None)
        ac.app.dependency_overrides.pop(FeatureFlag.POLICY_PREVIEW, None)


