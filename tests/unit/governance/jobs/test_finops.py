import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from uuid import uuid4
from app.modules.governance.domain.jobs.handlers.finops import FinOpsAnalysisHandler


@pytest.mark.asyncio
async def test_finops_analysis_handler():
    """Test FinOps analysis background job."""
    handler = FinOpsAnalysisHandler()
    job = MagicMock(tenant_id=uuid4(), payload={})
    db = MagicMock()
    aws_conn = MagicMock(id=uuid4(), provider="aws")

    with (
        patch(
            "app.modules.governance.domain.jobs.handlers.finops.list_tenant_connections",
            new=AsyncMock(return_value=[aws_conn]),
        ),
        patch(
            "app.modules.governance.domain.jobs.handlers.finops.resolve_provider_from_connection",
            return_value="aws",
        ),
        patch(
            "app.modules.governance.domain.jobs.handlers.finops.get_adapter_for_connection"
        ) as mock_get_adapter,
        patch(
            "app.modules.governance.domain.jobs.handlers.finops.fetch_daily_costs_if_supported",
            new=AsyncMock(),
        ) as mock_fetch_daily_costs,
        patch("app.modules.governance.domain.jobs.handlers.finops.LLMFactory.create"),
        patch(
            "app.modules.governance.domain.jobs.handlers.finops.FinOpsAnalyzer"
        ) as MockAnalyzer,
    ):
        adapter = MagicMock()
        usage_summary = MagicMock()
        usage_summary.records = [MagicMock()]
        mock_get_adapter.return_value = adapter
        mock_fetch_daily_costs.return_value = usage_summary

        analyzer = MockAnalyzer.return_value
        analyzer.analyze = AsyncMock(
            return_value={"insights": [], "recommendations": []}
        )

        res = await handler.execute(job, db)

        assert res["status"] == "completed"
        assert res["analysis_runs"] == 1
        analyzer.analyze.assert_awaited()
