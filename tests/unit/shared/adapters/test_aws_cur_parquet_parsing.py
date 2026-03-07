from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import patch

import pandas as pd
import pytest

from app.schemas.costs import CostRecord
from app.shared.adapters.aws_cur import AWSCURAdapter
from app.shared.core.credentials import AWSCredentials
from app.shared.core.exceptions import ConfigurationError


@pytest.mark.asyncio
class TestAWSCURAdapterParquetParsing:
    async def test_process_parquet_streamingly_logs_when_record_cap_exceeded(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        adapter._SUMMARY_RECORD_CAP = 2

        df = pd.DataFrame(
            {
                "lineItem/UsageStartDate": [
                    "2026-02-01T00:00:00Z",
                    "2026-02-01T01:00:00Z",
                    "2026-02-01T02:00:00Z",
                ],
                "lineItem/UnblendedCost": ["1.0", "2.0", "3.0"],
                "lineItem/CurrencyCode": ["USD", "USD", "USD"],
                "lineItem/ProductCode": ["AmazonEC2", "AmazonEC2", "AmazonEC2"],
                "product/region": ["us-east-1", "us-east-1", "us-east-1"],
                "lineItem/UsageType": ["BoxUsage", "BoxUsage", "BoxUsage"],
            }
        )

        class _FakeTable:
            def to_pandas(self):
                return df

        class _FakeParquetFile:
            num_row_groups = 1

            def read_row_group(self, idx: int):
                assert idx == 0
                return _FakeTable()

        with patch(
            "app.shared.adapters.aws_cur.pq.ParquetFile",
            return_value=_FakeParquetFile(),
        ), patch("app.shared.adapters.aws_cur.logger.warning") as mock_warning:
            summary = adapter._process_parquet_streamingly("/tmp/cur.parquet")

        assert len(summary.records) == 2
        assert summary.total_cost == 6
        mock_warning.assert_any_call(
            "cur_summary_record_cap_reached",
            cap=2,
            dropped_records=1,
            retained_records=2,
            start=None,
            end=None,
        )


    async def test_process_parquet_streamingly_prefers_iter_batches_when_available(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)

        df_first = pd.DataFrame(
            {
                "lineItem/UsageStartDate": [
                    "2026-02-01T00:00:00Z",
                    "2026-02-01T01:00:00Z",
                ],
                "lineItem/UnblendedCost": ["1.0", "2.0"],
                "lineItem/CurrencyCode": ["USD", "USD"],
                "lineItem/ProductCode": ["AmazonEC2", "AmazonEC2"],
                "product/region": ["us-east-1", "us-east-1"],
                "lineItem/UsageType": ["BoxUsage", "BoxUsage"],
            }
        )
        df_second = pd.DataFrame(
            {
                "lineItem/UsageStartDate": ["2026-02-01T02:00:00Z"],
                "lineItem/UnblendedCost": ["3.0"],
                "lineItem/CurrencyCode": ["USD"],
                "lineItem/ProductCode": ["AmazonS3"],
                "product/region": ["us-east-1"],
                "lineItem/UsageType": ["Storage"],
            }
        )

        class _FakeBatch:
            def __init__(self, frame: pd.DataFrame) -> None:
                self._frame = frame

            def to_pandas(self) -> pd.DataFrame:
                return self._frame

        class _FakeParquetFile:
            num_row_groups = 0

            def iter_batches(self, batch_size: int):
                assert batch_size > 0
                yield _FakeBatch(df_first)
                yield _FakeBatch(df_second)

            def read_row_group(self, _idx: int):
                raise AssertionError("read_row_group should not be used when iter_batches works")

        with patch(
            "app.shared.adapters.aws_cur.pq.ParquetFile",
            return_value=_FakeParquetFile(),
        ):
            summary = adapter._process_parquet_streamingly("/tmp/cur.parquet")

        assert summary.total_cost == Decimal("6")
        assert len(summary.records) == 3
        assert summary.by_service["AmazonEC2"] == Decimal("3")
        assert summary.by_service["AmazonS3"] == Decimal("3")


    async def test_process_parquet_streamingly_falls_back_when_iter_batches_fails(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        df = pd.DataFrame(
            {
                "lineItem/UsageStartDate": ["2026-02-01T00:00:00Z"],
                "lineItem/UnblendedCost": ["4.0"],
                "lineItem/CurrencyCode": ["USD"],
                "lineItem/ProductCode": ["AmazonRDS"],
                "product/region": ["us-east-1"],
                "lineItem/UsageType": ["InstanceUsage"],
            }
        )

        class _FakeTable:
            def to_pandas(self) -> pd.DataFrame:
                return df

        class _FakeParquetFile:
            num_row_groups = 1

            def iter_batches(self, batch_size: int):
                _ = batch_size
                raise RuntimeError("iter_batches failed")

            def read_row_group(self, idx: int):
                assert idx == 0
                return _FakeTable()

        with patch(
            "app.shared.adapters.aws_cur.pq.ParquetFile",
            return_value=_FakeParquetFile(),
        ), patch("app.shared.adapters.aws_cur.logger.warning") as mock_warning:
            summary = adapter._process_parquet_streamingly("/tmp/cur.parquet")

        assert summary.total_cost == Decimal("4")
        assert len(summary.records) == 1
        mock_warning.assert_any_call(
            "cur_iter_batches_failed_fallback",
            error="iter_batches failed",
        )


    async def test_process_parquet_streamingly_handles_read_and_row_parse_errors(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        good_record = CostRecord(
            date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            amount=Decimal("5"),
            amount_raw=Decimal("5"),
            currency="USD",
            service="AmazonS3",
            region="us-east-1",
            usage_type="Storage",
            tags={"team": "core"},
        )
        df = pd.DataFrame(
            {
                "lineItem/UsageStartDate": [
                    "2026-02-01T00:00:00Z",
                    "2026-02-01T01:00:00Z",
                ],
                "lineItem/UnblendedCost": ["5.0", "oops"],
            }
        )

        class _FakeTable:
            def __init__(self, frame: pd.DataFrame) -> None:
                self._frame = frame

            def to_pandas(self) -> pd.DataFrame:
                return self._frame

        class _FakeParquetFile:
            num_row_groups = 2

            def read_row_group(self, idx: int):
                if idx == 0:
                    raise RuntimeError("broken row-group")
                return _FakeTable(df)

        with patch(
            "app.shared.adapters.aws_cur.pq.ParquetFile",
            return_value=_FakeParquetFile(),
        ), patch.object(
            adapter,
            "_parse_row",
            side_effect=[good_record, ValueError("bad row")],
        ), patch("app.shared.adapters.aws_cur.logger.warning") as mock_warning:
            summary = adapter._process_parquet_streamingly("/tmp/cur.parquet")

        assert summary.total_cost == Decimal("5")
        assert len(summary.records) == 1
        assert summary.by_service["AmazonS3"] == Decimal("5")
        assert summary.by_tag["team"]["core"] == Decimal("5")
        mock_warning.assert_any_call(
            "cur_row_group_read_failed",
            error="broken row-group",
            row_group=0,
        )


    async def test_process_parquet_streamingly_skips_chunks_without_required_columns(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        df = pd.DataFrame({"lineItem/UsageStartDate": ["2026-02-01T00:00:00Z"]})

        class _FakeTable:
            def to_pandas(self):
                return df

        class _FakeParquetFile:
            num_row_groups = 1

            def read_row_group(self, _idx: int):
                return _FakeTable()

        with patch(
            "app.shared.adapters.aws_cur.pq.ParquetFile",
            return_value=_FakeParquetFile(),
        ):
            summary = adapter._process_parquet_streamingly(
                "/tmp/cur.parquet",
                start_date=date(2026, 2, 1),
                end_date=date(2026, 2, 2),
            )

        assert summary.total_cost == 0
        assert summary.records == []


    async def test_parse_row_handles_invalid_values(self, mock_creds: AWSCredentials) -> None:
        adapter = AWSCURAdapter(mock_creds)
        row = pd.Series(
            {
                "lineItem/UsageStartDate": "2026-02-01T12:00:00",
                "lineItem/UnblendedCost": "not-a-number",
                "lineItem/CurrencyCode": "",
                "lineItem/ProductCode": "",
                "product/region": "",
                "lineItem/UsageType": "",
            }
        )
        col_map = {
            "date": "lineItem/UsageStartDate",
            "cost": "lineItem/UnblendedCost",
            "currency": "lineItem/CurrencyCode",
            "service": "lineItem/ProductCode",
            "region": "product/region",
            "usage_type": "lineItem/UsageType",
        }

        parsed = adapter._parse_row(row, col_map)

        assert parsed.amount == Decimal("0")
        assert parsed.currency == "USD"
        assert parsed.service == "Unknown"
        assert parsed.region == "Global"
        assert parsed.usage_type == "Unknown"
        assert parsed.date.tzinfo == timezone.utc


    async def test_parse_row_raises_for_missing_or_invalid_date(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        row_missing = pd.Series({"lineItem/UnblendedCost": "1.0"})
        with pytest.raises(ConfigurationError, match="Missing date column mapping"):
            adapter._parse_row(
                row_missing,
                {
                    "date": None,
                    "cost": "lineItem/UnblendedCost",
                },
            )

        row_invalid = pd.Series(
            {
                "lineItem/UsageStartDate": pd.NaT,
                "lineItem/UnblendedCost": "1.0",
            }
        )
        with pytest.raises(ConfigurationError, match="Invalid usage start date"):
            adapter._parse_row(
                row_invalid,
                {
                    "date": "lineItem/UsageStartDate",
                    "cost": "lineItem/UnblendedCost",
                },
            )


    async def test_extract_tags_supports_both_column_prefixes(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        row = pd.Series(
            {
                "resourceTags/user:team": "core",
                "resource_tags_user_env": "prod",
                "resourceTags/user:empty": "",
                "other": "value",
            }
        )

        tags = adapter._extract_tags(row)

        assert tags == {"team": "core", "env": "prod"}
