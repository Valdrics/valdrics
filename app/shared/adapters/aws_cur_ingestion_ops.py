from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any, cast

from botocore.exceptions import BotoCoreError, ClientError

from app.schemas.costs import CloudUsageSummary
from app.shared.adapters.aws_pagination import iter_aws_paginator_pages


def _next_month(current: date) -> date:
    if current.month == 12:
        return current.replace(year=current.year + 1, month=1)
    return current.replace(month=current.month + 1)


async def list_cur_files_in_range(
    *,
    adapter: Any,
    start_date: date,
    end_date: date,
    logger: Any,
) -> list[str]:
    """
    List CUR parquet object keys for a date range.
    Uses manifest files when available and falls back to direct parquet listing.
    """
    creds = await adapter._get_credentials()
    prefix_base = adapter.credentials.cur_prefix or "cur"
    files: list[str] = []
    seen: set[str] = set()

    async with adapter.session.client(
        "s3",
        region_name=adapter._resolved_region,
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
    ) as s3:
        current = start_date.replace(day=1)
        while current <= end_date:
            month_prefix = f"{prefix_base}/{current.year}/{current.month:02d}/"
            paginator = s3.get_paginator("list_objects_v2")
            manifest_keys: list[tuple[Any, str]] = []
            parquet_keys: list[str] = []

            async for page in iter_aws_paginator_pages(
                paginator,
                operation_name="s3.list_objects_v2",
                paginate_kwargs={
                    "Bucket": adapter.bucket_name,
                    "Prefix": month_prefix,
                },
                max_pages=adapter._LIST_OBJECTS_MAX_PAGES_PER_MONTH,
            ):
                for obj in page.get("Contents", []):
                    key = obj["Key"]
                    if key.lower().endswith("manifest.json"):
                        manifest_keys.append((obj.get("LastModified"), key))
                    elif key.lower().endswith(".parquet"):
                        parquet_keys.append(key)

            if manifest_keys:
                manifest_keys.sort(key=lambda item: item[0] or datetime.min, reverse=True)
                latest_manifest = manifest_keys[0][1]
                try:
                    manifest_obj = await s3.get_object(
                        Bucket=adapter.bucket_name,
                        Key=latest_manifest,
                    )
                    manifest_data = json.loads(await manifest_obj["Body"].read())
                    for report_key in manifest_data.get("reportKeys", []):
                        if report_key.endswith(".parquet") and report_key not in seen:
                            files.append(report_key)
                            seen.add(report_key)
                except (
                    BotoCoreError,
                    ClientError,
                    RuntimeError,
                    json.JSONDecodeError,
                    ValueError,
                    TypeError,
                    KeyError,
                ) as exc:
                    logger.warning(
                        "manifest_parse_failed",
                        key=latest_manifest,
                        error=str(exc),
                    )
                    for parquet_key in parquet_keys:
                        if parquet_key not in seen:
                            files.append(parquet_key)
                            seen.add(parquet_key)
            else:
                for parquet_key in parquet_keys:
                    if parquet_key not in seen:
                        files.append(parquet_key)
                        seen.add(parquet_key)

            current = _next_month(current)

    return files


async def process_files_in_range(
    *,
    adapter: Any,
    files: list[str],
    start_date: date,
    end_date: date,
    logger: Any,
) -> CloudUsageSummary:
    """Process all discovered CUR files and aggregate one summary."""
    master_summary = adapter._empty_summary()
    master_summary.start_date = start_date
    master_summary.end_date = end_date
    per_file_record_cap = 10000
    truncated_records_total = 0

    for file_key in files:
        file_summary = await adapter._ingest_single_file(file_key, start_date, end_date)

        master_summary.total_cost += file_summary.total_cost
        retained_records = file_summary.records[:per_file_record_cap]
        master_summary.records.extend(retained_records)
        truncated_count = max(0, len(file_summary.records) - len(retained_records))
        if truncated_count > 0:
            truncated_records_total += truncated_count
            logger.warning(
                "cur_file_summary_records_truncated",
                file_key=file_key,
                cap=per_file_record_cap,
                truncated_records=truncated_count,
            )

        for key, cost in file_summary.by_service.items():
            master_summary.by_service[key] = (
                master_summary.by_service.get(key, Decimal("0")) + cost
            )
        for key, cost in file_summary.by_region.items():
            master_summary.by_region[key] = (
                master_summary.by_region.get(key, Decimal("0")) + cost
            )
        for tag_key, tag_map in file_summary.by_tag.items():
            if tag_key not in master_summary.by_tag:
                master_summary.by_tag[tag_key] = {}
            for tag_value, tag_cost in tag_map.items():
                master_summary.by_tag[tag_key][tag_value] = (
                    master_summary.by_tag[tag_key].get(tag_value, Decimal("0"))
                    + tag_cost
                )

    if truncated_records_total > 0:
        logger.warning(
            "cur_master_summary_records_truncated",
            cap_per_file=per_file_record_cap,
            truncated_records_total=truncated_records_total,
            files_processed=len(files),
        )

    return cast(CloudUsageSummary, master_summary)


def normalize_rows_for_projection(raw_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize CUR-shaped rows for downstream resource projection helpers."""
    normalized_rows: list[dict[str, Any]] = []
    for row in raw_rows:
        if not isinstance(row, dict):
            continue
        normalized_rows.append(
            {
                "provider": "aws",
                "service": row.get("service"),
                "region": row.get("region"),
                "usage_type": row.get("usage_type"),
                "resource_id": row.get("resource_id")
                or row.get("line_item_resource_id")
                or row.get("lineItem/ResourceId"),
                "usage_amount": row.get("usage_amount")
                or row.get("line_item_usage_amount")
                or row.get("lineItem/UsageAmount"),
                "usage_unit": row.get("usage_unit"),
                "cost_usd": row.get("cost_usd", row.get("amount")),
                "amount_raw": row.get("amount_raw"),
                "currency": row.get("currency"),
                "timestamp": row.get("timestamp", row.get("date")),
                "source_adapter": row.get("source_adapter", "cur_data_export"),
                "tags": row.get("tags") if isinstance(row.get("tags"), dict) else {},
            }
        )
    return normalized_rows
