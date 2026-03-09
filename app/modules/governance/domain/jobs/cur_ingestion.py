import structlog
from datetime import datetime, timedelta, timezone
import uuid
from typing import AsyncIterator, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.aws_connection import AWSConnection
from app.shared.adapters.aws_utils import resolve_aws_region_hint
from app.shared.core.async_utils import maybe_await
from app.shared.db.session import async_session_maker, mark_session_system_context

logger = structlog.get_logger()
CUR_DEFAULT_LOOKBACK_DAYS = 7
CUR_IDEMPOTENT_OVERLAP_HOURS = 24
CUR_CONNECTION_INGEST_RECOVERABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    RuntimeError,
    ValueError,
    TypeError,
    ConnectionError,
    TimeoutError,
    OSError,
)
CUR_MANIFEST_DISCOVERY_RECOVERABLE_EXCEPTIONS: tuple[type[BaseException], ...] = (
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    ConnectionError,
    TimeoutError,
    OSError,
)


class CURIngestionJob:
    """
    Background job to ingest AWS CUR data from S3.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def run(
        self, connection_id: Optional[str] = None, tenant_id: Optional[str] = None
    ) -> None:
        """
        Execute ingestion for a specific connection or all CUR-enabled connections.
        """
        if not self.db:
            async with async_session_maker() as session:
                await mark_session_system_context(session)
                previous_db = self.db
                try:
                    self.db = session
                    await self._execute(connection_id, tenant_id)
                    await maybe_await(session.commit())
                finally:
                    self.db = previous_db
        else:
            await self._execute(connection_id, tenant_id)

    async def _execute(
        self,
        connection_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        db: Optional[AsyncSession] = None,
    ) -> None:
        db_session = db or self.db
        if db_session is None:
            raise RuntimeError("Database session is required for CUR ingestion")

        # 1. Fetch connection(s)
        if not tenant_id:
            raise ValueError("tenant_id is required for CUR ingestion scope")

        query = select(AWSConnection)
        if connection_id:
            query = query.where(AWSConnection.id == connection_id)
        query = query.where(AWSConnection.tenant_id == tenant_id)

        # We only want connections where CUR is configured (e.g. has bucket info)
        # Note: CUR configuration status might be stored in metadata or a flag
        result = await db_session.execute(query)
        connections = result.scalars().all()

        for conn in connections:
            try:
                await self.ingest_for_connection(conn)
            except CUR_CONNECTION_INGEST_RECOVERABLE_EXCEPTIONS as e:
                logger.error(
                    "cur_ingestion_connection_failed",
                    connection_id=str(conn.id),
                    error=str(e),
                )

    async def ingest_for_connection(self, connection: AWSConnection) -> None:
        """
        Ingest the latest CUR data for a connection.
        """
        if self.db is None:
            raise RuntimeError("Database session is required for CUR ingestion")

        resolved_region = resolve_aws_region_hint(connection.region)
        bucket = (
            connection.cur_bucket_name
            or f"valdrics-cur-{connection.aws_account_id}-{resolved_region}"
        )
        adapter = self._build_cur_adapter(connection)
        persistence = self._build_persistence_service()
        start_date, end_date = self._build_ingestion_window(connection)

        cost_stream_or_awaitable = adapter.stream_cost_and_usage(
            start_date=start_date,
            end_date=end_date,
            granularity="HOURLY",
        )
        cost_stream = await maybe_await(cost_stream_or_awaitable)

        records_ingested = 0
        total_cost = 0.0

        async def normalized_records() -> AsyncIterator[dict[str, object]]:
            nonlocal records_ingested, total_cost
            async for raw in cost_stream:
                if not isinstance(raw, dict):
                    continue
                record = dict(raw)
                record.setdefault("provider", "aws")
                record.setdefault("service", "Unknown")
                record.setdefault("region", resolved_region)
                record.setdefault("usage_type", "Usage")
                record.setdefault("currency", "USD")
                record.setdefault("resource_id", None)
                record.setdefault("usage_amount", None)
                record.setdefault("usage_unit", None)
                record.setdefault("source_adapter", "cur_data_export")
                if not isinstance(record.get("tags"), dict):
                    record["tags"] = {}

                timestamp = record.get("timestamp")
                if isinstance(timestamp, datetime):
                    if timestamp.tzinfo is None:
                        record["timestamp"] = timestamp.replace(tzinfo=timezone.utc)
                else:
                    continue

                records_ingested += 1
                total_cost += float(record.get("cost_usd", 0) or 0)
                yield record

        save_result = await persistence.save_records_stream(
            records=normalized_records(),
            tenant_id=connection.tenant_id,
            account_id=connection.id,
            reconciliation_run_id=uuid.uuid4(),
            is_preliminary=True,
        )
        connection.last_ingested_at = end_date
        await maybe_await(self.db.add(connection))

        logger.info(
            "cur_ingestion_completed",
            connection_id=str(connection.id),
            bucket=bucket,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            records_saved=int(save_result.get("records_saved", 0) or 0),
            records_observed=records_ingested,
            total_cost=round(total_cost, 2),
        )

    @staticmethod
    def _build_cur_adapter(connection: AWSConnection):
        from app.shared.adapters.factory import AdapterFactory

        return AdapterFactory.get_adapter(connection)

    def _build_persistence_service(self):
        from app.modules.reporting.domain.persistence import CostPersistenceService

        if self.db is None:
            raise RuntimeError("Database session is required for CUR ingestion")
        return CostPersistenceService(self.db)

    @staticmethod
    def _normalize_ingestion_timestamp(value: object) -> datetime | None:
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    def _build_ingestion_window(
        self, connection: AWSConnection
    ) -> tuple[datetime, datetime]:
        end_date = datetime.now(timezone.utc)
        last_ingested_at = self._normalize_ingestion_timestamp(
            getattr(connection, "last_ingested_at", None)
        )
        if last_ingested_at is None:
            start_date = end_date - timedelta(days=CUR_DEFAULT_LOOKBACK_DAYS)
        else:
            start_date = last_ingested_at - timedelta(hours=CUR_IDEMPOTENT_OVERLAP_HOURS)
        if start_date >= end_date:
            start_date = end_date - timedelta(hours=1)
        return start_date, end_date

    async def _find_latest_cur_key(
        self, connection: AWSConnection, bucket: str
    ) -> Optional[str]:
        """
        Discovers the latest CUR manifest and returns the primary Parquet data key.
        Uses a cost-efficient ListObjectsV2/GetObject pattern.
        """
        import boto3
        from botocore.config import Config
        from botocore.exceptions import BotoCoreError, ClientError
        import json
        from typing import cast

        # 2026 Standard: Use regional endpoints and non-blocking patterns where possible
        resolved_region = resolve_aws_region_hint(connection.region)
        s3 = boto3.client(
            "s3",
            region_name=resolved_region,
            config=Config(retries={"max_attempts": 3, "mode": "standard"}),
        )

        prefix = connection.cur_prefix or ""
        report_name = connection.cur_report_name or "valdrics-cur"

        try:
            # 1. Look for all manifests matching the report name
            # Pattern: [prefix]/[report_name]/[date-range]/[report_name]-Manifest.json
            response = s3.list_objects_v2(
                Bucket=bucket,
                Prefix=f"{prefix}/{report_name}/" if prefix else f"{report_name}/",
            )

            if "Contents" not in response:
                logger.warning("cur_bucket_empty", bucket=bucket)
                return None

            # Find the latest manifest by LastModified
            manifests = [
                obj
                for obj in response["Contents"]
                if obj["Key"].endswith("-Manifest.json")
            ]

            if not manifests:
                logger.warning(
                    "cur_manifest_not_found", bucket=bucket, report=report_name
                )
                return None

            latest_manifest_obj = max(manifests, key=lambda x: x["LastModified"])
            manifest_key = latest_manifest_obj["Key"]

            # 2. Extract Parquet keys from the manifest
            manifest_resp = s3.get_object(Bucket=bucket, Key=manifest_key)
            manifest_data = json.loads(manifest_resp["Body"].read().decode("utf-8"))

            # CUR Parquet manifests list files in 'reportKeys'
            report_keys = manifest_data.get("reportKeys", [])
            if not report_keys:
                logger.warning("cur_manifest_empty_files", manifest=manifest_key)
                return None

            # Return the latest file (usually CUR overwrites or versioning applies)
            # For multi-part, we'd return a list, but simplified here to the newest key.
            return cast(Optional[str], report_keys[0])

        except (
            CUR_MANIFEST_DISCOVERY_RECOVERABLE_EXCEPTIONS
            + (BotoCoreError, ClientError, json.JSONDecodeError)
        ) as e:
            logger.error("cur_manifest_discovery_failed", error=str(e), bucket=bucket)
            raise
