from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field


class ExchangeRateUpdate(BaseModel):
    rate: float = Field(gt=0)
    provider: str = "manual"


class PricingPlanUpdate(BaseModel):
    price_usd: float = Field(gt=0)
    features: Optional[Dict[str, Any]] = None
    limits: Optional[Dict[str, Any]] = None


class CheckoutRequest(BaseModel):
    tier: str  # starter, growth, pro, enterprise
    billing_cycle: Literal["monthly", "annual"] = "monthly"
    currency: Optional[str] = None  # NGN (default), USD (feature-gated)
    callback_url: Optional[str] = None


class SubscriptionResponse(BaseModel):
    tier: str
    status: str
    next_payment_date: Optional[str] = None


class ConnectionUsageItem(BaseModel):
    connected: int
    limit: int | None
    remaining: int | None
    utilization_percent: float | None


class BillingUsageResponse(BaseModel):
    tier: str
    connections: Dict[str, ConnectionUsageItem]
    generated_at: str
