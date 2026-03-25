"""
Global pytest fixtures for Valdrics test suite.

Provides:
- Async database session with SQLite in-memory
- Mock FastAPI test client
- Authentication fixtures
- Test data factories
- Test isolation utilities
"""

pytest_plugins = ("tests.unit.shared.adapters.aws_cur_test_helpers",)

import asyncio
import asyncio.runners as asyncio_runners
import inspect
import os
import sys
import threading
import warnings
from contextlib import suppress
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Set test environment BEFORE any app imports (Crucial for lru_cache behavior)
os.environ.setdefault("TESTING", "true")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-for-testing-at-least-32-bytes")
os.environ.setdefault(
    "ENFORCEMENT_APPROVAL_TOKEN_SECRET",
    "test-approval-token-secret-for-testing-at-least-32-bytes",
)
os.environ.setdefault(
    "ENFORCEMENT_EXPORT_SIGNING_SECRET",
    "test-export-signing-secret-for-testing-at-least-32-bytes",
)
os.environ.setdefault("ENCRYPTION_KEY", "32-byte-long-test-encryption-key")
os.environ.setdefault("CSRF_SECRET_KEY", "test-csrf-secret-key-at-least-32-bytes")
os.environ.setdefault("KDF_SALT", "S0RGX1NBTFRfRk9SX1RFU1RJTkdfMzJfQllURVNfT0s=")
os.environ.setdefault(
    "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN",
    "arn:aws:iam::000000000000:role/ValdricsTestControlPlane",
)
os.environ.setdefault("DB_SSL_MODE", "disable")
os.environ.setdefault("is_production", "false")
# Keep test startup deterministic even when local .env contains non-boolean DEBUG strings.
if os.environ.get("DEBUG", "").strip().lower() not in {
    "",
    "0",
    "1",
    "true",
    "false",
    "yes",
    "no",
    "on",
    "off",
}:
    os.environ["DEBUG"] = "false"

# Mock heavy dependencies only if they cause issues in specific environments
# sys.modules["codecarbon"] = MagicMock()
# sys.modules["pandas"] = MagicMock()
# sys.modules["pyarrow"] = MagicMock()
# sys.modules["pyarrow.parquet"] = MagicMock()
# sys.modules["pyarrow.lib"] = MagicMock()
# We don't mock numpy directly here to allow other libs that might need it a bit,
# but we mock the things that trigger the re-load of native extensions.

from uuid import uuid4
from decimal import Decimal
import pytest
import pytest_asyncio
import pytest_asyncio.plugin as pytest_asyncio_plugin
import tenacity
from typing import AsyncGenerator, Generator, Optional
from datetime import datetime, timezone
from app.models.tenant import UserRole
from app.shared.core.pricing import PricingTier
from app.shared.testing.sqlite_artifact_cleanup import (
    build_sqlite_test_database_path,
    cleanup_sqlite_test_artifacts,
)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from fastapi.testclient import TestClient
    from httpx import AsyncClient

# Import test isolation utilities

# Environment variables are already set at the top

# Import all models to register them in SQLAlchemy mapper globally for all tests


_REAL_ASYNCIO_SLEEP = asyncio.sleep


async def _heartbeat_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        await _REAL_ASYNCIO_SLEEP(0.01)


class _AsyncioHeartbeat:
    def __init__(self) -> None:
        self._stop = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def __aenter__(self) -> "_AsyncioHeartbeat":
        self._task = asyncio.create_task(_heartbeat_loop(self._stop))
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            with suppress(asyncio.CancelledError):
                await self._task


async def _await_with_asyncio_heartbeat(awaitable):
    async with _AsyncioHeartbeat():
        return await awaitable


def _run_async_with_heartbeat(awaitable):
    return asyncio.run(_await_with_asyncio_heartbeat(awaitable))


