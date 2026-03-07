"""In-process bootstrap for acceptance evidence capture."""

from __future__ import annotations

import asyncio
import os
from contextlib import suppress
from datetime import timedelta
from pathlib import Path

import httpx


def ensure_test_env_for_in_process() -> None:
    # Set a minimal, deterministic test environment so in-process evidence capture can run
    # without requiring a live DB/server. Values are safe and non-secret.
    os.environ.setdefault("TESTING", "true")
    os.environ.setdefault("DB_SSL_MODE", "disable")
    os.environ.setdefault(
        "SUPABASE_JWT_SECRET", "test-jwt-secret-for-testing-at-least-32-bytes"
    )
    os.environ.setdefault("ENCRYPTION_KEY", "32-byte-long-test-encryption-key")
    os.environ.setdefault("CSRF_SECRET_KEY", "test-csrf-secret-key-at-least-32-bytes")
    os.environ.setdefault(
        "KDF_SALT",
        "S0RGX1NBTFRfRk9SX1RFU1RJTkdfMzJfQllURVNfT0s=",
    )


async def bootstrap_in_process_app_and_token() -> tuple[httpx.ASGITransport, str]:
    """
    Boot a local app instance and seed a minimal tenant+admin for evidence capture.

    This mode is intended for local dev/CI validation when a live environment is unavailable.
    """
    ensure_test_env_for_in_process()

    # Use a file-backed sqlite DB so multiple connections share the same state.
    sqlite_path = Path("/tmp/valdrics_acceptance_capture.sqlite")
    os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{sqlite_path}")

    # Import after env is set.
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.shared.db.base import Base
    from app.shared.db.session import engine as async_engine

    # Register models referenced by relationships.
    import app.models.background_job  # noqa: F401
    import app.models.cloud  # noqa: F401
    import app.models.llm  # noqa: F401
    import app.models.notification_settings  # noqa: F401
    import app.models.remediation_settings  # noqa: F401
    import app.models.tenant  # noqa: F401
    import app.models.tenant_identity_settings  # noqa: F401
    import app.modules.governance.domain.security.audit_log  # noqa: F401

    # Keep event loop responsive during sqlite bootstrap to avoid rare deadlocks/hangs.
    stop_wakeup = asyncio.Event()

    async def _wakeup_loop() -> None:
        while not stop_wakeup.is_set():
            await asyncio.sleep(0.2)

    wakeup_task = asyncio.create_task(_wakeup_loop())

    try:
        # Create tables
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        from uuid import UUID

        from app.models.tenant import Tenant, User, UserRole
        from app.shared.core.auth import create_access_token

        tenant_id = UUID("00000000-0000-0000-0000-000000000001")
        user_id = UUID("00000000-0000-0000-0000-000000000002")
        email = "admin@valdrics.local"

        session_maker = async_sessionmaker(
            async_engine, class_=AsyncSession, expire_on_commit=False
        )
        async with session_maker() as db:
            # Seed tenant/user idempotently.
            tenant = await db.get(Tenant, tenant_id)
            if tenant is None:
                db.add(
                    Tenant(
                        id=tenant_id,
                        name="Acceptance Evidence Tenant",
                        plan="enterprise",
                    )
                )
            user = await db.get(User, user_id)
            if user is None:
                db.add(
                    User(
                        id=user_id,
                        email=email,
                        tenant_id=tenant_id,
                        role=UserRole.ADMIN.value,
                    )
                )
            await db.commit()

        token = create_access_token(
            {"sub": str(user_id), "email": email}, timedelta(hours=2)
        )

        from app.main import app as valdrics_app

        return httpx.ASGITransport(app=valdrics_app), token
    finally:
        stop_wakeup.set()
        wakeup_task.cancel()
        with suppress(asyncio.CancelledError):
            await wakeup_task
