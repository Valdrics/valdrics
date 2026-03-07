from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.adapters.aws_cur import AWSCURAdapter
from app.shared.core.credentials import AWSCredentials


@pytest.mark.asyncio
class TestAWSCURAdapterResourceProjection:
    async def test_get_credentials_uses_multitenant_adapter(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        fake_mt = MagicMock()
        fake_mt.get_credentials = AsyncMock(
            return_value={
                "AccessKeyId": "AKIA...",
                "SecretAccessKey": "SECRET",
                "SessionToken": "TOKEN",
            }
        )
        with patch(
            "app.shared.adapters.aws_multitenant.MultiTenantAWSAdapter",
            return_value=fake_mt,
        ):
            creds = await adapter._get_credentials()

        assert creds["AccessKeyId"] == "AKIA..."


    async def test_empty_summary_and_noop_resource_methods(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        summary = adapter._empty_summary()

        assert summary.provider == "aws"
        assert summary.total_cost == 0
        with patch.object(adapter, "get_cost_and_usage", AsyncMock(return_value=[])):
            assert await adapter.discover_resources("ec2") == []
            assert await adapter.get_resource_usage("ec2") == []


    async def test_discover_resources_projects_cur_rows(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        adapter.last_error = "stale"
        rows = [
            {
                "date": datetime(2026, 2, 1, tzinfo=timezone.utc),
                "amount": Decimal("12.5"),
                "amount_raw": Decimal("12.5"),
                "currency": "USD",
                "service": "AmazonEC2",
                "region": "us-east-1",
                "usage_type": "BoxUsage:m5.large",
                "resource_id": "i-123",
                "usage_amount": Decimal("24"),
            },
            {
                "date": datetime(2026, 2, 1, tzinfo=timezone.utc),
                "amount": Decimal("2.0"),
                "currency": "USD",
                "service": "AmazonS3",
                "region": "us-east-1",
            },
        ]
        with patch.object(adapter, "get_cost_and_usage", AsyncMock(return_value=rows)):
            resources = await adapter.discover_resources("ec2", region="us-east-1")

        assert len(resources) == 2
        assert resources[0]["provider"] == "aws"
        assert resources[0]["type"] == "aws_resource"
        assert resources[0]["region"] == "us-east-1"
        assert adapter.last_error is None


    async def test_discover_resources_returns_empty_and_sets_error_on_failure(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        with patch.object(
            adapter,
            "get_cost_and_usage",
            AsyncMock(side_effect=RuntimeError("cur discovery failure")),
        ):
            out = await adapter.discover_resources("ec2")

        assert out == []
        assert adapter.last_error is not None
        assert "AWS CUR resource discovery failed" in adapter.last_error


    async def test_get_resource_usage_projects_and_filters_cur_rows(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        adapter.last_error = "stale"
        rows = [
            {
                "date": datetime(2026, 2, 1, tzinfo=timezone.utc),
                "amount": Decimal("12.5"),
                "amount_raw": Decimal("12.5"),
                "currency": "USD",
                "service": "AmazonEC2",
                "region": "us-east-1",
                "usage_type": "BoxUsage:m5.large",
                "resource_id": "i-123",
                "usage_amount": Decimal("24"),
            },
            {
                "date": datetime(2026, 2, 1, tzinfo=timezone.utc),
                "amount": Decimal("2.0"),
                "currency": "USD",
                "service": "AmazonS3",
                "region": "us-east-1",
            },
        ]
        with patch.object(adapter, "get_cost_and_usage", AsyncMock(return_value=rows)):
            out = await adapter.get_resource_usage("ec2", "i-123")

        assert len(out) == 1
        assert out[0]["provider"] == "aws"
        assert out[0]["service"] == "AmazonEC2"
        assert out[0]["resource_id"] == "i-123"
        assert out[0]["usage_unit"] == "unit"
        assert adapter.last_error is None


    async def test_get_resource_usage_returns_empty_and_sets_error_on_failure(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        with patch.object(
            adapter,
            "get_cost_and_usage",
            AsyncMock(side_effect=RuntimeError("cur usage failure")),
        ):
            out = await adapter.get_resource_usage("ec2")

        assert out == []
        assert adapter.last_error is not None
        assert "AWS CUR resource usage lookup failed" in adapter.last_error
