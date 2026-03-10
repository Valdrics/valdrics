"""Smoke-test the non-testing local sqlite bootstrap path end to end."""

from __future__ import annotations

import argparse
import base64
import os
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient


def _build_local_env(database_path: Path) -> dict[str, str]:
    return {
        "APP_NAME": "Valdrics",
        "ENVIRONMENT": "local",
        "DEBUG": "false",
        "TESTING": "false",
        "API_URL": "http://127.0.0.1:8000",
        "FRONTEND_URL": "http://localhost:5174",
        "DATABASE_URL": f"sqlite+aiosqlite:///{database_path.as_posix()}",
        "DB_SSL_MODE": "disable",
        "LOCAL_SQLITE_BOOTSTRAP": "true",
        "ENABLE_SCHEDULER": "false",
        "REDIS_URL": "",
        "CSRF_SECRET_KEY": "c" * 64,
        "SUPABASE_JWT_SECRET": "s" * 64,
        "ENCRYPTION_KEY": base64.urlsafe_b64encode(b"x" * 32).decode("utf-8"),
        "KDF_SALT": base64.b64encode(b"y" * 32).decode("utf-8"),
        "INTERNAL_JOB_SECRET": "j" * 64,
        "ENFORCEMENT_APPROVAL_TOKEN_SECRET": "a" * 64,
        "ENFORCEMENT_EXPORT_SIGNING_SECRET": "e" * 64,
    }


class _STSResponse:
    status_code = 302


class _STSClient:
    async def get(self, _url: str) -> _STSResponse:
        return _STSResponse()


def run_local_sqlite_bootstrap_smoke(
    *, database_path: Path | None = None
) -> dict[str, Any]:
    if database_path is None:
        database_path = Path(tempfile.gettempdir()) / "valdrics_local_smoke.sqlite3"
    database_path = database_path.resolve()
    environment = _build_local_env(database_path)

    with patch.dict(os.environ, environment, clear=False):
        from app.shared.core.config import get_settings
        from app.shared.db.session import reset_db_runtime

        get_settings.cache_clear()
        reset_db_runtime()
        try:
            with patch("app.shared.core.tracing.setup_tracing", return_value=None):
                from app.main import app

            with (
                patch("app.main.EmissionsTracker", None),
                patch("app.shared.core.http.get_http_client", return_value=_STSClient()),
            ):
                with TestClient(app) as client:
                    response = client.get("/health")
                    response.raise_for_status()
                    payload = response.json()
        finally:
            reset_db_runtime()
            get_settings.cache_clear()

    if payload.get("status") not in {"healthy", "degraded"}:
        raise RuntimeError(f"Unexpected health status: {payload.get('status')!r}")
    if payload.get("database", {}).get("status") != "up":
        raise RuntimeError(f"Database health check failed: {payload.get('database')!r}")

    return {
        "status": payload["status"],
        "database_status": payload["database"]["status"],
        "database_engine": payload["database"].get("engine"),
        "cache_status": payload.get("redis", {}).get("status"),
        "aws_status": payload.get("aws", {}).get("status"),
        "background_jobs_status": payload.get("checks", {})
        .get("background_jobs", {})
        .get("status"),
        "database_path": database_path.as_posix(),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Smoke-test the local sqlite bootstrap path with TESTING=false."
    )
    parser.add_argument(
        "--database-path",
        type=Path,
        help="Optional sqlite database path for the smoke run.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    result = run_local_sqlite_bootstrap_smoke(database_path=args.database_path)
    print(
        "[local-sqlite-smoke] ok "
        f"status={result['status']} "
        f"db={result['database_path']} "
        f"engine={result['database_engine']} "
        f"background_jobs={result['background_jobs_status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
