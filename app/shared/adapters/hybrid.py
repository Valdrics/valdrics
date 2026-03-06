from __future__ import annotations

from collections.abc import AsyncGenerator, Awaitable, Callable
from datetime import date, datetime
from decimal import InvalidOperation
from typing import Any

import httpx
from pydantic import SecretStr
import structlog

from app.shared.adapters.base import BaseAdapter
from app.shared.adapters.feed_utils import as_float, is_number, parse_timestamp
from app.shared.adapters.http_retry import execute_with_http_retry
from app.shared.adapters.hybrid_native_mixin import HybridNativeConnectorMixin
from app.shared.adapters.resource_usage_projection import (
    discover_resources_from_cost_rows,
    project_cost_rows_to_resource_usage,
    resource_usage_lookback_window,
)
from app.shared.core.credentials import HybridCredentials
from app.shared.core.currency import convert_to_usd
from app.shared.core.exceptions import ExternalAPIError

logger = structlog.get_logger()

_NATIVE_TIMEOUT_SECONDS = 20.0
_NATIVE_MAX_RETRIES = 3
_RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}
_LEDGER_HTTP_VENDOR_ALIASES = {"ledger_http", "cmdb_ledger", "cmdb-ledger", "ledger"}
_OPENSTACK_VENDOR_ALIASES = {"openstack", "cloudkitty"}
_VMWARE_VENDOR_ALIASES = {"vmware", "vcenter", "vsphere"}
_DISCOVERY_RESOURCE_TYPE_ALIASES = {
    "all",
    "hybrid",
    "infrastructure",
    "resource",
    "resources",
    "system",
    "systems",
    "workload",
    "workloads",
}
HYBRID_RESOURCE_USAGE_RECOVERABLE_ERRORS: tuple[type[Exception], ...] = (
    ExternalAPIError,
    httpx.HTTPError,
    InvalidOperation,
    RuntimeError,
    TypeError,
    ValueError,
    KeyError,
)


async def _hybrid_get_request(
    *,
    url: str,
    headers: dict[str, str],
    params: dict[str, Any] | None,
    verify_ssl: bool,
) -> httpx.Response:
    async with httpx.AsyncClient(
        timeout=_NATIVE_TIMEOUT_SECONDS,
        verify=verify_ssl,
    ) as client:
        return await client.get(url, headers=headers, params=params)