def _start_loop_waker(loop: asyncio.AbstractEventLoop) -> tuple[threading.Event, threading.Thread]:
    stop = threading.Event()

    def _wake_loop() -> None:
        while not stop.wait(0.01):
            try:
                loop.call_soon_threadsafe(lambda: None)
            except RuntimeError:
                break

    wake_thread = threading.Thread(
        target=_wake_loop,
        name="pytest-event-loop-waker",
        daemon=True,
    )
    wake_thread.start()
    return stop, wake_thread


_BASE_PYTEST_ASYNCIO_RUNNER = pytest_asyncio_plugin.Runner


class _WakefulPytestAsyncioRunner(_BASE_PYTEST_ASYNCIO_RUNNER):
    _shutdown_timeout_seconds = 5.0

    def _warn_on_shutdown_timeout(
        self,
        *,
        step: str,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        pending = [
            repr(task)
            for task in asyncio.all_tasks(loop)
            if not task.done()
        ]
        warnings.warn(
            (
                f"pytest-asyncio runner teardown timed out during {step}; "
                f"pending tasks: {pending}"
            ),
            RuntimeWarning,
            stacklevel=2,
        )

    def _cancel_all_tasks_with_timeout(
        self,
        loop: asyncio.AbstractEventLoop,
    ) -> None:
        to_cancel = asyncio.all_tasks(loop)
        if not to_cancel:
            return

        for task in to_cancel:
            task.cancel()

        try:
            loop.run_until_complete(
                asyncio.wait_for(
                    asyncio.gather(*to_cancel, return_exceptions=True),
                    timeout=self._shutdown_timeout_seconds,
                )
            )
        except TimeoutError:
            self._warn_on_shutdown_timeout(step="cancel_all_tasks", loop=loop)

    def _run_shutdown_step_with_timeout(
        self,
        loop: asyncio.AbstractEventLoop,
        *,
        step: str,
        awaitable,
    ) -> None:
        try:
            loop.run_until_complete(
                asyncio.wait_for(
                    awaitable,
                    timeout=self._shutdown_timeout_seconds,
                )
            )
        except TimeoutError:
            self._warn_on_shutdown_timeout(step=step, loop=loop)

    def close(self) -> None:
        loop = getattr(self, "_loop", None)
        if loop is None or loop.is_closed():
            super().close()
            return

        stop, wake_thread = _start_loop_waker(loop)
        try:
            if self._state is not asyncio_runners._State.INITIALIZED:
                return
            try:
                self._cancel_all_tasks_with_timeout(loop)
                self._run_shutdown_step_with_timeout(
                    loop,
                    step="shutdown_asyncgens",
                    awaitable=loop.shutdown_asyncgens(),
                )
                self._run_shutdown_step_with_timeout(
                    loop,
                    step="shutdown_default_executor",
                    awaitable=loop.shutdown_default_executor(
                        asyncio_runners.constants.THREAD_JOIN_TIMEOUT
                    ),
                )
            finally:
                if self._set_event_loop:
                    asyncio_runners.events.set_event_loop(None)
                loop.close()
                self._loop = None
                self._state = asyncio_runners._State.CLOSED
        finally:
            stop.set()
            wake_thread.join(timeout=1)


if pytest_asyncio_plugin.Runner is not _WakefulPytestAsyncioRunner:
    pytest_asyncio_plugin.Runner = _WakefulPytestAsyncioRunner


async def _dispose_async_engine(engine) -> None:
    await _await_with_asyncio_heartbeat(engine.dispose())


def _register_models():
    # Import all models to register them in SQLAlchemy mapper globally for all tests
    # We do NOT catch ImportError anymore to expose broken models immediately
    from app.models.cloud import CloudAccount, CostRecord  # noqa: F401
    from app.models.aws_connection import AWSConnection  # noqa: F401
    from app.models.azure_connection import AzureConnection  # noqa: F401
    from app.models.gcp_connection import GCPConnection  # noqa: F401
    from app.models.saas_connection import SaaSConnection  # noqa: F401
    from app.models.license_connection import LicenseConnection  # noqa: F401
    from app.models.tenant import Tenant  # noqa: F401
    from app.models.remediation import RemediationRequest  # noqa: F401
    from app.models.security import OIDCKey  # noqa: F401
    from app.models.notification_settings import NotificationSettings  # noqa: F401
    from app.models.tenant_identity_settings import TenantIdentitySettings  # noqa: F401
    from app.models.sso_domain_mapping import SsoDomainMapping  # noqa: F401
    from app.models.scim_group import ScimGroup, ScimGroupMember  # noqa: F401
    from app.models.background_job import BackgroundJob  # noqa: F401
    from app.models.llm import LLMUsage, LLMBudget  # noqa: F401
    from app.models.attribution import AttributionRule  # noqa: F401
    from app.models.anomaly_marker import AnomalyMarker  # noqa: F401
    from app.models.carbon_settings import CarbonSettings  # noqa: F401
    from app.models.carbon_factors import CarbonFactorSet, CarbonFactorUpdateLog  # noqa: F401
    from app.models.discovered_account import DiscoveredAccount  # noqa: F401
    from app.models.discovery_candidate import DiscoveryCandidate  # noqa: F401
    from app.shared.core.pricing import PricingTier  # noqa: F401
    from app.models.remediation_settings import RemediationSettings  # noqa: F401
    from app.models.optimization import OptimizationStrategy, StrategyRecommendation  # noqa: F401
    from app.models.cost_audit import CostAuditLog  # noqa: F401
    from app.models.invoice import ProviderInvoice  # noqa: F401
    from app.models.public_sales_inquiry import PublicSalesInquiry  # noqa: F401
    from app.models.realized_savings import RealizedSavingsEvent  # noqa: F401
    from app.models.tenant_growth_funnel_snapshot import (  # noqa: F401
        TenantGrowthFunnelSnapshot,
    )
    from app.models.enforcement import (  # noqa: F401
        EnforcementApprovalRequest,
        EnforcementBudgetAllocation,
        EnforcementCreditGrant,
        EnforcementDecision,
        EnforcementPolicy,
    )
    from app.models.unit_economics_settings import UnitEconomicsSettings  # noqa: F401
    from app.modules.governance.domain.security.audit_log import AuditLog  # noqa: F401


def pytest_configure(config):
    # Finding #5: Move model registration to pytest_configure
    # This prevents circular imports at module load time and 
    # ensures models are registered before any tests run.
    _register_models()


def _build_mock_async_session_maker(session: AsyncMock) -> MagicMock:
    """Create an async_session_maker-compatible mock for tests that do not need DB I/O."""
    session_maker = MagicMock()
    context_manager = AsyncMock()
    context_manager.__aenter__.return_value = session
    context_manager.__aexit__.return_value = None
    session_maker.return_value = context_manager
    return session_maker


def _build_async_db_override(session: object):
    async def _override():
        return session

    return _override


def pytest_sessionstart(session: pytest.Session) -> None:
    del session
    cleanup_sqlite_test_artifacts(Path.cwd())


def pytest_sessionfinish(
    session: pytest.Session, exitstatus: int | pytest.ExitCode
) -> None:
    del session, exitstatus
    cleanup_sqlite_test_artifacts(Path.cwd())


# Mock tiktoken if not installed
if "tiktoken" not in sys.modules:
    sys.modules["tiktoken"] = MagicMock()


# Mock tenacity to avoid retry delays
def mock_retry(*args, **kwargs):
    def decorator(f):
        return f

    return decorator


tenacity.retry = mock_retry


# ============================================================================
# Async Database Fixtures
# ============================================================================


@pytest.fixture
def async_engine(tmp_path_factory):
    """Create async SQLite engine for testing using a fresh sync-bootstrapped file DB."""
    from sqlalchemy import create_engine
    from sqlalchemy.ext.asyncio import create_async_engine
    from app.shared.db.base import Base

    db_path = build_sqlite_test_database_path(tmp_path_factory.mktemp("sqlite-db"))
    _register_models()
    sync_engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    try:
        Base.metadata.create_all(sync_engine)
    finally:
        sync_engine.dispose()

    db_url = f"sqlite+aiosqlite:///{db_path.as_posix()}"

    engine = create_async_engine(db_url, echo=False)
    yield engine
    _run_async_with_heartbeat(_dispose_async_engine(engine))

    for suffix in ("", "-journal", "-shm", "-wal"):
        Path(f"{db_path}{suffix}").unlink(missing_ok=True)


@pytest_asyncio.fixture
async def db_session(async_engine) -> AsyncGenerator["AsyncSession", None]:
    """Provide an async session backed by an isolated file-cloned SQLite schema."""
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    # Create session factory
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Provide session with proper cleanup
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================


@pytest.fixture
def app(reset_settings_cache, set_testing_env):
    """Use the real Valdrics app for integration tests."""
    del reset_settings_cache, set_testing_env
    from app.main import app as valdrics_app
    from app.main import settings

    # Force TESTING mode to True to bypass CSRF and other secure middlewares
    settings.TESTING = True
    return valdrics_app


@pytest.fixture
def client(app, db_session, async_engine) -> Generator["TestClient", None, None]:
    """Sync test client implemented on top of ASGITransport with an isolated DB override."""
    from httpx import AsyncClient, ASGITransport
    from app.shared.db.session import get_db, get_system_db
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
    from contextlib import ExitStack

    old_override = app.dependency_overrides.get(get_db)
    old_system_override = app.dependency_overrides.get(get_system_db)
    test_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    modules_to_patch = [
        "app.shared.db.session.async_session_maker",
        "app.shared.connections.oidc.async_session_maker",
        "app.modules.governance.api.v1.jobs.async_session_maker",
        "app.modules.governance.domain.jobs.cur_ingestion.async_session_maker",
        "app.modules.governance.domain.jobs.processor.async_session_maker",
        "app.tasks.scheduler_tasks.async_session_maker",
        "app.shared.llm.pricing_data.async_session_maker",
        "app.main.async_session_maker",
    ]

    class _SyncClientAdapter:
        def __init__(self, bound_app) -> None:
            self.app = bound_app

        def request(self, method: str, *args, **kwargs):
            async def _send():
                transport = ASGITransport(app=self.app)
                async with AsyncClient(
                    transport=transport,
                    base_url="http://test",
                ) as async_client:
                    return await async_client.request(method, *args, **kwargs)

            return _run_async_with_heartbeat(_send())

        def get(self, *args, **kwargs):
            return self.request("GET", *args, **kwargs)

        def post(self, *args, **kwargs):
            return self.request("POST", *args, **kwargs)

        def delete(self, *args, **kwargs):
            return self.request("DELETE", *args, **kwargs)

        def options(self, *args, **kwargs):
            return self.request("OPTIONS", *args, **kwargs)

        def close(self) -> None:
            return None

    with ExitStack() as stack:
        for target in modules_to_patch:
            try:
                stack.enter_context(patch(target, test_session_maker))
            except (ImportError, AttributeError):
                continue

        app.dependency_overrides[get_db] = _build_async_db_override(db_session)
        app.dependency_overrides[get_system_db] = _build_async_db_override(db_session)

        c = _SyncClientAdapter(app)
        try:
            yield c
        finally:
            c.close()
            if old_override:
                app.dependency_overrides[get_db] = old_override
            else:
                app.dependency_overrides.pop(get_db, None)

            if old_system_override:
                app.dependency_overrides[get_system_db] = old_system_override
            else:
                app.dependency_overrides.pop(get_system_db, None)


@pytest_asyncio.fixture
async def async_client(
    app,
    db_session,
    async_engine,
) -> AsyncGenerator["AsyncClient", None]:
    """Async test client for FastAPI with a real isolated SQLite session."""
    from contextlib import ExitStack
    from httpx import AsyncClient, ASGITransport
    from app.shared.db.session import get_db, get_system_db
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    old_override = app.dependency_overrides.get(get_db)
    old_system_override = app.dependency_overrides.get(get_system_db)
    test_session_maker = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    modules_to_patch = [
        "app.shared.db.session.async_session_maker",
        "app.shared.connections.oidc.async_session_maker",
        "app.modules.governance.api.v1.jobs.async_session_maker",
        "app.modules.governance.domain.jobs.cur_ingestion.async_session_maker",
        "app.modules.governance.domain.jobs.processor.async_session_maker",
        "app.tasks.scheduler_tasks.async_session_maker",
        "app.shared.llm.pricing_data.async_session_maker",
        "app.main.async_session_maker",
    ]

    with ExitStack() as stack:
        for target in modules_to_patch:
            try:
                stack.enter_context(patch(target, test_session_maker))
            except (ImportError, AttributeError):
                continue

        app.dependency_overrides[get_db] = _build_async_db_override(db_session)
        app.dependency_overrides[get_system_db] = _build_async_db_override(db_session)

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                setattr(client, "app", app)
                yield client
        finally:
            if old_override:
                app.dependency_overrides[get_db] = old_override
            else:
                app.dependency_overrides.pop(get_db, None)

            if old_system_override:
                app.dependency_overrides[get_system_db] = old_system_override
            else:
                app.dependency_overrides.pop(get_system_db, None)


@pytest_asyncio.fixture
async def ac(async_client):
    """Alias for async_client to match integration tests."""
    return async_client


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Minimal async DB session for smoke tests that should not hit real storage."""
    session = AsyncMock()
    session.execute = AsyncMock(return_value=MagicMock())
    session.commit = AsyncMock(return_value=None)
    session.rollback = AsyncMock(return_value=None)
    session.refresh = AsyncMock(return_value=None)
    session.flush = AsyncMock(return_value=None)
    session.close = AsyncMock(return_value=None)
    session.delete = AsyncMock(return_value=None)
    session.merge = AsyncMock(side_effect=lambda obj: obj)
    session.get = AsyncMock(return_value=None)
    return session


@pytest_asyncio.fixture
async def async_client_no_db(
    app,
    mock_db_session,
) -> AsyncGenerator["AsyncClient", None]:
    """Async client that overrides DB dependencies with a mock session for smoke tests."""
    from contextlib import ExitStack
    from httpx import AsyncClient, ASGITransport
    from app.shared.db.session import get_db, get_system_db

    old_override = app.dependency_overrides.get(get_db)
    old_system_override = app.dependency_overrides.get(get_system_db)
    mock_session_maker = _build_mock_async_session_maker(mock_db_session)
    modules_to_patch = [
        "app.shared.db.session.async_session_maker",
        "app.shared.connections.oidc.async_session_maker",
        "app.modules.governance.api.v1.jobs.async_session_maker",
        "app.modules.governance.domain.jobs.cur_ingestion.async_session_maker",
        "app.modules.governance.domain.jobs.processor.async_session_maker",
        "app.tasks.scheduler_tasks.async_session_maker",
        "app.shared.llm.pricing_data.async_session_maker",
        "app.main.async_session_maker",
    ]

    with ExitStack() as stack:
        for target in modules_to_patch:
            try:
                stack.enter_context(patch(target, mock_session_maker))
            except (ImportError, AttributeError):
                continue

        app.dependency_overrides[get_db] = _build_async_db_override(mock_db_session)
        app.dependency_overrides[get_system_db] = _build_async_db_override(mock_db_session)

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                setattr(client, "app", app)
                yield client
        finally:
            if old_override:
                app.dependency_overrides[get_db] = old_override
            else:
                app.dependency_overrides.pop(get_db, None)

            if old_system_override:
                app.dependency_overrides[get_system_db] = old_system_override
            else:
                app.dependency_overrides.pop(get_system_db, None)


@pytest_asyncio.fixture
async def ac_no_db(async_client_no_db):
    """Alias for async_client_no_db for endpoint smoke tests."""
    return async_client_no_db


@pytest_asyncio.fixture
async def db(db_session):
    """Alias for db_session to match integration tests."""
    return db_session


# ============================================================================
# Authentication Fixtures
# ============================================================================


@pytest.fixture
def mock_tenant_id():
    """Mock tenant ID for testing."""
    return uuid4()


@pytest.fixture
def mock_user_id():
    """Mock user ID for testing."""
    return uuid4()


@pytest.fixture
def mock_user(mock_tenant_id, mock_user_id):
    """Create mock CurrentUser for testing."""
    from app.shared.core.auth import CurrentUser

    return CurrentUser(
        id=mock_user_id,
        email="test@valdrics.io",
        tenant_id=mock_tenant_id,
        role=UserRole.ADMIN,
        tier=PricingTier.PRO,
    )


@pytest.fixture
def member_user(mock_tenant_id, mock_user_id):
    """Create mock member user for testing."""
    from app.shared.core.auth import CurrentUser

    return CurrentUser(
        id=mock_user_id,
        email="member@valdrics.io",
        tenant_id=mock_tenant_id,
        role=UserRole.MEMBER,
        tier=PricingTier.PRO,
    )


@pytest.fixture
async def test_tenant(db):
    """Create a test tenant for API tests."""
    from app.models.tenant import Tenant

    tenant = Tenant(id=uuid4(), name="API Test Tenant", plan="pro", is_deleted=False)
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return tenant


@pytest.fixture
async def test_remediation_request(db, test_tenant):
    """Create a test remediation request."""
    from app.models.remediation import (
        RemediationRequest,
        RemediationStatus,
        RemediationAction,
    )

    request = RemediationRequest(
        id=uuid4(),
        tenant_id=test_tenant.id,
        resource_id="i-test123",
        resource_type="ec2_instance",
        action=RemediationAction.STOP_INSTANCE,
        status=RemediationStatus.PENDING,
        requested_by_user_id=uuid4(),
        estimated_monthly_savings=Decimal("50.00"),
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request


# ============================================================================
# Mock Cloud Connection Fixtures
# ============================================================================


@pytest.fixture
def mock_aws_connection(mock_tenant_id):
    """Create mock AWS connection."""
    conn = MagicMock()
    conn.id = uuid4()
    conn.tenant_id = mock_tenant_id
    conn.provider = "aws"
    conn.role_arn = "arn:aws:iam::123456789012:role/ValdricsReadOnly"
    conn.external_id = "valdrics-test-external-id"
    conn.region = "us-east-1"
    conn.is_cur_enabled = True
    conn.cur_bucket = "valdrics-cur-test"
    conn.status = "active"
    return conn


@pytest.fixture
def mock_gcp_connection(mock_tenant_id):
    """Create mock GCP connection."""
    conn = MagicMock()
    conn.id = uuid4()
    conn.tenant_id = mock_tenant_id
    conn.provider = "gcp"
    conn.project_id = "valdrics-test-project"
    conn.billing_export_dataset = "billing_export"
    conn.status = "active"
    return conn


@pytest.fixture
def mock_azure_connection(mock_tenant_id):
    """Create mock Azure connection."""
    conn = MagicMock()
    conn.id = uuid4()
    conn.tenant_id = mock_tenant_id
    conn.provider = "azure"
    conn.subscription_id = "sub-12345678-test"
    conn.tenant_azure_id = "tenant-azure-test"
    conn.status = "active"
    return conn


# ============================================================================
# Test Data Factories
# ============================================================================


@pytest.fixture
def zombie_factory():
    """Factory for creating test zombie resources."""

    def _create_zombie(
        resource_type: str = "EC2",
        monthly_cost: float = 50.0,
        confidence: float = 0.85,
    ):
        return {
            "resource_id": f"arn:aws:ec2:us-east-1:123456789012:instance/i-{uuid4().hex[:8]}",
            "resource_type": resource_type,
            "resource_name": f"test-{resource_type.lower()}-{uuid4().hex[:4]}",
            "monthly_cost": Decimal(str(monthly_cost)),
            "confidence_score": confidence,
            "recommendation": f"Delete idle {resource_type}",
            "action": f"terminate_{resource_type.lower()}",
            "explainability_notes": f"Test {resource_type} has been idle for 7+ days",
        }

    return _create_zombie


@pytest.fixture
def cost_record_factory():
    """Factory for creating test cost records."""

    def _create_cost_record(
        service: str = "Amazon EC2",
        cost: float = 10.0,
        usage_date: Optional[str] = None,
    ):
        return {
            "service": service,
            "cost": Decimal(str(cost)),
            "usage_date": usage_date or datetime.now(timezone.utc).date().isoformat(),
            "resource_id": f"i-{uuid4().hex[:8]}",
            "region": "us-east-1",
        }

    return _create_cost_record


# ============================================================================
# Utility Fixtures
# ============================================================================


@pytest.fixture
def event_loop():
    """
    Provide a test event loop with an external wake thread.

    In constrained runners, cross-thread callbacks are not always sufficient to
    wake the loop promptly. The wake thread keeps the selector responsive during
    test execution and loop shutdown.
    """
    loop = asyncio.new_event_loop()
    try:
        previous_loop = asyncio.get_event_loop_policy().get_event_loop()
    except RuntimeError:
        previous_loop = None

    asyncio.set_event_loop(loop)
    stop, wake_thread = _start_loop_waker(loop)
    try:
        yield loop
    finally:
        stop.set()
        wake_thread.join(timeout=1)
        try:
            loop.run_until_complete(loop.shutdown_asyncgens())
        except RuntimeError:
            pass
        try:
            loop.run_until_complete(loop.shutdown_default_executor())
        except RuntimeError:
            pass
        asyncio.set_event_loop(previous_loop)
        loop.close()


@pytest.fixture(autouse=True)
def set_testing_env():
    """Ensure TESTING is set for all tests."""
    os.environ["TESTING"] = "true"
    yield


@pytest_asyncio.fixture(autouse=True)
async def keep_asyncio_loop_awake(request):
    if not inspect.iscoroutinefunction(getattr(request.node, "obj", None)):
        yield
        return

    async with _AsyncioHeartbeat():
        yield


@pytest.fixture(autouse=True)
def clean_dependency_overrides():
    """Clear dependency overrides without forcing app import for non-API tests."""
    yield

    import sys

    if "app.main" not in sys.modules:
        return

    import app.main as app_main

    app_main.app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_shared_http_clients():
    """Reset shared HTTP client singletons between tests to avoid loop/state bleed."""
    from app.shared.core.http import close_http_client

    _run_async_with_heartbeat(close_http_client())
    try:
        yield
    finally:
        _run_async_with_heartbeat(close_http_client())


@pytest.fixture(autouse=True)
def reset_settings_cache():
    """Ensure settings are fresh for every test to prevent leakage."""
    from app.shared.core.config import get_settings
    from app.shared.db.session import dispose_db_runtime
    import sys

    # 1. Clear the lru_cache
    get_settings.cache_clear()

    # 2. Reset the singleton if it was modified in-place
    # (Finding #L2: attribute-level mutation survives cache_clear if refs are held)
    settings = get_settings()
    settings.TESTING = True

    # Keep already-imported app modules aligned with the refreshed settings object.
    if "app.main" in sys.modules:
        import app.main as app_main

        app_main.settings = settings

    # 3. Reset DB runtime
    _run_async_with_heartbeat(dispose_db_runtime())

    yield

    # Teardown: ensure we don't leave it in a broken state
    get_settings.cache_clear()
    _run_async_with_heartbeat(dispose_db_runtime())
    
    # 4. Sync app.main if it exists
    if "app.main" in sys.modules:
        import app.main as app_main
        app_main.settings = get_settings()


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=False)
    return redis


@pytest.fixture
def mock_llm_response():
    """Mock LLM analysis response."""
    return {
        "summary": "Test analysis summary",
        "recommendations": ["Recommendation 1", "Recommendation 2"],
        "confidence": 0.9,
        "tokens_used": {"input": 500, "output": 200},
    }
