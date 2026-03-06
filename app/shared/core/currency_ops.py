from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP


def normalize_currency(value: str | None, default: str = "USD") -> str:
    return (value or default).strip().upper()


def convert_usd_to_ngn_subunits(
    usd_amount: float | Decimal, rate: float | Decimal
) -> int:
    ngn_amount = Decimal(str(usd_amount)) * Decimal(str(rate))
    return int(
        (ngn_amount * Decimal("100")).to_integral_value(rounding=ROUND_HALF_UP)
    )


def convert_to_usd_amount(amount: float | Decimal, rate: Decimal) -> Decimal:
    amount_dec = Decimal(str(amount))
    if rate <= 0:
        return amount_dec
    return amount_dec / rate


def format_currency_amount(amount: Decimal, currency: str) -> str:
    symbols = {"NGN": "₦", "USD": "$", "EUR": "€", "GBP": "£"}
    symbol = symbols.get(currency, f"{currency} ")
    return f"{symbol}{float(amount):,.2f}"
