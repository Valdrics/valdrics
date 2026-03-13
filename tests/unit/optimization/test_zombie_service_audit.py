import pytest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.modules.optimization.domain.service import ZombieService
from app.models.aws_connection import AWSConnection
from app.shared.core.pricing import PricingTier


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.mark.asyncio
async def test_scan_for_tenant_no_connections(mock_db, tenant_id):
    service = ZombieService(mock_db)

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    result = await service.scan_for_tenant(tenant_id)

    assert result["resources"] == {}
    assert result["total_monthly_waste"] == 0.0
    assert "No cloud connections found" in result["error"]


@pytest.mark.asyncio
async def test_scan_for_tenant_success(mock_db, tenant_id):
    service = ZombieService(mock_db)

    conn = MagicMock(spec=AWSConnection)
    conn.id = uuid4()
    conn.tenant_id = tenant_id
    conn.name = "Prod-AWS"
    conn.provider = "aws"
    conn.region = "us-east-1"
    conn.aws_account_id = "123456789012"
    conn.role_arn = "arn:aws:iam::123456789012:role/Valdrics"
    conn.external_id = "external-id"
    conn.cur_bucket_name = "cur-bucket"
    conn.cur_report_name = "cur-report"
    conn.cur_prefix = "cur-prefix"

    mock_detector = AsyncMock()
    mock_detector.provider_name = "aws"
    mock_detector.get_credentials = AsyncMock(
        return_value={"AccessKeyId": "AKIA_TEST", "SecretAccessKey": "SECRET_TEST"}
    )
    mock_detector.scan_all.return_value = {
        "unattached_volumes": [{"resource_id": "vol-1", "monthly_cost": 10.0}]
    }

    mock_rd = MagicMock()
    mock_rd.get_enabled_regions = AsyncMock(return_value=["us-east-1"])

    async def execute_side_effect(stmt: object) -> MagicMock:
        query = str(stmt).lower()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        if "aws_connections" in query:
            result.scalars.return_value.all.return_value = [conn]
        return result

    mock_db.execute.side_effect = execute_side_effect

    def fake_get_detector(*_args, **_kwargs):
        return mock_detector

    with (
        patch(
            "app.modules.optimization.domain.service.ZombieDetectorFactory",
            new=SimpleNamespace(get_detector=fake_get_detector),
        ),
        patch(
            "app.modules.optimization.adapters.aws.region_discovery.RegionDiscovery",
            return_value=mock_rd,
        ),
        patch(
            "app.shared.core.pricing.get_tenant_tier",
            return_value=PricingTier.STARTER,
        ),
        patch("app.shared.core.ops_metrics.SCAN_LATENCY"),
        patch(
            "app.shared.core.notifications.NotificationDispatcher.notify_zombies"
        ) as mock_notify,
    ):
        result = await service.scan_for_tenant(tenant_id)

    assert result["total_monthly_waste"] == 10.0
    assert len(result["unattached_volumes"]) == 1
    assert result["unattached_volumes"][0]["resource_id"] == "vol-1"
    assert result["waste_rightsizing"]["deterministic"] is True
    assert result["waste_rightsizing"]["summary"]["total_recommendations"] == 1
    assert result["architectural_inefficiency"]["deterministic"] is True
    mock_notify.assert_called_once()


