import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from scripts.in_process_runtime_env import build_isolated_test_environment_values


REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = REPO_ROOT / "app" / "static"


@pytest.fixture
def client():
    from app.main import app

    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def mock_lifespan_deps():
    mock_dispose = AsyncMock()

    class _EngineStub:
        async def dispose(self):
            await mock_dispose()

    with (
        patch("os.makedirs") as mock_makedirs,
        patch("app.main.EmissionsTracker") as mock_tracker,
        patch(
            "app.modules.governance.domain.scheduler.SchedulerService"
        ) as mock_scheduler,
        patch("app.main.get_engine", return_value=_EngineStub()),
    ):
        yield {
            "makedirs": mock_makedirs,
            "tracker": mock_tracker.return_value,
            "scheduler": mock_scheduler.return_value,
            "dispose": mock_dispose,
        }


@pytest.mark.asyncio
async def test_lifespan_flow(mock_lifespan_deps):
    """Test app lifespan setup and teardown."""
    from app.main import lifespan, app

    with (
        patch("app.main.should_bootstrap_local_sqlite", return_value=False),
        patch("app.main.reset_db_runtime"),
    ):
        async with lifespan(app):
            mock_lifespan_deps["makedirs"].assert_called_with(
                "/tmp/valdrics",
                exist_ok=True,
            )

    mock_lifespan_deps["dispose"].assert_called_once()


@pytest.mark.asyncio
async def test_lifespan_skips_scheduler_when_disabled(mock_lifespan_deps):
    from app.main import lifespan, app

    with patch("app.main.reload_settings_from_environment") as mock_reload:
        from app.main import settings as live_settings

        mock_reload.return_value = live_settings
        live_settings.TESTING = False
        live_settings.REDIS_URL = "redis://localhost:6379/0"
        live_settings.ENABLE_SCHEDULER = False

        with (
            patch("app.main.should_bootstrap_local_sqlite", return_value=False),
            patch("app.main.reset_db_runtime"),
        ):
            async with lifespan(app):
                pass

    mock_lifespan_deps["scheduler"].start.assert_not_called()


