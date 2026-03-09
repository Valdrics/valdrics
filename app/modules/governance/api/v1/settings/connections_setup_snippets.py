"""
Connection setup snippet endpoints (provider onboarding templates/instructions).
"""

from typing import Any

from fastapi import APIRouter, Depends, Request

from app.models.aws_connection import AWSConnection
from app.schemas.connections import TemplateResponse
from app.shared.connections.aws import AWSConnectionService
from app.shared.connections.instructions import ConnectionInstructionService
from app.modules.governance.api.v1.settings.connections_helpers import _require_tenant_id
from app.shared.core.auth import CurrentUser, requires_role_with_db_context
from app.shared.core.rate_limit import rate_limit

router = APIRouter()


@router.post("/aws/setup", response_model=TemplateResponse)
@rate_limit("10/minute")
async def get_aws_setup_templates(
    request: Request,
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
) -> TemplateResponse:
    """Get CloudFormation/Terraform templates and Magic Link for AWS setup."""
    _require_tenant_id(current_user)
    external_id = AWSConnection.generate_external_id()
    templates = AWSConnectionService.get_setup_templates(external_id)
    return TemplateResponse(**templates)


@router.post("/azure/setup")
async def get_azure_setup(
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
) -> dict[str, str]:
    """Get Azure Workload Identity setup instructions."""
    return ConnectionInstructionService.get_azure_setup_snippet(
        str(_require_tenant_id(current_user))
    )


@router.post("/gcp/setup")
async def get_gcp_setup(
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
) -> dict[str, str]:
    """Get GCP Identity Federation setup instructions."""
    return ConnectionInstructionService.get_gcp_setup_snippet(
        str(_require_tenant_id(current_user))
    )


@router.post("/saas/setup")
async def get_saas_setup(
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
) -> dict[str, Any]:
    """Get SaaS Cloud+ setup instructions."""
    return ConnectionInstructionService.get_saas_setup_snippet(
        str(_require_tenant_id(current_user))
    )


@router.post("/license/setup")
async def get_license_setup(
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
) -> dict[str, Any]:
    """Get License/ITAM Cloud+ setup instructions."""
    return ConnectionInstructionService.get_license_setup_snippet(
        str(_require_tenant_id(current_user))
    )


@router.post("/platform/setup")
async def get_platform_setup(
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
) -> dict[str, Any]:
    """Get internal platform Cloud+ setup instructions."""
    return ConnectionInstructionService.get_platform_setup_snippet(
        str(_require_tenant_id(current_user))
    )


@router.post("/hybrid/setup")
async def get_hybrid_setup(
    current_user: CurrentUser = Depends(requires_role_with_db_context("member")),
) -> dict[str, Any]:
    """Get private/hybrid infra Cloud+ setup instructions."""
    return ConnectionInstructionService.get_hybrid_setup_snippet(
        str(_require_tenant_id(current_user))
    )
