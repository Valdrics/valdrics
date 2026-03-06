from __future__ import annotations

from datetime import date, timezone
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Iterator

import pandas as pd

from app.schemas.costs import CloudUsageSummary, CostRecord
from app.shared.core.exceptions import ConfigurationError

CUR_COLUMNS: dict[str, list[str]] = {
    "date": [
        "lineItem/UsageStartDate",
        "identity/TimeInterval",
        "line_item_usage_start_date",
    ],
    "cost": [
        "lineItem/UnblendedCost",
        "line_item_unblended_cost",
        "lineItem/AmortizedCost",
        "line_item_amortized_cost",
    ],
    "currency": ["lineItem/CurrencyCode", "line_item_currency_code"],
    "service": ["lineItem/ProductCode", "line_item_product_code", "product/ProductName"],
    "region": ["product/region", "lineItem/AvailabilityZone", "product/location"],
    "usage_type": ["lineItem/UsageType", "line_item_operation"],
}

_ROW_PARSE_RECOVERABLE_EXCEPTIONS = (
    ConfigurationError,
    InvalidOperation,
    ValueError,
    TypeError,
    KeyError,
    AttributeError,
)


def process_parquet_streamingly(
    *,
    adapter: Any,
    parquet_file: Any,
    start_date: date | None,
    end_date: date | None,
    logger: Any,
) -> CloudUsageSummary:
    """
    Process a CUR parquet file chunk-wise with bounded memory.
    """
    total_cost_usd = Decimal("0")
    by_service: dict[str, Decimal] = {}
    by_region: dict[str, Decimal] = {}
    by_tag: dict[str, dict[str, Decimal]] = {}
    all_records: list[CostRecord] = []
    record_cap = max(1, int(getattr(adapter, "_SUMMARY_RECORD_CAP", 50000)))
    dropped_records = 0
    min_date_found: date | None = None
    max_date_found: date | None = None

    for df_chunk in adapter._iter_parquet_dataframes(parquet_file):
        if df_chunk.empty:
            continue

        col_map: dict[str, str | None] = {
            key: next((column for column in aliases if column in df_chunk.columns), None)
            for key, aliases in CUR_COLUMNS.items()
        }
        if not col_map.get("date") or not col_map.get("cost"):
            continue

        date_key = col_map["date"]
        if date_key is None:
            continue

        df_chunk[date_key] = pd.to_datetime(df_chunk[date_key])
        chunk_min = df_chunk[date_key].min().date()
        chunk_max = df_chunk[date_key].max().date()
        if start_date and chunk_max < start_date:
            continue
        if end_date and chunk_min > end_date:
            continue

        min_date_found = min(min_date_found, chunk_min) if min_date_found else chunk_min
        max_date_found = max(max_date_found, chunk_max) if max_date_found else chunk_max

        for _, row in df_chunk.iterrows():
            row_date = row[date_key].date()
            if start_date and row_date < start_date:
                continue
            if end_date and row_date > end_date:
                continue
            try:
                record = adapter._parse_row(row, col_map)
                if len(all_records) < record_cap:
                    all_records.append(record)
                else:
                    dropped_records += 1

                total_cost_usd += record.amount
                service = record.service or "Unknown"
                region = record.region or "Unknown"
                by_service[service] = by_service.get(service, Decimal("0")) + record.amount
                by_region[region] = by_region.get(region, Decimal("0")) + record.amount
                for tag_key, tag_value in record.tags.items():
                    if tag_key not in by_tag:
                        by_tag[tag_key] = {}
                    by_tag[tag_key][tag_value] = (
                        by_tag[tag_key].get(tag_value, Decimal("0")) + record.amount
                    )
            except _ROW_PARSE_RECOVERABLE_EXCEPTIONS:
                continue

    if dropped_records > 0:
        logger.warning(
            "cur_summary_record_cap_reached",
            cap=record_cap,
            dropped_records=dropped_records,
            retained_records=len(all_records),
            start=str(start_date) if start_date else None,
            end=str(end_date) if end_date else None,
        )

    return CloudUsageSummary(
        tenant_id="anonymous",
        provider="aws",
        start_date=min_date_found or date.today(),
        end_date=max_date_found or date.today(),
        total_cost=total_cost_usd,
        records=all_records,
        by_service=by_service,
        by_region=by_region,
        by_tag=by_tag,
    )


