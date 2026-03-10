"""Runtime helper operations for Paystack billing service internals."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import re
from typing import Any


def to_decimal_usd(value: Any) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"Invalid USD amount: {value}") from exc
    if amount < 0:
        raise ValueError(f"Invalid USD amount: {value}")
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def usd_to_subunit_cents(amount_usd: Decimal) -> int:
    return int(
        (amount_usd * Decimal("100")).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    )


def resolve_checkout_currency(
    requested_currency: str | None,
    *,
    settings: Any,
    default_checkout_currency: str,
) -> str:
    default_currency = str(
        getattr(
            settings,
            "PAYSTACK_DEFAULT_CHECKOUT_CURRENCY",
            default_checkout_currency,
        )
        or default_checkout_currency
    ).strip().upper()
    if default_currency not in {"NGN", "USD"}:
        default_currency = default_checkout_currency

    resolved = (
        str(requested_currency).strip().upper()
        if isinstance(requested_currency, str) and requested_currency.strip()
        else default_currency
    )
    if resolved == "USD" and not bool(
        getattr(settings, "PAYSTACK_ENABLE_USD_CHECKOUT", False)
    ):
        raise ValueError("USD checkout is not enabled")
    if resolved not in {"NGN", "USD"}:
        raise ValueError(f"Unsupported checkout currency: {resolved}")
    return resolved


def build_charge_reference(
    *,
    subscription_id: Any,
    charge_kind: str,
    sequence: Any,
) -> str:
    raw_kind = re.sub(r"[^a-z0-9]+", "-", str(charge_kind or "").strip().lower())
    normalized_kind = raw_kind.strip("-") or "charge"
    normalized_sequence = re.sub(r"[^a-z0-9]+", "-", str(sequence or "").strip().lower())
    normalized_sequence = normalized_sequence.strip("-") or "1"
    fingerprint = hashlib.sha256(
        f"{subscription_id}:{normalized_kind}:{normalized_sequence}".encode("utf-8")
    ).hexdigest()[:20]
    return (
        f"valdrics-{normalized_kind[:18]}-{normalized_sequence[:24]}-{fingerprint}"
    )[:96]


def parse_paystack_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def infer_interval_days(charge_data: dict[str, Any]) -> int:
    interval_raw: Any = None
    plan_data = charge_data.get("plan")
    if isinstance(plan_data, dict):
        interval_raw = plan_data.get("interval")
    if interval_raw is None:
        metadata = charge_data.get("metadata")
        if isinstance(metadata, dict):
            interval_raw = metadata.get("billing_cycle")

    interval = str(interval_raw or "").strip().lower()
    if interval in {"annual", "annually", "year", "yearly"}:
        return 365
    return 30


def _coerce_optional_datetime(value: Any) -> datetime | None:
    return value if isinstance(value, datetime) else None


def _require_datetime(value: Any, *, field_name: str) -> datetime:
    if not isinstance(value, datetime):
        raise TypeError(f"{field_name} must resolve to a datetime")
    return value


async def fetch_provider_next_payment_date(
    subscription: Any,
    *,
    client: Any,
    parse_paystack_datetime_fn: Any,
    logger: Any,
    runtime_recoverable_errors: tuple[type[Exception], ...],
) -> datetime | None:
    code_raw = getattr(subscription, "paystack_subscription_code", None)
    if not isinstance(code_raw, str) or not code_raw.strip():
        return None

    try:
        provider_payload = await client.fetch_subscription(code_raw.strip())
    except runtime_recoverable_errors as exc:
        logger.warning(
            "renewal_fetch_subscription_failed",
            tenant_id=str(subscription.tenant_id),
            subscription_code=code_raw,
            error=str(exc),
        )
        return None

    if not isinstance(provider_payload, dict):
        return None
    data = provider_payload.get("data")
    if not isinstance(data, dict):
        return None

    for raw_value in (
        data.get("next_payment_date"),
        data.get("next_payment"),
        data.get("current_period_end"),
    ):
        parsed_value = _coerce_optional_datetime(parse_paystack_datetime_fn(raw_value))
        if parsed_value is not None:
            return parsed_value
    return None


def compute_fallback_next_payment_date(
    subscription: Any,
    interval_days: int,
) -> datetime:
    now = datetime.now(timezone.utc)
    anchor = getattr(subscription, "next_payment_date", None)
    if isinstance(anchor, datetime):
        anchor_utc = anchor if anchor.tzinfo else anchor.replace(tzinfo=timezone.utc)
        if anchor_utc < now - timedelta(days=interval_days):
            anchor_utc = now
    else:
        anchor_utc = now

    candidate = anchor_utc + timedelta(days=interval_days)
    if candidate <= now:
        candidate = now + timedelta(days=interval_days)
    return candidate


async def resolve_renewal_next_payment_date(
    subscription: Any,
    charge_data: dict[str, Any],
    *,
    fetch_provider_next_payment_date_fn: Any,
    parse_paystack_datetime_fn: Any,
    infer_interval_days_fn: Any,
    compute_fallback_next_payment_date_fn: Any,
) -> datetime:
    provider_next_payment = _coerce_optional_datetime(
        await fetch_provider_next_payment_date_fn(subscription)
    )
    if provider_next_payment is not None:
        return provider_next_payment

    payload_next_payment = _coerce_optional_datetime(
        parse_paystack_datetime_fn(charge_data.get("next_payment_date"))
    )
    if payload_next_payment is not None:
        return payload_next_payment

    interval_days = infer_interval_days_fn(charge_data)
    return _require_datetime(
        compute_fallback_next_payment_date_fn(subscription, interval_days),
        field_name="next_payment_date",
    )
