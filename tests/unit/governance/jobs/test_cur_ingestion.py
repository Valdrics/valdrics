from contextlib import asynccontextmanager
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.modules.governance.domain.jobs.cur_ingestion import CURIngestionJob


@pytest.mark.asyncio
async def test_run_uses_existing_db():
    db = MagicMock()
    job = CURIngestionJob(db=db)

    with patch.object(job, "_execute", new_callable=AsyncMock) as mock_execute:
        await job.run(connection_id="conn-1", tenant_id="tenant-1")
        mock_execute.assert_awaited_once_with("conn-1", "tenant-1")


@pytest.mark.asyncio
async def test_run_without_db_uses_session_maker():
    session = MagicMock()
    session.commit = AsyncMock()

    @asynccontextmanager
    async def fake_session_maker():
        yield session

    with patch(
        "app.modules.governance.domain.jobs.cur_ingestion.async_session_maker",
        fake_session_maker,
    ):
        job = CURIngestionJob()
        with patch.object(job, "_execute", new_callable=AsyncMock) as mock_execute:
            await job.run(connection_id="conn-2", tenant_id="tenant-2")
            mock_execute.assert_awaited_once_with("conn-2", "tenant-2")
            session.commit.assert_awaited_once()
            assert job.db is None


@pytest.mark.asyncio
async def test_execute_calls_ingest_for_each_connection():
    conn1 = SimpleNamespace(
        id="1", aws_account_id="111", region="us-east-1", cur_bucket_name=None
    )
    conn2 = SimpleNamespace(
        id="2", aws_account_id="222", region="us-west-2", cur_bucket_name=None
    )

    result = MagicMock()
    result.scalars.return_value.all.return_value = [conn1, conn2]

    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    job = CURIngestionJob(db=db)
    with patch.object(
        job, "ingest_for_connection", new_callable=AsyncMock
    ) as mock_ingest:
        await job._execute(tenant_id="tenant-1")
        assert mock_ingest.await_count == 2


@pytest.mark.asyncio
async def test_execute_logs_errors_and_continues():
    conn1 = SimpleNamespace(
        id="1", aws_account_id="111", region="us-east-1", cur_bucket_name=None
    )
    conn2 = SimpleNamespace(
        id="2", aws_account_id="222", region="us-west-2", cur_bucket_name=None
    )

    result = MagicMock()
    result.scalars.return_value.all.return_value = [conn1, conn2]

    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    job = CURIngestionJob(db=db)
    with (
        patch.object(
            job, "ingest_for_connection", new_callable=AsyncMock
        ) as mock_ingest,
        patch("app.modules.governance.domain.jobs.cur_ingestion.logger") as mock_logger,
    ):
        mock_ingest.side_effect = [RuntimeError("boom"), None]

        await job._execute(tenant_id="tenant-1")

        assert mock_ingest.await_count == 2
        mock_logger.error.assert_called_once()


@pytest.mark.asyncio
async def test_execute_requires_tenant_scope():
    db = MagicMock()
    db.execute = AsyncMock()
    job = CURIngestionJob(db=db)

    with pytest.raises(ValueError, match="tenant_id is required"):
        await job._execute()


@pytest.mark.asyncio
async def test_ingest_uses_configured_bucket():
    conn = SimpleNamespace(
        id="conn-3",
        tenant_id="tenant-3",
        aws_account_id="123456789012",
        region="us-east-1",
        cur_bucket_name="custom-cur-bucket",
        last_ingested_at=None,
    )
    db = MagicMock()
    db.add = MagicMock()
    job = CURIngestionJob(db=db)
    adapter = MagicMock()

    async def _stream_costs(**kwargs):
        del kwargs
        yield {
            "timestamp": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "service": "AmazonEC2",
            "region": "us-east-1",
            "cost_usd": 12.5,
            "currency": "USD",
        }

    adapter.stream_cost_and_usage = _stream_costs
    persistence = AsyncMock()
    persistence.save_records_stream = AsyncMock(return_value={"records_saved": 1})

    with (
        patch.object(job, "_build_cur_adapter", return_value=adapter),
        patch.object(job, "_build_persistence_service", return_value=persistence),
        patch("app.modules.governance.domain.jobs.cur_ingestion.logger") as mock_logger,
    ):
        await job.ingest_for_connection(conn)

    persistence.save_records_stream.assert_awaited_once()
    assert conn.last_ingested_at is not None
    mock_logger.info.assert_called_once()
    assert mock_logger.info.call_args.kwargs["connection_id"] == "conn-3"
    assert mock_logger.info.call_args.kwargs["bucket"] == "custom-cur-bucket"
    assert mock_logger.info.call_args.kwargs["records_saved"] == 1


