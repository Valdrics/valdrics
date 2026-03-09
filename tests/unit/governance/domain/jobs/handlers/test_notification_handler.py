import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from types import SimpleNamespace
from uuid import uuid4
from app.modules.governance.domain.jobs.handlers.notifications import (
    NotificationHandler,
    WebhookRetryHandler,
)
from app.models.background_job import BackgroundJob
from app.models.public_sales_inquiry import PublicSalesInquiry


@pytest.mark.asyncio
async def test_notification_execute_message_required(db):
    handler = NotificationHandler()
    job = BackgroundJob(payload={})

    with pytest.raises(ValueError, match="message required"):
        await handler.execute(job, db)


@pytest.mark.asyncio
async def test_notification_execute_skipped_no_service(db):
    handler = NotificationHandler()
    job = BackgroundJob(payload={"message": "alert"}, tenant_id=uuid4())

    with patch(
        "app.modules.notifications.domain.get_tenant_slack_service",
        new_callable=AsyncMock,
        return_value=None,
    ):
        result = await handler.execute(job, db)
        assert result["status"] == "skipped"
        assert result["reason"] == "slack_not_configured"


@pytest.mark.asyncio
async def test_notification_execute_success(db):
    handler = NotificationHandler()
    job = BackgroundJob(
        payload={"message": "alert", "title": "Test Alert"},
        tenant_id=uuid4(),
    )

    mock_service = AsyncMock()
    mock_service.send_alert.return_value = True

    with patch(
        "app.modules.notifications.domain.get_tenant_slack_service",
        new_callable=AsyncMock,
        return_value=mock_service,
    ):
        result = await handler.execute(job, db)

        assert result["status"] == "completed"
        assert result["success"] is True
        mock_service.send_alert.assert_awaited_with(
            title="Test Alert", message="alert", severity="info"
        )


@pytest.mark.asyncio
async def test_notification_execute_non_tenant_fallback_service(db):
    handler = NotificationHandler()
    job = BackgroundJob(
        payload={"message": "alert", "title": "System Alert"}, tenant_id=None
    )

    mock_service = AsyncMock()
    mock_service.send_alert.return_value = True

    with (
        patch(
            "app.modules.notifications.domain.get_slack_service",
            return_value=mock_service,
        ),
        patch(
            "app.modules.notifications.domain.get_tenant_slack_service",
            new_callable=AsyncMock,
        ) as tenant_service,
    ):
        result = await handler.execute(job, db)

    tenant_service.assert_not_awaited()
    assert result["status"] == "completed"
    assert result["success"] is True


@pytest.mark.asyncio
async def test_notification_execute_sales_inquiry_email_success(db):
    handler = NotificationHandler()
    inquiry = PublicSalesInquiry(
        name="Buyer One",
        email="buyer@example.com",
        company="Example Inc",
        email_hash="a" * 64,
        inquiry_fingerprint="b" * 64,
        delivery_status="pending",
    )
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    job = BackgroundJob(
        payload={"provider": "sales_intake_email", "inquiry_id": str(inquiry.id)}
    )

    mock_service = AsyncMock()
    mock_service.send_sales_inquiry_notification.return_value = True

    with patch(
        "app.modules.notifications.domain.email_service.get_operational_email_service",
        return_value=mock_service,
    ):
        result = await handler.execute(job, db)

    await db.refresh(inquiry)
    assert result["status"] == "completed"
    assert result["success"] is True
    assert inquiry.delivery_status == "delivered"
    assert inquiry.delivery_attempts == 1
    assert inquiry.delivered_at is not None


@pytest.mark.asyncio
async def test_notification_execute_sales_inquiry_email_skips_already_delivered(db):
    handler = NotificationHandler()
    inquiry = PublicSalesInquiry(
        name="Buyer One",
        email="buyer@example.com",
        company="Example Inc",
        email_hash="a" * 64,
        inquiry_fingerprint="b" * 64,
        delivery_status="delivered",
    )
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    job = BackgroundJob(
        payload={"provider": "sales_intake_email", "inquiry_id": str(inquiry.id)}
    )

    with patch(
        "app.modules.notifications.domain.email_service.get_operational_email_service"
    ) as mock_factory:
        result = await handler.execute(job, db)

    assert result["status"] == "skipped"
    assert result["reason"] == "already_delivered"
    mock_factory.assert_not_called()


@pytest.mark.asyncio
async def test_notification_execute_sales_inquiry_email_failure_marks_inquiry(db):
    handler = NotificationHandler()
    inquiry = PublicSalesInquiry(
        name="Buyer One",
        email="buyer@example.com",
        company="Example Inc",
        email_hash="a" * 64,
        inquiry_fingerprint="b" * 64,
        delivery_status="pending",
    )
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    job = BackgroundJob(
        payload={"provider": "sales_intake_email", "inquiry_id": str(inquiry.id)}
    )

    mock_service = AsyncMock()
    mock_service.send_sales_inquiry_notification.return_value = False

    with (
        patch(
            "app.modules.notifications.domain.email_service.get_operational_email_service",
            return_value=mock_service,
        ),
        pytest.raises(RuntimeError, match="sales_inquiry_email_delivery_failed"),
    ):
        await handler.execute(job, db)

    await db.refresh(inquiry)
    assert inquiry.delivery_status == "delivery_failed"
    assert inquiry.delivery_attempts == 1


