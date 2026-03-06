from __future__ import annotations

import asyncio
from datetime import date, datetime

import pandas as pd
import pytest

from app.shared.adapters import aws_cur_ingestion_ops
from app.shared.adapters import aws_cur_parquet_ops
from app.shared.adapters import hybrid_native_mixin
from app.shared.adapters import platform_native_mixin
from app.shared.adapters import saas_native_stream_ops
from app.shared.core.exceptions import ExternalAPIError


class _HybridDummy(hybrid_native_mixin.HybridNativeConnectorMixin):
    def __init__(self, connector_config: dict[str, object]) -> None:
        self._connector_config = connector_config


class _PlatformDummy(platform_native_mixin.PlatformNativeConnectorMixin):
    pass


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = payload

    def json(self) -> object:
        return self._payload


def test_aws_cur_ingestion_next_month_rollover() -> None:
    assert aws_cur_ingestion_ops._next_month(date(2026, 1, 1)) == date(2026, 2, 1)
    assert aws_cur_ingestion_ops._next_month(date(2026, 12, 1)) == date(2027, 1, 1)


def test_aws_cur_ingestion_normalize_rows_for_projection() -> None:
    rows = [
        {
            "service": "AmazonEC2",
            "region": "us-east-1",
            "line_item_resource_id": "i-123",
            "line_item_usage_amount": 10,
            "cost_usd": 3.5,
            "tags": {"env": "prod"},
        },
        "skip-me",
    ]
    normalized = aws_cur_ingestion_ops.normalize_rows_for_projection(rows)
    assert len(normalized) == 1
    assert normalized[0]["provider"] == "aws"
    assert normalized[0]["resource_id"] == "i-123"
    assert normalized[0]["tags"] == {"env": "prod"}


def test_aws_cur_parquet_extract_cur_tags_from_prefixes() -> None:
    row = pd.Series(
        {
            "resourceTags/user:team": "finops",
            "resource_tags_user_env": "staging",
            "other": "value",
        }
    )
    tags = aws_cur_parquet_ops.extract_cur_tags(row)
    assert tags == {"team": "finops", "env": "staging"}


def test_hybrid_native_mixin_resolve_openstack_auth_url_variants() -> None:
    assert _HybridDummy({"auth_url": "https://keystone.example/v3"})._resolve_openstack_auth_url() == (
        "https://keystone.example/v3/auth/tokens"
    )
    assert _HybridDummy(
        {"auth_url": "https://keystone.example/v3/auth/tokens"}
    )._resolve_openstack_auth_url() == "https://keystone.example/v3/auth/tokens"
    with pytest.raises(ExternalAPIError):
        _HybridDummy({"auth_url": "not-a-url"})._resolve_openstack_auth_url()


def test_platform_native_mixin_extract_billable_usage_metrics() -> None:
    payload = {
        "billable_usage": [
            {"billing_dimension": "host", "usage": 12, "unit": "hour"},
            {"metric": "container", "quantity": 7},
        ]
    }
    metrics = _PlatformDummy()._extract_billable_usage_metrics(payload)
    assert metrics == [("host", 12.0, "hour"), ("container", 7.0, None)]


def test_saas_native_get_json_rejects_non_object_payload() -> None:
    async def _request_fn(
        url: str,
        headers: dict[str, str],
        params: dict[str, object] | None,
    ) -> _FakeResponse:
        del url, headers, params
        return _FakeResponse(payload=["not", "a", "dict"])

    async def _execute_with_http_retry_fn(
        *,
        request,
        url: str,
        max_retries: int,
        retryable_status_codes: set[int],
        retry_http_status_log_event: str,
        retry_transport_log_event: str,
        status_error_prefix: str,
        transport_error_prefix: str,
    ) -> _FakeResponse:
        del (
            url,
            max_retries,
            retryable_status_codes,
            retry_http_status_log_event,
            retry_transport_log_event,
            status_error_prefix,
            transport_error_prefix,
        )
        return await request()

    with pytest.raises(ExternalAPIError, match="invalid payload shape"):
        asyncio.run(
            saas_native_stream_ops.get_json(
                url="https://api.vendor.test/v1/usage",
                headers={},
                params=None,
                request_fn=_request_fn,
                execute_with_http_retry_fn=_execute_with_http_retry_fn,
                max_retries=1,
                retryable_status_codes={429, 500},
            )
        )


def test_platform_native_mixin_iter_month_starts() -> None:
    dummy = _PlatformDummy()
    starts = dummy._iter_month_starts(
        datetime(2026, 1, 15),
        datetime(2026, 3, 2),
    )
    assert starts == [date(2026, 1, 1), date(2026, 2, 1), date(2026, 3, 1)]