@pytest.mark.asyncio
async def test_ingest_uses_resolved_region_for_bucket_suffix_when_hint_is_global():
    conn = SimpleNamespace(
        id="conn-4",
        tenant_id="tenant-4",
        aws_account_id="123456789012",
        region="global",
        cur_bucket_name=None,
        last_ingested_at=None,
    )
    db = MagicMock()
    db.add = MagicMock()
    job = CURIngestionJob(db=db)
    adapter = MagicMock()

    async def _stream_costs(**kwargs):
        del kwargs
        if False:
            yield {}

    adapter.stream_cost_and_usage = _stream_costs
    persistence = AsyncMock()
    
    async def _consume(records, **kwargs):
        del kwargs
        async for _ in records:
            pass
        return {"records_saved": 0}

    persistence.save_records_stream = AsyncMock(side_effect=_consume)

    with (
        patch(
            "app.shared.adapters.aws_utils.get_settings",
            return_value=SimpleNamespace(
                AWS_SUPPORTED_REGIONS=["eu-west-1"],
                AWS_DEFAULT_REGION="eu-west-1",
            ),
        ),
        patch.object(job, "_build_cur_adapter", return_value=adapter),
        patch.object(job, "_build_persistence_service", return_value=persistence),
        patch("app.modules.governance.domain.jobs.cur_ingestion.logger") as mock_logger,
    ):
        await job.ingest_for_connection(conn)

    mock_logger.info.assert_called_once()
    assert (
        mock_logger.info.call_args.kwargs["bucket"]
        == "valdrics-cur-123456789012-eu-west-1"
    )


@pytest.mark.asyncio
async def test_ingest_for_connection_uses_last_ingested_overlap_window():
    conn = SimpleNamespace(
        id="conn-6",
        tenant_id="tenant-6",
        aws_account_id="123456789012",
        region="us-east-1",
        cur_bucket_name="cur-bucket",
        last_ingested_at=datetime(2026, 3, 5, 12, 0, tzinfo=timezone.utc),
    )
    db = MagicMock()
    db.add = MagicMock()
    job = CURIngestionJob(db=db)
    adapter = MagicMock()
    captured_window: dict[str, datetime] = {}

    async def _stream_costs(**kwargs):
        captured_window.update(kwargs)
        if False:
            yield {}

    adapter.stream_cost_and_usage = _stream_costs
    persistence = AsyncMock()

    async def _consume(records, **kwargs):
        del kwargs
        async for _ in records:
            pass
        return {"records_saved": 0}

    persistence.save_records_stream = AsyncMock(side_effect=_consume)

    with (
        patch.object(job, "_build_cur_adapter", return_value=adapter),
        patch.object(job, "_build_persistence_service", return_value=persistence),
    ):
        await job.ingest_for_connection(conn)

    assert captured_window["start_date"] == datetime(
        2026, 3, 4, 12, 0, tzinfo=timezone.utc
    )
    assert captured_window["granularity"] == "HOURLY"


@pytest.mark.asyncio
async def test_find_latest_cur_key_resolves_global_region_for_s3_client():
    conn = SimpleNamespace(
        id="conn-5",
        aws_account_id="123456789012",
        region="global",
        cur_prefix="cur",
        cur_report_name="valdrics-cur",
    )
    job = CURIngestionJob()

    mock_s3 = MagicMock()
    mock_s3.list_objects_v2.return_value = {}
    with (
        patch(
            "app.shared.adapters.aws_utils.get_settings",
            return_value=SimpleNamespace(
                AWS_SUPPORTED_REGIONS=["eu-west-1"],
                AWS_DEFAULT_REGION="eu-west-1",
            ),
        ),
        patch(
            "boto3.client",
            return_value=mock_s3,
        ) as mock_client,
    ):
        key = await job._find_latest_cur_key(conn, "test-bucket")

    assert key is None
    mock_client.assert_called_once()
    _, kwargs = mock_client.call_args
    assert kwargs["region_name"] == "eu-west-1"
