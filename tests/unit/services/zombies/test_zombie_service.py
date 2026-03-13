import pytest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.optimization.domain.service import ZombieService
from app.models.aws_connection import AWSConnection
from app.models.azure_connection import AzureConnection
from app.models.gcp_connection import GCPConnection
from app.models.hybrid_connection import HybridConnection
from app.models.license_connection import LicenseConnection
from app.models.platform_connection import PlatformConnection
from app.models.saas_connection import SaaSConnection
from app.shared.core.pricing import PricingTier


@pytest.fixture
def db_session():
    """Mock database session."""
    session = MagicMock(spec=AsyncSession)
    session.bind = MagicMock()
    session.bind.url = "sqlite://"
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.info = {}
    return session


@pytest.fixture
def zombie_service(db_session):
    return ZombieService(db_session)


@pytest.mark.asyncio
async def test_scan_for_tenant_no_connections(zombie_service, db_session):
    tenant_id = uuid4()

    # Mock all connection models returning empty lists
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    db_session.execute.return_value = mock_res

    results = await zombie_service.scan_for_tenant(tenant_id)

    assert results["total_monthly_waste"] == 0.0
    assert "No cloud connections found" in results["error"]


@pytest.mark.asyncio
async def test_scan_for_tenant_parallel_success(zombie_service, db_session):
    tenant_id = uuid4()

    # Mock AWS and GCP connections
    aws_conn = MagicMock(spec=AWSConnection)
    aws_conn.id = uuid4()
    aws_conn.tenant_id = tenant_id
    aws_conn.provider = "aws"
    aws_conn.region = "us-east-1"
    aws_conn.name = "Prod-AWS"
    aws_conn.aws_account_id = "123456789012"
    aws_conn.role_arn = "arn:aws:iam::123456789012:role/Valdrics"
    aws_conn.external_id = "external-id"
    aws_conn.cur_bucket_name = "cur-bucket"
    aws_conn.cur_report_name = "cur-report"
    aws_conn.cur_prefix = "cur-prefix"
    gcp_conn = MagicMock(spec=GCPConnection)
    gcp_conn.id = uuid4()
    gcp_conn.tenant_id = tenant_id
    gcp_conn.provider = "gcp"
    gcp_conn.region = "us-central1"
    gcp_conn.name = "Prod-GCP"

    rows_by_model = {
        AWSConnection: [aws_conn],
        AzureConnection: [],
        GCPConnection: [gcp_conn],
        SaaSConnection: [],
        LicenseConnection: [],
        PlatformConnection: [],
        HybridConnection: [],
    }

    async def _execute(stmt: object) -> MagicMock:
        query_text = str(stmt).lower()
        result = MagicMock()
        result.scalars.return_value.all.return_value = []
        for model, rows in rows_by_model.items():
            if getattr(model, "__tablename__", "").lower() in query_text:
                result.scalars.return_value.all.return_value = rows
                break
        return result

    db_session.execute.side_effect = _execute

    def _build_detector(provider_name: str) -> MagicMock:
        detector = MagicMock()
        detector.provider_name = provider_name
        detector.scan_all = AsyncMock(
            return_value={
                "unattached_volumes": [
                    {"id": f"{provider_name}-v-1", "monthly_waste": 10.0}
                ],
                "idle_instances": [
                    {"id": f"{provider_name}-i-1", "monthly_waste": 20.0}
                ],
            }
        )
        detector.get_credentials = AsyncMock(
            return_value={"AccessKeyId": "AK", "SecretAccessKey": "SK"}
        )
        return detector

    # Mock RegionDiscovery
    mock_rd = MagicMock()
    mock_rd.get_enabled_regions = AsyncMock(return_value=["us-east-1"])

    def detector_side_effect(conn: object, **_: object) -> MagicMock:
        return _build_detector(str(getattr(conn, "provider", "")).lower())

    with (
        patch(
            "app.modules.optimization.domain.service.ZombieDetectorFactory",
            new=SimpleNamespace(get_detector=detector_side_effect),
        ),
        patch(
            "app.modules.optimization.adapters.aws.region_discovery.RegionDiscovery",
            return_value=mock_rd,
        ),
        patch(
            "app.modules.optimization.domain.service.is_feature_enabled",
            return_value=False,
        ),
        patch(
            "app.shared.core.pricing.get_tenant_tier",
            AsyncMock(return_value=PricingTier.STARTER),
        ),
        patch(
            "app.shared.core.notifications.NotificationDispatcher.notify_zombies",
            new_callable=AsyncMock,
        ),
        patch("app.shared.core.ops_metrics.SCAN_LATENCY"),
    ):
        results = await zombie_service.scan_for_tenant(tenant_id)

    assert results["total_monthly_waste"] == 60.0
    assert len(results["unattached_volumes"]) == 2
    assert results["scanned_connections"] == 2
    assert results["waste_rightsizing"]["deterministic"] is True
    assert results["waste_rightsizing"]["summary"]["total_recommendations"] == 4
    assert results["architectural_inefficiency"]["deterministic"] is True


