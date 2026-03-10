"""Bootstrap the current ORM schema into a local sqlite database and stamp Alembic head."""

from __future__ import annotations

import argparse
import asyncio
import os


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Create the current Valdrics ORM schema in a local sqlite database and "
            "stamp the current Alembic head without replaying the legacy migration graph."
        )
    )
    parser.add_argument(
        "--database-url",
        help="Optional sqlite DATABASE_URL override for this bootstrap run.",
    )
    return parser


async def _run(database_url_override: str | None) -> int:
    if database_url_override:
        os.environ["DATABASE_URL"] = database_url_override
    os.environ["LOCAL_SQLITE_BOOTSTRAP"] = "true"

    from app.shared.core.config import reload_settings_from_environment
    from app.shared.db.local_sqlite_bootstrap import bootstrap_local_sqlite_schema
    from app.shared.db.session import get_engine, reset_db_runtime

    settings = reload_settings_from_environment()
    database_url = str(getattr(settings, "DATABASE_URL", "") or "").strip()

    if bool(getattr(settings, "TESTING", False)):
        raise SystemExit(
            "LOCAL_SQLITE_BOOTSTRAP requires TESTING=false. "
            "Use a local runtime env, not the test harness."
        )
    if "sqlite" not in database_url.lower():
        raise SystemExit(
            "bootstrap_local_sqlite_schema.py requires DATABASE_URL to use sqlite."
        )

    reset_db_runtime()
    engine = get_engine()
    try:
        result = await bootstrap_local_sqlite_schema(
            engine=engine,
            effective_url=database_url,
            settings_obj=settings,
        )
    finally:
        await engine.dispose()

    print(
        "[local-sqlite-bootstrap] ok "
        f"database={result['database_path']} "
        f"table_count={result['table_count']} "
        f"head={','.join(result['alembic_heads'])}"
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    return asyncio.run(_run(args.database_url))


if __name__ == "__main__":
    raise SystemExit(main())

