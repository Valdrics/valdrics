import asyncio
import os
from datetime import datetime, timezone

import aiohttp
import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.pricing import ExchangeRate
from app.shared.core.config import get_settings
from app.shared.db.session import async_session_maker

logger = structlog.get_logger()

# Standardized BE-FIN-01: Automated Exchange Rate Management.
settings = get_settings()


def _default_currencies() -> set[str]:
    return set(get_settings().SUPPORTED_CURRENCIES)


def _exchange_rate_api_config() -> tuple[str, str]:
    api_key = str(os.environ.get("EXCHANGE_RATE_API_KEY") or "").strip()
    if api_key:
        return (
            f"https://v6.exchangerate-api.com/v6/{api_key}/latest/USD",
            "exchangerate-api",
        )
    return ("https://open.er-api.com/v6/latest/USD", "open.er-api")


async def update_exchange_rates():
    """
    Fetches latest exchange rates and updates the database.
    Standardizes BE-FIN-01: Automated Exchange Rate Management.
    """
    logger.info("exchange_rate_update_starting")

    try:
        api_url, provider = _exchange_rate_api_config()
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(api_url) as response:
                if response.status != 200:
                    raise RuntimeError(f"Exchange rate API error: {response.status}")
                data = await response.json()

        if data.get("result") != "success":
            raise RuntimeError(f"Exchange rate API failed: {data}")

        rates = data.get("conversion_rates") or data.get("rates") or {}
        if not rates:
            raise RuntimeError("Exchange rate API returned no rates")

        async with async_session_maker() as session:
            # Determine which currencies to update
            result = await session.execute(select(ExchangeRate))
            existing_rates = result.scalars().all()
            existing_map = {r.to_currency: r for r in existing_rates}
            target_currencies = set(existing_map.keys()) or _default_currencies()

            for currency in target_currencies:
                rate_val = rates.get(currency)
                if rate_val is None:
                    logger.warning("exchange_rate_missing_currency", currency=currency)
                    continue
                rate = float(rate_val)

                stmt = select(ExchangeRate).where(
                    ExchangeRate.from_currency == "USD",
                    ExchangeRate.to_currency == currency,
                )
                result = await session.execute(stmt)
                db_rate = result.scalar_one_or_none()

                if db_rate:
                    logger.info("updating_existing_rate", currency=currency, rate=rate)
                    db_rate.rate = rate
                    db_rate.provider = provider
                    db_rate.last_updated = datetime.now(timezone.utc)
                else:
                    logger.info("creating_new_rate", currency=currency, rate=rate)
                    new_rate = ExchangeRate(
                        from_currency="USD",
                        to_currency=currency,
                        rate=rate,
                        provider=provider,
                    )
                    session.add(new_rate)

            await session.commit()
            logger.info("exchange_rate_update_complete")

    except (
        aiohttp.ClientError,
        SQLAlchemyError,
        OSError,
        RuntimeError,
        TypeError,
        ValueError,
    ) as exc:
        logger.error("exchange_rate_update_failed", error=str(exc))
        raise RuntimeError("exchange_rate_update_failed") from exc


def main(argv: list[str] | None = None) -> int:
    del argv
    try:
        asyncio.run(update_exchange_rates())
    except RuntimeError:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
