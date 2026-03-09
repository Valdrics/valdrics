"""
Email Notification Service

Sends carbon budget alerts via email using SMTP.
"""

import html
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any, Dict, List

import anyio
import structlog

from app.shared.core.config import get_settings

logger = structlog.get_logger()
EMAIL_DELIVERY_RECOVERABLE_EXCEPTIONS = (
    smtplib.SMTPException,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)
SALES_INQUIRY_PRIMARY_RECIPIENT = "enterprise@valdrics.com"
SALES_INQUIRY_CC_RECIPIENTS = ("sales@valdrics.com",)


def get_operational_email_service(settings: object | None = None) -> "EmailService":
    """Build the SMTP-backed service used for operational notifications."""
    settings_obj = settings or get_settings()
    smtp_host = str(getattr(settings_obj, "SMTP_HOST", "") or "").strip()
    smtp_user = str(getattr(settings_obj, "SMTP_USER", "") or "").strip()
    smtp_password = str(getattr(settings_obj, "SMTP_PASSWORD", "") or "").strip()
    from_email = str(
        getattr(settings_obj, "SMTP_FROM", "alerts@valdrics.ai") or ""
    ).strip()
    smtp_port = int(getattr(settings_obj, "SMTP_PORT", 587) or 587)
    if not smtp_host or not smtp_user or not smtp_password or not from_email:
        raise RuntimeError("smtp_not_configured_for_operational_email")
    if smtp_port <= 0:
        raise RuntimeError("smtp_port_invalid_for_operational_email")
    return EmailService(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_user=smtp_user,
        smtp_password=smtp_password,
        from_email=from_email,
    )


def escape_html(text: str) -> str:
    """BE-NOTIF-1: Escape user-provided content to prevent HTML injection."""
    if not text:
        return ""
    return html.escape(str(text))


def _sanitize_header_value(value: str) -> str:
    """Prevent CRLF/header injection in email metadata fields."""
    text = str(value or "")
    if "\r" in text or "\n" in text:
        raise ValueError("Invalid email header value")
    return text.strip()