class HybridAdapter(HybridNativeConnectorMixin, BaseAdapter):
    """
    Cloud+ adapter for private/hybrid infrastructure spend (on-prem, colo, private cloud).

    v1 is feed-based (manual/csv). Vendor-native pulls can be layered later for
    systems like VMware/VCF, OpenStack, or CMDB-backed ledgers.
    """

    def __init__(self, credentials: HybridCredentials):
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
        if self._vendor in _OPENSTACK_VENDOR_ALIASES:
            return "cloudkitty"
        if self._vendor in _VMWARE_VENDOR_ALIASES:
            return "vmware"
        return None

    def _resolve_api_key(self) -> str:
        token = self.credentials.api_key
        if token is None:
            raise ExternalAPIError("Missing API token for hybrid native connector")
        if isinstance(token, SecretStr):
            resolved = token.get_secret_value()
        elif isinstance(token, str):
            resolved = token
        else:
            raise ExternalAPIError("Missing API token for hybrid native connector")
        if not resolved or not resolved.strip():
            raise ExternalAPIError("Missing API token for hybrid native connector")
        return resolved.strip()

    def _resolve_api_secret(self) -> str:
        token = self.credentials.api_secret
        if token is None:
            raise ExternalAPIError("Missing API secret for hybrid native connector")
        if isinstance(token, SecretStr):
            resolved = token.get_secret_value()
        elif isinstance(token, str):
            resolved = token
        else:
            raise ExternalAPIError("Missing API secret for hybrid native connector")
        if not resolved or not resolved.strip():
            raise ExternalAPIError("Missing API secret for hybrid native connector")
        return resolved.strip()

    def _iter_month_starts(
        self, start_date: datetime, end_date: datetime
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

    def _resolve_verify_ssl(self) -> bool:
        raw = self._connector_config.get("verify_ssl")
        if isinstance(raw, bool):
            return raw
        raw = self._connector_config.get("ssl_verify")
        if isinstance(raw, bool):
            return raw
        return True

    def _native_timeout_seconds(self) -> float:
        return _NATIVE_TIMEOUT_SECONDS

    def _http_async_client(self, *, timeout: float, verify: bool) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=timeout, verify=verify)

    async def _convert_to_usd(self, amount_local: float, currency_code: str) -> float:
        return float(await convert_to_usd(amount_local, currency_code))

    def _resolve_native_verify_handler(
        self, native_vendor: str | None
    ) -> Callable[[], Awaitable[None]] | None:
        if native_vendor is None:
            return None
        handlers: dict[str, Callable[[], Awaitable[None]]] = {
            "ledger_http": self._verify_ledger_http,
            "cloudkitty": self._verify_cloudkitty,
            "vmware": self._verify_vmware,
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
            "cloudkitty": self._stream_cloudkitty_cost_and_usage,
            "vmware": self._stream_vmware_cost_and_usage,
        }
        return handlers.get(native_vendor)

    async def verify_connection(self) -> bool:
        self.last_error = None
        native_vendor = self._native_vendor
        if self._auth_method == "api_key" and native_vendor is None:
            supported = ", ".join(sorted(_LEDGER_HTTP_VENDOR_ALIASES))
            self.last_error = (
                f"Native Hybrid auth is not supported for vendor '{self._vendor}'. "
                f"Supported vendors: {supported}, openstack/cloudkitty, vmware/vcenter. "
                "Use auth_method manual/csv for custom vendors."
            )
            return False
        if self._auth_method not in {"manual", "csv", "api_key"}:
            self.last_error = (
                "Hybrid connector auth_method must be one of: manual, csv, api_key "
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
                    "hybrid_native_verify_failed", vendor=native_vendor, error=str(exc)
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
                    "hybrid_native_stream_failed_fallback_to_feed",
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
                or entry.get("system")
                or entry.get("vendor")
                or "Hybrid Infra"
            )
            usage_type = str(entry.get("usage_type") or "infrastructure")
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
                "provider": "hybrid",
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
                "source_adapter": "hybrid_feed",
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
            request=lambda: _hybrid_get_request(
                url=url,
                headers=headers,
                params=params,
                verify_ssl=self._resolve_verify_ssl(),
            ),
            url=url,
            max_retries=_NATIVE_MAX_RETRIES,
            retryable_status_codes=_RETRYABLE_STATUS_CODES,
            retry_http_status_log_event="hybrid_native_retry_http_status",
            retry_transport_log_event="hybrid_native_retry_transport_error",
            status_error_prefix="Hybrid request failed",
            transport_error_prefix="Hybrid request failed",
        )
        try:
            return response.json()
        except ValueError as exc:
            raise ExternalAPIError(
                "Hybrid request returned invalid JSON payload"
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
        except HYBRID_RESOURCE_USAGE_RECOVERABLE_ERRORS as exc:
            self.last_error = str(exc)
            logger.warning(
                "hybrid_discover_resources_failed",
                resource_type=resource_type,
                region=region,
                error=str(exc),
            )
            return []

        return discover_resources_from_cost_rows(
            cost_rows=cost_rows,
            resource_type=resource_type,
            supported_resource_types=_DISCOVERY_RESOURCE_TYPE_ALIASES,
            default_provider="hybrid",
            default_resource_type="hybrid_resource",
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
        except HYBRID_RESOURCE_USAGE_RECOVERABLE_ERRORS as exc:
            self.last_error = str(exc)
            logger.warning(
                "hybrid_resource_usage_failed",
                service_name=target_service,
                resource_id=resource_id,
                error=str(exc),
            )
            return []

        return project_cost_rows_to_resource_usage(
            cost_rows=cost_rows,
            service_name=target_service,
            resource_id=resource_id,
            default_provider="hybrid",
            default_source_adapter="hybrid_cost_feed",
        )
