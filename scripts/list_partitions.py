import asyncio

from sqlalchemy import text
from app.shared.db.session import get_engine


async def list_partitions():
    engine = get_engine()
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
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(list_partitions())
