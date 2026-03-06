from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Dict, cast
from uuid import UUID

from sqlalchemy import select

from app.models.invoice import ProviderInvoice


async def list_invoices_impl(
    service: Any,
    tenant_id: UUID,
    provider: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[ProviderInvoice]:
    normalized_provider = service._normalize_provider(provider) if provider else None
    stmt = select(ProviderInvoice).where(ProviderInvoice.tenant_id == tenant_id)
    if normalized_provider:
        stmt = stmt.where(ProviderInvoice.provider == normalized_provider)
    if start_date:
        stmt = stmt.where(ProviderInvoice.period_start >= start_date)
    if end_date:
        stmt = stmt.where(ProviderInvoice.period_end <= end_date)
    stmt = stmt.order_by(
        ProviderInvoice.period_start.desc(), ProviderInvoice.provider.asc()
    )
    result = await service.db.execute(stmt)
    return list(result.scalars().all())


async def get_invoice_impl(
    service: Any,
    tenant_id: UUID,
    invoice_id: UUID,
) -> ProviderInvoice | None:
    result = await service.db.execute(
        select(ProviderInvoice).where(
            ProviderInvoice.tenant_id == tenant_id,
            ProviderInvoice.id == invoice_id,
        )
    )
    return cast(ProviderInvoice | None, result.scalar_one_or_none())


async def upsert_invoice_impl(
    service: Any,
    tenant_id: UUID,
    *,
    provider: str,
    start_date: date,
    end_date: date,
    currency: str,
    total_amount: Decimal,
    invoice_number: str | None = None,
    status: str | None = None,
    notes: str | None = None,
) -> ProviderInvoice:
    normalized_provider = service._normalize_provider(provider)
    if start_date > end_date:
        raise ValueError("start_date must be <= end_date")

    currency_key = (currency or "USD").strip().upper() or "USD"
    total_amount_dec = Decimal(str(total_amount or 0))
    total_amount_usd = await service._invoice_total_to_usd(total_amount_dec, currency_key)

    existing_result = await service.db.execute(
        select(ProviderInvoice).where(
            ProviderInvoice.tenant_id == tenant_id,
            ProviderInvoice.provider == normalized_provider,
            ProviderInvoice.period_start == start_date,
            ProviderInvoice.period_end == end_date,
        )
    )
    invoice = existing_result.scalar_one_or_none()

    if invoice is None:
        invoice = ProviderInvoice(
            tenant_id=tenant_id,
            provider=normalized_provider,
            period_start=start_date,
            period_end=end_date,
        )
        service.db.add(invoice)

    invoice.invoice_number = invoice_number
    invoice.currency = currency_key
    invoice.total_amount = total_amount_dec
    invoice.total_amount_usd = total_amount_usd
    if status:
        invoice.status = str(status).strip().lower()
    if notes is not None:
        invoice.notes = notes

    await service.db.commit()
    await service.db.refresh(invoice)
    return cast(ProviderInvoice, invoice)


async def delete_invoice_impl(service: Any, tenant_id: UUID, invoice_id: UUID) -> bool:
    invoice = cast(ProviderInvoice | None, await service.get_invoice(tenant_id, invoice_id))
    if invoice is None:
        return False
    await service.db.delete(invoice)
    await service.db.commit()
    return True


async def update_invoice_status_impl(
    service: Any,
    tenant_id: UUID,
    invoice_id: UUID,
    *,
    status: str,
    notes: str | None = None,
) -> ProviderInvoice | None:
    invoice = await service.get_invoice(tenant_id, invoice_id)
    if invoice is None:
        return None
    invoice.status = str(status).strip().lower()
    if notes is not None:
        invoice.notes = notes
    await service.db.commit()
    await service.db.refresh(invoice)
    return cast(ProviderInvoice | None, invoice)


async def invoice_total_to_usd_impl(service: Any, amount: Decimal, currency: str) -> Decimal:
    currency_key = (currency or "USD").strip().upper()
    if currency_key == "USD":
        return amount

    try:
        from app.models.pricing import ExchangeRate
    except service.INVOICE_EXCHANGE_RATE_IMPORT_EXCEPTIONS:
        raise ValueError(
            "Exchange rate model unavailable; use USD currency for invoice totals."
        )

    rate_row = (
        await service.db.execute(
            select(ExchangeRate.rate).where(
                ExchangeRate.from_currency == "USD",
                ExchangeRate.to_currency == currency_key,
            )
        )
    ).first()
    if rate_row and rate_row[0]:
        rate_usd_to_currency = Decimal(str(rate_row[0]))
        if rate_usd_to_currency <= 0:
            raise ValueError(f"Invalid exchange rate for USD->{currency_key}.")
        return amount / rate_usd_to_currency

    inverse_row = (
        await service.db.execute(
            select(ExchangeRate.rate).where(
                ExchangeRate.from_currency == currency_key,
                ExchangeRate.to_currency == "USD",
            )
        )
    ).first()
    if inverse_row and inverse_row[0]:
        rate_currency_to_usd = Decimal(str(inverse_row[0]))
        if rate_currency_to_usd <= 0:
            raise ValueError(f"Invalid exchange rate for {currency_key}->USD.")
        return amount * rate_currency_to_usd

    raise ValueError(
        f"Missing exchange rate for invoice currency {currency_key}. "
        "Seed exchange_rates or provide invoice totals in USD."
    )


async def get_invoice_reconciliation_summary_impl(
    service: Any,
    *,
    tenant_id: UUID,
    provider: str,
    start_date: date,
    end_date: date,
    ledger_final_cost_usd: float,
    threshold_percent: float = 1.0,
) -> Dict[str, Any]:
    normalized_provider = service._normalize_provider(provider)
    invoice_result = await service.db.execute(
        select(ProviderInvoice).where(
            ProviderInvoice.tenant_id == tenant_id,
            ProviderInvoice.provider == normalized_provider,
            ProviderInvoice.period_start == start_date,
            ProviderInvoice.period_end == end_date,
        )
    )
    invoice = invoice_result.scalar_one_or_none()
    if invoice is None:
        return {
            "status": "missing_invoice",
            "provider": normalized_provider,
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
            },
            "ledger_final_cost_usd": float(ledger_final_cost_usd or 0.0),
            "threshold_percent": threshold_percent,
        }

    invoice_usd = float(invoice.total_amount_usd or 0)
    ledger_usd = float(ledger_final_cost_usd or 0.0)
    delta_usd = ledger_usd - invoice_usd
    abs_delta_usd = abs(delta_usd)
    denominator = invoice_usd if invoice_usd > 0 else max(ledger_usd, 1e-9)
    delta_percent = (abs_delta_usd / denominator) * 100.0 if denominator > 0 else 0.0
    matches = delta_percent <= float(threshold_percent or 0.0)

    payload = {
        "status": "match" if matches else "mismatch",
        "provider": normalized_provider,
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
        },
        "threshold_percent": float(threshold_percent),
        "invoice": {
            "id": str(invoice.id),
            "invoice_number": invoice.invoice_number,
            "currency": invoice.currency,
            "total_amount": float(invoice.total_amount or 0),
            "total_amount_usd": float(invoice.total_amount_usd or 0),
            "status": invoice.status,
            "notes": invoice.notes,
            "updated_at": invoice.updated_at.isoformat() if invoice.updated_at else None,
        },
        "ledger_final_cost_usd": float(ledger_usd),
        "delta_usd": float(delta_usd),
        "absolute_delta_usd": float(abs_delta_usd),
        "delta_percent": float(round(delta_percent, 4)),
    }
    payload["integrity_hash"] = service._stable_hash(payload)
    return payload
