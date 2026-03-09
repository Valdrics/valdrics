from urllib.parse import quote
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from typing import Any
import structlog
from app.models.aws_connection import AWSConnection
from app.shared.adapters.aws_multitenant import MultiTenantAWSAdapter
from app.shared.adapters.aws_utils import map_aws_connection_to_credentials
from app.shared.core.config import get_settings
from app.shared.core.exceptions import ResourceNotFoundError, AdapterError

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
    def get_setup_templates(external_id: str) -> dict[str, Any]:
        """
        Returns CloudFormation and Terraform snippets for provisioning the Valdrics role.
        """
        settings = get_settings()
        template_url = str(getattr(settings, "CLOUDFORMATION_TEMPLATE_URL", "") or "").strip()
        if not template_url:
            raise RuntimeError("CLOUDFORMATION_TEMPLATE_URL must be configured for AWS setup templates")

        configured_region = str(getattr(settings, "AWS_DEFAULT_REGION", "") or "").strip()
        supported_regions = {
            str(region).strip()
            for region in getattr(settings, "AWS_SUPPORTED_REGIONS", [])
            if str(region).strip()
        }
        if configured_region and (
            not supported_regions or configured_region in supported_regions
        ):
            console_region = configured_region
        else:
            console_region = "us-east-1"
        encoded_template_url = quote(template_url, safe="")
        return {
            "external_id": external_id,
            "cloudformation_yaml": template_url,
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
