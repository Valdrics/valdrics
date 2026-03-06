from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime
from typing import Any

from app.shared.core.exceptions import ExternalAPIError


async def get_json(
    *,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None,
    request_fn: Callable[[str, dict[str, str], dict[str, Any] | None], Awaitable[Any]],
    execute_with_http_retry_fn: Callable[..., Awaitable[Any]],
    max_retries: int,
    retryable_status_codes: set[int],
) -> dict[str, Any]:
    response = await execute_with_http_retry_fn(
        request=lambda: request_fn(url, headers, params),
        url=url,
        max_retries=max_retries,
        retryable_status_codes=retryable_status_codes,
        retry_http_status_log_event="saas_native_retry_http_status",
        retry_transport_log_event="saas_native_retry_transport_error",
        status_error_prefix="SaaS connector API request failed",
        transport_error_prefix="SaaS connector API request failed",
    )
    try:
        payload = response.json()
    except ValueError as exc:
        raise ExternalAPIError("SaaS connector API returned invalid JSON payload") from exc
    if not isinstance(payload, dict):
        raise ExternalAPIError("SaaS connector API returned invalid payload shape")
    return payload


async def stream_stripe_cost_and_usage(
    *,
    adapter: Any,
    start_date: datetime,
    end_date: datetime,
    logger: Any,
    convert_to_usd_fn: Callable[[float, str], Awaitable[Any]],
    as_float_fn: Callable[..., float],
    parse_timestamp_fn: Callable[[Any], datetime],
    currency_conversion_recoverable_errors: tuple[type[Exception], ...],
) -> AsyncGenerator[dict[str, Any], None]:
    api_key = adapter._resolve_api_key()
    headers = {"Authorization": f"Bearer {api_key}"}
    endpoint = "https://api.stripe.com/v1/invoices"
    starting_after: str | None = None

    while True:
        params: dict[str, Any] = {
            "limit": 100,
            "created[gte]": int(start_date.timestamp()),
            "created[lte]": int(end_date.timestamp()),
        }
        if starting_after:
            params["starting_after"] = starting_after

        payload = await adapter._get_json(endpoint, headers=headers, params=params)
        entries = payload.get("data")
        if not isinstance(entries, list):
            raise ExternalAPIError("Invalid Stripe invoices payload: expected list in data")

        for invoice in entries:
            if not isinstance(invoice, dict):
                continue
            timestamp = parse_timestamp_fn(invoice.get("created"))
            if timestamp < start_date or timestamp > end_date:
                continue

            amount_cents = invoice.get("amount_paid")
            if amount_cents is None:
                amount_cents = invoice.get("total")

            currency_code = str(invoice.get("currency") or "USD").upper()
            amount_local = as_float_fn(amount_cents, divisor=100)
            cost_usd = amount_local
            if currency_code != "USD":
                try:
                    cost_usd = float(await convert_to_usd_fn(amount_local, currency_code))
                except currency_conversion_recoverable_errors as exc:
                    logger.warning(
                        "saas_currency_conversion_failed",
                        vendor="stripe",
                        currency=currency_code,
                        error=str(exc),
                    )

            service_name = (
                str(invoice.get("description")).strip()
                if isinstance(invoice.get("description"), str) and invoice.get("description")
                else "Stripe Billing"
            )

            yield {
                "provider": "saas",
                "service": service_name,
                "region": "global",
                "usage_type": "subscription_invoice",
                "resource_id": str(invoice.get("id") or "").strip() or None,
                "usage_amount": 1.0,
                "usage_unit": "invoice",
                "cost_usd": cost_usd,
                "amount_raw": amount_local,
                "currency": currency_code,
                "timestamp": timestamp,
                "source_adapter": "saas_stripe_api",
                "tags": {
                    "vendor": "stripe",
                    "invoice_id": str(invoice.get("id") or ""),
                    "customer_id": str(invoice.get("customer") or ""),
                },
            }

        has_more = bool(payload.get("has_more"))
        if not has_more or not entries:
            break

        next_token = entries[-1].get("id")
        if not isinstance(next_token, str) or not next_token:
            break
        starting_after = next_token


async def stream_salesforce_cost_and_usage(
    *,
    adapter: Any,
    start_date: datetime,
    end_date: datetime,
    logger: Any,
    convert_to_usd_fn: Callable[[float, str], Awaitable[Any]],
    as_float_fn: Callable[..., float],
    parse_timestamp_fn: Callable[[Any], datetime],
    urljoin_fn: Callable[[str, str], str],
    currency_conversion_recoverable_errors: tuple[type[Exception], ...],
) -> AsyncGenerator[dict[str, Any], None]:
    token = adapter._resolve_api_key()
    base_url = adapter._connector_config.get("instance_url")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ExternalAPIError("Salesforce requires connector_config.instance_url")

    endpoint = urljoin_fn(base_url.rstrip("/") + "/", "services/data/v60.0/query")
    start_iso = start_date.date().isoformat()
    end_iso = end_date.date().isoformat()
    soql = (
        "SELECT Id, Description, ServiceDate, TotalPrice, CurrencyIsoCode "  # nosec B608
        "FROM ContractLineItem "
        f"WHERE ServiceDate >= {start_iso} "
        f"AND ServiceDate <= {end_iso} "
        "ORDER BY ServiceDate DESC"
    )
    headers = {"Authorization": f"Bearer {token}"}

    params: dict[str, Any] | None = {"q": soql}
    next_url: str | None = endpoint
    while next_url:
        payload = await adapter._get_json(next_url, headers=headers, params=params)
        records = payload.get("records")
        if not isinstance(records, list):
            raise ExternalAPIError("Invalid Salesforce query payload: expected list in records")

        for record in records:
            if not isinstance(record, dict):
                continue
            service_date = record.get("ServiceDate")
            timestamp = parse_timestamp_fn(service_date)
            if timestamp < start_date or timestamp > end_date:
                continue
            amount_local = as_float_fn(record.get("TotalPrice"))
            currency_code = str(record.get("CurrencyIsoCode") or "USD").upper()
            cost_usd = amount_local
            if currency_code != "USD":
                try:
                    cost_usd = float(await convert_to_usd_fn(amount_local, currency_code))
                except currency_conversion_recoverable_errors as exc:
                    logger.warning(
                        "saas_currency_conversion_failed",
                        vendor="salesforce",
                        currency=currency_code,
                        error=str(exc),
                    )
            yield {
                "provider": "saas",
                "service": str(record.get("Description") or "Salesforce Contract"),
                "region": "global",
                "usage_type": "contract_line_item",
                "resource_id": str(record.get("Id") or "").strip() or None,
                "usage_amount": 1.0,
                "usage_unit": "contract_line_item",
                "cost_usd": cost_usd,
                "amount_raw": amount_local,
                "currency": currency_code,
                "timestamp": timestamp,
                "source_adapter": "saas_salesforce_api",
                "tags": {
                    "vendor": "salesforce",
                    "record_id": str(record.get("Id") or ""),
                },
            }

        next_records = payload.get("nextRecordsUrl")
        if not isinstance(next_records, str) or not next_records.strip():
            break
        next_url = urljoin_fn(base_url.rstrip("/") + "/", next_records.lstrip("/"))
        params = None
