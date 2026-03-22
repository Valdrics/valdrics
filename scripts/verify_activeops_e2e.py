import asyncio
import os
from uuid import uuid4
from sqlalchemy import select
from app.shared.db.session import async_session_maker
from app.shared.core.config import get_settings
from app.models.remediation import RemediationRequest, RemediationAction
# Import all models to ensure SQLAlchemy mappers are initialized

from app.models.tenant import Tenant, User
from app.modules.optimization.domain import RemediationService


def _allow_live_db_mutation() -> bool:
    return os.getenv("ALLOW_LIVE_VERIFICATION_MUTATIONS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


def _require_safe_environment() -> None:
    settings = get_settings()
    if settings.ENVIRONMENT == "production" and not _allow_live_db_mutation():
        raise RuntimeError(
            "Refusing to run ActiveOps E2E verification against production without "
            "ALLOW_LIVE_VERIFICATION_MUTATIONS=true"
        )


async def verify_active_ops() -> int:
    print("🚀 Starting ActiveOps Dry-Run Verification...")
    try:
        _require_safe_environment()
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1

    async with async_session_maker() as db:
        # 1. Ensure a tenant exists
        print("🏢 Ensuring test tenant exists...")
        result_tenant = await db.execute(select(Tenant).limit(1))
        tenant = result_tenant.scalar_one_or_none()

        if tenant is None:
            tenant = Tenant(name="E2E Test Tenant", plan="pro")
            db.add(tenant)
            await db.flush()
            print(f"✨ Created test tenant: {tenant.id}")
        else:
            print(f"✅ Using existing tenant: {tenant.id}")

        tenant_id = tenant.id

        # 2. Ensure a user exists for this tenant
        result_user = await db.execute(
            select(User).where(User.tenant_id == tenant_id).limit(1)
        )
        user = result_user.scalar_one_or_none()

        if user is None:
            user = User(
                id=uuid4(), tenant_id=tenant_id, email="e2e@example.com", role="admin"
            )
            db.add(user)
            await db.flush()
            print(f"✨ Created test user: {user.id}")
        else:
            print(f"✅ Using existing user: {user.id}")

        user_id = user.id

        # 3. Simulate finding a zombie with Provider Integration
        print("🔍 Creating remediation request via mock provider...")

        # P-8: Resource Ownership Verification - Create mock AWS connection
        from app.models.aws_connection import AWSConnection

        result_conn = await db.execute(
            select(AWSConnection).where(AWSConnection.tenant_id == tenant_id).limit(1)
        )
        connection = result_conn.scalar_one_or_none()
        if connection is None:
            connection = AWSConnection(
                tenant_id=tenant_id,
                aws_account_id="123456789012",
                # name="E2E Mock AWS",  # Removed: Not in model
                role_arn="arn:aws:iam::123456789012:role/ValdricsRole",
                external_id="e2e-external-id",
                region="us-east-1",
                status="active",
            )
            db.add(connection)
            await db.flush()
            print(f"✨ Created mock AWS connection: {connection.id}")
        else:
            print(f"✅ Using existing AWS connection: {connection.id}")

        # Mock credentials for the service
        mock_creds = {
            "AccessKeyId": "ASIA_MOCK_ID",
            "SecretAccessKey": "MOCK_SECRET",
            "SessionToken": "MOCK_TOKEN",
            "Expiration": "2099-01-01T00:00:00Z",
        }

        rem_service = RemediationService(
            db=db, region="us-east-1", credentials=mock_creds
        )

        req = await rem_service.create_request(
            tenant_id=tenant_id,
            user_id=user_id,
            resource_id="i-e2e-12345",
            resource_type="ec2_instance",
            action=RemediationAction.TERMINATE_INSTANCE,
            estimated_savings=15.75,
            provider="aws",
            connection_id=connection.id,  # REQUIRED for provider verification (BE-SEC-02)
        )

        await db.commit()
        print(f"✅ Created remediation request: {req.id}")

        # 4. Verify in DB
        result_persisted = await db.execute(
            select(RemediationRequest).where(RemediationRequest.id == req.id)
        )
        persisted = result_persisted.scalar_one_or_none()

        if persisted is None:
            raise RuntimeError("Persisted remediation request could not be reloaded")
        if persisted.status.value != "pending":
            raise RuntimeError(
                f"Unexpected remediation request status: {persisted.status.value}"
            )

        print(f"📊 Verified status: {persisted.status.value}")
        print("🏆 ActiveOps Verification PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(verify_active_ops()))
