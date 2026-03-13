from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import datetime
from decimal import InvalidOperation
from typing import Any

import httpx
from pydantic import SecretStr
import structlog

from app.shared.adapters.base import BaseAdapter
from app.shared.adapters.feed_utils import as_float, is_number, parse_timestamp
from app.shared.adapters.http_retry import execute_with_http_retry
from app.shared.adapters.platform_native_mixin import PlatformNativeConnectorMixin
from app.shared.adapters.resource_usage_projection import (
    discover_resources_from_cost_rows,
    project_cost_rows_to_resource_usage,
    resource_usage_lookback_window,
)
from app.shared.core.credentials import PlatformCredentials
from app.shared.core.currency import convert_to_usd
from app.shared.core.exceptions import ExternalAPIError
from app.shared.core.http import get_http_client
from app.shared.core.outbound_tls import resolve_outbound_tls_verification

logger = structlog.get_logger()

_NATIVE_TIMEOUT_SECONDS = 20.0
_NATIVE_MAX_RETRIES = 3
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_LEDGER_HTTP_VENDOR_ALIASES = {"ledger_http", "cmdb_ledger", "cmdb-ledger", "ledger"}
_DATADOG_VENDOR = "datadog"
_NEWRELIC_VENDOR_ALIASES = {"newrelic", "new_relic", "new-relic"}
_DISCOVERY_RESOURCE_TYPE_ALIASES = {"all", "platform", "service", "services", "shared_service", "shared_services", "tooling"}
PLATFORM_RESOURCE_USAGE_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    ExternalAPIError,
    httpx.HTTPError,
    InvalidOperation,
    RuntimeError,
    TypeError,
    ValueError,
    KeyError,
)
async def _platform_get_request(
    *,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None,
    verify_ssl: bool,
) -> httpx.Response:
    client = get_http_client(verify=verify_ssl)
    return await client.get(url, headers=headers, params=params, timeout=_NATIVE_TIMEOUT_SECONDS)

async def _platform_post_request(
    *,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None,
    json: dict[str, Any],
    verify_ssl: bool,
) -> httpx.Response:
    client = get_http_client(verify=verify_ssl)
    return await client.post(
        url, headers=headers, params=params, json=json, timeout=_NATIVE_TIMEOUT_SECONDS
    )

