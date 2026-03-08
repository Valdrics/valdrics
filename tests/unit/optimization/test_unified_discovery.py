import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.modules.optimization.domain.unified_discovery import UnifiedDiscoveryService
from app.models.aws_connection import AWSConnection
from app.schemas.inventory import DiscoveredResource


@pytest.fixture
def mock_connection():
    conn = MagicMock(spec=AWSConnection)
    conn.tenant_id = "test-tenant-id"
    conn.aws_account_id = "123456789012"
    conn.region = "us-east-1"
    return conn


@pytest.mark.asyncio
async def test_discover_aws_inventory_resource_explorer_enabled(mock_connection):
    service = UnifiedDiscoveryService("test-tenant-id")

    # Mocking the Resource Explorer Adapter
    mock_explorer = MagicMock()
    mock_explorer.is_enabled = AsyncMock(return_value=True)
    mock_explorer.search_resources = AsyncMock(
        return_value=[
            {
                "id": "i-123",
                "arn": "arn:i-123",
                "service": "ec2",
                "resource_type": "instance",
                "region": "us-east-1",
            }
        ]
    )

    with patch.object(
        UnifiedDiscoveryService,
        "_build_aws_resource_explorer",
        return_value=mock_explorer,
    ):
        inventory = await service.discover_aws_inventory(mock_connection)

    assert inventory.discovery_method == "resource-explorer-2"
    assert len(inventory.resources) == 1
    assert inventory.resources[0].id == "i-123"


@pytest.mark.asyncio
async def test_discover_aws_inventory_resource_explorer_disabled_fallback(
    mock_connection,
):
    service = UnifiedDiscoveryService("test-tenant-id")

    mock_explorer = MagicMock()
    mock_explorer.is_enabled = AsyncMock(return_value=False)
    mock_region_discovery = MagicMock()
    mock_region_discovery.get_active_regions = AsyncMock(return_value=["us-east-1", "eu-west-1"])

    with patch.object(
        UnifiedDiscoveryService,
        "_build_aws_resource_explorer",
        return_value=mock_explorer,
    ), patch.object(
        UnifiedDiscoveryService,
        "_resolve_aws_credentials",
        new=AsyncMock(return_value={"AccessKeyId": "a", "SecretAccessKey": "b"}),
    ), patch.object(
        UnifiedDiscoveryService,
        "_build_region_discovery",
        return_value=mock_region_discovery,
    ), patch.object(
        UnifiedDiscoveryService,
        "_build_aws_session",
        return_value=MagicMock(),
    ), patch.object(
        UnifiedDiscoveryService,
        "_scan_aws_region",
        new=AsyncMock(
            side_effect=[
                (
                    [
                        DiscoveredResource(
                            id="i-123",
                            arn="arn:aws:ec2:us-east-1:123456789012:instance/i-123",
                            service="ec2",
                            resource_type="instance",
                            region="us-east-1",
                            provider="aws",
                            metadata={"discovery_method": "native-api-fallback"},
                        )
                    ],
                    [],
                ),
                (
                    [
                        DiscoveredResource(
                            id="db-1",
                            arn="arn:aws:rds:eu-west-1:123456789012:db:db-1",
                            service="rds",
                            resource_type="db_instance",
                            region="eu-west-1",
                            provider="aws",
                            metadata={"discovery_method": "native-api-fallback"},
                        )
                    ],
                    [],
                ),
            ]
        ),
    ):
        inventory = await service.discover_aws_inventory(mock_connection)

    assert inventory.discovery_method == "native-api-fallback"
    assert len(inventory.resources) == 2
    assert {resource.id for resource in inventory.resources} == {"i-123", "db-1"}


@pytest.mark.asyncio
async def test_discover_aws_inventory_resource_explorer_disabled_degraded_fallback(
    mock_connection,
):
    service = UnifiedDiscoveryService("test-tenant-id")

    mock_explorer = MagicMock()
    mock_explorer.is_enabled = AsyncMock(return_value=False)
    mock_region_discovery = MagicMock()
    mock_region_discovery.get_active_regions = AsyncMock(return_value=["us-east-1"])

    with patch.object(
        UnifiedDiscoveryService,
        "_build_aws_resource_explorer",
        return_value=mock_explorer,
    ), patch.object(
        UnifiedDiscoveryService,
        "_resolve_aws_credentials",
        new=AsyncMock(return_value={"AccessKeyId": "a", "SecretAccessKey": "b"}),
    ), patch.object(
        UnifiedDiscoveryService,
        "_build_region_discovery",
        return_value=mock_region_discovery,
    ), patch.object(
        UnifiedDiscoveryService,
        "_build_aws_session",
        return_value=MagicMock(),
    ), patch.object(
        UnifiedDiscoveryService,
        "_scan_aws_region",
        new=AsyncMock(
            return_value=([], [{"region": "us-east-1", "service": "ec2", "error_type": "RuntimeError"}])
        ),
    ):
        inventory = await service.discover_aws_inventory(mock_connection)

    assert inventory.discovery_method == "native-api-fallback-degraded"
    assert inventory.total_count == 0


