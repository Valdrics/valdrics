"""Bootstrap a deterministic sqlite fixture for dashboard Playwright E2E and start the API."""

from __future__ import annotations

import argparse
import asyncio
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch
from uuid import UUID

from app.models.pricing import PricingPlan, TenantSubscription
from app.models.tenant import Tenant, User
from app.shared.core.config import reload_settings_from_environment
from app.shared.core.pricing import PricingTier, TIER_CONFIG
from app.shared.db.local_sqlite_bootstrap import (
    resolve_sqlite_database_path,
    bootstrap_local_sqlite_schema,
)
from app.shared.db.session import (
    async_session_maker,
    dispose_db_runtime,
    get_engine,
    mark_session_system_context,
    reset_db_runtime,
)


@dataclass(frozen=True, slots=True)
class PlaywrightE2EFixture:
    database_url: str
    tenant_id: UUID
    tenant_name: str
    user_id: UUID
    user_name: str
    email: str
    role: str
    persona: str
    tier: str


def _resolve_env(name: str, default: str) -> str:
    value = str(os.getenv(name, "")).strip()
    return value or default


def resolve_fixture() -> PlaywrightE2EFixture:
    return PlaywrightE2EFixture(
        database_url=_resolve_env(
            "DATABASE_URL",
            "sqlite+aiosqlite:////tmp/valdrics-dashboard-playwright.sqlite3",
        ),
        tenant_id=UUID(
            _resolve_env(
                "PLAYWRIGHT_E2E_TENANT_ID", "11111111-1111-4111-8111-111111111111"
            )
        ),
        tenant_name=_resolve_env(
            "PLAYWRIGHT_E2E_TENANT_NAME", "Playwright Test Tenant"
        ),
        user_id=UUID(
            _resolve_env(
                "PLAYWRIGHT_E2E_USER_ID", "22222222-2222-4222-8222-222222222222"
            )
        ),
        user_name=_resolve_env("PLAYWRIGHT_E2E_USER_NAME", "E2E Test User"),
        email=_resolve_env("PLAYWRIGHT_E2E_USER_EMAIL", "e2e@valdrics.test"),
        role=_resolve_env("PLAYWRIGHT_E2E_USER_ROLE", "admin").lower(),
        persona=_resolve_env("PLAYWRIGHT_E2E_USER_PERSONA", "engineering").lower(),
        tier=_resolve_env("PLAYWRIGHT_E2E_TIER", PricingTier.GROWTH.value).lower(),
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create a deterministic sqlite-backed Valdrics fixture for dashboard Playwright E2E "
            "and then start uvicorn against it."
        )
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser


def _is_temp_sqlite_path(path: Path) -> bool:
    temp_root = Path(tempfile.gettempdir()).resolve()
    try:
        path.resolve().relative_to(temp_root)
    except ValueError:
        return False
    return True


def _delete_sqlite_artifacts(database_path: Path | None) -> None:
    if database_path is None or not _is_temp_sqlite_path(database_path):
        return
    for suffix in ("", "-shm", "-wal", "-journal", ".bootstrap.lock"):
        target = (
            database_path.with_suffix(f"{database_path.suffix}.bootstrap.lock")
            if suffix == ".bootstrap.lock"
            else Path(f"{database_path}{suffix}")
        )
        target.unlink(missing_ok=True)


def _serialize_limits(raw_limits: dict[str, Any]) -> dict[str, Any]:
    serialized: dict[str, Any] = {}
    for key, value in raw_limits.items():
        if isinstance(value, set):
            serialized[key] = sorted(str(item) for item in value)
            continue
        if hasattr(value, "value"):
            serialized[key] = getattr(value, "value")
            continue
        serialized[key] = value
    return serialized


def _build_pricing_plan_rows() -> list[PricingPlan]:
    rows: list[PricingPlan] = []
    for tier in (
        PricingTier.FREE,
        PricingTier.STARTER,
        PricingTier.GROWTH,
        PricingTier.PRO,
    ):
        config = TIER_CONFIG[tier]
        price_cfg = config["price_usd"]
        monthly_price = float(
            price_cfg["monthly"] if isinstance(price_cfg, dict) else price_cfg or 0
        )
        rows.append(
            PricingPlan(
                id=tier.value,
                name=str(config.get("name", tier.value.capitalize())),
                description=str(config.get("description", "")),
                price_usd=monthly_price,
                features={},
                limits=_serialize_limits(dict(config.get("limits", {}))),
                display_features=[
                    str(item) for item in config.get("display_features", [])
                ],
                cta_text=str(config.get("cta", "Get Started")),
                is_popular=tier == PricingTier.GROWTH,
                is_active=True,
            )
        )
    return rows


async def _bootstrap_schema(database_url: str) -> None:
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": database_url,
            "TESTING": "false",
            "LOCAL_SQLITE_BOOTSTRAP": "true",
        },
        clear=False,
    ):
        settings = reload_settings_from_environment()
        reset_db_runtime()
        engine = get_engine()
        try:
            await bootstrap_local_sqlite_schema(
                engine=engine,
                effective_url=database_url,
                settings_obj=settings,
            )
        finally:
            await engine.dispose()
            await dispose_db_runtime()


async def _seed_fixture(fixture: PlaywrightE2EFixture) -> None:
    with patch.dict(
        os.environ,
        {
            "DATABASE_URL": fixture.database_url,
            "TESTING": "true",
        },
        clear=False,
    ):
        os.environ.pop("LOCAL_SQLITE_BOOTSTRAP", None)
        reload_settings_from_environment()
        reset_db_runtime()

        async with async_session_maker() as session:
            await mark_session_system_context(session)
            now = datetime.now(timezone.utc)
            session.add(
                Tenant(
                    id=fixture.tenant_id,
                    name=fixture.tenant_name,
                    plan=fixture.tier,
                    is_deleted=False,
                )
            )
            session.add(
                User(
                    id=fixture.user_id,
                    tenant_id=fixture.tenant_id,
                    email=fixture.email,
                    role=fixture.role,
                    persona=fixture.persona,
                    is_active=True,
                )
            )
            session.add(
                TenantSubscription(
                    tenant_id=fixture.tenant_id,
                    tier=fixture.tier,
                    status="active",
                    next_payment_date=now + timedelta(days=30),
                    billing_currency="USD",
                    billing_cycle="monthly",
                )
            )
            session.add_all(_build_pricing_plan_rows())
            await session.commit()

        await dispose_db_runtime()


async def _prepare_database(fixture: PlaywrightE2EFixture) -> None:
    database_path = resolve_sqlite_database_path(fixture.database_url)
    _delete_sqlite_artifacts(database_path)
    await _bootstrap_schema(fixture.database_url)
    await _seed_fixture(fixture)


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    fixture = resolve_fixture()
    asyncio.run(_prepare_database(fixture))

    os.environ["DATABASE_URL"] = fixture.database_url
    os.environ["TESTING"] = "true"
    os.environ.pop("LOCAL_SQLITE_BOOTSTRAP", None)
    reload_settings_from_environment()
    reset_db_runtime()

    import uvicorn

    uvicorn.run("app.main:app", host=args.host, port=args.port, log_level="info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