@pytest.mark.asyncio
async def test_webhook_retry_execute_generic_success(db):
    handler = WebhookRetryHandler()
    job = BackgroundJob(
        payload={"url": "https://example.com/webhook", "data": {"foo": "bar"}}
    )

    with (
        patch("app.shared.core.http.get_http_client") as MockGetClient,
        patch(
            "app.modules.governance.domain.jobs.handlers.notifications.get_settings",
            return_value=SimpleNamespace(
                WEBHOOK_ALLOWED_DOMAINS=["example.com"],
                WEBHOOK_REQUIRE_HTTPS=True,
                WEBHOOK_BLOCK_PRIVATE_IPS=True,
            ),
        ),
    ):
        mock_client = MockGetClient.return_value
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))

        result = await handler.execute(job, db)

        assert result["status"] == "completed"
        assert result["status_code"] == 200
        mock_client.post.assert_awaited_with(
            "https://example.com/webhook",
            json={"foo": "bar"},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )


@pytest.mark.asyncio
async def test_webhook_retry_execute_marketing_subscribe_payload(db):
    handler = WebhookRetryHandler()
    job = BackgroundJob(
        payload={
            "provider": "marketing_subscribe",
            "url": "https://hooks.example.com/subscribe",
            "data": {"email": "buyer@example.com"},
            "headers": {"Content-Type": "application/json"},
        }
    )

    with (
        patch("app.shared.core.http.get_http_client") as MockGetClient,
        patch(
            "app.modules.governance.domain.jobs.handlers.notifications.get_settings",
            return_value=SimpleNamespace(
                WEBHOOK_ALLOWED_DOMAINS=["example.com"],
                WEBHOOK_REQUIRE_HTTPS=True,
                WEBHOOK_BLOCK_PRIVATE_IPS=True,
            ),
        ),
    ):
        mock_client = MockGetClient.return_value
        mock_client.post = AsyncMock(return_value=MagicMock(status_code=202))

        result = await handler.execute(job, db)

    assert result["status"] == "completed"
    assert result["status_code"] == 202
    mock_client.post.assert_awaited_with(
        "https://hooks.example.com/subscribe",
        json={"email": "buyer@example.com"},
        headers={"Content-Type": "application/json"},
        timeout=30,
    )


@pytest.mark.asyncio
async def test_webhook_retry_execute_generic_rejects_private_ip(db):
    handler = WebhookRetryHandler()
    job = BackgroundJob(
        payload={"url": "https://127.0.0.1/internal", "data": {"foo": "bar"}}
    )

    with patch(
        "app.modules.governance.domain.jobs.handlers.notifications.get_settings",
        return_value=SimpleNamespace(
            WEBHOOK_ALLOWED_DOMAINS=["example.com"],
            WEBHOOK_REQUIRE_HTTPS=True,
            WEBHOOK_BLOCK_PRIVATE_IPS=True,
        ),
    ):
        with pytest.raises(ValueError, match="private or link-local"):
            await handler.execute(job, db)


@pytest.mark.asyncio
async def test_webhook_retry_execute_generic_rejects_non_json_content_type(db):
    handler = WebhookRetryHandler()
    job = BackgroundJob(
        payload={
            "url": "https://example.com/webhook",
            "data": {"foo": "bar"},
            "headers": {"Content-Type": "text/plain"},
        }
    )

    with patch(
        "app.modules.governance.domain.jobs.handlers.notifications.get_settings",
        return_value=SimpleNamespace(
            WEBHOOK_ALLOWED_DOMAINS=["example.com"],
            WEBHOOK_REQUIRE_HTTPS=True,
            WEBHOOK_BLOCK_PRIVATE_IPS=True,
        ),
    ):
        with pytest.raises(ValueError, match="content-type"):
            await handler.execute(job, db)


@pytest.mark.asyncio
async def test_webhook_retry_execute_generic_rejects_private_ip(db):
    handler = WebhookRetryHandler()
    job = BackgroundJob(
        payload={"url": "https://127.0.0.1/internal", "data": {"foo": "bar"}}
    )

    with patch(
        "app.modules.governance.domain.jobs.handlers.notifications.get_settings",
        return_value=SimpleNamespace(
            WEBHOOK_ALLOWED_DOMAINS=["example.com"],
            WEBHOOK_REQUIRE_HTTPS=True,
            WEBHOOK_BLOCK_PRIVATE_IPS=True,
        ),
    ):
        with pytest.raises(ValueError, match="private or link-local"):
            await handler.execute(job, db)


@pytest.mark.asyncio
async def test_webhook_retry_execute_generic_rejects_non_json_content_type(db):
    handler = WebhookRetryHandler()
    job = BackgroundJob(
        payload={
            "url": "https://example.com/webhook",
            "data": {"foo": "bar"},
            "headers": {"Content-Type": "text/plain"},
        }
    )

    with patch(
        "app.modules.governance.domain.jobs.handlers.notifications.get_settings",
        return_value=SimpleNamespace(
            WEBHOOK_ALLOWED_DOMAINS=["example.com"],
            WEBHOOK_REQUIRE_HTTPS=True,
            WEBHOOK_BLOCK_PRIVATE_IPS=True,
        ),
    ):
        with pytest.raises(ValueError, match="content-type"):
            await handler.execute(job, db)


@pytest.mark.asyncio
async def test_webhook_retry_execute_paystack(db):
    handler = WebhookRetryHandler()
    job = BackgroundJob(payload={"provider": "paystack"})

    with patch(
        "app.modules.billing.domain.billing.webhook_retry.process_paystack_webhook",
        new_callable=AsyncMock,
    ) as mock_process:
        mock_process.return_value = {"status": "processed"}

        result = await handler.execute(job, db)

        assert result == {"status": "processed"}
        mock_process.assert_awaited_with(job, db)
