"""
Slack notification service for Valdrics.
Sends alerts and daily digests to configured Slack channel.
"""

import structlog
from typing import Any
import asyncio
import hashlib
import time
from threading import Lock
from uuid import UUID

from redis.exceptions import RedisError
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.errors import SlackApiError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger()
SLACK_CLIENT_RECOVERABLE_EXCEPTIONS = (
    RuntimeError,
    TypeError,
    AttributeError,
    OSError,
    ValueError,
)
SLACK_DEDUP_REDIS_RECOVERABLE_EXCEPTIONS = (
    RedisError,
    RuntimeError,
    TypeError,
    AttributeError,
    OSError,
    ValueError,
)
_service_cache: dict[tuple[str, str], "SlackService"] = {}
_service_cache_lock = Lock()


class SlackService:
    """Service for sending notifications to Slack."""

    # Color mapping for severity levels
    SEVERITY_COLORS = {
        "info": "#10b981",  # Green
        "warning": "#f59e0b",  # Amber
        "critical": "#f43f5e",  # Red
    }

    @staticmethod
    def escape_mrkdwn(text: str) -> str:
        """
        Escape Slack control characters to prevent mrkdwn injection.
        References: https://api.slack.com/reference/surfaces/formatting#escaping
        """
        if not text:
            return ""
        return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def __init__(self, bot_token: str, channel_id: str):
        """Initialize with bot token and target channel."""
        self.client = AsyncWebClient(token=bot_token)
        self.bot_token = bot_token
        self.channel_id = channel_id

        # Local fallback when distributed Redis-backed deduplication is unavailable.
        self._sent_alerts: dict[str, float] = {}
        self._dedup_window_seconds = 3600  # 1 hour deduplication window

    @staticmethod
    def _dedup_cache_key(channel_id: str, alert_hash: str) -> str:
        return f"notifications:slack:dedup:{channel_id}:{alert_hash}"

    async def _is_duplicate_alert(self, alert_hash: str, current_time: float) -> bool:
        try:
            from app.shared.core.rate_limit import get_redis_client

            redis_client = get_redis_client()
            if redis_client is not None:
                cache_key = self._dedup_cache_key(self.channel_id, alert_hash)
                recorded = await redis_client.set(
                    cache_key,
                    str(int(current_time)),
                    ex=int(self._dedup_window_seconds),
                    nx=True,
                )
                return not bool(recorded)
        except SLACK_DEDUP_REDIS_RECOVERABLE_EXCEPTIONS as exc:
            logger.warning("slack_dedup_redis_unavailable", error=str(exc))

        last_sent = self._sent_alerts.get(alert_hash)
        if last_sent is not None and (
            current_time - last_sent < self._dedup_window_seconds
        ):
            return True

        self._sent_alerts[alert_hash] = current_time
        self._sent_alerts = {
            key: value
            for key, value in self._sent_alerts.items()
            if current_time - value < self._dedup_window_seconds
        }
        return False

    async def _send_with_retry(self, method: str, **kwargs: Any) -> bool:
        """Generic Slack API call with exponential backoff for rate limiting."""
        max_retries = 3
        for attempt in range(max_retries + 1):
            try:
                # Use getattr to call the method (e.g., chat_postMessage)
                func = getattr(self.client, method)
                await func(**kwargs)
                return True
            except SlackApiError as e:
                error_code = e.response.get("error", "")
                if error_code == "ratelimited" and attempt < max_retries:
                    retry_after = int(e.response.headers.get("Retry-After", 2**attempt))
                    logger.warning(
                        "slack_rate_limited_retrying",
                        retry_after=retry_after,
                        attempt=attempt,
                    )
                    await asyncio.sleep(retry_after)
                    continue
                logger.error("slack_api_error", method=method, error_code=error_code)
                return False
            except SLACK_CLIENT_RECOVERABLE_EXCEPTIONS as e:
                logger.error("slack_method_failed", method=method, error=str(e))
                return False
        return False

    async def health_check(self) -> bool:
        """
        Perform a non-invasive Slack connectivity check.

        This avoids sending messages (unlike send_alert) and is safe to run on
        a schedule for SaaS multi-tenant monitoring.
        """
        return await self._send_with_retry("auth_test")

    async def send_alert(
        self, title: str, message: str, severity: str = "warning"
    ) -> bool:
        """Send an alert message to Slack with retry logic and deduplication."""

        # BE-NOTIF-4: Check for duplicate alerts within dedup window
        # Include message hash to avoid suppressing distinct alerts with same title
        msg_hash = hashlib.sha256(message.encode()).hexdigest()[:12]
        alert_hash = hashlib.sha256(
            f"{title}:{severity}:{msg_hash}".encode()
        ).hexdigest()
        current_time = time.time()

        if await self._is_duplicate_alert(alert_hash, current_time):
            logger.info("duplicate_alert_suppressed", title=title)
            return True  # Suppress duplicate

        color = self.SEVERITY_COLORS.get(severity, self.SEVERITY_COLORS["warning"])
        return await self._send_with_retry(
            "chat_postMessage",
            channel=self.channel_id,
            text=f"Alert: {title}",  # BE-NOTIF-5: Fallback text for notifications
            attachments=[
                {
                    "fallback": message,  # BE-NOTIF-5: Slack fallback text for older clients
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": f"🚨 {title}"},
                        },
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": message},
                        },
                    ],
                }
            ],
        )

    async def send_digest(self, stats: dict[str, Any]) -> bool:
        """Send daily cost digest to Slack with retry logic."""
        return await self._send_with_retry(
            "chat_postMessage",
            channel=self.channel_id,
            text="Daily Cloud Cost Digest",  # BE-NOTIF-5: Fallback text
            blocks=[
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Daily Cloud Cost Digest",
                    },
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*💰 Total Cost*\n${stats.get('total_cost', 0):.2f}",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*🌱 Carbon*\n{stats.get('carbon_kg', 0):.2f} kg CO₂",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*👻 Zombies*\n{stats.get('zombie_count', 0)} resources",
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*📅 Period*\n{stats.get('period', 'Last 24h')}",
                        },
                    ],
                },
                {
                    "type": "context",
                    "elements": [{"type": "mrkdwn", "text": "Powered by Valdrics"}],
                },
            ],
        )

    async def notify_zombies(
        self, zombies: dict[str, Any], estimated_savings: float = 0.0
    ) -> bool:
        """
        Send zombie detection alert.

        Args:
            zombies: Dict of zombie categories to lists of resources
            estimated_savings: Estimated monthly savings in dollars
        """
        zombie_count = sum(
            len(items) for items in zombies.values() if isinstance(items, list)
        )
        if zombie_count == 0:
            return True  # No zombies, nothing to report

        summary_lines = []
        for cat, items in zombies.items():
            if isinstance(items, list) and len(items) > 0:
                # BE-SLACK-1: Escape category label
                safe_label = self.escape_mrkdwn(cat.replace("_", " ").title())
                summary_lines.append(f"• {safe_label}: {len(items)}")

        message = (
            f"Found *{zombie_count} zombie resources*.\n"
            + "\n".join(summary_lines)
            + f"\n💰 Estimated Savings: *${estimated_savings:.2f}/mo*"
        )

        return await self.send_alert(
            title="Zombie Resources Detected!", message=message, severity="warning"
        )

    async def notify_budget_alert(
        self, current_spend: float, budget_limit: float, percent_used: float
    ) -> bool:
        """
        Send budget threshold alert.

        Args:
            current_spend: Current spend amount
            budget_limit: Budget limit
            percent_used: Percentage of budget used (0-100)
        """
        severity = "critical" if percent_used >= 100 else "warning"

        message = (
            f"*Current Spend:* ${current_spend:.2f}\n"
            f"*Budget Limit:* ${budget_limit:.2f}\n"
            f"*Usage:* {percent_used:.1f}%"
        )

        return await self.send_alert(
            title="Budget Alert Threshold Reached", message=message, severity=severity
        )