@pytest.mark.asyncio
async def test_scan_for_tenant_aws_global_region_fallback_uses_configured_default(
    mock_db, tenant_id
):
    service = ZombieService(mock_db)

    conn = MagicMock(spec=AWSConnection)
    conn.id = uuid4()
    conn.tenant_id = tenant_id
    conn.name = "Prod-AWS"
    conn.provider = "aws"
    conn.region = "global"
    conn.aws_account_id = "123456789012"
    conn.role_arn = "arn:aws:iam::123456789012:role/Valdrics"
    conn.external_id = "external-id"
    conn.cur_bucket_name = "cur-bucket"
    conn.cur_report_name = "cur-report"
    conn.cur_prefix = "cur-prefix"

    mock_detector = AsyncMock()
    mock_detector.provider_name = "aws"
    mock_detector.get_credentials = AsyncMock(
        return_value={
            "AccessKeyId": "AKIA_TEST",
            "SecretAccessKey": "SECRET_TEST",
        }
    )
    mock_detector.scan_all.return_value = {"unattached_volumes": []}

    mock_rd = MagicMock()
    mock_rd.get_enabled_regions = AsyncMock(return_value=[])

    async def execute_side_effect(stmt: object) -> MagicMock:
        query = str(stmt).lower()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        if "aws_connections" in query:
            result.scalars.return_value.all.return_value = [conn]
        return result

    called_regions: list[str] = []

    def fake_get_detector(*_args, **kwargs):
        called_regions.append(str(kwargs.get("region")))
        return mock_detector

    with (
        patch(
            "app.shared.core.connection_state.get_settings",
            return_value=SimpleNamespace(AWS_DEFAULT_REGION="eu-west-2"),
        ),
        patch(
            "app.modules.optimization.domain.service.ZombieDetectorFactory",
            new=SimpleNamespace(get_detector=fake_get_detector),
        ),
        patch(
            "app.modules.optimization.adapters.aws.region_discovery.RegionDiscovery",
            return_value=mock_rd,
        ),
        patch(
            "app.shared.core.pricing.get_tenant_tier",
            return_value=PricingTier.STARTER,
        ),
        patch("app.shared.core.ops_metrics.SCAN_LATENCY"),
        patch(
            "app.shared.core.notifications.NotificationDispatcher.notify_zombies"
        ),
    ):
        mock_db.execute.side_effect = execute_side_effect
        await service.scan_for_tenant(tenant_id, region="global")

    assert called_regions
    assert "global" not in called_regions
    assert "eu-west-2" in called_regions


@pytest.mark.asyncio
async def test_scan_for_tenant_preserves_custom_categories_and_maps_provider_keys(
    mock_db, tenant_id
):
    service = ZombieService(mock_db)

    conn = MagicMock(spec=AWSConnection)
    conn.id = uuid4()
    conn.tenant_id = tenant_id
    conn.name = "Prod-AWS"
    conn.provider = "aws"
    conn.region = "us-east-1"
    conn.aws_account_id = "123456789012"
    conn.role_arn = "arn:aws:iam::123456789012:role/Valdrics"
    conn.external_id = "external-id"
    conn.cur_bucket_name = "cur-bucket"
    conn.cur_report_name = "cur-report"
    conn.cur_prefix = "cur-prefix"

    mock_detector = AsyncMock()
    mock_detector.provider_name = "aws"
    mock_detector.get_credentials = AsyncMock(
        return_value={"AccessKeyId": "AKIA_TEST", "SecretAccessKey": "SECRET_TEST"}
    )
    mock_detector.scan_all.return_value = {
        "orphan_load_balancers": [{"id": "lb-1", "monthly_waste": 12.0}],
        "orphan_azure_ips": [{"id": "pip-1", "monthly_waste": 3.0}],
        "orphan_azure_nics": [{"id": "nic-1", "monthly_waste": 0.0}],
        "empty_gke_clusters": [{"id": "gke-1", "monthly_waste": 20.0}],
        "idle_cloud_functions": [{"id": "fn-1", "monthly_waste": 2.0}],
        "custom_category": [{"id": "x-1", "monthly_waste": 4.0}],
    }

    mock_rd = MagicMock()
    mock_rd.get_enabled_regions = AsyncMock(return_value=["us-east-1"])

    async def execute_side_effect(stmt: object) -> MagicMock:
        query = str(stmt).lower()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        if "aws_connections" in query:
            result.scalars.return_value.all.return_value = [conn]
        return result

    mock_db.execute.side_effect = execute_side_effect

    def fake_get_detector(*_args, **_kwargs):
        return mock_detector

    with (
        patch(
            "app.modules.optimization.domain.service.ZombieDetectorFactory",
            new=SimpleNamespace(get_detector=fake_get_detector),
        ),
        patch(
            "app.modules.optimization.adapters.aws.region_discovery.RegionDiscovery",
            return_value=mock_rd,
        ),
        patch(
            "app.shared.core.pricing.get_tenant_tier",
            return_value=PricingTier.STARTER,
        ),
        patch("app.shared.core.ops_metrics.SCAN_LATENCY"),
        patch(
            "app.shared.core.notifications.NotificationDispatcher.notify_zombies"
        ),
    ):
        result = await service.scan_for_tenant(tenant_id)

    assert result["total_monthly_waste"] == 41.0
    assert len(result["orphan_load_balancers"]) == 1
    assert len(result["unused_elastic_ips"]) == 1
    assert len(result["orphan_network_components"]) == 1
    assert len(result["idle_container_clusters"]) == 1
    assert len(result["idle_serverless_functions"]) == 1
    assert len(result["custom_category"]) == 1
    assert result["orphan_load_balancers"][0]["resource_id"] == "lb-1"


