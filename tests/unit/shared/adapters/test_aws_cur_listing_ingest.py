from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas.costs import CloudUsageSummary, CostRecord
from app.shared.adapters.aws_cur import AWSCURAdapter
from app.shared.core.credentials import AWSCredentials
from tests.unit.shared.adapters.aws_cur_test_helpers import (
    _AsyncBody,
    _Paginator,
    _ReadBody,
    _async_cm,
    _summary_with_records,
)


@pytest.mark.asyncio
class TestAWSCURAdapterListingAndIngest:
    async def test_get_daily_costs_empty_and_error_paths(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        with patch.object(
            adapter,
            "_list_cur_files_in_range",
            new=AsyncMock(return_value=[]),
        ):
            summary = await adapter.get_daily_costs(date(2026, 2, 1), date(2026, 2, 2))
        assert summary.total_cost == 0
        assert summary.records == []

        with patch.object(
            adapter,
            "_list_cur_files_in_range",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ), pytest.raises(RuntimeError):
            await adapter.get_daily_costs(date(2026, 2, 1), date(2026, 2, 2))


    async def test_stream_cost_and_usage_yields_flat_records(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        record = CostRecord(
            date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            amount=Decimal("1.25"),
            amount_raw=Decimal("1.25"),
            currency="USD",
            service="AmazonS3",
            region="us-east-1",
            usage_type="Storage",
            tags={"team": "platform"},
        )
        summary = _summary_with_records([record], Decimal("1.25"))

        with patch.object(
            adapter,
            "_list_cur_files_in_range",
            new=AsyncMock(return_value=["a.parquet", "b.parquet"]),
        ), patch.object(
            adapter,
            "_ingest_single_file",
            new=AsyncMock(return_value=summary),
        ):
            results = [
                item
                async for item in adapter.stream_cost_and_usage(
                    datetime(2026, 2, 1, tzinfo=timezone.utc),
                    datetime(2026, 2, 2, tzinfo=timezone.utc),
                )
            ]

        assert len(results) == 2
        assert results[0]["source_adapter"] == "cur_data_export"
        assert results[0]["cost_usd"] == Decimal("1.25")


    async def test_list_cur_files_prefers_latest_manifest_and_deduplicates(
        self, mock_creds: AWSCredentials
    ) -> None:
        jan_prefix = "cur/2026/01/"
        feb_prefix = "cur/2026/02/"
        paginator = _Paginator(
            {
                jan_prefix: [
                    {
                        "Contents": [
                            {
                                "Key": f"{jan_prefix}older-manifest.json",
                                "LastModified": datetime(
                                    2026, 1, 10, tzinfo=timezone.utc
                                ),
                            },
                            {
                                "Key": f"{jan_prefix}latest-manifest.json",
                                "LastModified": datetime(
                                    2026, 1, 20, tzinfo=timezone.utc
                                ),
                            },
                            {"Key": f"{jan_prefix}direct.parquet"},
                        ]
                    }
                ],
                feb_prefix: [{"Contents": [{"Key": f"{feb_prefix}feb.parquet"}]}],
            }
        )
        manifest_payload = {
            "reportKeys": [
                "cur/2026/01/a.parquet",
                "cur/2026/01/a.parquet",
                "cur/2026/01/b.parquet",
            ]
        }
        mock_s3 = MagicMock()
        mock_s3.get_paginator.return_value = paginator
        mock_s3.get_object = AsyncMock(
            return_value={"Body": _ReadBody(json.dumps(manifest_payload).encode())}
        )
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
            keys = await adapter._list_cur_files_in_range(
                date(2026, 1, 1), date(2026, 2, 5)
            )

        assert keys == [
            "cur/2026/01/a.parquet",
            "cur/2026/01/b.parquet",
            "cur/2026/02/feb.parquet",
        ]
        mock_s3.get_object.assert_awaited_once_with(
            Bucket=adapter.bucket_name,
            Key=f"{jan_prefix}latest-manifest.json",
        )


    async def test_list_cur_files_manifest_parse_failure_falls_back_to_listing(
        self, mock_creds: AWSCredentials
    ) -> None:
        month_prefix = "cur/2026/03/"
        paginator = _Paginator(
            {
                month_prefix: [
                    {
                        "Contents": [
                            {
                                "Key": f"{month_prefix}manifest.json",
                                "LastModified": datetime(
                                    2026, 3, 10, tzinfo=timezone.utc
                                ),
                            },
                            {"Key": f"{month_prefix}part-1.parquet"},
                            {"Key": f"{month_prefix}part-2.parquet"},
                        ]
                    }
                ]
            }
        )
        mock_s3 = MagicMock()
        mock_s3.get_paginator.return_value = paginator
        mock_s3.get_object = AsyncMock(side_effect=RuntimeError("manifest read failed"))
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
            keys = await adapter._list_cur_files_in_range(
                date(2026, 3, 1), date(2026, 3, 1)
            )

        assert keys == [f"{month_prefix}part-1.parquet", f"{month_prefix}part-2.parquet"]


    async def test_process_files_in_range_merges_and_truncates(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        record = CostRecord(
            date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            amount=Decimal("1"),
            amount_raw=Decimal("1"),
            currency="USD",
            service="svc",
            region="us-east-1",
            usage_type="x",
            tags={"team": "core"},
        )
        large_records = [record] * 10001
        small_record = CostRecord(
            date=datetime(2026, 2, 2, tzinfo=timezone.utc),
            amount=Decimal("2"),
            amount_raw=Decimal("2"),
            currency="USD",
            service="svc",
            region="us-west-2",
            usage_type="y",
            tags={"team": "edge"},
        )
        file_a = CloudUsageSummary(
            tenant_id="t",
            provider="aws",
            start_date=date(2026, 2, 1),
            end_date=date(2026, 2, 1),
            total_cost=Decimal("10001"),
            records=large_records,
            by_service={"svc": Decimal("10001")},
            by_region={"us-east-1": Decimal("10001")},
            by_tag={"team": {"core": Decimal("10001")}},
        )
        file_b = CloudUsageSummary(
            tenant_id="t",
            provider="aws",
            start_date=date(2026, 2, 2),
            end_date=date(2026, 2, 2),
            total_cost=Decimal("2"),
            records=[small_record],
            by_service={"svc": Decimal("2")},
            by_region={"us-west-2": Decimal("2")},
            by_tag={"team": {"edge": Decimal("2")}},
        )

        with patch.object(
            adapter,
            "_ingest_single_file",
            new=AsyncMock(side_effect=[file_a, file_b]),
        ), patch("app.shared.adapters.aws_cur.logger.warning") as mock_warning:
            summary = await adapter._process_files_in_range(
                ["a.parquet", "b.parquet"],
                date(2026, 2, 1),
                date(2026, 2, 2),
            )

        assert summary.total_cost == Decimal("10003")
        assert len(summary.records) == 10001
        assert summary.by_region["us-east-1"] == Decimal("10001")
        assert summary.by_region["us-west-2"] == Decimal("2")
        assert summary.by_tag["team"]["core"] == Decimal("10001")
        assert summary.by_tag["team"]["edge"] == Decimal("2")
        mock_warning.assert_any_call(
            "cur_file_summary_records_truncated",
            file_key="a.parquet",
            cap=10000,
            truncated_records=1,
        )
        mock_warning.assert_any_call(
            "cur_master_summary_records_truncated",
            cap_per_file=10000,
            truncated_records_total=1,
            files_processed=2,
        )


    async def test_ingest_single_file_downloads_and_cleans_up(
        self, mock_creds: AWSCredentials
    ) -> None:
        adapter = AWSCURAdapter(mock_creds)
        mock_s3 = AsyncMock()
        mock_s3.get_object = AsyncMock(
            return_value={"Body": _AsyncBody([b"abc", b"def", b""])}
        )
        adapter.session = MagicMock()
        adapter.session.client.return_value = _async_cm(mock_s3)
        expected = adapter._empty_summary()

        with patch.object(
            adapter,
            "_get_credentials",
            new=AsyncMock(
                return_value={
                    "AccessKeyId": "AKIA...",
                    "SecretAccessKey": "SECRET",
                    "SessionToken": "TOKEN",
                }
            ),
        ), patch.object(
            adapter,
            "_process_parquet_streamingly",
            return_value=expected,
        ) as process_mock, patch(
            "app.shared.adapters.aws_cur.os.path.exists",
            return_value=True,
        ), patch(
            "app.shared.adapters.aws_cur.os.remove"
        ) as remove_mock:
            summary = await adapter._ingest_single_file(
                "cur/file.parquet",
                date(2026, 2, 1),
                date(2026, 2, 2),
            )

        assert summary is expected
        process_mock.assert_called_once()
        remove_mock.assert_called_once()