@pytest.mark.asyncio
async def test_lifespan_bootstraps_local_sqlite_when_enabled(mock_lifespan_deps):
    from app.main import app, lifespan

    with (
        patch("app.main.should_bootstrap_local_sqlite", return_value=True),
        patch("app.main.bootstrap_local_sqlite_schema", new_callable=AsyncMock) as bootstrap,
        patch("app.main.reset_db_runtime"),
    ):
        async with lifespan(app):
            pass

    bootstrap.assert_awaited_once()


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_liveness_endpoint(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_check_healthy(client):
    mock_health = {
        "status": "healthy",
        "database": {"status": "up"},
        "redis": {"status": "up"},
        "aws": {"status": "up"},
    }
    with patch(
        "app.shared.core.health.HealthService.check_all", new_callable=AsyncMock
    ) as mock_check:
        mock_check.return_value = mock_health
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_valdrics_exception_handler(client):
    from app.main import app
    from app.shared.core.exceptions import ValdricsException

    @app.get("/test-valdrics-exc")
    async def trigger_exc():
        raise ValdricsException(
            message="Test message", code="test_code", status_code=418
        )

    response = client.get("/test-valdrics-exc")
    assert response.status_code == 418
    assert response.json()["error"]["code"] == "test_code"


def test_generic_exception_handler(client):
    from app.main import app

    @app.get("/test-generic-exc")
    async def trigger_exc():
        raise Exception("Boom")

    response = client.get("/test-generic-exc")
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"


def test_docs_endpoints(client):
    from app.main import settings as live_settings

    original_environment = live_settings.ENVIRONMENT
    original_docs_public = live_settings.EXPOSE_API_DOCUMENTATION_PUBLICLY
    live_settings.ENVIRONMENT = "development"
    live_settings.EXPOSE_API_DOCUMENTATION_PUBLICLY = False
    # Swagger
    try:
        with patch("app.main.render_swagger_ui_html") as mock_swagger:
            mock_swagger.return_value = MagicMock()
            mock_swagger.return_value.body = b"<html></html>"
            mock_swagger.return_value.status_code = 200
            response = client.get("/docs")
            assert response.status_code == 200

        # Redoc
        with patch("app.main.render_redoc_ui_html") as mock_redoc:
            mock_redoc.return_value = MagicMock()
            mock_redoc.return_value.body = b"<html></html>"
            mock_redoc.return_value.status_code = 200
            response = client.get("/redoc")
            assert response.status_code == 200
    finally:
        live_settings.ENVIRONMENT = original_environment
        live_settings.EXPOSE_API_DOCUMENTATION_PUBLICLY = original_docs_public


def test_docs_static_assets_exist() -> None:
    expected_assets = {
        "favicon.png": 1024,
        "swagger-ui-bundle.js": 100_000,
        "swagger-ui.css": 10_000,
        "redoc.standalone.js": 100_000,
    }

    for asset_name, minimum_size_bytes in expected_assets.items():
        asset_path = STATIC_DIR / asset_name
        assert asset_path.exists(), asset_name
        assert asset_path.stat().st_size >= minimum_size_bytes, asset_name


def test_docs_endpoints_render_with_real_static_assets(client):
    from app.main import settings as live_settings

    original_environment = live_settings.ENVIRONMENT
    original_docs_public = live_settings.EXPOSE_API_DOCUMENTATION_PUBLICLY
    live_settings.ENVIRONMENT = "development"
    live_settings.EXPOSE_API_DOCUMENTATION_PUBLICLY = False
    try:
        docs_response = client.get("/docs")
        redoc_response = client.get("/redoc")
        static_response = client.get("/static/redoc.standalone.js")

        assert docs_response.status_code == 200
        assert redoc_response.status_code == 200
        assert static_response.status_code == 200
        assert 'src="/static/swagger-ui-bundle.js"' in docs_response.text
        assert 'href="/static/swagger-ui.css"' in docs_response.text
        assert 'src="/static/redoc.standalone.js"' in redoc_response.text
        assert 'integrity="sha384-' in docs_response.text
        assert 'integrity="sha384-' in redoc_response.text
        assert len(static_response.text) >= 100_000
    finally:
        live_settings.ENVIRONMENT = original_environment
        live_settings.EXPOSE_API_DOCUMENTATION_PUBLICLY = original_docs_public


def test_app_import_is_stable_outside_repo_cwd(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("DEBUG=release\n", encoding="utf-8")
    env = os.environ.copy()
    env.pop("DEBUG", None)
    env.update(
        build_isolated_test_environment_values(
            database_url="sqlite+aiosqlite:///:memory:"
        )
    )
    env.update(
        {
            "PYTHONPATH": str(REPO_ROOT),
            "ENFORCEMENT_APPROVAL_TOKEN_SECRET": (
                "test-approval-token-secret-for-testing-at-least-32-bytes"
            ),
            "ENFORCEMENT_EXPORT_SIGNING_SECRET": (
                "test-export-signing-secret-for-testing-at-least-32-bytes"
            ),
            "AWS_ASSUME_ROLE_TRUST_PRINCIPAL_ARN": (
                "arn:aws:iam::000000000000:role/ValdricsTestControlPlane"
            ),
        }
    )
    script = textwrap.dedent(
        """
        from app.main import valdrics_app
        from app.shared.core.runtime_paths import DEFAULT_ENV_FILE, STATIC_DIR

        static_mount = next(
            route for route in valdrics_app.routes if getattr(route, "path", None) == "/static"
        )
        print(DEFAULT_ENV_FILE)
        print(STATIC_DIR)
        print(static_mount.app.directory)
        """
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    output_lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    assert output_lines == [
        str(REPO_ROOT / ".env"),
        str(STATIC_DIR),
        str(STATIC_DIR),
    ]


def test_docs_endpoints_blocked_in_strict_env(client):
    from app.main import settings as live_settings

    original_environment = live_settings.ENVIRONMENT
    original_docs_public = live_settings.EXPOSE_API_DOCUMENTATION_PUBLICLY
    original_testing = live_settings.TESTING
    live_settings.ENVIRONMENT = "production"
    live_settings.EXPOSE_API_DOCUMENTATION_PUBLICLY = False
    live_settings.TESTING = False
    try:
        assert client.get("/docs").status_code == 404
        assert client.get("/redoc").status_code == 404
        assert client.get("/openapi.json").status_code == 404
    finally:
        live_settings.ENVIRONMENT = original_environment
        live_settings.EXPOSE_API_DOCUMENTATION_PUBLICLY = original_docs_public
        live_settings.TESTING = original_testing