@pytest.mark.asyncio
async def test_scan_for_tenant_timeout(mock_db, tenant_id):
    service = ZombieService(mock_db)

    conn = MagicMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [conn]
    mock_db.execute.return_value = mock_res

    async def slow_scan(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {}

    with patch(
        "app.modules.optimization.domain.service.ZombieDetectorFactory.get_detector"
    ) as mock_factory:
        mock_detector = AsyncMock()
        mock_detector.provider_name = "aws"
        mock_detector.scan_all.side_effect = slow_scan
        mock_factory.return_value = mock_detector

        with patch(
            "app.shared.core.pricing.get_tenant_tier",
            return_value=PricingTier.FREE,
        ):
            with patch("app.shared.core.ops_metrics.SCAN_TIMEOUTS"):
                # Use a very short timeout for testing
                with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
                    result = await service.scan_for_tenant(tenant_id)
                    assert result["scan_timeout"] is True
                    assert result["partial_results"] is True


@pytest.mark.asyncio
async def test_scan_for_tenant_invalid_tenant_config_in_detector(mock_db, tenant_id):
    """Invalid tenant configuration from provider detector should fail safely."""
    service = ZombieService(mock_db)

    conn = MagicMock(spec=AWSConnection)
    conn.id = uuid4()
    conn.tenant_id = tenant_id
    conn.name = "Prod-AWS"

    mock_res_aws = MagicMock()
    mock_res_aws.scalars.return_value.all.return_value = [conn]
    mock_res_empty = MagicMock()
    mock_res_empty.scalars.return_value.all.return_value = []
    mock_db.execute.side_effect = [mock_res_aws, mock_res_empty, mock_res_empty]

    mock_detector = AsyncMock()
    mock_detector.provider_name = "aws"
    mock_detector.scan_all.side_effect = ValueError("Invalid tenant config for scan")

    mock_rd = MagicMock()
    mock_rd.get_enabled_regions = AsyncMock(return_value=["us-east-1"])

    with patch(
        "app.modules.optimization.domain.service.ZombieDetectorFactory.get_detector",
        return_value=mock_detector,
    ):
        with patch(
            "app.modules.optimization.adapters.aws.region_discovery.RegionDiscovery",
            return_value=mock_rd,
        ):
            with patch(
                "app.shared.core.pricing.get_tenant_tier",
                return_value=PricingTier.FREE,
            ):
                with patch("app.shared.core.ops_metrics.SCAN_LATENCY"):
                    with patch(
                        "app.shared.core.notifications.NotificationDispatcher.notify_zombies"
                    ):
                        result = await service.scan_for_tenant(tenant_id)

    assert result["scanned_connections"] == 1
    assert result["total_monthly_waste"] == 0.0
    assert result["unattached_volumes"] == []
