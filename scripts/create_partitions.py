from __future__ import annotations

import asyncio
import argparse
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.shared.db.session import async_session_maker


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create legacy cost-record partitions.")
    parser.add_argument(
        "--months-before",
        type=int,
        default=12,
        help="How many historical months of partitions to create.",
    )
    parser.add_argument(
        "--months-ahead",
        type=int,
        default=12,
        help="How many future months of partitions to create.",
    )
    return parser


async def create_partitions(
    *,
    months_before: int = 12,
    months_ahead: int = 12,
) -> int:
    session = async_session_maker()
    today = date.today()
    had_failure = False
    try:
        for i in range(-months_before, months_ahead + 1):
            target = today + relativedelta(months=i)
            p_name = f"cost_records_{target.year}_{target.month:02d}"
            start = date(target.year, target.month, 1)
            end = start + relativedelta(months=1)

            sql = text(
                f"""
                CREATE TABLE IF NOT EXISTS {p_name}
                PARTITION OF cost_records
                FOR VALUES FROM ('{start.isoformat()}') TO ('{end.isoformat()}')
            """
            )
            print(f"Creating partition {p_name}...")
            try:
                await session.execute(sql)
                await session.commit()
            except (SQLAlchemyError, OSError, RuntimeError, TypeError, ValueError) as e:
                print(f"Failed to create {p_name}: {e}")
                had_failure = True
                await session.rollback()
    finally:
        await session.close()

    return 1 if had_failure else 0


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.months_before < 0:
        raise SystemExit("--months-before must be >= 0")
    if args.months_ahead < 0:
        raise SystemExit("--months-ahead must be >= 0")
    return asyncio.run(
        create_partitions(months_before=args.months_before, months_ahead=args.months_ahead)
    )

if __name__ == "__main__":
    raise SystemExit(main())
