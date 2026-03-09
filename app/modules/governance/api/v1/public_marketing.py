from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_job import JobType
from app.models.public_sales_inquiry import PublicSalesInquiry
from app.modules.governance.domain.jobs.processor import enqueue_job
from app.modules.notifications.domain.email_service import get_operational_email_service
from app.shared.core.config import get_settings
from app.shared.db.session import get_db
from app.shared.core.proxy_headers import resolve_client_ip
from app.shared.core.rate_limit import rate_limit
from app.shared.core.turnstile import require_turnstile_for_public_sales_intake
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
PUBLIC_SALES_INQUIRY_RECOVERABLE_EXCEPTIONS = MARKETING_SUBSCRIBE_RECOVERABLE_EXCEPTIONS
PUBLIC_SALES_INQUIRY_DEDUPLICATION_WINDOW = timedelta(minutes=15)


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


class PublicSalesInquiryRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr
    company: str = Field(min_length=1, max_length=120)
    role: str | None = Field(default=None, max_length=120)
    teamSize: (
        Literal["1-5", "6-20", "21-50", "51-200", "201-1000", "1000+"] | None
    ) = None
    deploymentScope: str | None = Field(default=None, max_length=200)
    timeline: (
        Literal["this_month", "this_quarter", "next_quarter", "evaluating"] | None
    ) = None
    interestArea: (
        Literal[
            "plan_fit",
            "security_review",
            "procurement",
            "multi_cloud",
            "greenops",
            "saas_governance",
            "executive_briefing",
        ]
        | None
    ) = None
    message: str | None = Field(default=None, max_length=2000)
    referrer: str | None = Field(default=None, max_length=200)
    source: str | None = Field(default=None, max_length=120)
    utmSource: str | None = Field(default=None, max_length=120)
    utmMedium: str | None = Field(default=None, max_length=120)
    utmCampaign: str | None = Field(default=None, max_length=120)
    honey: str | None = Field(default=None, max_length=120)

    model_config = ConfigDict(extra="forbid")


class PublicSalesInquiryResponse(BaseModel):
    ok: bool
    accepted: bool | None = None
    inquiryId: str | None = None
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
            "company": _normalize_optional_text(payload.company),
            "role": _normalize_optional_text(payload.role),
            "referrer": _normalize_optional_text(payload.referrer),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "headers": {"Content-Type": "application/json"},
    }


def _normalize_optional_text(value: str | None) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalized_public_sales_inquiry_payload(
    payload: PublicSalesInquiryRequest,
) -> dict[str, str | None]:
    return {
        "name": _normalize_optional_text(payload.name),
        "email": str(payload.email).strip().lower(),
        "company": _normalize_optional_text(payload.company),
        "role": _normalize_optional_text(payload.role),
        "teamSize": _normalize_optional_text(payload.teamSize),
        "deploymentScope": _normalize_optional_text(payload.deploymentScope),
        "timeline": _normalize_optional_text(payload.timeline),
        "interestArea": _normalize_optional_text(payload.interestArea),
        "message": _normalize_optional_text(payload.message),
        "referrer": _normalize_optional_text(payload.referrer),
        "source": _normalize_optional_text(payload.source),
        "utmSource": _normalize_optional_text(payload.utmSource),
        "utmMedium": _normalize_optional_text(payload.utmMedium),
        "utmCampaign": _normalize_optional_text(payload.utmCampaign),
    }


def _build_public_sales_inquiry_fingerprint(
    normalized_payload: dict[str, str | None],
) -> str:
    dedupe_payload = {
        key: normalized_payload.get(key)
        for key in (
            "name",
            "email",
            "company",
            "role",
            "teamSize",
            "deploymentScope",
            "timeline",
            "interestArea",
            "message",
        )
    }
    return hashlib.sha256(
        json.dumps(dedupe_payload, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    ).hexdigest()


def _public_sales_inquiry_lock_id(fingerprint: str) -> int:
    raw = int(hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16], 16)
    return raw if raw < 2**63 else raw - 2**64


