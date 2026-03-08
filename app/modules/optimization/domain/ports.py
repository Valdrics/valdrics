import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import List, Dict, Any, Optional, cast
import structlog
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.core.config import get_settings
from app.shared.core.exceptions import ExternalAPIError
from app.modules.optimization.domain.plugin import ZombiePlugin

logger = structlog.get_logger()
settings = get_settings()

ZOMBIE_SCAN_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ExternalAPIError,
    RuntimeError,
    OSError,
    TimeoutError,
    ValueError,
    TypeError,
    KeyError,
    LookupError,
    AttributeError,
)
ZOMBIE_PLUGIN_SCAN_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ExternalAPIError,
    RuntimeError,
    OSError,
    TimeoutError,
    ValueError,
    TypeError,
    KeyError,
    LookupError,
    AttributeError,
)


class BaseZombieDetector(ABC):
    """
    Abstract Base Class for multi-cloud zombie resource detection.

    Responsibilities:
    - Orchestrate scans across multiple plugins (Strategy Pattern).
    - Aggregate results and calculate total waste.
    - Handle timeouts and region-specific context.
    - Provide a bridge between generic plugins and provider-specific clients.
    """

    def __init__(
        self,
        region: str = "global",
        credentials: Optional[Dict[str, Any]] = None,
        db: Optional[AsyncSession] = None,
        connection: Any = None,
    ):
        """
        Initializes the detector for a specific region.

        Args:
            region: Cloud region (e.g., 'us-east-1').
            credentials: Optional provider-specific credentials override.
            db: Optional database session for persistence.
            connection: Optional connection model instance (e.g. AWSConnection).
        """
        self.region = region
        self.credentials = credentials
        self.db = db
        self.connection = connection
        self.plugins: List[ZombiePlugin] = []

    @abstractmethod
    def _initialize_plugins(self) -> None:
        """Register provider-specific plugins for the cloud service."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """The cloud provider identifier (e.g., 'aws')."""

    async def scan_all(
        self,
        on_category_complete: Callable[[str, list[dict[str, Any]]], Awaitable[None]]
        | None = None,
    ) -> Dict[str, Any]:
        """
        Orchestrates the scan across all registered plugins in parallel.

        Args:
            on_category_complete: Optional async callback triggered after each plugin finishing.

        Returns:
            A dictionary containing scan results, waste metrics, and metadata.
        """
        if not self.plugins:
            self._initialize_plugins()

        results = {
            "provider": self.provider_name,
            "region": self.region,
            "scanned_at": datetime.now(timezone.utc).isoformat(),
            "total_monthly_waste": Decimal("0"),
            "scan_completeness": {
                "provider": self.provider_name,
                "region": self.region,
                "degraded": False,
                "error_count": 0,
                "plugins": {},
                "overall_error": None,
            },
        }

        # Initialize results keys for all plugins
        for plugin in self.plugins:
            results[plugin.category_key] = []

        try:
            # Run plugins in parallel with timeout protection
            tasks = [self._run_plugin_with_timeout(plugin) for plugin in self.plugins]

            async def run_and_checkpoint(
                task: Awaitable[tuple[str, list[dict[str, Any]], dict[str, Any]]],
            ) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
                cat_key, items, metadata = await task
                if on_category_complete:
                    await on_category_complete(cat_key, items)
                return cat_key, items, metadata

            checkpoint_tasks = [run_and_checkpoint(t) for t in tasks]
            plugin_results = await asyncio.gather(
                *checkpoint_tasks,
                return_exceptions=True,
            )

            # Aggregate individual plugin results
            for plugin, plugin_result in zip(self.plugins, plugin_results, strict=True):
                if isinstance(plugin_result, asyncio.CancelledError):
                    raise plugin_result
                if isinstance(plugin_result, BaseException) and not isinstance(
                    plugin_result, Exception
                ):
                    raise plugin_result
                category_key: str = plugin.category_key
                items: list[dict[str, Any]] = []
                plugin_metadata: dict[str, Any] = {
                    "status": "failed",
                    "item_count": 0,
                    "validated_item_count": 0,
                    "error": "Unhandled plugin result failure",
                    "error_type": "UnhandledPluginResult",
                }
                if isinstance(plugin_result, Exception):
                    logger.error(
                        "plugin_scan_unhandled_exception",
                        plugin=plugin.category_key,
                        error=str(plugin_result),
                    )
                    plugin_metadata = {
                        "status": "failed",
                        "item_count": 0,
                        "validated_item_count": 0,
                        "error": str(plugin_result),
                        "error_type": type(plugin_result).__name__,
                    }
                elif (
                    isinstance(plugin_result, tuple)
                    and len(plugin_result) == 3
                ):
                    category_key, items, plugin_metadata = plugin_result
                else:
                    logger.error(
                        "plugin_scan_invalid_result_type",
                        plugin=plugin.category_key,
                        result_type=type(plugin_result).__name__,
                    )
                    plugin_metadata = {
                        "status": "failed",
                        "item_count": 0,
                        "validated_item_count": 0,
                        "error": (
                            "Invalid plugin result type "
                            f"{type(plugin_result).__name__}"
                        ),
                        "error_type": "InvalidResultType",
                    }
                # BE-ZD-5: Robust Regional Validation
                # Prevent cross-region data leakage by ensuring all items match detector region
                validated_items = []
                for item in items:
                    item_region = item.get("region", self.region)
                    if item_region != self.region:
                        logger.warning(
                            "cross_region_resource_detected",
                            plugin=category_key,
                            resource=item.get("resource_id"),
                            item_region=item_region,
                            detector_region=self.region,
                        )
                        continue

                    # Ensure region is set consistently in output
                    item["region"] = self.region
                    validated_items.append(item)

                results[category_key] = validated_items
                plugin_metadata = dict(plugin_metadata or {})
                plugin_metadata["item_count"] = int(len(items))
                plugin_metadata["validated_item_count"] = int(len(validated_items))
                completeness = results["scan_completeness"]
                assert isinstance(completeness, dict)
                cast(dict[str, Any], completeness)["plugins"][category_key] = plugin_metadata
                if plugin_metadata.get("status") != "ok":
                    cast(dict[str, Any], completeness)["degraded"] = True
                    cast(dict[str, Any], completeness)["error_count"] = int(
                        completeness.get("error_count", 0)
                    ) + 1

            # Calculate the total monthly waste across all items
            total = Decimal("0")
            for result_value in results.values():
                if isinstance(result_value, list):
                    for item in result_value:
                        total += Decimal(str(item.get("monthly_cost", 0)))

            results["total_monthly_waste"] = float(round(total, 2))

            logger.info(
                "zombie_scan_complete",
                provider=self.provider_name,
                waste=results["total_monthly_waste"],
                plugins_run=len(self.plugins),
            )

        except asyncio.CancelledError:
            # O4: Propagate cancellation for proper cleanup
            logger.info("zombie_scan_cancelled", provider=self.provider_name)
            raise
        except ZOMBIE_SCAN_RECOVERABLE_EXCEPTIONS as e:
            logger.error(
                "zombie_scan_failed", provider=self.provider_name, error=str(e)
            )
            results["error"] = str(e)
            completeness = results["scan_completeness"]
            assert isinstance(completeness, dict)
            cast(dict[str, Any], completeness)["degraded"] = True
            cast(dict[str, Any], completeness)["overall_error"] = str(e)
            cast(dict[str, Any], completeness)["error_count"] = int(
                completeness.get("error_count", 0)
            ) + 1

        results["partial_results"] = bool(
            cast(dict[str, Any], results["scan_completeness"]).get("degraded")
        )

        return results

    async def _run_plugin_with_timeout(
        self, plugin: ZombiePlugin
    ) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
        """Wraps plugin execution with a generic timeout."""
        from app.modules.optimization.domain.cloud_api_budget import (
            cloud_api_scan_context,
        )

        tenant_id = str(getattr(self.connection, "tenant_id", "unknown"))
        connection_id = str(getattr(self.connection, "id", "unknown"))

        try:
            scan_coro = self._execute_plugin_scan(plugin)

            # Use global timeout from settings
            timeout = settings.ZOMBIE_PLUGIN_TIMEOUT_SECONDS
            with cloud_api_scan_context(
                tenant_id=tenant_id,
                provider=self.provider_name,
                connection_id=connection_id,
                region=self.region,
                plugin=plugin.category_key,
            ):
                items = await asyncio.wait_for(scan_coro, timeout=timeout)
            return plugin.category_key, items, {
                "status": "ok",
                "error": None,
                "error_type": None,
            }

        except asyncio.TimeoutError:
            logger.error("plugin_timeout", plugin=plugin.category_key)
            return plugin.category_key, [], {
                "status": "timeout",
                "error": "Plugin scan timed out",
                "error_type": "TimeoutError",
            }
        except asyncio.CancelledError:
            # O4: Propagate cancellation
            raise
        except ZOMBIE_PLUGIN_SCAN_RECOVERABLE_EXCEPTIONS as e:
            logger.error("plugin_scan_failed", plugin=plugin.category_key, error=str(e))
            return plugin.category_key, [], {
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    @abstractmethod
    async def _execute_plugin_scan(self, plugin: ZombiePlugin) -> List[Dict[str, Any]]:
        """
        Performs the actual API call to the cloud provider.
        Must be implemented by concrete subclasses to bridge to boto3, etc.
        """
        pass
