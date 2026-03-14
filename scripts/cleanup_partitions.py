import argparse
import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.shared.db.session import get_engine

async def cleanup_old_partitions(*, execute: bool) -> int:
    """
    Audits and drops cost_records partitions from 2025.
    """
    engine = get_engine()
    
    try:
        async with engine.connect() as conn:
            await conn.execution_options(isolation_level="AUTOCOMMIT")
            
            # List partitions
            res = await conn.execute(text("""
                SELECT child.relname AS partition_name 
                FROM pg_inherits 
                JOIN pg_class parent ON pg_inherits.inhparent = parent.oid 
                JOIN pg_class child ON pg_inherits.inhrelid = child.oid 
                WHERE parent.relname='cost_records' 
                AND child.relname LIKE 'cost_records_2025_%'
                ORDER BY partition_name;
            """))
            to_drop = [r[0] for r in res]
            
            if not to_drop:
                print("No 2025 partitions found.")
                return 0

            action = "drop" if execute else "drop (dry-run)"
            print(f"Found {len(to_drop)} partitions from 2025 to {action}.")
            if not execute:
                for part in to_drop:
                    print(f"  Would drop {part}")
                return 0

            preparer = conn.dialect.identifier_preparer
            for part in to_drop:
                print(f"  Dropping {part}...")
                quoted_table = preparer.quote(part)
                await conn.execute(text(f"DROP TABLE IF EXISTS {quoted_table} CASCADE;"))
            
            print("✅ 2025 partitions dropped successfully.")
            return 0

    except (SQLAlchemyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"❌ ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run by default. Audit or drop 2025 cost_records partitions."
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually drop the discovered partitions.",
    )
    args = parser.parse_args(argv)
    return asyncio.run(cleanup_old_partitions(execute=bool(args.execute)))


if __name__ == "__main__":
    raise SystemExit(main())
