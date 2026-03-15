import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from datetime import date, datetime, timezone

from app.modules.optimization.domain.service import OptimizationService


@pytest.mark.asyncio
async def test_generate_recommendations_persists_results():
    db = AsyncMock()
    db.add_all = MagicMock()
    db.commit = AsyncMock()

    mock_strategy = MagicMock()
    mock_strategy.id = uuid4()
    mock_strategy.name = "Compute Savings Plan"
    mock_strategy.type = "savings_plan"
    mock_strategy.provider = "aws"
    mock_strategy.config = {}

    strategies_result = MagicMock()
    strategies_result.scalars.return_value.all.return_value = [mock_strategy]
    db.execute = AsyncMock(side_effect=[strategies_result, MagicMock()])

    recs = [MagicMock(name="rec1"), MagicMock(name="rec2")]

    with patch(
        "app.modules.optimization.domain.strategies.compute_savings.ComputeSavingsStrategy"
    ) as mock_strategy_cls:
        mock_strategy = mock_strategy_cls.return_value
        mock_strategy.analyze = AsyncMock(return_value=recs)

        service = OptimizationService(db)
        with patch.object(
            service, "_aggregate_usage", AsyncMock(return_value={"avg": 1.0})
        ):
            out = await service.generate_recommendations(uuid4())

    assert out == recs
    db.add_all.assert_called_once_with(recs)
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_generate_recommendations_handles_strategy_error():
    db = AsyncMock()
    db.add_all = MagicMock()
    db.commit = AsyncMock()

    mock_strategy = MagicMock()
    mock_strategy.id = uuid4()
    mock_strategy.name = "Compute Savings Plan"
    mock_strategy.type = "savings_plan"
    mock_strategy.provider = "aws"
    mock_strategy.config = {}

    strategies_result = MagicMock()
    strategies_result.scalars.return_value.all.return_value = [mock_strategy]
    db.execute = AsyncMock(return_value=strategies_result)

    with (
        patch(
            "app.modules.optimization.domain.strategies.compute_savings.ComputeSavingsStrategy"
        ) as mock_strategy_cls,
        patch("app.modules.optimization.domain.strategy_service.logger") as mock_logger,
    ):
        mock_strategy = mock_strategy_cls.return_value
        mock_strategy.analyze = AsyncMock(side_effect=RuntimeError("boom"))

        service = OptimizationService(db)
        with patch.object(
            service, "_aggregate_usage", AsyncMock(return_value={"avg": 1.0})
        ):
            out = await service.generate_recommendations(uuid4())

    assert out == []
    db.add_all.assert_not_called()
    db.commit.assert_not_awaited()
    mock_logger.error.assert_called()


@pytest.mark.asyncio
async def test_aggregate_usage_computes_spend_metrics():
    db = AsyncMock()
    result = MagicMock()
    result.all.return_value = [
        (
            datetime(2026, 2, 10, 10, 0, tzinfo=timezone.utc),
            date(2026, 2, 10),
            "us-east-1",
            1.0,
        ),
        (
            datetime(2026, 2, 10, 11, 0, tzinfo=timezone.utc),
            date(2026, 2, 10),
            "us-east-1",
            2.0,
        ),
        (
            datetime(2026, 2, 10, 12, 0, tzinfo=timezone.utc),
            date(2026, 2, 10),
            "us-east-1",
            3.0,
        ),
    ]
    db.execute = AsyncMock(return_value=result)

    service = OptimizationService(db)
    out = await service._aggregate_usage(uuid4())

    assert out["total_monthly_spend"] == 6.0
    assert out["average_hourly_spend"] == pytest.approx(2.0, rel=1e-6)
    assert out["baseline_hourly_spend"] == pytest.approx(1.5, rel=1e-6)
    assert 0.0 <= out["confidence_score"] <= 1.0
    assert out["observed_buckets"] == 3
    assert out["granularity"] == "hourly"
    assert out["region"] == "global"
    assert out["top_region"] == "us-east-1"
    assert out["region_totals"]["us-east-1"] == 6.0
    assert len(out["hourly_cost_series"]) >= 3


@pytest.mark.asyncio
async def test_generate_recommendations_clears_stale_open_rows_when_strategy_returns_no_recs():
    db = AsyncMock()
    db.add_all = MagicMock()
    db.commit = AsyncMock()

    strategy = MagicMock()
    strategy.id = uuid4()
    strategy.name = "Reserved Instance"
    strategy.type = "reserved_instance"
    strategy.provider = "aws"

    strategies_result = MagicMock()
    strategies_result.scalars.return_value.all.return_value = [strategy]
    delete_result = MagicMock()
    delete_result.rowcount = 1
    db.execute = AsyncMock(side_effect=[strategies_result, delete_result])

    with patch(
        "app.modules.optimization.domain.strategies.baseline_commitment.BaselineCommitmentStrategy"
    ) as mock_strategy_cls:
        mock_strategy_cls.return_value.analyze = AsyncMock(return_value=[])

        service = OptimizationService(db)
        with patch.object(
            service, "_aggregate_usage", AsyncMock(return_value={"avg": 1.0})
        ):
            out = await service.generate_recommendations(uuid4())

    assert out == []
    db.add_all.assert_not_called()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_aggregate_usage_uses_requested_lookback_for_daily_coverage():
    db = AsyncMock()
    result = MagicMock()
    result.all.return_value = [
        (
            datetime(2026, 2, day, 0, 0, tzinfo=timezone.utc),
            date(2026, 2, day),
            "us-east-1",
            10.0,
        )
        for day in range(1, 8)
    ]
    db.execute = AsyncMock(return_value=result)

    service = OptimizationService(db)
    out = await service._aggregate_usage(uuid4(), lookback_days=7)

    assert out["granularity"] == "daily"
    assert out["expected_buckets"] == 7
    assert out["observed_buckets"] == 7
    assert out["coverage_ratio"] == 1.0
