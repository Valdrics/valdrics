from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_job import JobType
from app.modules.governance.domain.jobs.processor import enqueue_job
from app.shared.core.config import get_settings
from app.shared.db.session import get_db
from app.shared.core.proxy_headers import resolve_client_ip
from app.shared.core.rate_limit import rate_limit
from app.shared.core.webhooks import validate_webhook_url

logger = structlog.get_logger()
router = APIRouter(tags=["Public"])

MARKETING_SUBSCRIBE_RECOVERABLE_EXCEPTIONS = (
    RuntimeError,
    TypeError,
    ValueError,
    ConnectionError,
    TimeoutError,
    OSError,
    SQLAlchemyError,
)


class MarketingSubscribeRequest(BaseModel):
    email: EmailStr
    company: str | None = Field(default=None, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    referrer: str | None = Field(default=None, max_length=200)
    honey: str | None = Field(default=None, max_length=120)

    model_config = ConfigDict(extra="forbid")


class MarketingSubscribeResponse(BaseModel):
    ok: bool
    accepted: bool | None = None
    emailHash: str | None = None
    error: str | None = None

    model_config = ConfigDict(extra="forbid")


def _hash_email_for_public_flow(email: str) -> str:
    return hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()


def _build_marketing_subscribe_job_payload(
    payload: MarketingSubscribeRequest,
) -> dict[str, object]:
    settings = get_settings()
    webhook_url = str(
        getattr(settings, "MARKETING_SUBSCRIBE_WEBHOOK_URL", "") or ""
    ).strip()
    if not webhook_url:
        raise RuntimeError(
            "MARKETING_SUBSCRIBE_WEBHOOK_URL must be configured for marketing subscribe delivery"
        )

    allowlist = {
        str(domain).strip().lower()
        for domain in getattr(settings, "WEBHOOK_ALLOWED_DOMAINS", [])
        if str(domain).strip()
    }
    if not allowlist:
        raise RuntimeError(
            "WEBHOOK_ALLOWED_DOMAINS must be configured before enabling marketing subscribe delivery"
        )

    validate_webhook_url(
        url=webhook_url,
        allowlist=allowlist,
        require_https=bool(getattr(settings, "WEBHOOK_REQUIRE_HTTPS", True)),
        block_private_ips=bool(getattr(settings, "WEBHOOK_BLOCK_PRIVATE_IPS", True)),
    )

    return {
        "provider": "marketing_subscribe",
        "url": webhook_url,
        "data": {
            "email": str(payload.email).strip().lower(),
            "company": payload.company,
            "role": payload.role,
            "referrer": payload.referrer,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "headers": {"Content-Type": "application/json"},
    }


@router.post("/marketing/subscribe", response_model=MarketingSubscribeResponse, status_code=202)
@rate_limit("8/minute")
async def marketing_subscribe(
    request: Request,
    payload: MarketingSubscribeRequest,
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    email_hash = _hash_email_for_public_flow(str(payload.email))
    if payload.honey:
        return JSONResponse(
            status_code=202,
            content={"ok": True, "accepted": True},
        )

    try:
        job_payload = _build_marketing_subscribe_job_payload(payload)
        await enqueue_job(
            db=db,
            job_type=JobType.WEBHOOK_RETRY,
            payload=job_payload,
            max_attempts=5,
        )
    except MARKETING_SUBSCRIBE_RECOVERABLE_EXCEPTIONS as exc:
        logger.error(
            "marketing_subscribe_enqueue_failed",
            email_hash=email_hash,
            client_ip=resolve_client_ip(request, settings_obj=get_settings()),
            error=str(exc),
        )
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "delivery_failed"},
        )

    return JSONResponse(
        status_code=202,
        content={"ok": True, "accepted": True, "emailHash": email_hash},
    )