class _AsyncClientContext:
    def __init__(self, client):
        self._client = client

    async def __aenter__(self):
        return self._client

    async def __aexit__(self, exc_type, exc, tb):
        return None


class _FakeSession:
    def __init__(self, clients):
        self._clients = clients

    def client(self, service_name, **kwargs):
        del kwargs
        return _AsyncClientContext(self._clients[service_name])


@pytest.mark.asyncio
async def test_scan_aws_region_includes_network_and_registry_fallback_resources() -> None:
    service = UnifiedDiscoveryService("tenant-1")

    class Ec2Client:
        async def describe_instances(self):
            return {
                "Reservations": [
                    {
                        "Instances": [
                            {
                                "InstanceId": "i-123",
                                "State": {"Name": "running"},
                                "InstanceType": "t3.micro",
                                "Tags": [{"Key": "Name", "Value": "web"}],
                            }
                        ]
                    }
                ]
            }

        async def describe_volumes(self):
            return {
                "Volumes": [
                    {
                        "VolumeId": "vol-123",
                        "State": "available",
                        "VolumeType": "gp3",
                        "Tags": [{"Key": "Owner", "Value": "ops"}],
                    }
                ]
            }

        async def describe_addresses(self):
            return {
                "Addresses": [
                    {
                        "AllocationId": "eipalloc-123",
                        "PublicIp": "203.0.113.10",
                        "AssociationId": "",
                        "NetworkInterfaceId": "",
                    }
                ]
            }

        async def describe_nat_gateways(self):
            return {
                "NatGateways": [
                    {
                        "NatGatewayId": "nat-123",
                        "State": "available",
                        "ConnectivityType": "public",
                        "SubnetId": "subnet-123",
                        "VpcId": "vpc-123",
                    }
                ]
            }

    class Elbv2Client:
        async def describe_load_balancers(self):
            return {
                "LoadBalancers": [
                    {
                        "LoadBalancerArn": "arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/app-lb/123",
                        "LoadBalancerName": "app-lb",
                        "Scheme": "internet-facing",
                        "Type": "application",
                    }
                ]
            }

    class RdsClient:
        async def describe_db_instances(self):
            return {
                "DBInstances": [
                    {
                        "DBInstanceArn": "arn:aws:rds:us-east-1:123456789012:db:db-1",
                        "DBInstanceIdentifier": "db-1",
                        "Engine": "postgres",
                        "DBInstanceClass": "db.t3.micro",
                        "DBInstanceStatus": "available",
                    }
                ]
            }

    class EcrClient:
        async def describe_repositories(self):
            return {
                "repositories": [
                    {
                        "repositoryName": "payments",
                        "repositoryArn": "arn:aws:ecr:us-east-1:123456789012:repository/payments",
                        "imageTagMutability": "MUTABLE",
                    }
                ]
            }

    resources, failures = await service._scan_aws_region(
        session=_FakeSession(
            {
                "ec2": Ec2Client(),
                "elbv2": Elbv2Client(),
                "rds": RdsClient(),
                "ecr": EcrClient(),
            }
        ),
        region="us-east-1",
        account_id="123456789012",
        credentials={"AccessKeyId": "a", "SecretAccessKey": "b"},
    )

    assert failures == []
    resource_types = {(resource.service, resource.resource_type) for resource in resources}
    assert ("ec2", "instance") in resource_types
    assert ("ec2", "volume") in resource_types
    assert ("ec2", "elastic_ip") in resource_types
    assert ("ec2", "nat_gateway") in resource_types
    assert ("elasticloadbalancing", "load_balancer") in resource_types
    assert ("rds", "db_instance") in resource_types
    assert ("ecr", "repository") in resource_types