class EmailService:
    """
    Email notification service for carbon alerts.

    Uses SMTP to send HTML-formatted carbon budget alerts.
    Supports multiple recipients.
    """

    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        from_email: str,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.from_email = from_email

    def _send_message_sync(self, message: MIMEMultipart, recipients: List[str]) -> None:
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.sendmail(self.from_email, recipients, message.as_string())

    async def _send_message(
        self, message: MIMEMultipart, recipients: List[str]
    ) -> None:
        await anyio.to_thread.run_sync(self._send_message_sync, message, recipients)

    async def send_carbon_alert(
        self,
        recipients: List[str],
        budget_status: Dict[str, Any],
    ) -> bool:
        """
        Send carbon budget alert email.

        Args:
            recipients: List of email addresses
            budget_status: Budget status dict with usage info

        Returns:
            True if email sent successfully
        """
        if not recipients:
            logger.warning("email_alert_skipped", reason="No recipients")
            return False

        try:
            status = budget_status.get("alert_status", "unknown")
            subject = f"⚠️ Valdrics: Carbon Budget {'Exceeded' if status == 'exceeded' else 'Warning'}"

            html_body = self._build_email_html(budget_status)

            msg = MIMEMultipart("alternative")
            msg["Subject"] = _sanitize_header_value(subject)
            msg["From"] = _sanitize_header_value(self.from_email)
            msg["To"] = _sanitize_header_value(", ".join(recipients))

            msg.attach(MIMEText(html_body, "html"))

            await self._send_message(msg, recipients)

            logger.info(
                "carbon_email_sent",
                recipients=recipients,
                status=status,
            )
            return True

        except EMAIL_DELIVERY_RECOVERABLE_EXCEPTIONS as e:
            logger.error("carbon_email_failed", error=str(e))
            return False

    def _build_email_html(self, budget_status: Dict[str, Any]) -> str:
        """Build HTML email body."""
        status = budget_status.get("alert_status", "unknown")
        status_color = "#dc2626" if status == "exceeded" else "#f59e0b"
        status_text = "🚨 EXCEEDED" if status == "exceeded" else "⚠️ WARNING"

        recommendations = budget_status.get("recommendations", [])
        # BE-NOTIF-1: Escape user-provided content
        recs_html = "".join(
            f"<li>{escape_html(rec)}</li>" for rec in recommendations[:3]
        )

        return f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #0f172a; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8fafc; padding: 20px; border-radius: 0 0 8px 8px; }}
        .status {{ color: {status_color}; font-size: 24px; font-weight: bold; }}
        .metric {{ background: white; padding: 15px; border-radius: 8px; margin: 10px 0; }}
        .progress {{ background: #e5e7eb; height: 20px; border-radius: 10px; overflow: hidden; }}
        .progress-bar {{ background: {status_color}; height: 100%; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🌱 Valdrics Carbon Alert</h1>
        </div>
        <div class="content">
            <p class="status">{status_text}</p>

            <div class="metric">
                <h3>Monthly Carbon Usage</h3>
                <p><strong>{budget_status.get("current_usage_kg", 0):.2f} kg</strong> of {budget_status.get("budget_kg", 100):.0f} kg budget</p>
                <div class="progress">
                    <div class="progress-bar" style="width: {min(budget_status.get("usage_percent", 0), 100)}%"></div>
                </div>
                <p>{budget_status.get("usage_percent", 0):.1f}% used</p>
            </div>

            <div class="metric">
                <h3>💡 Recommendations</h3>
                <ul>{recs_html}</ul>
            </div>

            <p style="color: #64748b; font-size: 12px;">
                Sent by Valdrics GreenOps Dashboard<br>
                <a href="https://valdrics.io/greenops">View Dashboard</a>
            </p>
        </div>
    </div>
</body>
</html>
"""

    async def send_dunning_notification(
        self,
        to_email: str,
        attempt: int,
        max_attempts: int,
        next_retry_date: "datetime",
        tier: str,
    ) -> bool:
        """
        Send payment failed notification for dunning workflow.
        """

        try:
            subject = f"⚠️ Valdrics: Payment Failed ({attempt}/{max_attempts})"

            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #dc2626; color: white; padding: 20px; border-radius: 8px 8px 0 0; }}
        .content {{ background: #f8fafc; padding: 20px; border-radius: 0 0 8px 8px; }}
        .warning {{ color: #dc2626; font-weight: bold; }}
        .cta {{ background: #2563eb; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; display: inline-block; margin: 15px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>💳 Payment Failed</h1>
        </div>
        <div class="content">
            <p>We were unable to process your subscription payment for the <strong>{escape_html(tier)}</strong> plan.</p>
            
            <p class="warning">Attempt {attempt} of {max_attempts}</p>
            
            <p>We will automatically retry your payment on <strong>{next_retry_date.strftime("%B %d, %Y")}</strong>.</p>
            
            <p>To avoid service interruption, please ensure your payment method is updated:</p>
            
            <a href="https://app.valdrics.io/settings/billing" class="cta">Update Payment Method</a>
            
            <p>If you have any questions, contact our support team.</p>
            
            <p style="color: #64748b; font-size: 12px;">
                Sent by Valdrics Billing
            </p>
        </div>
    </div>
</body>
</html>
"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = _sanitize_header_value(subject)
            msg["From"] = _sanitize_header_value(self.from_email)
            msg["To"] = _sanitize_header_value(to_email)

            msg.attach(MIMEText(html_body, "html"))

            await self._send_message(msg, [to_email])

            logger.info("dunning_email_sent", to_email=to_email, attempt=attempt)
            return True

        except EMAIL_DELIVERY_RECOVERABLE_EXCEPTIONS as e:
            logger.error("dunning_email_failed", error=str(e))
            return False

    async def send_payment_recovered_notification(self, to_email: str) -> bool:
        """Send payment recovered confirmation."""
        try:
            subject = "✅ Valdrics: Payment Successful - Account Reactivated"

            html_body = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #16a34a; color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { background: #f8fafc; padding: 20px; border-radius: 0 0 8px 8px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>✅ Payment Successful</h1>
        </div>
        <div class="content">
            <p>Great news! Your payment has been processed successfully.</p>
            
            <p>Your Valdrics subscription is now active and you have full access to all features.</p>
            
            <p>Thank you for your continued trust in Valdrics.</p>
            
            <p style="color: #64748b; font-size: 12px;">
                Sent by Valdrics Billing
            </p>
        </div>
    </div>
</body>
</html>
"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = _sanitize_header_value(subject)
            msg["From"] = _sanitize_header_value(self.from_email)
            msg["To"] = _sanitize_header_value(to_email)

            msg.attach(MIMEText(html_body, "html"))

            await self._send_message(msg, [to_email])

            logger.info("payment_recovered_email_sent", to_email=to_email)
            return True

        except EMAIL_DELIVERY_RECOVERABLE_EXCEPTIONS as e:
            logger.error("payment_recovered_email_failed", error=str(e))
            return False

    async def send_account_downgraded_notification(self, to_email: str) -> bool:
        """Send account downgraded notice."""
        try:
            subject = "🔻 Valdrics: Account Downgraded to Free Tier"

            html_body = """
<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #f59e0b; color: white; padding: 20px; border-radius: 8px 8px 0 0; }
        .content { background: #f8fafc; padding: 20px; border-radius: 0 0 8px 8px; }
        .cta { background: #2563eb; color: white; padding: 12px 24px; border-radius: 6px; text-decoration: none; display: inline-block; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔻 Account Downgraded</h1>
        </div>
        <div class="content">
            <p>We were unable to process your payment after multiple attempts.</p>
            
            <p>Your account has been downgraded to the <strong>Free Tier</strong>.</p>
            
            <p>You can resubscribe at any time to regain full access to premium features:</p>
            
            <a href="https://app.valdrics.io/settings/billing" class="cta">Resubscribe Now</a>
            
            <p>Your data is safe and will remain accessible on the Free Tier.</p>
            
            <p style="color: #64748b; font-size: 12px;">
                Sent by Valdrics Billing
            </p>
        </div>
    </div>
</body>
</html>
"""

            msg = MIMEMultipart("alternative")
            msg["Subject"] = _sanitize_header_value(subject)
            msg["From"] = _sanitize_header_value(self.from_email)
            msg["To"] = _sanitize_header_value(to_email)

            msg.attach(MIMEText(html_body, "html"))

            await self._send_message(msg, [to_email])

            logger.info("account_downgraded_email_sent", to_email=to_email)
            return True

        except EMAIL_DELIVERY_RECOVERABLE_EXCEPTIONS as e:
            logger.error("account_downgraded_email_failed", error=str(e))
            return False

    async def send_sales_inquiry_notification(
        self,
        *,
        inquiry_id: str,
        submitted_at: datetime,
        name: str,
        email: str,
        company: str,
        role: str | None,
        team_size: str | None,
        deployment_scope: str | None,
        timeline: str | None,
        interest_area: str | None,
        message: str | None,
        source: str | None,
        referrer: str | None,
        utm_source: str | None,
        utm_medium: str | None,
        utm_campaign: str | None,
    ) -> bool:
        """Send a durable sales-intake inquiry notification."""
        recipients = [SALES_INQUIRY_PRIMARY_RECIPIENT, *SALES_INQUIRY_CC_RECIPIENTS]

        try:
            subject = (
                f"Valdrics sales inquiry: {company}"
                + (f" ({interest_area})" if interest_area else "")
            )
            msg = MIMEMultipart("alternative")
            msg["Subject"] = _sanitize_header_value(subject)
            msg["From"] = _sanitize_header_value(self.from_email)
            msg["To"] = _sanitize_header_value(SALES_INQUIRY_PRIMARY_RECIPIENT)
            msg["Cc"] = _sanitize_header_value(", ".join(SALES_INQUIRY_CC_RECIPIENTS))
            msg["Reply-To"] = _sanitize_header_value(email)

            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f3f7fb; color: #0f172a; }}
        .container {{ max-width: 680px; margin: 0 auto; padding: 24px; }}
        .hero {{ background: linear-gradient(145deg, #07121c, #0b1b28); color: #f8fbff; padding: 24px; border-radius: 18px 18px 0 0; }}
        .hero p {{ color: #b8d5df; }}
        .content {{ background: #ffffff; border: 1px solid #d8e7ef; border-top: 0; border-radius: 0 0 18px 18px; padding: 24px; }}
        .grid {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 20px; }}
        .card {{ background: #f8fbfd; border: 1px solid #d7e8ef; border-radius: 12px; padding: 14px; }}
        .label {{ display: block; margin-bottom: 6px; font-size: 12px; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; color: #129ec0; }}
        .value {{ font-size: 14px; line-height: 1.6; color: #0f172a; }}
        .message {{ white-space: pre-wrap; }}
        .foot {{ color: #64748b; font-size: 12px; margin-top: 18px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="hero">
            <h1>New Valdrics sales inquiry</h1>
            <p>Inquiry ID {escape_html(inquiry_id)} arrived on {escape_html(submitted_at.isoformat())}.</p>
        </div>
        <div class="content">
            <div class="grid">
                <div class="card"><span class="label">Name</span><div class="value">{escape_html(name)}</div></div>
                <div class="card"><span class="label">Work email</span><div class="value">{escape_html(email)}</div></div>
                <div class="card"><span class="label">Company</span><div class="value">{escape_html(company)}</div></div>
                <div class="card"><span class="label">Role</span><div class="value">{escape_html(role or "Not provided")}</div></div>
                <div class="card"><span class="label">Team size</span><div class="value">{escape_html(team_size or "Not provided")}</div></div>
                <div class="card"><span class="label">Timeline</span><div class="value">{escape_html(timeline or "Not provided")}</div></div>
                <div class="card"><span class="label">Interest area</span><div class="value">{escape_html(interest_area or "Not provided")}</div></div>
                <div class="card"><span class="label">Scope</span><div class="value">{escape_html(deployment_scope or "Not provided")}</div></div>
            </div>
            <div class="card">
                <span class="label">Message</span>
                <div class="value message">{escape_html(message or "No additional context provided.")}</div>
            </div>
            <div class="grid" style="margin-top: 12px;">
                <div class="card"><span class="label">Source</span><div class="value">{escape_html(source or "Not provided")}</div></div>
                <div class="card"><span class="label">Referrer</span><div class="value">{escape_html(referrer or "Not provided")}</div></div>
                <div class="card"><span class="label">UTM source</span><div class="value">{escape_html(utm_source or "Not provided")}</div></div>
                <div class="card"><span class="label">UTM medium</span><div class="value">{escape_html(utm_medium or "Not provided")}</div></div>
                <div class="card"><span class="label">UTM campaign</span><div class="value">{escape_html(utm_campaign or "Not provided")}</div></div>
            </div>
            <p class="foot">Reply directly to this email to continue the conversation with the buyer.</p>
        </div>
    </div>
</body>
</html>
"""

            msg.attach(MIMEText(html_body, "html"))
            await self._send_message(msg, recipients)

            logger.info(
                "sales_inquiry_email_sent",
                inquiry_id=inquiry_id,
                recipient_count=len(recipients),
            )
            return True

        except EMAIL_DELIVERY_RECOVERABLE_EXCEPTIONS as e:
            logger.error(
                "sales_inquiry_email_failed",
                inquiry_id=inquiry_id,
                error=str(e),
            )
            return False