class PlatformAdapter(PlatformNativeConnectorMixin, BaseAdapter):
    """Cloud+ adapter for internal platform/shared-services spend."""

    def __init__(self, credentials: PlatformCredentials):
        self.credentials = credentials
        self.last_error = None

    @property
    def _auth_method(self) -> str:
        return self.credentials.auth_method.strip().lower()

    @property
    def _vendor(self) -> str:
        return self.credentials.vendor.strip().lower()

    @property
    def _connector_config(self) -> dict[str, Any]:
        return self.credentials.connector_config

    @property
    def _native_vendor(self) -> str | None:
        if self._auth_method not in {"api_key"}:
            return None
        if self._vendor in _LEDGER_HTTP_VENDOR_ALIASES:
            return "ledger_http"
        if self._vendor == _DATADOG_VENDOR:
            return _DATADOG_VENDOR
        if self._vendor in _NEWRELIC_VENDOR_ALIASES:
            return "newrelic"
        return None

    def _resolve_api_key(self) -> str:
        token = self.credentials.api_key
        if token is None:
            raise ExternalAPIError("Missing API token for platform native connector")
        if isinstance(token, SecretStr):
            resolved = token.get_secret_value()
        elif hasattr(token, "get_secret_value"):
            resolved = token.get_secret_value()
        elif isinstance(token, str):
            resolved = token
        else:
            raise ExternalAPIError("Missing API token for platform native connector")
        if not resolved or not resolved.strip():
            raise ExternalAPIError("Missing API token for platform native connector")
        return resolved.strip()

    def _resolve_api_secret(self) -> str:
        token = self.credentials.api_secret
        if token is None:
            raise ExternalAPIError("Missing API secret for platform native connector")
        if isinstance(token, SecretStr):
            resolved = token.get_secret_value()
        elif hasattr(token, "get_secret_value"):
            resolved = token.get_secret_value()
        elif isinstance(token, str):
            resolved = token
        else:
            raise ExternalAPIError("Missing API secret for platform native connector")
        if not resolved or not resolved.strip():
            raise ExternalAPIError("Missing API secret for platform native connector")
        return resolved.strip()

    def _resolve_datadog_base_url(self) -> str:
        base_url = self._connector_config.get(
            "api_base_url"
        ) or self._connector_config.get("base_url")
        if isinstance(base_url, str) and base_url.strip():
            base_url = base_url.strip()
            if not base_url.startswith(("https://", "http://")):
                raise ExternalAPIError(
                    "Datadog connector_config.api_base_url must be an http(s) URL"
                )
            return base_url.rstrip("/")

        site = self._connector_config.get("site")
        if isinstance(site, str) and site.strip():
            site = site.strip()
            if site.startswith(("https://", "http://")):
                return site.rstrip("/")
            if "/" in site:
                raise ExternalAPIError(
                    "Datadog connector_config.site must be a hostname, not a path"
                )
            host = site if site.startswith("api.") else f"api.{site}"
            return f"https://{host}".rstrip("/")

        return "https://api.datadoghq.com"

    def _resolve_newrelic_endpoint(self) -> str:
        base_url = self._connector_config.get(
            "api_base_url"
        ) or self._connector_config.get("base_url")
        if isinstance(base_url, str) and base_url.strip():
            base_url = base_url.strip()
            if not base_url.startswith(("https://", "http://")):
                raise ExternalAPIError(
                    "New Relic connector_config.api_base_url must be an http(s) URL"
                )
            return base_url.rstrip("/")
        return "https://api.newrelic.com/graphql"

    def _resolve_unit_prices(self) -> dict[str, float]:
        raw = self._connector_config.get("unit_prices_usd")
        if not isinstance(raw, dict) or not raw:
            raise ExternalAPIError(
                "Missing connector_config.unit_prices_usd for platform native pricing"
            )
        prices: dict[str, float] = {}
        for key, value in raw.items():
            if not isinstance(key, str) or not key.strip():
                continue
            if not isinstance(value, (int, float)) or value <= 0:
                continue
            prices[key.strip()] = float(value)
        if not prices:
            raise ExternalAPIError(
                "connector_config.unit_prices_usd must contain at least one positive numeric price"
            )
        return prices

    def _resolve_verify_ssl(self) -> bool:
        raw = self._connector_config.get("verify_ssl")
        if isinstance(raw, bool):
            verify_requested = raw
        else:
            raw = self._connector_config.get("ssl_verify")
            verify_requested = raw if isinstance(raw, bool) else True
        try:
            return resolve_outbound_tls_verification(verify_requested)
        except ValueError as exc:
            raise ExternalAPIError(str(exc)) from exc

    async def _convert_to_usd(self, amount_local: float, currency_code: str) -> float:
        return float(await convert_to_usd(amount_local, currency_code))

    def _resolve_native_verify_handler(
        self, native_vendor: str | None
    ) -> Callable[[], Awaitable[None]] | None:
        if native_vendor is None:
            return None
        handlers: dict[str, Callable[[], Awaitable[None]]] = {
            "ledger_http": self._verify_ledger_http,
            _DATADOG_VENDOR: self._verify_datadog,
            "newrelic": self._verify_newrelic,
        }
        return handlers.get(native_vendor)

    def _resolve_native_stream_handler(
        self, native_vendor: str | None
    ) -> Callable[[datetime, datetime], AsyncGenerator[dict[str, Any], None]] | None:
        if native_vendor is None:
            return None
        handlers: dict[
            str, Callable[[datetime, datetime], AsyncGenerator[dict[str, Any], None]]
        ] = {
            "ledger_http": self._stream_ledger_http_cost_and_usage,
            _DATADOG_VENDOR: self._stream_datadog_cost_and_usage,
            "newrelic": self._stream_newrelic_cost_and_usage,
        }
        return handlers.get(native_vendor)

    async def verify_connection(self) -> bool:
        self.last_error = None
        native_vendor = self._native_vendor
        if self._auth_method == "api_key" and native_vendor is None:
            supported = ", ".join(sorted(_LEDGER_HTTP_VENDOR_ALIASES))
            self.last_error = (
                f"Native Platform auth is not supported for vendor '{self._vendor}'. "
                f"Supported vendors: {supported}, datadog, newrelic. "
                "Use auth_method manual/csv for custom vendors."
            )
            return False
        if self._auth_method not in {"manual", "csv", "api_key"}:
            self.last_error = (
                "Platform connector auth_method must be one of: manual, csv, api_key "
                f"(got '{self._auth_method}')."
            )
            return False

        verify_handler = self._resolve_native_verify_handler(native_vendor)
        if verify_handler is not None:
            try:
                await verify_handler()
                return True
            except ExternalAPIError as exc:
                self.last_error = str(exc)
                logger.warning(
                    "platform_native_verify_failed",
                    vendor=native_vendor,
                    error=str(exc),
                )
                return False

        feed = self.credentials.spend_feed
        is_valid = self._validate_manual_feed(feed)
        if not is_valid and self.last_error is None:
            self.last_error = "Spend feed is missing or invalid."
        return is_valid

    def _validate_manual_feed(self, feed: Any) -> bool:
        if not isinstance(feed, list) or not feed:
            self.last_error = "Spend feed must contain at least one record for manual/csv verification."
            return False
        for idx, entry in enumerate(feed):
            if not isinstance(entry, dict):
                self.last_error = f"Spend feed entry #{idx + 1} must be a JSON object."
                return False
            has_timestamp = entry.get("timestamp") or entry.get("date")
            if not has_timestamp:
                self.last_error = (
                    f"Spend feed entry #{idx + 1} is missing timestamp/date."
                )
                return False
            amount = entry.get("cost_usd", entry.get("amount_usd"))
            if not is_number(amount):
                self.last_error = f"Spend feed entry #{idx + 1} must include numeric cost_usd or amount_usd."
                return False
        return True

    async def get_cost_and_usage(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "DAILY",
    ) -> list[dict[str, Any]]:
        records = []
        async for row in self.stream_cost_and_usage(start_date, end_date, granularity):
            records.append(row)
        return records

    async def stream_cost_and_usage(
        self,
        start_date: datetime,
        end_date: datetime,
        granularity: str = "DAILY",
    ) -> AsyncGenerator[dict[str, Any], None]:
        native_vendor = self._native_vendor
        stream_handler = self._resolve_native_stream_handler(native_vendor)
        if stream_handler is not None:
            try:
                async for row in stream_handler(start_date, end_date):
                    yield row
                return
            except ExternalAPIError as exc:
                self.last_error = str(exc)
                logger.warning(
                    "platform_native_stream_failed_fallback_to_feed",
                    vendor=native_vendor,
                    error=str(exc),
                )

        feed = self.credentials.spend_feed
        if not isinstance(feed, list):
            return

        for entry in feed:
            timestamp = parse_timestamp(entry.get("timestamp") or entry.get("date"))
            if timestamp < start_date or timestamp > end_date:
                continue
            service_name = str(
                entry.get("service")
                or entry.get("platform")
                or entry.get("vendor")
                or "Internal Platform"
            )
            usage_type = str(entry.get("usage_type") or "shared_service")
            region = str(entry.get("region") or entry.get("location") or "global")
            cost_value = entry.get("cost_usd", entry.get("amount_usd", 0.0))
            try:
                cost_usd = float(cost_value or 0.0)
            except (TypeError, ValueError):
                cost_usd = 0.0
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

            yield {
                "provider": "platform",
                "service": service_name,
                "region": region,
                "usage_type": usage_type,
                "resource_id": resource_id,
                "usage_amount": usage_amount,
                "usage_unit": usage_unit,
                "cost_usd": cost_usd,
                "amount_raw": entry.get("amount_raw"),
                "currency": str(entry.get("currency") or "USD").upper(),
                "timestamp": timestamp,
                "source_adapter": "platform_feed",
                "tags": entry.get("tags")
                if isinstance(entry.get("tags"), dict)
                else {},
            }

    async def _get_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        params: dict[str, Any] | None = None,
    ) -> object:
        response = await execute_with_http_retry(
            request=lambda: _platform_get_request(
                url=url,
                headers=headers,
                params=params,
                verify_ssl=self._resolve_verify_ssl(),
            ),
            url=url,
            max_retries=_NATIVE_MAX_RETRIES,
            retryable_status_codes=_RETRYABLE_STATUS_CODES,
            retry_http_status_log_event="platform_native_retry_http_status",
            retry_transport_log_event="platform_native_retry_transport_error",
            status_error_prefix="Platform request failed",
            transport_error_prefix="Platform request failed",
        )
        try:
            return response.json()
        except ValueError as exc:
            raise ExternalAPIError(
                "Platform request returned invalid JSON payload"
            ) from exc

    async def _post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict[str, Any],
        params: dict[str, Any] | None = None,
    ) -> object:
        response = await execute_with_http_retry(
            request=lambda: _platform_post_request(
                url=url,
                headers=headers,
                params=params,
                json=json,
                verify_ssl=self._resolve_verify_ssl(),
            ),
            url=url,
            max_retries=_NATIVE_MAX_RETRIES,
            retryable_status_codes=_RETRYABLE_STATUS_CODES,
            retry_http_status_log_event="platform_native_retry_http_status",
            retry_transport_log_event="platform_native_retry_transport_error",
            status_error_prefix="Platform native request failed",
            transport_error_prefix="Platform native request failed",
        )
        try:
            return response.json()
        except ValueError as exc:
            raise ExternalAPIError(
                "Platform native request returned invalid JSON payload"
            ) from exc

    async def discover_resources(
        self, resource_type: str, region: str | None = None
    ) -> list[dict[str, Any]]:
        self._clear_last_error()
        start_date, end_date = resource_usage_lookback_window()
        try:
            cost_rows = await self.get_cost_and_usage(
                start_date=start_date,
                end_date=end_date,
                granularity="DAILY",
            )
        except PLATFORM_RESOURCE_USAGE_RECOVERABLE_ERRORS as exc:
            self.last_error = str(exc)
            logger.warning(
                "platform_discover_resources_failed",
                resource_type=resource_type,
                region=region,
                error=str(exc),
            )
            return []

        return discover_resources_from_cost_rows(
            cost_rows=cost_rows,
            resource_type=resource_type,
            supported_resource_types=_DISCOVERY_RESOURCE_TYPE_ALIASES,
            default_provider="platform",
            default_resource_type="platform_service",
            region=region,
        )

    async def get_resource_usage(
        self, service_name: str, resource_id: str | None = None
    ) -> list[dict[str, Any]]:
        self._clear_last_error()
        target_service = service_name.strip()
        if not target_service:
            return []

        start_date, end_date = resource_usage_lookback_window()
        try:
            cost_rows = await self.get_cost_and_usage(
                start_date=start_date,
                end_date=end_date,
                granularity="DAILY",
            )
        except PLATFORM_RESOURCE_USAGE_RECOVERABLE_ERRORS as exc:
            self.last_error = str(exc)
            logger.warning(
                "platform_resource_usage_failed",
                service_name=target_service,
                resource_id=resource_id,
                error=str(exc),
            )
            return []

        return project_cost_rows_to_resource_usage(
            cost_rows=cost_rows,
            service_name=target_service,
            resource_id=resource_id,
            default_provider="platform",
            default_source_adapter="platform_cost_feed",
        )
