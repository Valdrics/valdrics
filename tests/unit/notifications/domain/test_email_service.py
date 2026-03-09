import smtplib
from datetime import datetime
from unittest.mock import patch, ANY

import pytest

from app.modules.notifications.domain.email_service import EmailService


@pytest.fixture
def email_service():
    return EmailService(
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_user="user",
        smtp_password="password",
        from_email="noreply@valdrics.io",
    )


@pytest.mark.asyncio
async def test_send_carbon_alert_success(email_service):
    recipients = ["test@example.com"]
    status = {
        "alert_status": "exceeded",
        "current_usage_kg": 150,
        "budget_kg": 100,
        "usage_percent": 150,
        "recommendations": ["Reduce usage"],
    }

    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = mock_smtp.return_value.__enter__.return_value

        result = await email_service.send_carbon_alert(recipients, status)

        assert result is True
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user", "password")
        mock_server.sendmail.assert_called_once_with(
            "noreply@valdrics.io", recipients, ANY
        )


@pytest.mark.asyncio
async def test_send_carbon_alert_no_recipients(email_service):
    result = await email_service.send_carbon_alert([], {})
    assert result is False


@pytest.mark.asyncio
async def test_send_carbon_alert_failure(email_service):
    with patch("smtplib.SMTP", side_effect=smtplib.SMTPException("SMTP Error")):
        result = await email_service.send_carbon_alert(["test@example.com"], {})
        assert result is False


@pytest.mark.asyncio
async def test_send_dunning_notification_success(email_service):
    from datetime import datetime

    with patch("smtplib.SMTP"):
        result = await email_service.send_dunning_notification(
            to_email="user@example.com",
            attempt=1,
            max_attempts=3,
            next_retry_date=datetime.now(),
            tier="Growth",
        )
        assert result is True


@pytest.mark.asyncio
async def test_send_payment_recovered(email_service):
    with patch("smtplib.SMTP"):
        result = await email_service.send_payment_recovered_notification(
            "user@example.com"
        )
        assert result is True


@pytest.mark.asyncio
async def test_send_account_downgraded(email_service):
    with patch("smtplib.SMTP"):
        result = await email_service.send_account_downgraded_notification(
            "user@example.com"
        )
        assert result is True


@pytest.mark.asyncio
async def test_send_sales_inquiry_notification_success(email_service):
    with patch("smtplib.SMTP") as mock_smtp:
        mock_server = mock_smtp.return_value.__enter__.return_value

        result = await email_service.send_sales_inquiry_notification(
            inquiry_id="inq-1",
            submitted_at=datetime(2026, 3, 9, 12, 0, 0),
            name="Buyer One",
            email="buyer@example.com",
            company="Example Inc",
            role="FinOps",
            team_size="21-50",
            deployment_scope="AWS + Datadog",
            timeline="this_quarter",
            interest_area="security_review",
            message="Need security review support.",
            source="pricing_page",
            referrer="https://valdrics.com/pricing",
            utm_source="linkedin",
            utm_medium="paid_social",
            utm_campaign="q1",
        )

        assert result is True
        mock_server.sendmail.assert_called_once_with(
            "noreply@valdrics.io",
            ["enterprise@valdrics.com", "sales@valdrics.com"],
            ANY,
        )
        sent_message = mock_server.sendmail.call_args.args[2]
        assert "Reply-To: buyer@example.com" in sent_message
        assert "Valdrics sales inquiry: Example Inc" in sent_message


@pytest.mark.asyncio
async def test_send_sales_inquiry_notification_rejects_header_injection(email_service):
    result = await email_service.send_sales_inquiry_notification(
        inquiry_id="inq-1",
        submitted_at=datetime(2026, 3, 9, 12, 0, 0),
        name="Buyer One",
        email="buyer@example.com\r\nBcc:bad@example.com",
        company="Example Inc",
        role=None,
        team_size=None,
        deployment_scope=None,
        timeline=None,
        interest_area=None,
        message=None,
        source=None,
        referrer=None,
        utm_source=None,
        utm_medium=None,
        utm_campaign=None,
    )

    assert result is False
