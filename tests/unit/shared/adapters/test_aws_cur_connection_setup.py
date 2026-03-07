from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from botocore.exceptions import ClientError

from app.schemas.costs import CostRecord
from app.shared.adapters.aws_cur import AWSCURAdapter
from app.shared.core.credentials import AWSCredentials
from tests.unit.shared.adapters.aws_cur_test_helpers import _async_cm, _summary_with_records


@pytest.mark.asyncio
class TestAWSCURAdapterConnectionSetup:
    async def test_constructor_resolves_global_region_hint(self) -> None:
        creds = AWSCredentials(
            account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/ValdricsRole",
            external_id="ext-id",
            region="global",
        )

        with patch(
            "app.shared.adapters.aws_utils.get_settings",
            return_value=SimpleNamespace(
                AWS_SUPPORTED_REGIONS=["eu-west-1"],
                AWS_DEFAULT_REGION="eu-west-1",
            ),
        ):
            adapter = AWSCURAdapter(creds)

        assert adapter._resolved_region == "eu-west-1"
        assert adapter.bucket_name == "valdrics-cur-123456789012-eu-west-1"


    async def test_verify_connection_success(self, mock_creds: AWSCredentials) -> None:
        mock_s3 = AsyncMock()
        mock_session = MagicMock()
        mock_session.client.return_value = _async_cm(mock_s3)

        with patch.object(
            AWSCURAdapter,
            "_get_credentials",
            new=AsyncMock(
                return_value={
                    "AccessKeyId": "test",
                    "SecretAccessKey": "test",
                    "SessionToken": "test",
                }
            ),
        ):
            adapter = AWSCURAdapter(mock_creds)
            adapter.session = mock_session
            adapter.last_error = "stale"

            success = await adapter.verify_connection()
            assert success is True
            mock_s3.head_bucket.assert_awaited_with(Bucket=adapter.bucket_name)
            assert adapter.last_error is None


    async def test_verify_connection_failure_returns_false(
        self, mock_creds: AWSCredentials
    ) -> None:
        mock_s3 = AsyncMock()
        mock_s3.head_bucket.side_effect = RuntimeError("access denied")
        mock_session = MagicMock()
        mock_session.client.return_value = _async_cm(mock_s3)

        with patch.object(
            AWSCURAdapter,
            "_get_credentials",
            new=AsyncMock(
                return_value={
                    "AccessKeyId": "test",
                    "SecretAccessKey": "test",
                    "SessionToken": "test",
                }
            ),
        ), patch("app.shared.adapters.aws_cur.logger.error") as mock_error:
            adapter = AWSCURAdapter(mock_creds)
            adapter.session = mock_session
            success = await adapter.verify_connection()

        assert success is False
        assert adapter.last_error is not None
        assert "AWS CUR bucket verification failed" in adapter.last_error
        mock_error.assert_called_once()


    async def test_setup_cur_automation_creates_bucket_and_report(
        self, mock_creds: AWSCredentials
    ) -> None:
        mock_s3 = AsyncMock()
        mock_cur = AsyncMock()
        mock_s3.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadBucket",
        )

        mock_session = MagicMock()
        mock_session.client.side_effect = [_async_cm(mock_s3), _async_cm(mock_cur)]

        with patch.object(
            AWSCURAdapter,
            "_get_credentials",
            new=AsyncMock(
                return_value={
                    "AccessKeyId": "AKIA...",
                    "SecretAccessKey": "SECRET",
                    "SessionToken": "TOKEN",
                }
            ),
        ):
            adapter = AWSCURAdapter(mock_creds)
            adapter.session = mock_session

            result = await adapter.setup_cur_automation()

        assert result["status"] == "success"
        assert result["bucket_name"] == adapter.bucket_name
        mock_s3.create_bucket.assert_awaited_once_with(Bucket=adapter.bucket_name)
        mock_s3.put_bucket_policy.assert_awaited_once()
        mock_cur.put_report_definition.assert_awaited_once()
        call_args = mock_cur.put_report_definition.call_args[1]
        assert (
            call_args["ReportDefinition"]["ReportName"]
            == f"valdrics-cur-{mock_creds.account_id}"
        )


    async def test_setup_cur_automation_non_us_east_adds_location_constraint(
        self,
    ) -> None:
        creds = AWSCredentials(
            account_id="123456789012",
            role_arn="arn:aws:iam::123456789012:role/ValdricsRole",
            external_id="ext-id",
            region="eu-west-1",
        )
        mock_s3 = AsyncMock()
        mock_cur = AsyncMock()
        mock_s3.head_bucket.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadBucket",
        )
        mock_session = MagicMock()
        mock_session.client.side_effect = [_async_cm(mock_s3), _async_cm(mock_cur)]

        with patch.object(
            AWSCURAdapter,
            "_get_credentials",
            new=AsyncMock(
                return_value={
                    "AccessKeyId": "AKIA...",
                    "SecretAccessKey": "SECRET",
                    "SessionToken": "TOKEN",
                }
            ),
        ):
            adapter = AWSCURAdapter(creds)
            adapter.session = mock_session
            result = await adapter.setup_cur_automation()

        assert result["status"] == "success"
        mock_s3.create_bucket.assert_awaited_once_with(
            Bucket=adapter.bucket_name,
            CreateBucketConfiguration={"LocationConstraint": "eu-west-1"},
        )


    async def test_setup_cur_automation_returns_error_when_s3_step_fails(
        self, mock_creds: AWSCredentials
    ) -> None:
        mock_s3 = AsyncMock()
        mock_s3.put_bucket_policy.side_effect = RuntimeError("policy failed")
        mock_session = MagicMock()
        mock_session.client.return_value = _async_cm(mock_s3)

        with patch.object(
            AWSCURAdapter,
            "_get_credentials",
            new=AsyncMock(
                return_value={
                    "AccessKeyId": "AKIA...",
                    "SecretAccessKey": "SECRET",
                    "SessionToken": "TOKEN",
                }
            ),
        ):
            adapter = AWSCURAdapter(mock_creds)
            adapter.session = mock_session
            result = await adapter.setup_cur_automation()

        assert result["status"] == "error"
        assert "S3 setup failed" in result["message"]


    async def test_setup_cur_automation_returns_error_when_cur_step_fails(
        self, mock_creds: AWSCredentials
    ) -> None:
        mock_s3 = AsyncMock()
        mock_cur = AsyncMock()
        mock_cur.put_report_definition.side_effect = RuntimeError("cur failed")
        mock_session = MagicMock()
        mock_session.client.side_effect = [_async_cm(mock_s3), _async_cm(mock_cur)]

        with patch.object(
            AWSCURAdapter,
            "_get_credentials",
            new=AsyncMock(
                return_value={
                    "AccessKeyId": "AKIA...",
                    "SecretAccessKey": "SECRET",
                    "SessionToken": "TOKEN",
                }
            ),
        ):
            adapter = AWSCURAdapter(mock_creds)
            adapter.session = mock_session
            result = await adapter.setup_cur_automation()

        assert result["status"] == "error"
        assert "CUR setup failed" in result["message"]


    async def test_get_cost_and_usage_converts_dates(self, mock_creds: AWSCredentials) -> None:
        adapter = AWSCURAdapter(mock_creds)
        record = CostRecord(
            date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            amount=Decimal("4.5"),
            amount_raw=Decimal("4.5"),
            currency="USD",
            service="AmazonEC2",
            region="us-east-1",
            usage_type="BoxUsage",
            tags={},
        )
        summary = _summary_with_records([record], Decimal("4.5"))

        with patch.object(
            adapter,
            "get_daily_costs",
            new=AsyncMock(return_value=summary),
        ) as get_daily_costs:
            rows = await adapter.get_cost_and_usage(
                datetime(2026, 2, 1, tzinfo=timezone.utc),
                datetime(2026, 2, 2, tzinfo=timezone.utc),
            )

        get_daily_costs.assert_awaited_once_with(date(2026, 2, 1), date(2026, 2, 2))
        assert rows[0]["service"] == "AmazonEC2"
        assert rows[0]["amount"] == Decimal("4.5")
