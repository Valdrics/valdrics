from typing import Any, Optional

from app.modules.optimization.domain.actions.base import BaseRemediationAction, RemediationContext
from app.shared.core.config import get_settings


def create_aws_session() -> Any:
    from app.modules.optimization.adapters.common.remediation_clients import (
        create_aws_session as _create_aws_session,
    )

    return _create_aws_session()


def build_aws_client(**kwargs: Any) -> Any:
    from app.modules.optimization.adapters.common.remediation_clients import (
        build_aws_client as _build_aws_client,
    )

    return _build_aws_client(**kwargs)


class BaseAWSAction(BaseRemediationAction):
    """
    Base class for AWS remediation actions.
    Provides aioboto3 client management.
    """

    def __init__(self) -> None:
        self.session: Any | None = None

    @staticmethod
    def _session_factory(context: RemediationContext) -> Any:
        factories = context.parameters if isinstance(context.parameters, dict) else {}
        session_factory = factories.get("aws_session_factory")
        if callable(session_factory):
            return session_factory
        return create_aws_session

    @staticmethod
    def _client_factory(context: RemediationContext) -> Any:
        factories = context.parameters if isinstance(context.parameters, dict) else {}
        client_factory = factories.get("aws_client_factory")
        if callable(client_factory):
            return client_factory
        return build_aws_client

    async def _get_client(self, service_name: str, context: RemediationContext) -> Any:
        """Helper to get aioboto3 client with context credentials."""
        settings = get_settings()
        if self.session is None:
            self.session = self._session_factory(context)()
        return self._client_factory(context)(
            session=self.session,
            service_name=service_name,
            region=context.region,
            endpoint_url=settings.AWS_ENDPOINT_URL,
            raw_credentials=context.credentials,
        )

    async def validate(self, resource_id: str, context: RemediationContext) -> bool:
        # Default validation is True, specific actions can override
        return True

    async def create_backup(self, resource_id: str, context: RemediationContext) -> Optional[str]:
        # Default no backup, specific actions (e.g., DeleteVolume) can override
        return None
