from typing import Any, Optional

from app.modules.optimization.domain.actions.base import BaseRemediationAction, RemediationContext
from app.shared.core.pricing import FeatureFlag


def create_gcp_action_credentials(raw_credentials: Any) -> Any:
    from app.modules.optimization.adapters.common.remediation_clients import (
        create_gcp_action_credentials as _create_gcp_action_credentials,
    )

    return _create_gcp_action_credentials(raw_credentials)


def create_gcp_instances_client(raw_credentials: Any) -> Any:
    from app.modules.optimization.adapters.common.remediation_clients import (
        create_gcp_instances_client as _create_gcp_instances_client,
    )

    return _create_gcp_instances_client(raw_credentials)


class BaseGCPAction(BaseRemediationAction):
    """
    Base class for GCP remediation actions.
    Provides InstancesClient management.
    """

    @property
    def required_feature(self) -> FeatureFlag:
        return FeatureFlag.MULTI_CLOUD

    @staticmethod
    def _credentials_factory(context: RemediationContext) -> Any:
        factories = context.parameters if isinstance(context.parameters, dict) else {}
        credentials_factory = factories.get("gcp_action_credentials_factory")
        if callable(credentials_factory):
            return credentials_factory
        return create_gcp_action_credentials

    @staticmethod
    def _instances_client_factory(context: RemediationContext) -> Any:
        factories = context.parameters if isinstance(context.parameters, dict) else {}
        client_factory = factories.get("gcp_instances_client_factory")
        if callable(client_factory):
            return client_factory
        return create_gcp_instances_client

    async def _get_credentials(self, context: RemediationContext) -> Any:
        return self._credentials_factory(context)(context.credentials or None)

    async def _get_instances_client(self, context: RemediationContext) -> Any:
        return self._instances_client_factory(context)(context.credentials or None)

    async def validate(self, resource_id: str, context: RemediationContext) -> bool:
        return True

    async def create_backup(self, resource_id: str, context: RemediationContext) -> Optional[str]:
        # GCP machine image or disk snapshot could be implemented here
        return None
