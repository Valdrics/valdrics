import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch, AsyncMock
from app.modules.optimization.adapters.aws.detector import AWSZombieDetector
from app.modules.optimization.adapters.aws.plugins import UnattachedVolumesPlugin


@pytest.fixture
def mock_boto_session():
    with patch("aioboto3.Session") as mock:
        yield mock


@pytest.fixture
def detector(mock_boto_session):
    return AWSZombieDetector(
        region="us-west-2",
        credentials={
            "AccessKeyId": "test",
            "SecretAccessKey": "test",
            "SessionToken": "test",
        },
    )


def test_initialization(detector):
    assert detector.region == "us-west-2"
    assert detector.provider_name == "aws"
    assert detector.credentials == {
        "AccessKeyId": "test",
        "SecretAccessKey": "test",
        "SessionToken": "test",
    }


def test_plugin_registration(detector):
    detector._initialize_plugins()
    assert len(detector.plugins) > 0
    assert any(isinstance(p, UnattachedVolumesPlugin) for p in detector.plugins)


@pytest.mark.asyncio
async def test_execute_plugin_scan(detector):
    # Mock a plugin
    mock_plugin = AsyncMock()
    mock_plugin.scan.return_value = [{"id": "vol-123"}]

    # Mock the session (not actually used by the mock plugin but passed)
    detector.session = MagicMock()

    results = await detector._execute_plugin_scan(mock_plugin)

    assert results == [{"id": "vol-123"}]
    mock_plugin.scan.assert_called_once()
    kwargs = mock_plugin.scan.call_args.kwargs
    assert kwargs["session"] == detector.session
    assert kwargs["region"] == "us-west-2"
    assert kwargs["credentials"] == detector.credentials


@pytest.mark.asyncio
async def test_scan_all_marks_partial_inventory_discovery(detector):
    detector.connection = SimpleNamespace(tenant_id="tenant-1")

    with (
        patch(
            "app.modules.optimization.domain.unified_discovery.UnifiedDiscoveryService"
        ) as discovery_cls,
        patch(
            "app.modules.optimization.domain.ports.BaseZombieDetector.scan_all",
            new=AsyncMock(
                return_value={
                    "provider": "aws",
                    "partial_results": False,
                    "scan_completeness": {
                        "provider": "aws",
                        "region": "us-west-2",
                        "degraded": False,
                        "error_count": 0,
                        "plugins": {},
                        "overall_error": None,
                    },
                }
            ),
        ),
    ):
        discovery_cls.return_value.discover_aws_inventory = AsyncMock(
            return_value=SimpleNamespace(
                total_count=7,
                discovery_method="native-api-fallback-partial",
            )
        )

        results = await detector.scan_all()

    assert results["partial_results"] is True
    assert results["scan_completeness"]["degraded"] is True
    assert results["scan_completeness"]["inventory_discovery"]["status"] == "partial"
    assert results["inventory_discovery"]["resource_count"] == 7
