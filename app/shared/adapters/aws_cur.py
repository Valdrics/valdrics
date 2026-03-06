"""
AWS Cost and Usage Report (CUR) Ingestion Service

Ingests granular, high-fidelity Parquet files from S3 to provide
tag-based attribution and source-of-truth cost data.
"""

import os
import json
import tempfile
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, AsyncGenerator, cast, Iterator
import aioboto3
import pandas as pd
import pyarrow.parquet as pq
import structlog
from botocore.exceptions import BotoCoreError, ClientError
from app.shared.adapters.base import BaseAdapter
from app.shared.adapters.aws_cur_ingestion_ops import (
    list_cur_files_in_range,
    normalize_rows_for_projection,
    process_files_in_range,
)
from app.shared.adapters.aws_cur_parquet_ops import (
    extract_cur_tags,
    iter_parquet_dataframes,
    parse_cur_row,
    process_parquet_streamingly,
)
from app.shared.adapters.aws_utils import resolve_aws_region_hint
from app.shared.adapters.resource_usage_projection import (
    discover_resources_from_cost_rows,
    project_cost_rows_to_resource_usage,
    resource_usage_lookback_window,
)
from app.shared.core.credentials import AWSCredentials
from app.schemas.costs import CloudUsageSummary, CostRecord

logger = structlog.get_logger()

_DISCOVERY_RESOURCE_TYPE_ALIASES = {
    "all",
    "aws",
    "compute",
    "container",
    "containers",
    "database",
    "ec2",
    "eks",
    "elasticache",
    "lambda",
    "network",
    "resource",
    "resources",
    "s3",
    "security",
    "storage",
}


