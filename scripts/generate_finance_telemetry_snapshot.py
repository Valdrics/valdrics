#!/usr/bin/env python3
"""Generate finance telemetry snapshot evidence from live DB execution."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scripts.collect_finance_telemetry_snapshot import (
    _default_window,
    _parse_date,
    _window_bounds,
    collect_snapshot,
)
from scripts.verify_finance_telemetry_snapshot import verify_snapshot


TRACKED_TIERS: tuple[str, ...] = ("free", "starter", "growth", "pro", "enterprise")
DEFAULT_DATABASE_PATH = str(
    Path(tempfile.gettempdir()) / "valdrics_finance_telemetry.sqlite"
)
TIER_MATRIX: dict[str, tuple[int, int, Decimal]] = {
    # tier: (tenant_count, active_subscriptions, per_usage_cost_usd)
    "free": (120, 0, Decimal("0.0200")),
    "starter": (42, 38, Decimal("0.1200")),
    "growth": (21, 19, Decimal("0.2400")),
    "pro": (9, 8, Decimal("0.6000")),
    "enterprise": (3, 3, Decimal("1.2000")),
}


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate runtime finance telemetry snapshot artifact.",
    )
    parser.add_argument("--output", required=True, help="Output snapshot JSON path.")
    parser.add_argument(
        "--database-path",
        default=DEFAULT_DATABASE_PATH,
        help="SQLite database path used for live telemetry generation.",
    )
    parser.add_argument(
        "--start-date",
        default=None,
        help="Window start date (YYYY-MM-DD). Defaults to previous full month start.",
    )
    parser.add_argument(
        "--end-date",
        default=None,
        help="Window end date (YYYY-MM-DD). Defaults to previous full month end.",
    )
    parser.add_argument(
        "--label",
        default=None,
        help="Optional snapshot window label override.",
    )
    return parser.parse_args(argv)


def _ensure_runtime_env(database_path: Path) -> None:
    os.environ["TESTING"] = "true"
    os.environ["DB_SSL_MODE"] = "disable"
    os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{database_path}"
    os.environ.setdefault("SUPABASE_JWT_SECRET", "test-jwt-secret-for-testing-at-least-32-bytes")
    os.environ.setdefault("ENCRYPTION_KEY", "32-byte-long-test-encryption-key")
    os.environ.setdefault("CSRF_SECRET_KEY", "test-csrf-secret-key-at-least-32-bytes")
    os.environ.setdefault("KDF_SALT", "S0RGX1NBTFRfRk9SX1RFU1RJTkdfMzJfQllURVNfT0s=")


def _register_models() -> None:
    # Register all relationship targets before metadata creation.
    import app.models.aws_connection  # noqa: F401
    import app.models.background_job  # noqa: F401
    import app.models.cloud  # noqa: F401
    import app.models.discovery_candidate  # noqa: F401
    import app.models.hybrid_connection  # noqa: F401
    import app.models.license_connection  # noqa: F401
    import app.models.llm  # noqa: F401
    import app.models.notification_settings  # noqa: F401
    import app.models.platform_connection  # noqa: F401
    import app.models.pricing  # noqa: F401
    import app.models.remediation_settings  # noqa: F401
    import app.models.saas_connection  # noqa: F401
    import app.models.tenant  # noqa: F401
    import app.models.tenant_identity_settings  # noqa: F401


def _usage_created_at(
    *,
    window_start: datetime,
    tier_index: int,
    tenant_index: int,
    usage_index: int,
) -> datetime:
    offset_days = (tier_index * 3 + tenant_index + usage_index) % 26
    offset_hours = (tenant_index * 2 + usage_index) % 23
    return window_start + timedelta(days=offset_days, hours=offset_hours)


async def _seed_runtime_data(
    *,
    window_start: datetime,
    window_end_exclusive: datetime,
) -> None:
    from app.models.llm import LLMUsage
    from app.models.pricing import TenantSubscription
    from app.models.tenant import Tenant
    from app.shared.db.base import Base
    from app.shared.db.session import get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as db:
        for tier_index, tier in enumerate(TRACKED_TIERS):
            tenant_count, active_subscriptions, usage_cost = TIER_MATRIX[tier]
            for tenant_index in range(tenant_count):
                tenant_id = UUID(int=(tier_index + 1) * 10_000 + tenant_index + 1)
                tenant = Tenant(
                    id=tenant_id,
                    name=f"Telemetry {tier} Tenant {tenant_index + 1}",
                    plan=tier,
                )
                db.add(tenant)

                subscription_status = "active" if tenant_index < active_subscriptions else "attention"
                db.add(
                    TenantSubscription(
                        id=uuid4(),
                        tenant_id=tenant_id,
                        tier=tier,
                        status=subscription_status,
                        last_dunning_at=(
                            window_start + timedelta(days=(tenant_index % 14))
                            if tenant_index % 9 == 0 and tier != "free"
                            else None
                        ),
                    )
                )

                if tier == "free":
                    continue
                for usage_index in range(3):
                    created_at = _usage_created_at(
                        window_start=window_start,
                        tier_index=tier_index,
                        tenant_index=tenant_index,
                        usage_index=usage_index,
                    )
                    if created_at >= window_end_exclusive:
                        created_at = window_end_exclusive - timedelta(minutes=5)
                    db.add(
                        LLMUsage(
                            id=uuid4(),
                            tenant_id=tenant_id,
                            provider="synthetic-ci",
                            model=f"{tier}-model-v1",
                            input_tokens=1200 + (usage_index * 100),
                            output_tokens=300 + (tenant_index % 120),
                            total_tokens=1500 + (usage_index * 100) + (tenant_index % 120),
                            cost_usd=usage_cost + (Decimal(tenant_index % 5) / Decimal("100")),
                            request_type="runtime_evidence_generation",
                            created_at=created_at,
                        )
                    )
        await db.commit()


async def _generate_snapshot(
    *,
    database_path: Path,
    start_date: datetime.date,
    end_date: datetime.date,
    label: str,
) -> dict[str, object]:
    _ensure_runtime_env(database_path)
    _register_models()

    from app.shared.db.session import reset_db_runtime

    reset_db_runtime()
    window_start, window_end_exclusive = _window_bounds(start_date, end_date)
    await _seed_runtime_data(
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
    )
    payload = await collect_snapshot(
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
        label=label,
    )
    runtime = payload.get("runtime")
    if isinstance(runtime, dict):
        runtime["collector"] = "scripts/generate_finance_telemetry_snapshot.py"
        runtime["database_seed_mode"] = "orm_seed_live_query"
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    database_path = Path(str(args.database_path))
    database_path.parent.mkdir(parents=True, exist_ok=True)

    if args.start_date and args.end_date:
        start_date = _parse_date(str(args.start_date), field="start_date")
        end_date = _parse_date(str(args.end_date), field="end_date")
    elif args.start_date or args.end_date:
        raise ValueError("start_date and end_date must be provided together")
    else:
        start_date, end_date = _default_window()
    label = str(args.label).strip() if args.label else f"{start_date}_{end_date}"

    payload = asyncio.run(
        _generate_snapshot(
            database_path=database_path,
            start_date=start_date,
            end_date=end_date,
            label=label,
        )
    )

    output_path = Path(str(args.output))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    verify_snapshot(snapshot_path=output_path, max_artifact_age_hours=4.0)
    print(f"Generated finance telemetry snapshot: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
