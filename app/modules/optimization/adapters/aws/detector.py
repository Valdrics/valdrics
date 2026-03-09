from typing import List, Dict, Any, Optional
import aioboto3
import structlog
from app.modules.optimization.domain.ports import BaseZombieDetector
from app.modules.optimization.domain.plugin import ZombiePlugin
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.optimization.domain.registry import registry

# Import plugins to trigger registration
import app.modules.optimization.adapters.aws.plugins  # noqa

logger = structlog.get_logger()


class AWSZombieDetector(BaseZombieDetector):
    """
    Concrete implementation of ZombieDetector for AWS.
    Manages aioboto3 session and AWS-specific plugin execution.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        credentials: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
        connection: Any = None,
    ) -> None:
        super().__init__(region, credentials, db, connection)
        self.session = aioboto3.Session()
        self._adapter = None
        if connection:
            from app.shared.adapters.aws_multitenant import MultiTenantAWSAdapter

            self._adapter = MultiTenantAWSAdapter(connection)

        self._initialize_plugins()

    @property
    def provider_name(self) -> str:
        return "aws"

    def _initialize_plugins(self) -> None:
        """Register every available AWS detection plugin from the registry."""
        self.plugins = registry.get_plugins_for_provider("aws")

    @staticmethod
    def _inventory_scan_metadata(inventory: Any) -> dict[str, Any]:
        method = str(getattr(inventory, "discovery_method", "") or "").strip()
        degraded_methods = {
            "native-api-fallback-partial",
            "native-api-fallback-degraded",
        }
        status = "ok"
        if method == "native-api-fallback-partial":
            status = "partial"
        elif method == "native-api-fallback-degraded":
            status = "degraded"
        return {
            "status": status,
            "method": method or "unknown",
            "resource_count": int(getattr(inventory, "total_count", 0) or 0),
            "coverage_limitations": (
                "Inventory was derived from native fallback discovery and may not "
                "cover the full AWS account resource surface."
                if method in degraded_methods
                else None
            ),
        }

    @classmethod
    def _apply_inventory_completeness(
        cls, results: Dict[str, Any], inventory: Any | None
    ) -> Dict[str, Any]:
        if inventory is None:
            return results

        metadata = cls._inventory_scan_metadata(inventory)
        completeness = results.get("scan_completeness")
        if not isinstance(completeness, dict):
            return results

        completeness["inventory_discovery"] = metadata
        if metadata["status"] == "ok":
            return results

        completeness["degraded"] = True
        completeness["error_count"] = int(completeness.get("error_count", 0) or 0) + 1
        results["partial_results"] = True
        results["inventory_discovery"] = metadata
        return results

    async def scan_all(
        self, on_category_complete: Optional[Any] = None
    ) -> Dict[str, Any]:
        """
        Overrides the base scan_all to include global discovery via Resource Explorer 2.
        """
        from app.modules.optimization.domain.unified_discovery import (
            UnifiedDiscoveryService,
        )

        # 1. Perform Global Inventory Discovery (Hybrid Model)
        # This is fast and cheap, providing a bird's eye view of the account.
        inventory = None
        if self.connection:
            discovery_service = UnifiedDiscoveryService(str(self.connection.tenant_id))
            inventory = await discovery_service.discover_aws_inventory(self.connection)
            logger.info(
                "aws_detector_global_inventory_loaded",
                count=inventory.total_count,
                method=inventory.discovery_method,
            )

        # Store inventory for plugins to use
        self._inventory = inventory

        # 2. Proceed with standard parallel plugin execution
        results = await super().scan_all(on_category_complete=on_category_complete)
        return self._apply_inventory_completeness(results, inventory)

    async def _execute_plugin_scan(self, plugin: ZombiePlugin) -> List[Dict[str, Any]]:
        """
        Execute AWS plugin scan, passing the aioboto3 session and standard config.
        Injects the discovered inventory if available.
        """
        from botocore.config import Config
        from app.shared.core.config import get_settings

        settings = get_settings()
        boto_config = Config(
            connect_timeout=settings.ZOMBIE_PLUGIN_TIMEOUT_SECONDS,
            read_timeout=settings.ZOMBIE_PLUGIN_TIMEOUT_SECONDS,
            retries={"max_attempts": 2},
        )

        creds = self.credentials
        if self._adapter:
            creds = await self._adapter.get_credentials()

        return await plugin.scan(
            session=self.session,
            region=self.region,
            credentials=creds,
            config=boto_config,
            inventory=getattr(self, "_inventory", None),  # Inject inventory
        )
