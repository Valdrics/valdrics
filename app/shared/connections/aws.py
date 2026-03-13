from typing import Any
from urllib.parse import quote
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.models.aws_connection import AWSConnection
from app.shared.adapters.aws_multitenant import MultiTenantAWSAdapter
from app.shared.adapters.aws_utils import map_aws_connection_to_credentials
from app.shared.core.config import get_settings
from app.shared.core.exceptions import ResourceNotFoundError, AdapterError
from app.shared.core.runtime_paths import PROJECT_ROOT

logger = structlog.get_logger()
AWS_CONNECTION_VERIFY_RECOVERABLE_EXCEPTIONS = (
    SQLAlchemyError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
    AttributeError,
    KeyError,
    LookupError,
)
_CLOUDFORMATION_TEMPLATE_PATH = (
    PROJECT_ROOT / "cloudformation" / "valdrics-role.yaml"
)
_CLOUDFORMATION_PUBLIC_PATH = "/api/v1/public/templates/aws/valdrics-role.yaml"
_TRUST_PRINCIPAL_TOKEN = "__VALDRICS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN__"


class AWSConnectionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _build_verification_adapter(connection: AWSConnection) -> MultiTenantAWSAdapter:
        """
        Build an AWS verification adapter that only validates STS AssumeRole.

        Verification must not depend on CUR ingestion state.
        """
        return MultiTenantAWSAdapter(map_aws_connection_to_credentials(connection))

    @staticmethod
    def _resolve_cloudformation_console_region(settings_obj: Any) -> str:
        configured_region = str(
            getattr(settings_obj, "AWS_DEFAULT_REGION", "") or ""
        ).strip()
        supported_regions = {
            str(region).strip()
            for region in getattr(settings_obj, "AWS_SUPPORTED_REGIONS", [])
            if str(region).strip()
        }
        if configured_region and (
            not supported_regions or configured_region in supported_regions
        ):
            return configured_region
        return "us-east-1"

    @staticmethod
    def _resolve_assume_role_trust_principal_arn(settings_obj: Any) -> str:
        principal_arn = str(
            getattr(settings_obj, "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN", "") or ""
        ).strip()
        if not principal_arn:
            raise RuntimeError(
                "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN must be configured for AWS setup templates"
            )
        return principal_arn

    @staticmethod
    def get_cloudformation_template_yaml() -> str:
        """Return the release-owned CloudFormation template with injected trust principal."""
        settings = get_settings()
        principal_arn = AWSConnectionService._resolve_assume_role_trust_principal_arn(
            settings
        )
        if not _CLOUDFORMATION_TEMPLATE_PATH.exists():
            raise RuntimeError(
                "AWS setup template file is missing from the application release bundle"
            )
        template = _CLOUDFORMATION_TEMPLATE_PATH.read_text(encoding="utf-8")
        if _TRUST_PRINCIPAL_TOKEN not in template:
            raise RuntimeError(
                "AWS setup template is missing the trust principal injection token"
            )
        return template.replace(_TRUST_PRINCIPAL_TOKEN, principal_arn, 1)

    @staticmethod
    def get_cloudformation_template_url() -> str:
        """Return the public URL used by CloudFormation launch links."""
        settings = get_settings()
        configured = str(
            getattr(settings, "CLOUDFORMATION_TEMPLATE_URL", "") or ""
        ).strip()
        if configured:
            return configured
        api_url = str(getattr(settings, "API_URL", "") or "").strip()
        if not api_url:
            raise RuntimeError(
                "API_URL must be configured to derive the public AWS setup template URL"
            )
        return f"{api_url.rstrip('/')}{_CLOUDFORMATION_PUBLIC_PATH}"

    @staticmethod
    def get_setup_templates(external_id: str) -> dict[str, Any]:
        """
        Returns CloudFormation and Terraform snippets for provisioning the Valdrics role.
        """
        settings = get_settings()
        template_url = AWSConnectionService.get_cloudformation_template_url()
        console_region = AWSConnectionService._resolve_cloudformation_console_region(
            settings
        )
        encoded_template_url = quote(template_url, safe="")
        return {
            "external_id": external_id,
            "cloudformation_yaml": AWSConnectionService.get_cloudformation_template_yaml(),
            "terraform_hcl": f'module "valdrics_connection" {{ source = "valdrics/aws-connection" external_id = "{external_id}" }}',
            "magic_link": (
                "https://console.aws.amazon.com/cloudformation/home"
                f"?region={console_region}"
                "#/stacks/create/review"
                "?stackName=ValdricsAccess"
                f"&templateURL={encoded_template_url}"
                f"&param_ExternalId={external_id}"
            ),
            "instructions": (
                "Launch the CloudFormation stack from the AWS console link or use the "
                "Terraform snippet to provision the cross-account role, then create the "
                "AWS connection with the generated external ID."
            ),
            "permissions_summary": ["sts:AssumeRole"],
        }

    async def verify_connection(
        self, connection_id: UUID, tenant_id: UUID
    ) -> dict[str, Any]:
        """
        Verifies that the STS AssumeRole works for the given connection.
        """
        result = await self.db.execute(
            select(AWSConnection).where(
                AWSConnection.id == connection_id, AWSConnection.tenant_id == tenant_id
            )
        )
        connection = result.scalar_one_or_none()
        if not connection:
            raise ResourceNotFoundError(f"AWS Connection {connection_id} not found")

        try:
            adapter = self._build_verification_adapter(connection)
            success = await adapter.verify_connection()
            if success:
                connection.status = "active"
                await self.db.commit()
                return {
                    "status": "success",
                    "message": "Connection verified and active.",
                }
            else:
                connection.status = "error"
                await self.db.commit()
                failure_message = getattr(adapter, "last_error", None) or (
                    "Failed to assume role. Check IAM policy and Trust Relationship."
                )
                return {
                    "status": "failed",
                    "message": failure_message,
                }
        except AdapterError as e:
            connection.status = "error"
            await self.db.commit()
            return {"status": "error", "message": str(e), "code": e.code}
        except AWS_CONNECTION_VERIFY_RECOVERABLE_EXCEPTIONS as e:
            connection.status = "error"
            await self.db.commit()
            logger.error(
                "aws_verification_unexpected_error",
                error=str(e),
                connection_id=str(connection_id),
            )
            return {
                "status": "error",
                "message": "An unexpected error occurred during verification.",
            }
