import asyncio

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from app.shared.db.session import get_engine


async def list_partitions() -> int:
    engine = get_engine()
    try:
        async with engine.connect() as conn:
            print("\n--- Partition Audit ---")
            for table in ["cost_records", "audit_logs"]:
                print(f"\nTable: {table}")
                res = await conn.execute(
                    text(
                        """
                        SELECT child.relname AS partition_name
                        FROM pg_inherits
                        JOIN pg_class parent ON pg_inherits.inhparent = parent.oid
                        JOIN pg_class child ON pg_inherits.inhrelid = child.oid
                        WHERE parent.relname = :table_name
                        ORDER BY partition_name
                        """
                    ),
                    {"table_name": table},
                )
                for r in res:
                    print(f"  {r.partition_name}")
        return 0
    except (SQLAlchemyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"Error: {exc}")
        return 1
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    del argv
    return asyncio.run(list_partitions())


if __name__ == "__main__":
    raise SystemExit(main())
