"""
Webhook Retry Service - Revenue Protection (Tier 2)

Provides durable webhook processing using background_jobs infrastructure:
- Store failed webhooks for automatic retry
- Idempotency keys to prevent duplicate processing
- Exponential backoff on failures

Usage:
    service = WebhookRetryService(db)

    # Store webhook for processing (idempotent)
    job = await service.store_webhook(
        provider="paystack",
        event_type="charge.success",
        payload=data,
        idempotency_key=reference
    )

    # Process webhook (called by JobProcessor)
    result = await service.process_webhook(job_id)
"""

from datetime import datetime, timezone, timedelta
import inspect
from typing import Optional, Dict, Any
import hashlib
import json
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_job import BackgroundJob, JobStatus, JobType
from app.modules.governance.domain.jobs.errors import (
    JobExecutionError,
    PermanentJobError,
)
from app.modules.governance.domain.jobs.processor import (
    JOB_LOCK_TIMEOUT_MINUTES,
    enqueue_job,
)
from app.shared.core.config import get_settings

logger = structlog.get_logger()
PAYSTACK_STORED_PAYLOAD_PARSE_RECOVERABLE_EXCEPTIONS = (
    json.JSONDecodeError,
    UnicodeError,
    TypeError,
    ValueError,
    AttributeError,
)

# Webhook configuration
WEBHOOK_MAX_ATTEMPTS = 5  # More retries for revenue-critical
# L5: Now configurable via settings
WEBHOOK_IDEMPOTENCY_TTL_HOURS = get_settings().WEBHOOK_IDEMPOTENCY_TTL_HOURS


class WebhookRetryableError(JobExecutionError):
    """Webhook failure that should be retried by the background job processor."""


class WebhookPermanentError(PermanentJobError):
    """Webhook failure that should be sent to dead letter immediately."""


