from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import date, datetime, time, timezone
from decimal import InvalidOperation
from typing import Any
from urllib.parse import urljoin

import httpx
import structlog

from app.shared.adapters.feed_utils import as_float, is_number, parse_timestamp
from app.shared.core.currency import ExchangeRateUnavailableError
from app.shared.core.exceptions import ExternalAPIError

logger = structlog.get_logger()

_DATADOG_VENDOR = "datadog"
PLATFORM_CURRENCY_CONVERSION_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    ExchangeRateUnavailableError,
    httpx.HTTPError,
    InvalidOperation,
    RuntimeError,
    TypeError,
    ValueError,
)


class PlatformNativeConnectorMixin:
    def _iter_month_starts(
        self: Any, start_date: datetime, end_date: datetime
    ) -> list[date]:
        start_day = start_date.date()
        end_day = end_date.date()
        current = date(start_day.year, start_day.month, 1)
        months: list[date] = []
        while current <= end_day:
            months.append(current)
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        return months

    def _extract_billable_usage_metrics(
        self: Any, payload: object
    ) -> list[tuple[str, float, str | None]]:
        """
        Best-effort extraction of billable usage metrics from vendor payloads.

        Returns tuples of (metric_key, usage_quantity, usage_unit).
        """
        metrics: list[tuple[str, float, str | None]] = []

        if isinstance(payload, dict):
            # Common: list-shaped under usage/billable_usage.
            for key in ("billable_usage", "usage", "data", "items"):
                value = payload.get(key)
                if isinstance(value, list):
                    for entry in value:
                        if not isinstance(entry, dict):
                            continue
                        metric_key = (
                            entry.get("billing_dimension")
                            or entry.get("usage_type")
                            or entry.get("metric")
                            or entry.get("product")
                            or entry.get("name")
                        )
                        quantity = entry.get(
                            "usage", entry.get("quantity", entry.get("value"))
                        )
                        unit = entry.get("unit") or entry.get("usage_unit")
                        if (
                            isinstance(metric_key, str)
                            and metric_key.strip()
                            and is_number(quantity)
                        ):
                            metrics.append(
                                (
                                    metric_key.strip(),
                                    as_float(quantity),
                                    str(unit) if unit else None,
                                )
                            )
                    if metrics:
                        return metrics

            # Common: dict-shaped metrics under "usage".
            usage = payload.get("usage")
            if isinstance(usage, dict):
                for metric_key, quantity in usage.items():
                    if (
                        isinstance(metric_key, str)
                        and metric_key.strip()
                        and is_number(quantity)
                    ):
                        metrics.append((metric_key.strip(), as_float(quantity), None))
                if metrics:
                    return metrics

            # Fallback: treat top-level numeric keys as metrics.
            for metric_key, quantity in payload.items():
                if (
                    isinstance(metric_key, str)
                    and metric_key.strip()
                    and is_number(quantity)
                ):
                    metrics.append((metric_key.strip(), as_float(quantity), None))
            if metrics:
                return metrics

        raise ExternalAPIError("Vendor payload is missing billable usage metrics")

    async def _verify_datadog(self: Any) -> None:
        api_key = self._resolve_api_key()
        app_key = self._resolve_api_secret()
        base_url = self._resolve_datadog_base_url()

        # Use a usage endpoint for verification: it validates both API + application keys.
        today = datetime.now(timezone.utc).date()
        month = date(today.year, today.month, 1).isoformat()
        endpoint = urljoin(base_url.rstrip("/") + "/", "api/v1/usage/billable-summary")
        payload = await self._get_json(
            endpoint,
            headers={
                "DD-API-KEY": api_key,
                "DD-APPLICATION-KEY": app_key,
            },
            params={"month": month},
        )
        self._extract_billable_usage_metrics(payload)
        self._resolve_unit_prices()

    async def _stream_datadog_cost_and_usage(
        self: Any,
        start_date: datetime,
        end_date: datetime,
    ) -> AsyncGenerator[dict[str, Any], None]:
        api_key = self._resolve_api_key()
        app_key = self._resolve_api_secret()
        base_url = self._resolve_datadog_base_url()
        unit_prices = self._resolve_unit_prices()
        strict_pricing = bool(self._connector_config.get("strict_pricing", False))

        endpoint = urljoin(base_url.rstrip("/") + "/", "api/v1/usage/billable-summary")
        for month_start in self._iter_month_starts(start_date, end_date):
            payload = await self._get_json(
                endpoint,
                headers={
                    "DD-API-KEY": api_key,
                    "DD-APPLICATION-KEY": app_key,
                },
                params={"month": month_start.isoformat()},
            )
            metrics = self._extract_billable_usage_metrics(payload)
            timestamp = datetime.combine(month_start, time.min, tzinfo=timezone.utc)

            for metric_key, quantity, unit in metrics:
                price = unit_prices.get(metric_key)
                if price is None and strict_pricing:
                    raise ExternalAPIError(
                        f"Missing unit price for Datadog metric '{metric_key}'"
                    )
                cost_usd = float(quantity * float(price or 0.0))

                yield {
                    "provider": "platform",
                    "service": f"Datadog {metric_key}",
                    "region": "global",
                    "usage_type": "billable_usage",
                    "resource_id": None,
                    "usage_amount": float(quantity),
                    "usage_unit": unit or "unit",
                    "cost_usd": cost_usd,
                    "amount_raw": cost_usd,
                    "currency": "USD",
                    "timestamp": timestamp,
                    "source_adapter": "platform_datadog_api",
                    "tags": {
                        "vendor": "datadog",
                        "metric": metric_key,
                        "unpriced": price is None,
                    },
                }

    def _resolve_newrelic_account_id(self: Any) -> int:
        raw = self._connector_config.get("account_id")
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str) and raw.isdigit():
            return int(raw)
        raise ExternalAPIError(
            "New Relic requires connector_config.account_id (numeric)"
        )

    def _resolve_newrelic_nrql_template(self: Any) -> str:
        template = self._connector_config.get(
            "nrql_template"
        ) or self._connector_config.get("nrql_query")
        if not isinstance(template, str) or not template.strip():
            raise ExternalAPIError(
                "New Relic requires connector_config.nrql_template (or nrql_query)"
            )
        return template.strip()

    async def _verify_newrelic(self: Any) -> None:
        api_key = self._resolve_api_key()
        endpoint = self._resolve_newrelic_endpoint()
        payload = await self._post_json(
            endpoint,
            headers={"API-Key": api_key},
            json={
                "query": "query { actor { requestContext { userId apiKey } } }",
            },
        )
        if not isinstance(payload, dict):
            raise ExternalAPIError("New Relic verify returned invalid payload")
        data = payload.get("data")
        if not isinstance(data, dict):
            raise ExternalAPIError(
                "New Relic verify returned invalid response: missing data"
            )
        actor = data.get("actor")
        if not isinstance(actor, dict):
            raise ExternalAPIError(
                "New Relic verify returned invalid response: missing actor"
            )
        ctx = actor.get("requestContext")
        if not isinstance(ctx, dict) or not ctx.get("userId"):
            raise ExternalAPIError("New Relic API key validation failed")
        self._resolve_newrelic_account_id()
        self._resolve_newrelic_nrql_template()
        self._resolve_unit_prices()

    async def _stream_newrelic_cost_and_usage(
        self: Any,
        start_date: datetime,
        end_date: datetime,
    ) -> AsyncGenerator[dict[str, Any], None]:
        api_key = self._resolve_api_key()
        endpoint = self._resolve_newrelic_endpoint()
        account_id = self._resolve_newrelic_account_id()
        nrql_template = self._resolve_newrelic_nrql_template()
        unit_prices = self._resolve_unit_prices()

        graphql = (
            "query($accountId: Int!, $nrql: String!) {"
            "  actor {"
            "    account(id: $accountId) {"
            "      nrql(query: $nrql) { results }"
            "    }"
            "  }"
            "}"
        )

        for month_start in self._iter_month_starts(start_date, end_date):
            # Use inclusive month range; NRQL accepts date strings.
            month_end = date(
                month_start.year + (1 if month_start.month == 12 else 0),
                1 if month_start.month == 12 else (month_start.month + 1),
                1,
            )
            month_end = month_end.fromordinal(month_end.toordinal() - 1)

            nrql = nrql_template.format(
                start=month_start.isoformat(), end=month_end.isoformat()
            )
            payload = await self._post_json(
                endpoint,
                headers={"API-Key": api_key},
                json={
                    "query": graphql,
                    "variables": {"accountId": account_id, "nrql": nrql},
                },
            )
            if not isinstance(payload, dict):
                raise ExternalAPIError("New Relic NRQL returned invalid payload")
            data = payload.get("data")
            if not isinstance(data, dict):
                raise ExternalAPIError(
                    "New Relic NRQL returned invalid response: missing data"
                )
            actor = data.get("actor")
            if not isinstance(actor, dict):
                raise ExternalAPIError(
                    "New Relic NRQL returned invalid response: missing actor"
                )
            account = actor.get("account")
            if not isinstance(account, dict):
                raise ExternalAPIError(
                    "New Relic NRQL returned invalid response: missing account"
                )
            nrql_data = account.get("nrql")
            if not isinstance(nrql_data, dict):
                raise ExternalAPIError(
                    "New Relic NRQL returned invalid response: missing nrql"
                )
            results = nrql_data.get("results")
            if not isinstance(results, list):
                raise ExternalAPIError("New Relic NRQL results missing list")

            timestamp = datetime.combine(month_start, time.min, tzinfo=timezone.utc)
            for result in results:
                if not isinstance(result, dict):
                    continue
                for metric_key, price in unit_prices.items():
                    value = result.get(metric_key)
                    if not is_number(value):
                        continue
                    quantity = as_float(value)
                    cost_usd = float(quantity * float(price))
                    yield {
                        "provider": "platform",
                        "service": f"New Relic {metric_key}",
                        "region": "global",
                        "usage_type": "billable_usage",
                        "resource_id": None,
                        "usage_amount": float(quantity),
                        "usage_unit": "unit",
                        "cost_usd": cost_usd,
                        "amount_raw": cost_usd,
                        "currency": "USD",
                        "timestamp": timestamp,
                        "source_adapter": "platform_newrelic_nerdgraph",
                        "tags": {
                            "vendor": "newrelic",
                            "metric": metric_key,
                        },
                    }

    def _resolve_ledger_http_base_url(self: Any) -> str:
        base_url = self._connector_config.get("base_url")
        if not isinstance(base_url, str) or not base_url.strip():
            raise ExternalAPIError(
                "Missing connector_config.base_url for platform ledger HTTP connector"
            )
        base_url = base_url.strip()
        if not base_url.startswith(("https://", "http://")):
            raise ExternalAPIError("connector_config.base_url must be an http(s) URL")
        return base_url

    def _resolve_ledger_http_costs_path(self: Any) -> str:
        path = (
            self._connector_config.get("costs_path")
            or self._connector_config.get("path")
            or "/api/v1/finops/costs"
        )
        if not isinstance(path, str) or not path.strip():
            return "/api/v1/finops/costs"
        normalized = "/" + path.strip().lstrip("/")
        return normalized

    def _resolve_ledger_http_headers(self: Any) -> dict[str, str]:
        token = self._resolve_api_key()
        header_name = self._connector_config.get("api_key_header")
        if isinstance(header_name, str) and header_name.strip():
            return {header_name.strip(): token}
        return {"Authorization": f"Bearer {token}"}

    async def _verify_ledger_http(self: Any) -> None:
        base_url = self._resolve_ledger_http_base_url()
        endpoint = urljoin(
            base_url.rstrip("/") + "/",
            self._resolve_ledger_http_costs_path().lstrip("/"),
        )
        headers = self._resolve_ledger_http_headers()
        # Verification is connectivity + payload-shape check; empty datasets are OK.
        payload = await self._get_json(endpoint, headers=headers, params={"limit": 1})
        self._extract_ledger_records(payload)

    async def _stream_ledger_http_cost_and_usage(
        self: Any,
        start_date: datetime,
        end_date: datetime,
    ) -> AsyncGenerator[dict[str, Any], None]:
        base_url = self._resolve_ledger_http_base_url()
        endpoint = urljoin(
            base_url.rstrip("/") + "/",
            self._resolve_ledger_http_costs_path().lstrip("/"),
        )
        headers = self._resolve_ledger_http_headers()
        start_param = self._connector_config.get("start_param") or "start_date"
        end_param = self._connector_config.get("end_param") or "end_date"
        params = {
            str(start_param): start_date.date().isoformat(),
            str(end_param): end_date.date().isoformat(),
        }
        payload = await self._get_json(endpoint, headers=headers, params=params)
        records = self._extract_ledger_records(payload)

        for entry in records:
            timestamp = parse_timestamp(entry.get("timestamp") or entry.get("date"))
            if timestamp < start_date or timestamp > end_date:
                continue

            service_name = str(
                entry.get("service")
                or entry.get("platform")
                or entry.get("vendor")
                or self._vendor
                or "Internal Platform"
            )
            usage_type = str(entry.get("usage_type") or "shared_service")
            region = str(entry.get("region") or entry.get("location") or "global")

            currency_code = str(entry.get("currency") or "USD").upper()
            cost_usd: float
            amount_raw: float | None = None

            cost_candidate = entry.get("cost_usd", entry.get("amount_usd"))
            if is_number(cost_candidate):
                cost_usd = as_float(cost_candidate)
                amount_raw = (
                    as_float(entry.get("amount_raw"), default=cost_usd)
                    if entry.get("amount_raw") is not None
                    else None
                )
            else:
                amount_local = as_float(
                    entry.get("amount_raw", entry.get("amount", entry.get("cost", 0.0))),
                    default=0.0,
                )
                amount_raw = amount_local
                cost_usd = float(amount_local)
                if currency_code != "USD":
                    try:
                        cost_usd = float(
                            await self._convert_to_usd(amount_local, currency_code)
                        )
                    except PLATFORM_CURRENCY_CONVERSION_RECOVERABLE_ERRORS as exc:
                        logger.warning(
                            "platform_ledger_currency_conversion_failed",
                            currency=currency_code,
                            error=str(exc),
                        )

            resource_id_raw = entry.get("resource_id") or entry.get("id")
            resource_id = (
                str(resource_id_raw).strip()
                if resource_id_raw not in (None, "")
                else None
            )
            usage_amount = (
                as_float(entry.get("usage_amount"), default=0.0)
                if is_number(entry.get("usage_amount"))
                else None
            )
            usage_unit_raw = entry.get("usage_unit")
            usage_unit = (
                str(usage_unit_raw).strip()
                if usage_unit_raw not in (None, "")
                else None
            )
            tags = entry.get("tags") if isinstance(entry.get("tags"), dict) else {}

            yield {
                "provider": "platform",
                "service": service_name,
                "region": region,
                "usage_type": usage_type,
                "resource_id": resource_id,
                "usage_amount": usage_amount,
                "usage_unit": usage_unit,
                "cost_usd": cost_usd,
                "amount_raw": amount_raw,
                "currency": currency_code,
                "timestamp": timestamp,
                "source_adapter": "platform_ledger_http",
                "tags": tags,
            }

    def _extract_ledger_records(self: Any, payload: object) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [entry for entry in payload if isinstance(entry, dict)]
        if isinstance(payload, dict):
            records = (
                payload.get("records")
                or payload.get("data")
                or payload.get("items")
                or []
            )
            if records is None:
                return []
            if not isinstance(records, list):
                raise ExternalAPIError(
                    "Platform ledger HTTP payload is missing a list of records"
                )
            return [entry for entry in records if isinstance(entry, dict)]
        raise ExternalAPIError(
            "Platform ledger HTTP connector returned invalid payload shape"
        )
