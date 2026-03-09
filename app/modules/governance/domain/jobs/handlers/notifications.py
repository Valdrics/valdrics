"""Notification and Webhook Job Handlers."""

from datetime import datetime, timezone
from typing import Any, Dict
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.background_job import BackgroundJob
from app.modules.governance.domain.jobs.handlers.base import BaseJobHandler
from app.shared.core.config import get_settings
from app.shared.core.webhooks import sanitize_webhook_headers, validate_webhook_url

logger = structlog.get_logger()


class NotificationHandler(BaseJobHandler):
    """Handle notification job (Slack, Email, etc.)."""

    async def execute(self, job: BackgroundJob, db: AsyncSession) -> Dict[str, Any]:
        payload = job.payload or {}
        provider = str(payload.get("provider", "") or "").strip().lower()
        if provider == "sales_intake_email":
            return await self._execute_sales_intake_email(job, db, payload)

        from app.modules.notifications.domain import (
            get_slack_service,
            get_tenant_slack_service,
        )

        message = payload.get("message")
        title = payload.get("title", "Valdrics Notification")
        severity = payload.get("severity", "info")

        if not message:
            raise ValueError("message required for notification")

        service = None
        if job.tenant_id:
            service = await get_tenant_slack_service(db, job.tenant_id)
        else:
            service = get_slack_service()
        if not service:
            return {"status": "skipped", "reason": "slack_not_configured"}

        success = await service.send_alert(
            title=title, message=message, severity=severity
        )

        return {"status": "completed", "success": success}

    async def _execute_sales_intake_email(
        self,
        job: BackgroundJob,
        db: AsyncSession,
        payload: dict[str, Any],
    ) -> Dict[str, Any]:
        from app.models.public_sales_inquiry import PublicSalesInquiry
        from app.modules.notifications.domain.email_service import (
            get_operational_email_service,
        )

        inquiry_id_raw = str(payload.get("inquiry_id", "") or "").strip()
        if not inquiry_id_raw:
            raise ValueError("inquiry_id required for sales_intake_email")
        try:
            inquiry_id = UUID(inquiry_id_raw)
        except ValueError as exc:
            raise ValueError("inquiry_id must be a valid UUID") from exc

        inquiry = (
            await db.execute(
                select(PublicSalesInquiry).where(PublicSalesInquiry.id == inquiry_id)
            )
        ).scalar_one_or_none()
        if inquiry is None:
            return {"status": "skipped", "reason": "inquiry_not_found"}
        if inquiry.delivery_status == "delivered":
            return {
                "status": "skipped",
                "reason": "already_delivered",
                "inquiry_id": str(inquiry.id),
            }

        inquiry.delivery_attempts += 1

        try:
            service = get_operational_email_service()
            success = await service.send_sales_inquiry_notification(
                inquiry_id=str(inquiry.id),
                submitted_at=inquiry.created_at,
                name=inquiry.name,
                email=inquiry.email,
                company=inquiry.company,
                role=inquiry.role,
                team_size=inquiry.team_size,
                deployment_scope=inquiry.deployment_scope,
                timeline=inquiry.timeline,
                interest_area=inquiry.interest_area,
                message=inquiry.message,
                source=inquiry.source,
                referrer=inquiry.referrer,
                utm_source=inquiry.utm_source,
                utm_medium=inquiry.utm_medium,
                utm_campaign=inquiry.utm_campaign,
            )
        except (RuntimeError, TypeError, ValueError, OSError) as exc:
            inquiry.delivery_status = "delivery_failed"
            inquiry.last_delivery_error = str(exc)
            await db.flush()
            logger.error(
                "sales_inquiry_notification_handler_failed",
                inquiry_id=str(inquiry.id),
                email_hash=inquiry.email_hash,
                error=str(exc),
            )
            raise

        if not success:
            inquiry.delivery_status = "delivery_failed"
            inquiry.last_delivery_error = "sales_inquiry_email_delivery_failed"
            await db.flush()
            raise RuntimeError("sales_inquiry_email_delivery_failed")

        inquiry.delivery_status = "delivered"
        inquiry.delivered_at = datetime.now(timezone.utc)
        inquiry.last_delivery_error = None
        await db.flush()
        return {
            "status": "completed",
            "success": True,
            "inquiry_id": str(inquiry.id),
        }


class WebhookRetryHandler(BaseJobHandler):
    """Handle webhook retry job (e.g., Paystack)."""

    async def execute(self, job: BackgroundJob, db: AsyncSession) -> Dict[str, Any]:
        payload = job.payload or {}
        provider = payload.get("provider", "generic")

        if provider == "paystack":
            from app.modules.billing.domain.billing.webhook_retry import (
                process_paystack_webhook,
            )

            return await process_paystack_webhook(job, db)

        # Generic HTTP webhook retry

        url = payload.get("url")
        data = payload.get("data")
        headers = payload.get("headers", {})

        if not url:
            raise ValueError("url required for generic webhook_retry")

        settings = get_settings()
        allowlist = {d.lower() for d in settings.WEBHOOK_ALLOWED_DOMAINS if d}
        if not allowlist:
            raise ValueError(
                "WEBHOOK_ALLOWED_DOMAINS must be configured for generic webhook retries"
            )

        validate_webhook_url(
            url=url,
            allowlist=allowlist,
            require_https=settings.WEBHOOK_REQUIRE_HTTPS,
            block_private_ips=settings.WEBHOOK_BLOCK_PRIVATE_IPS,
        )

        try:
            headers = sanitize_webhook_headers(headers)
        except ValueError as exc:
            logger.warning("webhook_headers_rejected", error=str(exc))
            raise

        from app.shared.core.http import get_http_client

        client = get_http_client()
        response = await client.post(url, json=data, headers=headers, timeout=30)
        response.raise_for_status()

        return {"status": "completed", "status_code": response.status_code}