class WebhookRetryService:
    """
    Durable webhook processing with retry and idempotency.

    Revenue Protection Features:
    - Webhooks are stored before processing (survives crashes)
    - Automatic retry with exponential backoff
    - Idempotency prevents duplicate subscription activations
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _job_status_value(job: BackgroundJob) -> str:
        return job.status.value if hasattr(job.status, "value") else str(job.status)

    @staticmethod
    def _normalize_datetime(value: Any) -> datetime | None:
        if not isinstance(value, datetime):
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    def _generate_idempotency_key(
        self, provider: str, event_type: str, reference: str
    ) -> str:
        """Generate idempotency key from webhook data."""
        data = f"{provider}:{event_type}:{reference}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    @staticmethod
    def _resolve_reference(
        *, payload: Dict[str, Any], reference: Optional[str]
    ) -> str:
        """
        Resolve a stable reference for webhook idempotency.

        Priority:
        1) Explicit `reference` argument
        2) Payload-native identifiers (`data.reference`, `data.id`, `id`, `event_id`)
        3) Deterministic payload hash fallback
        """
        explicit_ref = str(reference or "").strip()
        if explicit_ref:
            return explicit_ref

        data = payload.get("data", {})
        if isinstance(data, dict):
            for key in ("reference", "id"):
                value = data.get(key)
                if value is None:
                    continue
                normalized = str(value).strip()
                if normalized:
                    return normalized

        for key in ("id", "event_id"):
            value = payload.get(key)
            if value is None:
                continue
            normalized = str(value).strip()
            if normalized:
                return normalized

        payload_fingerprint = hashlib.sha256(
            json.dumps(
                payload, sort_keys=True, separators=(",", ":"), default=str
            ).encode("utf-8")
        ).hexdigest()
        return f"payload_sha256:{payload_fingerprint[:24]}"

    async def is_duplicate(self, idempotency_key: str) -> bool:
        """Check if webhook was already processed successfully."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=WEBHOOK_IDEMPOTENCY_TTL_HOURS)
        result = await self.db.execute(
            select(BackgroundJob).where(
                BackgroundJob.job_type == JobType.WEBHOOK_RETRY,
                BackgroundJob.payload["idempotency_key"].as_string() == idempotency_key,
                BackgroundJob.status == JobStatus.COMPLETED,
                BackgroundJob.completed_at >= cutoff,
            )
        )

        existing = result.scalar_one_or_none()
        return existing is not None

    def _completed_within_ttl(self, job: BackgroundJob, *, now: datetime) -> bool:
        terminal_time = (
            self._normalize_datetime(getattr(job, "completed_at", None))
            or self._normalize_datetime(getattr(job, "updated_at", None))
            or self._normalize_datetime(getattr(job, "created_at", None))
        )
        if terminal_time is None:
            return False
        cutoff = now - timedelta(hours=WEBHOOK_IDEMPOTENCY_TTL_HOURS)
        return terminal_time >= cutoff

    def _is_stale_running(self, job: BackgroundJob, *, now: datetime) -> bool:
        started_at = self._normalize_datetime(getattr(job, "started_at", None))
        if started_at is None:
            return False
        cutoff = now - timedelta(minutes=JOB_LOCK_TIMEOUT_MINUTES)
        return started_at <= cutoff

    async def _reload_existing_job_for_update(self, job_id: Any) -> BackgroundJob | None:
        result = await self.db.execute(
            select(BackgroundJob)
            .where(BackgroundJob.id == job_id)
            .with_for_update()
        )
        job = result.scalar_one_or_none()
        if inspect.isawaitable(job):
            job = await job
        if job is None or not hasattr(job, "status"):
            return None
        return job

    async def _requeue_existing_job(
        self,
        job: BackgroundJob,
        *,
        reason: str,
        reset_attempts: bool,
    ) -> BackgroundJob:
        now = datetime.now(timezone.utc)
        if reset_attempts:
            job.attempts = 0
        job.status = JobStatus.PENDING.value
        job.scheduled_for = now
        job.started_at = None
        job.completed_at = None
        job.error_message = None
        job.result = {
            "status": "requeued",
            "reason": reason,
            "requeued_at": now.isoformat(),
        }
        await self.db.commit()
        setattr(job, "_enqueue_created", False)
        return job

    async def store_webhook(
        self,
        provider: str,
        event_type: str,
        payload: Dict[str, Any],
        reference: Optional[str] = None,
        signature: Optional[str] = None,
        raw_payload: Optional[str] = None,
    ) -> Optional[BackgroundJob]:
        """
        Store webhook for durable processing.

        Args:
            provider: Webhook source (e.g., "paystack", "stripe")
            event_type: Event type (e.g., "charge.success")
            payload: Full webhook payload
            reference: Unique reference for idempotency (e.g., transaction ref)

        Returns:
            BackgroundJob if new, None if duplicate
        """
        # Generate idempotency key
        ref = self._resolve_reference(payload=payload, reference=reference)
        idempotency_key = self._generate_idempotency_key(provider, event_type, ref)

        # Store new webhook job
        job_payload = {
            "provider": provider,
            "event_type": event_type,
            "payload": payload,
            "idempotency_key": idempotency_key,
            "reference": ref,
            "signature": signature,
            "raw_payload": raw_payload,
        }

        job = await enqueue_job(
            db=self.db,
            job_type=JobType.WEBHOOK_RETRY,
            payload=job_payload,
            max_attempts=WEBHOOK_MAX_ATTEMPTS,
            deduplication_key=f"webhook:{provider}:{idempotency_key}",
        )

        created = bool(getattr(job, "_enqueue_created", True))
        if not created:
            existing = await self._reload_existing_job_for_update(job.id)
            if existing is None:
                existing = job

            now = datetime.now(timezone.utc)
            job_status = self._job_status_value(existing)
            if job_status == JobStatus.COMPLETED.value and self._completed_within_ttl(
                existing, now=now
            ):
                logger.info(
                    "webhook_duplicate_ignored",
                    job_id=str(existing.id),
                    provider=provider,
                    event_type=event_type,
                    idempotency_key=idempotency_key,
                    status=job_status,
                )
                return None

            if job_status == JobStatus.PENDING.value:
                logger.info(
                    "webhook_already_queued",
                    job_id=str(existing.id),
                    provider=provider,
                    event_type=event_type,
                    idempotency_key=idempotency_key,
                    status=job_status,
                )
                return None

            if job_status == JobStatus.RUNNING.value and not self._is_stale_running(
                existing, now=now
            ):
                logger.info(
                    "webhook_already_running",
                    job_id=str(existing.id),
                    provider=provider,
                    event_type=event_type,
                    idempotency_key=idempotency_key,
                    status=job_status,
                )
                return None

            requeue_reason = "duplicate_redelivery_requeued"
            reset_attempts = job_status in {
                JobStatus.COMPLETED.value,
                JobStatus.FAILED.value,
                JobStatus.DEAD_LETTER.value,
            }
            if job_status == JobStatus.COMPLETED.value:
                requeue_reason = "dedupe_ttl_expired"
            elif job_status == JobStatus.RUNNING.value:
                requeue_reason = "stale_running_redelivery"
                reset_attempts = False
            existing = await self._requeue_existing_job(
                existing,
                reason=requeue_reason,
                reset_attempts=reset_attempts,
            )
            logger.info(
                "webhook_requeued_existing_job",
                job_id=str(existing.id),
                provider=provider,
                event_type=event_type,
                idempotency_key=idempotency_key,
                prior_status=job_status,
                reason=requeue_reason,
            )
            return existing

        logger.info(
            "webhook_stored",
            job_id=str(job.id),
            provider=provider,
            event_type=event_type,
            idempotency_key=idempotency_key,
        )

        return job

    async def mark_inline_processed(
        self,
        job: BackgroundJob,
        result: Dict[str, Any] | None = None,
    ) -> None:
        """
        Mark a queued webhook job as completed after successful inline processing.

        This prevents the same webhook from being re-processed by the async worker
        when the synchronous HTTP path already handled it successfully.
        """
        now = datetime.now(timezone.utc)
        current_attempts = int(getattr(job, "attempts", 0) or 0)
        job.status = JobStatus.COMPLETED.value
        job.completed_at = now
        job.error_message = None
        job.result = result or {"status": "success", "mode": "inline"}
        job.attempts = current_attempts + 1
        await self.db.commit()

    async def get_pending_webhooks(
        self, provider: Optional[str] = None
    ) -> list[BackgroundJob]:
        """Get all pending webhook jobs."""
        query = (
            select(BackgroundJob)
            .where(
                BackgroundJob.job_type == JobType.WEBHOOK_RETRY,
                BackgroundJob.status == JobStatus.PENDING,
            )
            .order_by(BackgroundJob.scheduled_for)
        )

        if provider:
            query = query.where(
                BackgroundJob.payload["provider"].as_string() == provider
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())


