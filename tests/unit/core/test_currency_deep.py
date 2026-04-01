import time
from contextlib import asynccontextmanager
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.shared.core.currency import (
    ExchangeRateService,
    ExchangeRateUnavailableError,
    _RATES_CACHE,
    convert_usd,
    format_currency,
    get_exchange_rate,
    list_exchange_rates,
)


@pytest.fixture(autouse=True)
def clear_cache():
    _RATES_CACHE.clear()
    _RATES_CACHE["USD"] = (Decimal("1.0"), time.monotonic(), "internal")
    with patch("app.shared.core.cache.get_cache_service") as mock_cache_cls:
        mock_cache_cls.return_value.enabled = False
        yield


class TestCurrencyDeep:
    @pytest.mark.asyncio
    async def test_fetch_public_rates_success_from_db_cache(self):
        row = MagicMock()
        row.to_currency = "EUR"
        row.rate = 0.95
        result = MagicMock()
        result.scalars.return_value.all.return_value = [row]
        session = MagicMock()
        session.execute = AsyncMock(return_value=result)

        @asynccontextmanager
        async def fake_scope(self):
            yield session

        with patch.object(ExchangeRateService, "_session_scope", fake_scope):
            rates = await list_exchange_rates()
            assert rates["EUR"] == Decimal("0.95")

    @pytest.mark.asyncio
    async def test_fetch_public_rates_failure_falls_back_to_l1(self):
        _RATES_CACHE["EUR"] = (Decimal("0.91"), time.monotonic(), "internal")

        @asynccontextmanager
        async def broken_scope(self):
            raise RuntimeError("db down")
            yield  # pragma: no cover

        with patch.object(ExchangeRateService, "_session_scope", broken_scope):
            rates = await list_exchange_rates()
            assert rates["EUR"] == Decimal("0.91")

    @pytest.mark.asyncio
    async def test_fetch_ngn_rate_from_cbn_uses_latest_row(self):
        service = ExchangeRateService()
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = [
            {"ratedate": "January-26-2026", "weightedAvgRate": "1418.9522"},
            {"ratedate": "February-18-2026", "weightedAvgRate": "1338.1066"},
        ]
        mock_client = MagicMock()
        mock_client.get = AsyncMock(return_value=mock_response)

        with patch("app.shared.core.http.get_http_client", return_value=mock_client):
            rate = await service._fetch_ngn_from_cbn()
            assert rate == Decimal("1338.1066")

    @pytest.mark.asyncio
    async def test_get_exchange_rate_cached_l1(self):
        _RATES_CACHE["EUR"] = (Decimal("0.90"), time.monotonic(), "internal")
        rate = await get_exchange_rate("EUR")
        assert rate == Decimal("0.90")

    @pytest.mark.asyncio
    async def test_get_exchange_rate_l1_uses_monotonic_time_not_wall_clock(self):
        service = ExchangeRateService()
        _RATES_CACHE["EUR"] = (Decimal("0.90"), 1_000.0, "internal")

        with (
            patch("app.shared.core.currency.time.monotonic", return_value=1_400.5),
            patch("app.shared.core.currency.time.time", return_value=500.0),
            patch.object(
                service,
                "_read_redis_rate",
                new=AsyncMock(return_value=(None, None, None)),
            ),
            patch.object(
                service,
                "_read_db_rate",
                new=AsyncMock(return_value=(None, None, None)),
            ),
            patch.object(
                service,
                "_fetch_live_rate",
                new=AsyncMock(return_value=(Decimal("1.23"), "cbn_nfem")),
            ),
            patch.object(
                service,
                "_write_redis_rate",
                new=AsyncMock(return_value=None),
            ),
            patch.object(
                service,
                "_upsert_db_rate",
                new=AsyncMock(return_value=None),
            ),
        ):
            rate = await service.get_rate("EUR")

        assert rate == Decimal("1.23")

    @pytest.mark.asyncio
    async def test_get_exchange_rate_redis_hit(self):
        mock_cache = MagicMock()
        mock_cache.enabled = True
        mock_cache._get = AsyncMock(
            return_value={"rate": 1500.0, "updated_at": time.time()}
        )
        mock_cache._set = AsyncMock()

        with patch("app.shared.core.cache.get_cache_service", return_value=mock_cache):
            rate = await get_exchange_rate("NGN")
            assert rate == Decimal("1500.0")
            assert "NGN" in _RATES_CACHE

    @pytest.mark.asyncio
    async def test_get_exchange_rate_strict_failure_raises(self):
        service = ExchangeRateService()
        with (
            patch.object(
                service,
                "_read_db_rate",
                new=AsyncMock(return_value=(None, None, None)),
            ),
            patch.object(
                service,
                "_fetch_live_rate",
                new=AsyncMock(side_effect=RuntimeError("provider down")),
            ),
        ):
            with pytest.raises(ExchangeRateUnavailableError, match="unavailable"):
                await service.get_rate("NGN", strict=True)

    @pytest.mark.asyncio
    async def test_get_exchange_rate_total_failure_returns_one_non_strict(self):
        service = ExchangeRateService()
        with (
            patch.object(
                service,
                "_read_db_rate",
                new=AsyncMock(return_value=(None, None, None)),
            ),
            patch.object(
                service,
                "_fetch_live_rate",
                new=AsyncMock(side_effect=RuntimeError("provider down")),
            ),
        ):
            rate = await service.get_rate("UNKNOWN", strict=False)
            assert rate == Decimal("1.0")

    @pytest.mark.asyncio
    async def test_convert_usd_simple(self):
        with patch(
            "app.shared.core.currency.get_exchange_rate",
            AsyncMock(return_value=Decimal("1500.0")),
        ):
            converted = await convert_usd(10.0, "NGN")
            assert converted == Decimal("15000.0")

    @pytest.mark.asyncio
    async def test_format_currency_variants(self):
        with patch(
            "app.shared.core.currency.get_exchange_rate",
            AsyncMock(return_value=Decimal("1.0")),
        ):
            assert "$" in await format_currency(10, "USD")
            assert "₦" in await format_currency(10, "NGN")
            assert "€" in await format_currency(10, "EUR")
            assert "£" in await format_currency(10, "GBP")
            assert "ZAR" in await format_currency(10, "ZAR")

    @pytest.mark.asyncio
    async def test_get_exchange_rate_updates_redis(self):
        mock_cache = MagicMock()
        mock_cache.enabled = True
        mock_cache._get = AsyncMock(return_value=None)
        mock_cache._set = AsyncMock()

        with (
            patch("app.shared.core.cache.get_cache_service", return_value=mock_cache),
            patch.object(
                ExchangeRateService,
                "_read_db_rate",
                new=AsyncMock(return_value=(None, None, None)),
            ),
            patch.object(
                ExchangeRateService,
                "_fetch_live_rate",
                new=AsyncMock(return_value=(Decimal("1500.0"), "cbn_nfem")),
            ),
            patch.object(
                ExchangeRateService,
                "_upsert_db_rate",
                new=AsyncMock(return_value=None),
            ),
        ):
            rate = await get_exchange_rate("NGN")
            assert rate == Decimal("1500.0")
            assert mock_cache._set.called

    def test_exchange_rate_service_cache_ttl_hours_uses_live_settings(self):
        first_settings = MagicMock(EXCHANGE_RATE_SYNC_INTERVAL_HOURS=2)
        second_settings = MagicMock(EXCHANGE_RATE_SYNC_INTERVAL_HOURS=6)

        with patch(
            "app.shared.core.currency.get_settings",
            side_effect=[first_settings, second_settings],
        ):
            service = ExchangeRateService()
            assert service.cache_ttl_hours == 2
            assert service.cache_ttl_hours == 6
