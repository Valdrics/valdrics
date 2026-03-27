"""Shared runtime state and primitives for Paystack billing modules."""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Optional

import structlog

from app.shared.core.config import get_settings
from app.shared.core.security import decrypt_string as _decrypt_string
from app.shared.core.security import encrypt_string as _encrypt_string

logger = structlog.get_logger()
PAYSTACK_CHECKOUT_CURRENCY = "NGN"
PAYSTACK_FX_PROVIDER = "cbn_nfem"
PAYSTACK_USD_FX_PROVIDER = "native_usd"

encrypt_string = _encrypt_string
decrypt_string = _decrypt_string


class _SettingsProxy:
    """Resolve Paystack runtime settings lazily so config refreshes are honored."""

    def __getattr__(self, name: str):
        return getattr(get_settings(), name)

    def __setattr__(self, name: str, value) -> None:
        setattr(get_settings(), name, value)

    def __delattr__(self, name: str) -> None:
        delattr(get_settings(), name)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({get_settings()!r})"


settings = _SettingsProxy()


class SubscriptionStatus(str, Enum):
    """Paystack subscription statuses."""

    ACTIVE = "active"
    NON_RENEWING = "non-renewing"
    ATTENTION = "attention"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


def email_hash(email: Optional[str]) -> Optional[str]:
    if not email:
        return None
    return hashlib.sha256(email.strip().lower().encode()).hexdigest()[:12]