async def process_paystack_webhook(
    job: BackgroundJob, db: AsyncSession
) -> Dict[str, Any]:
    """
    Process Paystack webhook from background job.

    Called by JobProcessor._handle_webhook_retry()
    """
    from app.modules.billing.domain.billing.paystack_billing import WebhookHandler

    if not job.payload:
        raise WebhookPermanentError("Missing stored webhook payload")

    payload = job.payload
    raw_payload = payload.get("raw_payload")
    signature = payload.get("signature")

    logger.info(
        "processing_paystack_webhook",
        job_id=str(job.id),
        event_type=payload.get("event_type"),
    )

    handler = WebhookHandler(db)

    event: str | None = None
    data: Dict[str, Any] = {}
    if raw_payload and signature:
        try:
            payload_bytes = raw_payload.encode("utf-8")
            if not handler.verify_signature(payload_bytes, signature):
                logger.critical(
                    "paystack_retry_signature_invalid",
                    job_id=str(job.id),
                    event_type=payload.get("event_type"),
                )
                raise WebhookPermanentError("Stored Paystack signature verification failed")
            parsed = json.loads(raw_payload)
            if not isinstance(parsed, dict):
                raise WebhookPermanentError("Stored webhook payload is not a JSON object")
            event = parsed.get("event", payload.get("event_type"))
            data = parsed.get("data", {})
        except PAYSTACK_STORED_PAYLOAD_PARSE_RECOVERABLE_EXCEPTIONS as exc:
            logger.error(
                "paystack_retry_payload_parse_failed",
                job_id=str(job.id),
                error=str(exc),
            )
            raise WebhookPermanentError("Stored webhook payload could not be parsed") from exc
    else:
        logger.critical(
            "paystack_retry_missing_signature_material",
            job_id=str(job.id),
            event_type=payload.get("event_type"),
        )
        raise WebhookPermanentError("Stored webhook signature material is missing")

    result = {"status": "processed", "event": event}

    # Route to appropriate handler based on event type
    if event == "subscription.create":
        await handler._handle_subscription_create(data, commit=False)
    elif event == "charge.success":
        await handler._handle_charge_success(data, commit=False)
    elif event == "subscription.disable":
        await handler._handle_subscription_disable(data, commit=False)
    elif event == "invoice.payment_failed":
        await handler._handle_invoice_failed(data, commit=False)
    else:
        result["status"] = "ignored"
        result["reason"] = f"Unknown event type: {event}"

    return result
