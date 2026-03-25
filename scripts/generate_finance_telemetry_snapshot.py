#!/usr/bin/env python3
"""Generate finance telemetry snapshot evidence from live DB execution."""

from __future__ import annotations

import argparse
import asyncio
import os
import tempfile
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from contextlib import suppress
from unittest.mock import patch
from uuid import UUID, uuid4
from collections.abc import Awaitable
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scripts.collect_finance_telemetry_snapshot import (
    _default_window,
    _parse_date,
    _window_bounds,
    collect_snapshot,
)
from scripts.env_generation_common import (
    checked_in_evidence_paths as _checked_in_evidence_paths_shared,
    ensure_parent_dir as _ensure_parent_dir_shared,
    promote_staged_file as _promote_staged_file,
    protected_output_paths_from_root as _protected_output_paths_from_root,
    repo_root_for as _repo_root_for,
    resolve_output_path_from_root as _resolve_output_path_from_root,
    resolve_repo_relative_path_from_root as _resolve_repo_relative_path_from_root,
    stage_json_file as _stage_json_file,
)
from scripts.verify_finance_telemetry_snapshot import verify_snapshot


TRACKED_TIERS: tuple[str, ...] = ("free", "starter", "growth", "pro", "enterprise")
TIER_MATRIX: dict[str, tuple[int, int, Decimal]] = {
    # tier: (tenant_count, active_subscriptions, per_usage_cost_usd)
    "free": (12, 0, Decimal("0.0200")),
    "starter": (8, 6, Decimal("0.1200")),
    "growth": (6, 5, Decimal("0.2400")),
    "pro": (4, 3, Decimal("0.6000")),
    "enterprise": (3, 3, Decimal("1.2000")),
}


async def _heartbeat_loop(stop: asyncio.Event) -> None:
    while not stop.is_set():
        await asyncio.sleep(0.01)


async def _await_with_heartbeat(awaitable: Awaitable[Any]) -> Any:
    stop = asyncio.Event()
    heartbeat = asyncio.create_task(_heartbeat_loop(stop))
    try:
        return await awaitable
    finally:
        stop.set()
        await heartbeat


def _run_async(awaitable: Awaitable[Any]) -> Any:
    return asyncio.run(_await_with_heartbeat(awaitable))


def _repo_root() -> Path:
    return _repo_root_for(__file__)


def _checked_in_evidence_paths(repo_root: Path) -> set[Path]:
    return _checked_in_evidence_paths_shared(repo_root)


def _protected_output_paths() -> set[Path]:
    return _protected_output_paths_from_root(
        _repo_root(),
        __file__,
        "scripts/collect_finance_telemetry_snapshot.py",
        "scripts/verify_finance_telemetry_snapshot.py",
        "docs/ops/evidence/finance_telemetry_snapshot_TEMPLATE.json",
        "docs/ops/evidence/finance_telemetry_snapshot_2026-02-28.json",
        "docs/ops/evidence/finance_committee_packet_assumptions_TEMPLATE.json",
        "docs/ops/evidence/finance_committee_packet_assumptions_2026-02-28.json",
        "docs/ops/evidence/finance_guardrails_TEMPLATE.json",
        "docs/ops/evidence/finance_guardrails_2026-02-27.json",
        "docs/ops/evidence/pkg_fin_policy_decisions_TEMPLATE.json",
        "docs/ops/evidence/pkg_fin_policy_decisions_2026-02-28.json",
        "docs/ops/evidence/README.md",
    )


def _resolve_output_path(value: str) -> Path:
    return _resolve_output_path_from_root(
        _repo_root(),
        value,
        field_name="output",
        protected_paths=_protected_output_paths(),
        protected_error=(
            "output must not overwrite finance telemetry source, collector, verifier, or template files"
        ),
    )


def _resolve_database_path(value: str) -> Path:
    return _resolve_repo_relative_path_from_root(
        _repo_root(),
        value,
        field_name="database_path",
    )


def _build_default_database_path() -> Path:
    database_root = Path(tempfile.mkdtemp(prefix="valdrics_finance_telemetry_"))
    return database_root / "telemetry.sqlite3"


def _cleanup_temporary_database(database_path: Path) -> None:
    for suffix in ("", "-journal", "-shm", "-wal"):
        Path(f"{database_path}{suffix}").unlink(missing_ok=True)
    with suppress(OSError):
        database_path.parent.rmdir()


def _ensure_output_parent_dir(output_path: Path) -> None:
    current = output_path.parent
    while True:
        if current.exists():
            if not current.is_dir():
                raise ValueError(
                    f"output parent must be a directory path: {current.as_posix()}"
                )
            return
        if current == current.parent:
            return
        current = current.parent