@pytest.mark.asyncio
async def test_scan_for_tenant_timeout_handling(zombie_service, db_session):
    tenant_id = uuid4()
    aws_conn = AWSConnection(id=uuid4(), tenant_id=tenant_id)

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.side_effect = [[aws_conn], [], []]
    db_session.execute.return_value = mock_res

    mock_detector = MagicMock()
    mock_detector.scan_all = AsyncMock()
    with patch(
        "app.modules.optimization.domain.factory.ZombieDetectorFactory.get_detector",
        return_value=mock_detector,
    ):
        with patch("app.shared.core.ops_metrics.SCAN_TIMEOUTS"):
            with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError()):
                results = await zombie_service.scan_for_tenant(tenant_id)
                assert results.get("scan_timeout") is True
                assert results.get("partial_results") is True


@pytest.mark.asyncio
async def test_ai_enrichment_tier_gating(zombie_service, db_session):
    tenant_id = uuid4()
    zombies = {"unattached_volumes": []}

    with (
        patch(
            "app.modules.optimization.domain.service.is_feature_enabled",
            new=lambda *_args, **_kwargs: False,
        ),
        patch(
            "app.shared.llm.factory.LLMFactory.create",
            side_effect=AssertionError("LLMFactory.create must not be called"),
        ) as mock_llm_create,
    ):
        await zombie_service._enrich_with_ai(zombies, tenant_id, PricingTier.STARTER)

    assert zombies["ai_analysis"]["upgrade_required"] is True
    mock_llm_create.assert_not_called()


@pytest.mark.asyncio
async def test_ai_enrichment_failure_handling(zombie_service, db_session):
    tenant_id = uuid4()
    MagicMock(tenant_id=tenant_id, tier="growth")
    zombies = {"unattached_volumes": []}

    with patch(
        "app.modules.optimization.domain.service.is_feature_enabled", return_value=True
    ):
        with patch(
            "app.shared.llm.factory.LLMFactory.create",
            side_effect=RuntimeError("LLM Down"),
        ):
            from app.shared.core.pricing import PricingTier

            await zombie_service._enrich_with_ai(zombies, tenant_id, PricingTier.GROWTH)
            assert "AI analysis failed" in zombies["ai_analysis"]["error"]


@pytest.mark.asyncio
async def test_parallel_scan_exception_handling(zombie_service, db_session):
    tenant_id = uuid4()
    aws_conn = AWSConnection(id=uuid4(), tenant_id=tenant_id)

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.side_effect = [[aws_conn], [], []]
    db_session.execute.return_value = mock_res

    mock_detector = MagicMock()
    mock_detector.provider_name = "aws"
    mock_detector.scan_all = AsyncMock(side_effect=RuntimeError("Provider Failure"))

    with patch(
        "app.modules.optimization.domain.factory.ZombieDetectorFactory.get_detector",
        return_value=mock_detector,
    ):
        results = await zombie_service.scan_for_tenant(tenant_id)
        # Should finish successfully but with 0 waste due to error in provider
        assert results["total_monthly_waste"] == 0.0
