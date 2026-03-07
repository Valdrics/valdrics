from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schemas.costs import CloudUsageSummary, CostRecord
from app.shared.core.credentials import AWSCredentials


def _async_cm(value: object) -> MagicMock:
    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=value)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


class _AsyncBody:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = list(chunks)

    async def __aenter__(self) -> "_AsyncBody":
        return self

    async def __aexit__(self, _exc_type, _exc, _tb) -> None:
        return None

    async def read(self, _size: int) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""


class _ReadBody:
    def __init__(self, payload: bytes) -> None:
        self._payload = payload

    async def read(self) -> bytes:
        return self._payload


class _Paginator:
    def __init__(self, pages_by_prefix: dict[str, list[dict[str, object]]]) -> None:
        self._pages_by_prefix = pages_by_prefix

    def paginate(self, *, Bucket: str, Prefix: str):  # noqa: N803
        _ = Bucket
        pages = self._pages_by_prefix.get(Prefix, [])

        async def _aiter():
            for page in pages:
                yield page

        return _aiter()


@pytest.fixture
def mock_creds() -> AWSCredentials:
    return AWSCredentials(
        account_id="123456789012",
        role_arn="arn:aws:iam::123456789012:role/ValdricsRole",
        external_id="ext-id",
        region="us-east-1",
    )


def _summary_with_records(records: list[CostRecord], total: Decimal) -> CloudUsageSummary:
    return CloudUsageSummary(
        tenant_id="tenant",
        provider="aws",
        start_date=date(2026, 2, 1),
        end_date=date(2026, 2, 2),
        total_cost=total,
        records=records,
        by_service={"svc": total},
        by_region={"us-east-1": total},
        by_tag={"team": {"core": total}},
    )
