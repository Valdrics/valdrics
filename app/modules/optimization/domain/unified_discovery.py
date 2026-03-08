"""
Unified Discovery Service

Orchestrates resource discovery across different cloud providers and discovery methods.
Implements a hybrid model:
1. Try global discovery first (e.g., AWS Resource Explorer 2) - Fast & Cheap/Free.
2. Fallback to regional/service-specific discovery if global is unavailable or incomplete.
"""

from datetime import datetime
from typing import Any

import structlog

from app.models.aws_connection import AWSConnection
from app.schemas.inventory import CloudInventory, DiscoveredResource
from app.modules.optimization.domain.unified_discovery_support import (
    AWS_NATIVE_DISCOVERY_RECOVERABLE_EXCEPTIONS,
    build_arn,
    tags_to_dict,
)

logger = structlog.get_logger()


class UnifiedDiscoveryService:
    """
    Main entry point for account-wide resource inventory discovery.
    """

    def __init__(
        self,
        tenant_id: str,
        *,
        aws_resource_explorer_builder: Any | None = None,
        aws_credentials_resolver: Any | None = None,
        region_discovery_builder: Any | None = None,
        aws_session_factory: Any | None = None,
    ):
        self.tenant_id = tenant_id
        self._aws_resource_explorer_builder = aws_resource_explorer_builder
        self._aws_credentials_resolver = aws_credentials_resolver
        self._region_discovery_builder = region_discovery_builder
        self._aws_session_factory = aws_session_factory

    @staticmethod
    def _build_aws_resource_explorer(connection: AWSConnection) -> object:
        from app.shared.adapters.aws_resource_explorer import AWSResourceExplorerAdapter

        return AWSResourceExplorerAdapter(connection)

    @staticmethod
    async def _resolve_aws_credentials(connection: AWSConnection) -> dict[str, str]:
        from app.shared.adapters.aws_multitenant import MultiTenantAWSAdapter
        from app.shared.adapters.aws_utils import map_aws_connection_to_credentials

        adapter = MultiTenantAWSAdapter(map_aws_connection_to_credentials(connection))
        return dict(await adapter.get_credentials())

    @staticmethod
    def _build_region_discovery(
        connection: AWSConnection, credentials: dict[str, str]
    ) -> object:
        from app.modules.optimization.adapters.aws.region_discovery import RegionDiscovery

        return RegionDiscovery(credentials=credentials, connection=connection)

    @staticmethod
    def _build_aws_session() -> object:
        import aioboto3

        return aioboto3.Session()

    async def _scan_aws_region(
        self,
        *,
        session: Any,
        region: str,
        account_id: str,
        credentials: dict[str, str],
    ) -> tuple[list[DiscoveredResource], list[dict[str, str]]]:
        from app.shared.adapters.aws_utils import DEFAULT_BOTO_CONFIG, map_aws_credentials

        resources: list[DiscoveredResource] = []
        failures: list[dict[str, str]] = []
        client_kwargs = {
            "region_name": region,
            "config": DEFAULT_BOTO_CONFIG,
            **map_aws_credentials(credentials),
        }

        def _record_failure(*, service: str, operation: str, exc: Exception) -> None:
            failures.append(
                {
                    "region": region,
                    "service": service,
                    "operation": operation,
                    "error_type": type(exc).__name__,
                }
            )
            logger.warning(
                "aws_discovery_native_region_service_failed",
                region=region,
                service=service,
                operation=operation,
                error_type=type(exc).__name__,
                error=str(exc),
            )

        try:
            async with session.client("ec2", **client_kwargs) as ec2:
                try:
                    instances = await ec2.describe_instances()
                    for reservation in instances.get("Reservations", []):
                        for instance in reservation.get("Instances", []):
                            instance_id = str(instance.get("InstanceId") or "").strip()
                            if not instance_id:
                                continue
                            state = (
                                str(instance.get("State", {}).get("Name") or "").strip().lower()
                            )
                            if state == "terminated":
                                continue
                            resources.append(
                                DiscoveredResource(
                                    id=instance_id,
                                    arn=build_arn(
                                        service="ec2",
                                        region=region,
                                        account_id=account_id,
                                    resource_segment="instance",
                                    resource_id=instance_id,
                                ),
                                    service="ec2",
                                    resource_type="instance",
                                    region=region,
                                    provider="aws",
                                    tags=tags_to_dict(instance.get("Tags")),
                                    metadata={
                                        "discovery_method": "native-api-fallback",
                                        "service_call": "ec2.describe_instances",
                                        "state": state,
                                        "instance_type": str(
                                            instance.get("InstanceType") or ""
                                        ),
                                    },
                                )
                            )
                except AWS_NATIVE_DISCOVERY_RECOVERABLE_EXCEPTIONS as exc:
                    _record_failure(
                        service="ec2",
                        operation="describe_instances",
                        exc=exc,
                    )

                try:
                    volumes = await ec2.describe_volumes()
                    for volume in volumes.get("Volumes", []):
                        volume_id = str(volume.get("VolumeId") or "").strip()
                        if not volume_id:
                            continue
                        resources.append(
                            DiscoveredResource(
                                id=volume_id,
                                arn=build_arn(
                                    service="ec2",
                                    region=region,
                                    account_id=account_id,
                                    resource_segment="volume",
                                    resource_id=volume_id,
                                ),
                                service="ec2",
                                resource_type="volume",
                                region=region,
                                provider="aws",
                                tags=tags_to_dict(volume.get("Tags")),
                                metadata={
                                    "discovery_method": "native-api-fallback",
                                    "service_call": "ec2.describe_volumes",
                                    "state": str(volume.get("State") or ""),
                                    "volume_type": str(volume.get("VolumeType") or ""),
                                },
                            )
                        )
                except AWS_NATIVE_DISCOVERY_RECOVERABLE_EXCEPTIONS as exc:
                    _record_failure(
                        service="ec2",
                        operation="describe_volumes",
                        exc=exc,
                    )

                try:
                    addresses = await ec2.describe_addresses()
                    for address in addresses.get("Addresses", []):
                        allocation_id = str(
                            address.get("AllocationId") or address.get("PublicIp") or ""
                        ).strip()
                        if not allocation_id:
                            continue
                        resources.append(
                            DiscoveredResource(
                                id=allocation_id,
                                arn=build_arn(
                                    service="ec2",
                                    region=region,
                                    account_id=account_id,
                                    resource_segment="elastic-ip",
                                    resource_id=allocation_id,
                                ),
                                service="ec2",
                                resource_type="elastic_ip",
                                region=region,
                                provider="aws",
                                metadata={
                                    "discovery_method": "native-api-fallback",
                                    "service_call": "ec2.describe_addresses",
                                    "public_ip": str(address.get("PublicIp") or ""),
                                    "association_id": str(
                                        address.get("AssociationId") or ""
                                    ),
                                    "network_interface_id": str(
                                        address.get("NetworkInterfaceId") or ""
                                    ),
                                },
                            )
                        )
                except AWS_NATIVE_DISCOVERY_RECOVERABLE_EXCEPTIONS as exc:
                    _record_failure(
                        service="ec2",
                        operation="describe_addresses",
                        exc=exc,
                    )

                try:
                    nat_gateways = await ec2.describe_nat_gateways()
                    for nat_gateway in nat_gateways.get("NatGateways", []):
                        nat_gateway_id = str(
                            nat_gateway.get("NatGatewayId") or ""
                        ).strip()
                        if not nat_gateway_id:
                            continue
                        state = str(nat_gateway.get("State") or "").strip().lower()
                        if state == "deleted":
                            continue
                        resources.append(
                            DiscoveredResource(
                                id=nat_gateway_id,
                                arn=build_arn(
                                    service="ec2",
                                    region=region,
                                    account_id=account_id,
                                    resource_segment="natgateway",
                                    resource_id=nat_gateway_id,
                                ),
                                service="ec2",
                                resource_type="nat_gateway",
                                region=region,
                                provider="aws",
                                metadata={
                                    "discovery_method": "native-api-fallback",
                                    "service_call": "ec2.describe_nat_gateways",
                                    "state": state,
                                    "connectivity_type": str(
                                        nat_gateway.get("ConnectivityType") or ""
                                    ),
                                    "subnet_id": str(nat_gateway.get("SubnetId") or ""),
                                    "vpc_id": str(nat_gateway.get("VpcId") or ""),
                                },
                            )
                        )
                except AWS_NATIVE_DISCOVERY_RECOVERABLE_EXCEPTIONS as exc:
                    _record_failure(
                        service="ec2",
                        operation="describe_nat_gateways",
                        exc=exc,
                    )
        except AWS_NATIVE_DISCOVERY_RECOVERABLE_EXCEPTIONS as exc:
            _record_failure(
                service="ec2",
                operation="client",
                exc=exc,
            )

        try:
            async with session.client("elbv2", **client_kwargs) as elbv2:
                load_balancers = await elbv2.describe_load_balancers()
                for load_balancer in load_balancers.get("LoadBalancers", []):
                    load_balancer_arn = str(load_balancer.get("LoadBalancerArn") or "").strip()
                    if not load_balancer_arn:
                        continue
                    resources.append(
                        DiscoveredResource(
                            id=str(load_balancer.get("LoadBalancerName") or load_balancer_arn),
                            arn=load_balancer_arn,
                            service="elasticloadbalancing",
                            resource_type="load_balancer",
                            region=region,
                            provider="aws",
                            metadata={
                                "discovery_method": "native-api-fallback",
                                "service_call": "elbv2.describe_load_balancers",
                                "scheme": str(load_balancer.get("Scheme") or ""),
                                "type": str(load_balancer.get("Type") or ""),
                            },
                        )
                    )
        except AWS_NATIVE_DISCOVERY_RECOVERABLE_EXCEPTIONS as exc:
            _record_failure(
                service="elasticloadbalancing",
                operation="describe_load_balancers",
                exc=exc,
            )

        try:
            async with session.client("rds", **client_kwargs) as rds:
                databases = await rds.describe_db_instances()
                for database in databases.get("DBInstances", []):
                    db_instance_arn = str(database.get("DBInstanceArn") or "").strip()
                    db_instance_id = str(database.get("DBInstanceIdentifier") or "").strip()
                    if not db_instance_id:
                        continue
                    resources.append(
                        DiscoveredResource(
                            id=db_instance_id,
                            arn=db_instance_arn or None,
                            service="rds",
                            resource_type="db_instance",
                            region=region,
                            provider="aws",
                            metadata={
                                "discovery_method": "native-api-fallback",
                                "service_call": "rds.describe_db_instances",
                                "engine": str(database.get("Engine") or ""),
                                "instance_class": str(database.get("DBInstanceClass") or ""),
                                "status": str(database.get("DBInstanceStatus") or ""),
                            },
                        )
                    )
        except AWS_NATIVE_DISCOVERY_RECOVERABLE_EXCEPTIONS as exc:
            _record_failure(
                service="rds",
                operation="describe_db_instances",
                exc=exc,
            )

        try:
            async with session.client("ecr", **client_kwargs) as ecr:
                repositories = await ecr.describe_repositories()
                for repository in repositories.get("repositories", []):
                    repository_name = str(repository.get("repositoryName") or "").strip()
                    if not repository_name:
                        continue
                    repository_arn = str(repository.get("repositoryArn") or "").strip()
                    resources.append(
                        DiscoveredResource(
                            id=repository_name,
                            arn=repository_arn
                            or build_arn(
                                service="ecr",
                                region=region,
                                account_id=account_id,
                                resource_segment="repository",
                                resource_id=repository_name,
                            ),
                            service="ecr",
                            resource_type="repository",
                            region=region,
                            provider="aws",
                            metadata={
                                "discovery_method": "native-api-fallback",
                                "service_call": "ecr.describe_repositories",
                                "image_tag_mutability": str(
                                    repository.get("imageTagMutability") or ""
                                ),
                            },
                        )
                    )
        except AWS_NATIVE_DISCOVERY_RECOVERABLE_EXCEPTIONS as exc:
            _record_failure(
                service="ecr",
                operation="describe_repositories",
                exc=exc,
            )

        return resources, failures

    async def _discover_aws_inventory_via_native_fallback(
        self, connection: AWSConnection
    ) -> CloudInventory:
        credentials_resolver = self._aws_credentials_resolver or self._resolve_aws_credentials
        region_discovery_builder = (
            self._region_discovery_builder or self._build_region_discovery
        )
        aws_session_factory = self._aws_session_factory or self._build_aws_session

        credentials = await credentials_resolver(connection)
        region_discovery = region_discovery_builder(connection, credentials)
        active_regions = list(await region_discovery.get_active_regions())
        if not active_regions:
            active_regions = [str(connection.region or "us-east-1")]

        session = aws_session_factory()
        resources: list[DiscoveredResource] = []
        failures: list[dict[str, str]] = []
        seen_keys: set[str] = set()

        for region in active_regions:
            regional_resources, regional_failures = await self._scan_aws_region(
                session=session,
                region=region,
                account_id=str(connection.aws_account_id),
                credentials=credentials,
            )
            for resource in regional_resources:
                dedupe_key = str(resource.arn or f"{resource.service}:{resource.region}:{resource.id}")
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                resources.append(resource)
            failures.extend(regional_failures)

        discovery_method = "native-api-fallback"
        if failures and resources:
            discovery_method = "native-api-fallback-partial"
        elif failures and not resources:
            discovery_method = "native-api-fallback-degraded"

        logger.info(
            "aws_discovery_native_fallback_complete",
            account=connection.aws_account_id,
            regions=len(active_regions),
            resources=len(resources),
            failures=len(failures),
            discovery_method=discovery_method,
        )
        return CloudInventory(
            tenant_id=str(connection.tenant_id),
            provider="aws",
            resources=resources,
            total_count=len(resources),
            discovery_method=discovery_method,
            discovered_at=datetime.now().isoformat(),
        )

    async def discover_aws_inventory(self, connection: AWSConnection) -> CloudInventory:
        """
        Discovers all resources in an AWS account using the Hybrid Model.
        """
        resource_explorer_builder = (
            self._aws_resource_explorer_builder or self._build_aws_resource_explorer
        )
        explorer = resource_explorer_builder(connection)

        # Phase 1: Try Resource Explorer 2 (Global & Cost-Free)
        if await explorer.is_enabled():
            logger.info(
                "aws_discovery_global_search_start", account=connection.aws_account_id
            )

            raw_resources = await explorer.search_resources()

            resources = [
                DiscoveredResource(
                    id=r["id"],
                    arn=r["arn"],
                    service=r["service"],
                    resource_type=r["resource_type"],
                    region=r["region"],
                    provider="aws",
                    metadata={"discovery_method": "resource-explorer-2"},
                )
                for r in raw_resources
            ]

            return CloudInventory(
                tenant_id=str(connection.tenant_id),
                provider="aws",
                resources=resources,
                total_count=len(resources),
                discovery_method="resource-explorer-2",
                discovered_at=datetime.now().isoformat(),
            )

        # Phase 2: Fallback to service-specific scans when global search is unavailable.
        logger.warning(
            "aws_discovery_global_search_unavailable_fallback",
            account=connection.aws_account_id,
        )
        return await self._discover_aws_inventory_via_native_fallback(connection)