def _ensure_parent_dir(path: Path, *, field_name: str) -> None:
    _ensure_parent_dir_shared(path, field_name=field_name)


def _write_verified_snapshot(*, output_path: Path, payload: dict[str, object]) -> None:
    temp_path = _stage_json_file(output_path, payload)
    try:
        verify_snapshot(snapshot_path=temp_path, max_artifact_age_hours=4.0)
        _promote_staged_file(temp_path, output_path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate runtime finance telemetry snapshot artifact.",
    )
    parser.add_argument("--output", required=True, help="Output snapshot JSON path.")
    parser.add_argument(
        "--database-path",
        default=None,
        help="Optional SQLite database path used for live telemetry generation.",
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


def _runtime_env_overrides(database_path: Path) -> dict[str, str]:
    overrides = {
        "TESTING": "true",
        "DB_SSL_MODE": "disable",
        "DATABASE_URL": f"sqlite+aiosqlite:///{database_path}",
    }
    defaults = {
        "SUPABASE_JWT_SECRET": "test-jwt-secret-for-testing-at-least-32-bytes",
        "ENCRYPTION_KEY": "32-byte-long-test-encryption-key",
        "CSRF_SECRET_KEY": "test-csrf-secret-key-at-least-32-bytes",
        "KDF_SALT": "S0RGX1NBTFRfRk9SX1RFU1RJTkdfMzJfQllURVNfT0s=",
    }
    for key, value in defaults.items():
        if key not in os.environ:
            overrides[key] = value
    return overrides


def _register_models() -> None:
    # Register only the ORM models required by this snapshot's seed/query path.
    import app.models.llm  # noqa: F401
    import app.models.pricing  # noqa: F401
    import app.models.tenant  # noqa: F401


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
    from app.models.tenant import Tenant, User
    from app.shared.db.session import get_engine

    engine = get_engine()
    seed_tables = (
        Tenant.__table__,
        User.__table__,
        TenantSubscription.__table__,
        LLMUsage.__table__,
    )
    metadata = Tenant.__table__.metadata
    async with engine.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: metadata.drop_all(
                sync_conn,
                tables=seed_tables,
                checkfirst=True,
            )
        )
        await conn.run_sync(
            lambda sync_conn: metadata.create_all(
                sync_conn,
                tables=seed_tables,
                checkfirst=True,
            )
        )

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
    from app.shared.core.config import reload_settings_from_environment
    from app.shared.db.session import dispose_db_runtime

    try:
        with patch.dict(os.environ, _runtime_env_overrides(database_path), clear=False):
            _register_models()

            await dispose_db_runtime()
            reload_settings_from_environment()
            try:
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
            finally:
                await dispose_db_runtime()
    finally:
        reload_settings_from_environment()

    runtime = payload.get("runtime")
    if isinstance(runtime, dict):
        runtime["collector"] = "scripts/generate_finance_telemetry_snapshot.py"
        runtime["database_seed_mode"] = "orm_seed_live_query"
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    auto_database_path = not args.database_path
    database_path = (
        _build_default_database_path()
        if auto_database_path
        else _resolve_database_path(str(args.database_path))
    )
    output_path = _resolve_output_path(str(args.output))
    try:
        _ensure_output_parent_dir(output_path)
        if database_path.exists() and not database_path.is_file():
            raise ValueError(f"database_path must be a file path: {database_path}")
        _ensure_parent_dir(database_path, field_name="database_path")
        if output_path.resolve() == database_path.resolve():
            raise ValueError("output and database_path must be different files")

        if args.start_date and args.end_date:
            start_date = _parse_date(str(args.start_date), field="start_date")
            end_date = _parse_date(str(args.end_date), field="end_date")
        elif args.start_date or args.end_date:
            raise ValueError("start_date and end_date must be provided together")
        else:
            start_date, end_date = _default_window()
        if args.label is not None:
            label = str(args.label).strip()
            if not label:
                raise ValueError("label must be a non-empty string")
        else:
            label = f"{start_date}_{end_date}"

        database_path.parent.mkdir(parents=True, exist_ok=True)
        payload = _run_async(
            _generate_snapshot(
                database_path=database_path,
                start_date=start_date,
                end_date=end_date,
                label=label,
            )
        )
        _write_verified_snapshot(output_path=output_path, payload=payload)
        print(f"Generated finance telemetry snapshot: {output_path}")
        return 0
    finally:
        if auto_database_path:
            _cleanup_temporary_database(database_path)


if __name__ == "__main__":
    raise SystemExit(main())
