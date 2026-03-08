from __future__ import annotations

from functools import lru_cache
from importlib import import_module
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.optimization.domain.ports import BaseZombieDetector
from app.shared.core.config import get_settings
from app.shared.core.connection_state import resolve_connection_region
from app.shared.core.provider import normalize_provider, resolve_provider_from_connection

_DETECTOR_MODULES = {
    "aws": ("app.modules.optimization.adapters.aws.detector", "AWSZombieDetector"),
    "azure": ("app.modules.optimization.adapters.azure.detector", "AzureZombieDetector"),
    "gcp": ("app.modules.optimization.adapters.gcp.detector", "GCPZombieDetector"),
    "saas": ("app.modules.optimization.adapters.saas.detector", "SaaSZombieDetector"),
    "license": (
        "app.modules.optimization.adapters.license.detector",
        "LicenseZombieDetector",
    ),
    "platform": (
        "app.modules.optimization.adapters.platform.detector",
        "PlatformZombieDetector",
    ),
    "hybrid": ("app.modules.optimization.adapters.hybrid.detector", "HybridZombieDetector"),
}


@lru_cache(maxsize=len(_DETECTOR_MODULES))
def _load_detector_class(provider: str) -> type[BaseZombieDetector]:
    module_name, class_name = _DETECTOR_MODULES[provider]
    module = import_module(module_name)
    detector_class = getattr(module, class_name)
    if not isinstance(detector_class, type):
        raise TypeError(f"Detector {class_name} in {module_name} is not a class.")
    return detector_class


def _cloud_plus_credentials(connection: Any, *, feed_key: str) -> dict[str, Any]:
    connector_config = getattr(connection, "connector_config", None)
    feed = getattr(connection, feed_key, None)
    credentials: dict[str, Any] = {
        "vendor": getattr(connection, "vendor", None),
        "auth_method": getattr(connection, "auth_method", None),
        "api_key": getattr(connection, "api_key", None),
        "connector_config": connector_config if isinstance(connector_config, dict) else {},
    }
    if hasattr(connection, "api_secret"):
        credentials["api_secret"] = getattr(connection, "api_secret", None)
    credentials[feed_key] = feed if isinstance(feed, list) else []
    return credentials


class ZombieDetectorFactory:
    """
    Factory to instantiate the correct ZombieDetector based on connection type.
    """

    @staticmethod
    def get_detector(
        connection: Any, region: str = "", db: Optional[AsyncSession] = None
    ) -> BaseZombieDetector:
        class_name = (
            getattr(getattr(connection, "__class__", None), "__name__", "")
            or type(connection).__name__
        )
        type_name = class_name.strip().lower()
        provider = normalize_provider(resolve_provider_from_connection(connection))
        requested_region = str(region or "").strip()
        connection_region = resolve_connection_region(connection)
        effective_region = requested_region or connection_region

        if provider == "aws" or (not provider and "awsconnection" in type_name):
            # Treat "global" as a region hint and resolve to connection/default region
            # so AWS scans are not unintentionally pinned to a hardcoded region.
            aws_region = effective_region
            if aws_region == "global":
                aws_region = connection_region
            if not aws_region or aws_region == "global":
                aws_region = str(get_settings().AWS_DEFAULT_REGION or "").strip() or "us-east-1"
            detector_class = _load_detector_class("aws")
            return detector_class(region=aws_region, connection=connection, db=db)

        elif provider == "azure" or (not provider and "azureconnection" in type_name):
            detector_class = _load_detector_class("azure")
            return detector_class(region=effective_region, connection=connection, db=db)

        elif provider == "gcp" or (not provider and "gcpconnection" in type_name):
            detector_class = _load_detector_class("gcp")
            return detector_class(region=effective_region, connection=connection, db=db)

        elif provider == "saas" or (not provider and "saasconnection" in type_name):
            detector_class = _load_detector_class("saas")
            return detector_class(
                region=effective_region or "global",
                connection=connection,
                credentials=_cloud_plus_credentials(connection, feed_key="spend_feed"),
                db=db,
            )

        elif provider == "license" or (
            not provider and "licenseconnection" in type_name
        ):
            detector_class = _load_detector_class("license")
            return detector_class(
                region=effective_region or "global",
                connection=connection,
                credentials=_cloud_plus_credentials(connection, feed_key="license_feed"),
                db=db,
            )

        elif provider == "platform" or (
            not provider and "platformconnection" in type_name
        ):
            detector_class = _load_detector_class("platform")
            return detector_class(
                region=effective_region or "global",
                connection=connection,
                credentials=_cloud_plus_credentials(connection, feed_key="spend_feed"),
                db=db,
            )

        elif provider == "hybrid" or (not provider and "hybridconnection" in type_name):
            detector_class = _load_detector_class("hybrid")
            return detector_class(
                region=effective_region or "global",
                connection=connection,
                credentials=_cloud_plus_credentials(connection, feed_key="spend_feed"),
                db=db,
            )

        raise ValueError(
            f"Unsupported connection type: {type_name} (provider={provider})"
        )
