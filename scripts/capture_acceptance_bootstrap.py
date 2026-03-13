"""In-process bootstrap for acceptance evidence capture."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from datetime import timedelta
from pathlib import Path

import httpx

from scripts.in_process_runtime_env import (
    build_unique_sqlite_database_url,
    configure_isolated_test_environment,
)


def _build_acceptance_capture_database_url() -> tuple[str, Path]:
    return build_unique_sqlite_database_url(prefix="valdrics-acceptance-capture")


def ensure_test_env_for_in_process(database_url: str) -> None:
    # Force a safe, deterministic runtime instead of inheriting an operator shell DATABASE_URL.
    configure_isolated_test_environment(database_url=database_url)


async def bootstrap_in_process_app_and_token() -> tuple[httpx.ASGITransport, str]:
    """
    Boot a local app instance and seed a minimal tenant+admin for evidence capture.

    This mode is intended for local dev/CI validation when a live environment is unavailable.
    """
    database_url, _sqlite_path = _build_acceptance_capture_database_url()
    ensure_test_env_for_in_process(database_url)

    # Import after env is set.
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.shared.db.base import Base
    from app.shared.db.session import get_engine, reset_db_runtime

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
        reset_db_runtime()
        async_engine = get_engine()
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
