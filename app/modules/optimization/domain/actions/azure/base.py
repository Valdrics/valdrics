from typing import Any, Optional

from app.modules.optimization.domain.actions.base import BaseRemediationAction, RemediationContext
from app.shared.core.pricing import FeatureFlag


def create_azure_action_credential(raw_credentials: Any) -> Any:
    from app.modules.optimization.adapters.common.remediation_clients import (
        create_azure_action_credential as _create_azure_action_credential,
    )

    return _create_azure_action_credential(raw_credentials)


def create_azure_compute_client(*, credential: Any, subscription_id: str) -> Any:
    from app.modules.optimization.adapters.common.remediation_clients import (
        create_azure_compute_client as _create_azure_compute_client,
    )

    return _create_azure_compute_client(
        credential=credential,
        subscription_id=subscription_id,
    )


class BaseAzureAction(BaseRemediationAction):
    """
    Base class for Azure remediation actions.
    Provides ComputeManagementClient management.
    """

    @property
    def required_feature(self) -> FeatureFlag:
        return FeatureFlag.MULTI_CLOUD

    def __init__(self) -> None:
        self._credential: Optional[Any] = None
        self._compute_client: Optional[Any] = None

    @staticmethod
    def _credential_factory(context: RemediationContext) -> Any:
        factories = context.parameters if isinstance(context.parameters, dict) else {}
        credential_factory = factories.get("azure_action_credential_factory")
        if callable(credential_factory):
            return credential_factory
        return create_azure_action_credential

    @staticmethod
    def _compute_client_factory(context: RemediationContext) -> Any:
        factories = context.parameters if isinstance(context.parameters, dict) else {}
        compute_client_factory = factories.get("azure_compute_client_factory")
        if callable(compute_client_factory):
            return compute_client_factory
        return create_azure_compute_client

    async def _get_credentials(self, context: RemediationContext) -> Any:
        if not self._credential:
            self._credential = self._credential_factory(context)(
                context.credentials or {}
            )
        return self._credential

    async def _get_compute_client(self, context: RemediationContext) -> Any:
        if not self._compute_client:
            creds = await self._get_credentials(context)
            subscription_id = str((context.credentials or {}).get("subscription_id", ""))
            self._compute_client = self._compute_client_factory(context)(
                credential=creds, subscription_id=subscription_id
            )
        return self._compute_client

    async def validate(self, resource_id: str, context: RemediationContext) -> bool:
        return True

    async def create_backup(self, resource_id: str, context: RemediationContext) -> Optional[str]:
        # Backup (Snapshot) for Azure VM disks could be implemented here
        return None