class AWSCURAdapter(BaseAdapter):
    """
    Ingests AWS CUR (Cost and Usage Report) data from S3.
    """
    _SUMMARY_RECORD_CAP = 50000
    _PARQUET_BATCH_SIZE = 4096
    _LIST_OBJECTS_MAX_PAGES_PER_MONTH = 512

    def __init__(self, credentials: AWSCredentials):
        self.credentials = credentials
        self.last_error = None
        self._resolved_region = resolve_aws_region_hint(credentials.region)
        self.session = aioboto3.Session()
        # Use dynamic bucket name from automated setup, fallback to connection-derived if needed
        self.bucket_name = (
            credentials.cur_bucket_name
            or f"valdrics-cur-{credentials.account_id}-{self._resolved_region}"
        )

    async def verify_connection(self) -> bool:
        """Verify S3 access."""
        self._clear_last_error()
        try:
            creds = await self._get_credentials()
            async with self.session.client(
                "s3",
                region_name=self._resolved_region,
                aws_access_key_id=creds["AccessKeyId"],
                aws_secret_access_key=creds["SecretAccessKey"],
                aws_session_token=creds["SessionToken"],
            ) as s3:
                await s3.head_bucket(Bucket=self.bucket_name)
            return True
        except (BotoCoreError, ClientError, RuntimeError, ValueError, TypeError) as e:
            self._set_last_error_from_exception(
                e, prefix="AWS CUR bucket verification failed"
            )
            logger.error(
                "cur_bucket_verify_failed", bucket=self.bucket_name, error=str(e)
            )
            return False

    async def setup_cur_automation(self) -> Dict[str, Any]:
        """
        Automates the creation of an S3 bucket and CUR report definition.
        """
        creds = await self._get_credentials()

        async with self.session.client(
            "s3",
            region_name=self._resolved_region,
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        ) as s3:
            try:
                # 1. Check if bucket exists
                bucket_exists = True
                try:
                    await s3.head_bucket(Bucket=self.bucket_name)
                except ClientError as e:
                    if e.response["Error"]["Code"] in ["404", "403"]:
                        bucket_exists = False
                    else:
                        raise

                # 2. Create bucket if needed
                if not bucket_exists:
                    if self._resolved_region == "us-east-1":
                        await s3.create_bucket(Bucket=self.bucket_name)
                    else:
                        await s3.create_bucket(
                            Bucket=self.bucket_name,
                            CreateBucketConfiguration={
                                "LocationConstraint": self._resolved_region
                            },
                        )

                # 3. Put bucket policy
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Sid": "AllowCURPutObject",
                            "Effect": "Allow",
                            "Principal": {"Service": "billingreports.amazonaws.com"},
                            "Action": "s3:PutObject",
                            "Resource": f"arn:aws:s3:::{self.bucket_name}/*",
                            "Condition": {
                                "StringEquals": {
                                    "aws:SourceAccount": self.credentials.account_id,
                                    "aws:SourceArn": f"arn:aws:cur:us-east-1:{self.credentials.account_id}:definition/*",
                                }
                            },
                        },
                        {
                            "Sid": "AllowCURGetBucketAcl",
                            "Effect": "Allow",
                            "Principal": {"Service": "billingreports.amazonaws.com"},
                            "Action": "s3:GetBucketAcl",
                            "Resource": f"arn:aws:s3:::{self.bucket_name}",
                        },
                    ],
                }
                await s3.put_bucket_policy(
                    Bucket=self.bucket_name, Policy=json.dumps(policy)
                )

            except (
                BotoCoreError,
                ClientError,
                RuntimeError,
                ValueError,
                TypeError,
                KeyError,
            ) as e:
                logger.error("s3_setup_failed", error=str(e))
                return {"status": "error", "message": f"S3 setup failed: {str(e)}"}

        async with self.session.client(
            "cur",
            region_name="us-east-1",  # CUR is global but uses us-east-1 endpoint
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        ) as cur:
            try:
                # 4. Create CUR Report Definition
                report_name = f"valdrics-cur-{self.credentials.account_id}"
                await cur.put_report_definition(
                    ReportDefinition={
                        "ReportName": report_name,
                        "TimeUnit": "HOURLY",
                        "Format": "Parquet",
                        "Compression": "GZIP",
                        "AdditionalSchemaElements": ["RESOURCES"],
                        "S3Bucket": self.bucket_name,
                        "S3Prefix": "cur",
                        "S3Region": self._resolved_region,
                        "ReportVersioning": "OVERWRITE_REPORT",
                        "RefreshClosedReports": True,
                    }
                )

                return {
                    "status": "success",
                    "bucket_name": self.bucket_name,
                    "report_name": report_name,
                }
            except (
                BotoCoreError,
                ClientError,
                RuntimeError,
                ValueError,
                TypeError,
                KeyError,
            ) as e:
                logger.error("cur_setup_failed", error=str(e))
                return {"status": "error", "message": f"CUR setup failed: {str(e)}"}

    async def get_cost_and_usage(
        self, start_date: datetime, end_date: datetime, granularity: str = "DAILY"
    ) -> List[Dict[str, Any]]:
        """Materialized interface for cost ingestion."""
        # Convert to date for internal processing
        s_date = start_date.date() if isinstance(start_date, datetime) else start_date
        e_date = end_date.date() if isinstance(end_date, datetime) else end_date

        summary = await self.get_daily_costs(s_date, e_date)
        return [r.model_dump() for r in summary.records]

    async def get_daily_costs(
        self,
        start_date: date,
        end_date: date,
        usage_only: bool = False,
        group_by_service: bool = True,
    ) -> CloudUsageSummary:
        """
        Fetch daily costs from CUR files in S3 for a specific date range.
        Consolidates logic from previous CUR and S3 adapters.
        """
        # 1. Discover relevant Parquet files
        report_files = await self._list_cur_files_in_range(start_date, end_date)

        if not report_files:
            logger.warning(
                "no_cur_files_found_in_range",
                bucket=self.bucket_name,
                start=start_date.isoformat(),
                end=end_date.isoformat(),
            )
            return self._empty_summary()

        # 2. Process and aggregate
        return await self._process_files_in_range(
            report_files, start_date, end_date
        )

    async def discover_resources(
        self, resource_type: str, region: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        Project CUR cost rows into deterministic resource inventory snapshots.
        """
        self._clear_last_error()
        start_date, end_date = resource_usage_lookback_window()
        try:
            raw_rows = await self.get_cost_and_usage(
                start_date=start_date,
                end_date=end_date,
                granularity="DAILY",
            )
        except (
            BotoCoreError,
            ClientError,
            RuntimeError,
            ValueError,
            TypeError,
            KeyError,
            OSError,
        ) as exc:
            self._set_last_error_from_exception(
                exc, prefix="AWS CUR resource discovery failed"
            )
            logger.warning(
                "aws_cur_discover_resources_failed",
                resource_type=resource_type,
                region=region,
                error=str(exc),
            )
            return []

        normalized_rows = self._normalize_rows_for_projection(raw_rows)
        return discover_resources_from_cost_rows(
            cost_rows=normalized_rows,
            resource_type=resource_type,
            supported_resource_types=_DISCOVERY_RESOURCE_TYPE_ALIASES,
            default_provider="aws",
            default_resource_type="aws_resource",
            region=region,
        )

    async def stream_cost_and_usage(
        self, start_date: datetime, end_date: datetime, granularity: str = "DAILY"
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Efficiently stream cost data without loading full summary into memory.
        """
        s_date = start_date.date() if isinstance(start_date, datetime) else start_date
        e_date = end_date.date() if isinstance(end_date, datetime) else end_date
        
        report_files = await self._list_cur_files_in_range(s_date, e_date)
        
        for file_key in report_files:
            # We process one file at a time and yield records
            file_summary = await self._ingest_single_file(file_key, s_date, e_date)
            for record in file_summary.records:
                yield {
                    "timestamp": record.date,
                    "service": record.service,
                    "region": record.region,
                    "cost_usd": record.amount,
                    "currency": record.currency,
                    "amount_raw": record.amount_raw,
                    "usage_type": record.usage_type,
                    "tags": record.tags,
                    "source_adapter": "cur_data_export",
                }

    async def _list_cur_files_in_range(self, start_date: date, end_date: date) -> List[str]:
        """
        Lists S3 keys for CUR Parquet files representing the date range.
        Handles the year/month subdirectory structure and manifest files.
        """
        return await list_cur_files_in_range(
            adapter=self,
            start_date=start_date,
            end_date=end_date,
            logger=logger,
        )

    async def _process_files_in_range(
        self, files: List[str], start_date: date, end_date: date
    ) -> CloudUsageSummary:
        """Processes multiple files and aggregates into a single summary."""
        return await process_files_in_range(
            adapter=self,
            files=files,
            start_date=start_date,
            end_date=end_date,
            logger=logger,
        )

    async def _ingest_single_file(self, key: str, start_date: date, end_date: date) -> CloudUsageSummary:
        """Downloads and processes a single Parquet file."""
        creds = await self._get_credentials()
        async with self.session.client(
            "s3",
            region_name=self._resolved_region,
            aws_access_key_id=creds["AccessKeyId"],
            aws_secret_access_key=creds["SecretAccessKey"],
            aws_session_token=creds["SessionToken"],
        ) as s3:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet") as tmp:
                tmp_path = tmp.name
                try:
                    obj = await s3.get_object(Bucket=self.bucket_name, Key=key)
                    async with obj["Body"] as stream:
                        while True:
                            chunk = await stream.read(1024 * 1024 * 16) # 16MB chunks
                            if not chunk:
                                break
                            tmp.write(chunk)
                    
                    return self._process_parquet_streamingly(tmp_path, start_date, end_date)
                finally:
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)

    def _process_parquet_streamingly(self, file_path: str, start_date: date | None = None, end_date: date | None = None) -> CloudUsageSummary:
        """
        Processes a Parquet file using row groups to keep memory low.
        Aggregates metrics on the fly with optional date filtering.
        """
        parquet_file = pq.ParquetFile(file_path)
        return process_parquet_streamingly(
            adapter=self,
            parquet_file=parquet_file,
            start_date=start_date,
            end_date=end_date,
            logger=logger,
        )

    def _iter_parquet_dataframes(self, parquet_file: Any) -> Iterator[pd.DataFrame]:
        """Yield CUR dataframes with bounded memory when batch iteration is available."""
        return iter_parquet_dataframes(
            adapter=self,
            parquet_file=parquet_file,
            logger=logger,
        )

    def _parse_row(self, row: pd.Series, col_map: Dict[str, str | None]) -> CostRecord:
        """Parses a single CUR row into a CostRecord."""
        return parse_cur_row(
            row=row,
            col_map=col_map,
            extract_tags=self._extract_tags,
        )

    def _extract_tags(self, row: pd.Series) -> Dict[str, str]:
        """Extracts user-defined tags from CUR columns."""
        return extract_cur_tags(row)

    async def _get_credentials(self) -> dict[str, str]:
        """Helper to get credentials from existing adapter logic or shared util."""
        # For simplicity, we assume the credentials logic is shared or we re-implement
        from app.shared.adapters.aws_multitenant import MultiTenantAWSAdapter

        adapter = MultiTenantAWSAdapter(self.credentials)
        credentials = await adapter.get_credentials()
        return cast(dict[str, str], credentials)

    def _empty_summary(self) -> CloudUsageSummary:
        return CloudUsageSummary(
            tenant_id="anonymous", # Decoupled from tenant model in adapter
            provider="aws",
            start_date=date.today(),
            end_date=date.today(),
            total_cost=Decimal("0"),
            records=[],
            by_service={},
            by_region={},
        )

    async def get_resource_usage(
        self, service_name: str, resource_id: str | None = None
    ) -> List[Dict[str, Any]]:
        """
        Project CUR cost rows into normalized resource-usage rows.

        CUR may not always include explicit resource identifiers in every record; in such
        cases this returns service-level usage rows with `resource_id=None`.
        """
        self._clear_last_error()
        target_service = service_name.strip()
        if not target_service:
            return []

        start_date, end_date = resource_usage_lookback_window()
        try:
            raw_rows = await self.get_cost_and_usage(
                start_date=start_date,
                end_date=end_date,
                granularity="DAILY",
            )
        except (
            BotoCoreError,
            ClientError,
            RuntimeError,
            ValueError,
            TypeError,
            KeyError,
            OSError,
        ) as exc:
            self._set_last_error_from_exception(
                exc, prefix="AWS CUR resource usage lookup failed"
            )
            logger.warning(
                "aws_cur_resource_usage_failed",
                service_name=target_service,
                resource_id=resource_id,
                error=str(exc),
            )
            return []

        normalized_rows = self._normalize_rows_for_projection(raw_rows)

        return project_cost_rows_to_resource_usage(
            cost_rows=normalized_rows,
            service_name=target_service,
            resource_id=resource_id,
            default_provider="aws",
            default_source_adapter="cur_data_export",
        )

    def _normalize_rows_for_projection(
        self, raw_rows: List[Dict[str, Any]]
    ) -> list[dict[str, Any]]:
        return normalize_rows_for_projection(raw_rows)