async def _acquire_public_sales_inquiry_lock(
    db: AsyncSession, fingerprint: str
) -> None:
    bind = db.get_bind()
    dialect_name = str(getattr(getattr(bind, "dialect", None), "name", "") or "").lower()
    if dialect_name != "postgresql":
        return
    await db.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": _public_sales_inquiry_lock_id(fingerprint)},
    )


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


@router.post(
    "/marketing/talk-to-sales",
    response_model=PublicSalesInquiryResponse,
    status_code=202,
)
@rate_limit("6/hour")
async def public_sales_inquiry(
    request: Request,
    payload: PublicSalesInquiryRequest,
    _: None = Depends(require_turnstile_for_public_sales_intake),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    normalized_payload = _normalized_public_sales_inquiry_payload(payload)
    email = normalized_payload["email"] or ""
    email_hash = _hash_email_for_public_flow(email)
    if payload.honey:
        return JSONResponse(
            status_code=202,
            content={"ok": True, "accepted": True},
        )

    client_ip = resolve_client_ip(request, settings_obj=get_settings())
    try:
        # Fail fast when delivery infrastructure is not configured.
        get_operational_email_service()

        fingerprint = _build_public_sales_inquiry_fingerprint(normalized_payload)
        await _acquire_public_sales_inquiry_lock(db, fingerprint)
        duplicate_threshold = datetime.now(timezone.utc) - (
            PUBLIC_SALES_INQUIRY_DEDUPLICATION_WINDOW
        )
        duplicate = (
            await db.execute(
                select(PublicSalesInquiry)
                .where(
                    PublicSalesInquiry.inquiry_fingerprint == fingerprint,
                    PublicSalesInquiry.created_at >= duplicate_threshold,
                )
                .order_by(PublicSalesInquiry.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            logger.info(
                "public_sales_inquiry_deduplicated",
                inquiry_id=str(duplicate.id),
                email_hash=duplicate.email_hash,
                client_ip=client_ip,
            )
            return JSONResponse(
                status_code=202,
                content={
                    "ok": True,
                    "accepted": True,
                    "inquiryId": str(duplicate.id),
                    "emailHash": duplicate.email_hash,
                },
            )

        inquiry = PublicSalesInquiry(
            name=normalized_payload["name"] or "",
            email=email,
            company=normalized_payload["company"] or "",
            role=normalized_payload["role"],
            email_hash=email_hash,
            inquiry_fingerprint=fingerprint,
            team_size=normalized_payload["teamSize"],
            deployment_scope=normalized_payload["deploymentScope"],
            timeline=normalized_payload["timeline"],
            interest_area=normalized_payload["interestArea"],
            message=normalized_payload["message"],
            referrer=normalized_payload["referrer"],
            source=normalized_payload["source"],
            utm_source=normalized_payload["utmSource"],
            utm_medium=normalized_payload["utmMedium"],
            utm_campaign=normalized_payload["utmCampaign"],
            delivery_status="pending",
            delivery_attempts=0,
        )
        db.add(inquiry)
        await db.flush()
        await enqueue_job(
            db=db,
            job_type=JobType.NOTIFICATION,
            payload={
                "provider": "sales_intake_email",
                "inquiry_id": str(inquiry.id),
                "email_hash": email_hash,
            },
            max_attempts=5,
            deduplication_key=f"public_sales_inquiry_delivery:{inquiry.id}",
        )
    except PUBLIC_SALES_INQUIRY_RECOVERABLE_EXCEPTIONS as exc:
        await db.rollback()
        logger.error(
            "public_sales_inquiry_enqueue_failed",
            email_hash=email_hash,
            client_ip=client_ip,
            error=str(exc),
        )
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "delivery_failed"},
        )

    logger.info(
        "public_sales_inquiry_accepted",
        inquiry_id=str(inquiry.id),
        email_hash=email_hash,
        client_ip=client_ip,
    )
    return JSONResponse(
        status_code=202,
        content={
            "ok": True,
            "accepted": True,
            "inquiryId": str(inquiry.id),
            "emailHash": email_hash,
        },
    )