def get_slack_service() -> SlackService | None:
    """
    Factory function to get a configured SlackService instance.
    Returns None if Slack is not configured.
    """
    from app.shared.core.config import get_settings

    settings = get_settings()

    if getattr(settings, "SAAS_STRICT_INTEGRATIONS", False):
        logger.info("env_slack_service_disabled_by_saas_strict_mode")
        return None

    if settings.SLACK_BOT_TOKEN and settings.SLACK_CHANNEL_ID:
        cache_key = (settings.SLACK_BOT_TOKEN, settings.SLACK_CHANNEL_ID)
        with _service_cache_lock:
            service = _service_cache.get(cache_key)
            if service is None:
                service = SlackService(settings.SLACK_BOT_TOKEN, settings.SLACK_CHANNEL_ID)
                _service_cache[cache_key] = service
            return service
    return None


async def get_tenant_slack_service(
    db: AsyncSession, tenant_id: UUID | str
) -> SlackService | None:
    """
    Build Slack service from tenant-scoped notification settings.
    Uses global bot token and tenant channel override when present.
    Returns None when Slack is disabled or not fully configured.
    """
    from app.models.notification_settings import NotificationSettings
    from app.models.tenant import Tenant
    from app.shared.core.config import get_settings
    from app.shared.core.pricing import FeatureFlag, is_feature_enabled, normalize_tier

    try:
        tenant_uuid = UUID(str(tenant_id))
    except ValueError:
        logger.warning(
            "tenant_slack_settings_invalid_tenant_id", tenant_id=str(tenant_id)
        )
        return None

    tenant_result = await db.execute(select(Tenant.plan).where(Tenant.id == tenant_uuid))
    tenant_plan = tenant_result.scalar_one_or_none()
    if not is_feature_enabled(
        normalize_tier(tenant_plan), FeatureFlag.SLACK_INTEGRATION
    ):
        logger.info(
            "tenant_slack_settings_blocked_by_tier",
            tenant_id=str(tenant_uuid),
            tenant_plan=str(tenant_plan or "free"),
        )
        return None

    result = await db.execute(
        select(NotificationSettings).where(
            NotificationSettings.tenant_id == tenant_uuid
        )
    )
    notif = result.scalar_one_or_none()
    if notif and not bool(getattr(notif, "slack_enabled", True)):
        return None

    settings = get_settings()
    channel_override = getattr(notif, "slack_channel_override", None) if notif else None
    channel = channel_override or settings.SLACK_CHANNEL_ID
    if not settings.SLACK_BOT_TOKEN or not channel:
        logger.warning(
            "tenant_slack_settings_incomplete",
            tenant_id=str(tenant_uuid),
            has_bot_token=bool(settings.SLACK_BOT_TOKEN),
            has_channel=bool(channel),
        )
        return None

    cache_key = (settings.SLACK_BOT_TOKEN, channel)
    with _service_cache_lock:
        service = _service_cache.get(cache_key)
        if service is None:
            service = SlackService(settings.SLACK_BOT_TOKEN, channel)
            _service_cache[cache_key] = service
        return service
