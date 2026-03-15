from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Dict, Any
from app.shared.core.auth import get_current_user
from app.models.tenant import User
from app.shared.core.currency import ExchangeRateUnavailableError, get_exchange_rate
from app.shared.core.config import get_settings

router = APIRouter(tags=["Currency"])


@router.get("/rates")
async def get_all_rates(
    current_user: User = Depends(get_current_user),
) -> Dict[str, float]:
    """
    Returns all supported exchange rates against USD.
    Initializes from cache/external source if needed.
    """
    settings = get_settings()
    rates = {}

    for currency in settings.SUPPORTED_CURRENCIES:
        rate = await get_exchange_rate(currency)
        rates[currency] = float(rate)

    return rates


@router.get("/convert")
async def convert_currency(
    amount: float = Query(...),
    to: str = Query("NGN"),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Converts a USD amount to a target currency.
    """
    from app.shared.core.currency import convert_usd, format_currency

    target_currency = str(to).strip().upper()
    supported_currencies = {
        str(currency).strip().upper()
        for currency in get_settings().SUPPORTED_CURRENCIES
    }
    if target_currency not in supported_currencies:
        supported = ", ".join(sorted(supported_currencies))
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported target currency '{to}'. Use one of: {supported}",
        )

    try:
        converted_amount = await convert_usd(amount, target_currency, strict=True)
        formatted = await format_currency(amount, target_currency, strict=True)
    except ExchangeRateUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Exchange rate unavailable for {target_currency}: {exc}",
        ) from exc

    return {
        "original_amount_usd": amount,
        "converted_amount": float(converted_amount),
        "target_currency": target_currency,
        "formatted": formatted,
    }