def iter_parquet_dataframes(
    *,
    adapter: Any,
    parquet_file: Any,
    logger: Any,
) -> Iterator[pd.DataFrame]:
    """Yield CUR dataframes using iter_batches when available, else row groups."""
    iter_batches = getattr(parquet_file, "iter_batches", None)
    if callable(iter_batches):
        processed_batch = False
        try:
            try:
                batch_iter = iter_batches(batch_size=adapter._PARQUET_BATCH_SIZE)
            except TypeError:
                batch_iter = iter_batches(adapter._PARQUET_BATCH_SIZE)

            for batch in batch_iter:
                processed_batch = True
                try:
                    yield batch.to_pandas()
                except (ValueError, TypeError, RuntimeError, AttributeError) as exc:
                    logger.warning("cur_batch_to_pandas_failed", error=str(exc))
                    continue
            return
        except (ValueError, TypeError, RuntimeError, AttributeError) as exc:
            logger.warning("cur_iter_batches_failed_fallback", error=str(exc))
            if processed_batch:
                return

    for row_group in range(parquet_file.num_row_groups):
        try:
            table = parquet_file.read_row_group(row_group)
            yield table.to_pandas()
        except (ValueError, TypeError, RuntimeError, AttributeError) as exc:
            logger.warning(
                "cur_row_group_read_failed",
                error=str(exc),
                row_group=row_group,
            )
            continue


def parse_cur_row(
    *,
    row: pd.Series,
    col_map: dict[str, str | None],
    extract_tags: Callable[[pd.Series], dict[str, str]],
) -> CostRecord:
    """Parse one CUR row into a normalized CostRecord."""
    cost_key = col_map.get("cost")
    raw_value = row.get(cost_key, 0) if cost_key else 0
    if pd.isna(raw_value) or raw_value == "":
        raw_amount = Decimal("0")
    else:
        try:
            raw_amount = Decimal(str(raw_value))
        except (InvalidOperation, ValueError, TypeError):
            raw_amount = Decimal("0")
    if raw_amount.is_nan() or raw_amount.is_infinite():
        raw_amount = Decimal("0")

    currency_key = col_map.get("currency")
    currency_value = row.get(currency_key, "USD") if currency_key else "USD"
    currency = "USD" if pd.isna(currency_value) or currency_value == "" else str(currency_value)

    service_key = col_map.get("service")
    service_value = row.get(service_key, "Unknown") if service_key else "Unknown"
    service = "Unknown" if pd.isna(service_value) or service_value == "" else str(service_value)

    region_key = col_map.get("region")
    region_value = row.get(region_key, "Global") if region_key else "Global"
    region = "Global" if pd.isna(region_value) or region_value == "" else str(region_value)

    usage_key = col_map.get("usage_type")
    usage_value = row.get(usage_key, "Unknown") if usage_key else "Unknown"
    usage_type = "Unknown" if pd.isna(usage_value) or usage_value == "" else str(usage_value)

    date_column = col_map["date"]
    if not date_column:
        raise ConfigurationError("Missing date column mapping")
    dt = pd.to_datetime(row[date_column])
    if pd.isna(dt):
        raise ConfigurationError("Invalid usage start date")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return CostRecord(
        date=dt,
        amount=raw_amount,
        amount_raw=raw_amount,
        currency=currency,
        service=service,
        region=region,
        usage_type=usage_type,
        tags=extract_tags(row),
    )


def extract_cur_tags(row: pd.Series) -> dict[str, str]:
    """Extract user-defined tags from known CUR tag prefixes."""
    tags: dict[str, str] = {}
    for key, value in row.items():
        if pd.notna(value) and value != "":
            string_key = str(key)
            if "resourceTags/user:" in string_key:
                tags[string_key.split("resourceTags/user:")[-1]] = str(value)
            elif "resource_tags_user_" in string_key:
                tags[string_key.replace("resource_tags_user_", "")] = str(value)
    return tags
