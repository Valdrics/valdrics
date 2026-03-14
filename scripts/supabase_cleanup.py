import asyncio
import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.shared.db.session import async_session_maker, get_engine

SUPABASE_CLEANUP_RECOVERABLE_EXCEPTIONS = (
    SQLAlchemyError,
    OSError,
    RuntimeError,
    TypeError,
    ValueError,
)

async def monitor_usage(session):
    print("\n--- DB Storage Usage (Top Tables/Partitions) ---")
    res = await session.execute(text("""
        SELECT c.relname as table_name, 
               pg_size_pretty(pg_total_relation_size(c.oid)) as total_size,
               n_live_tup as row_count
        FROM pg_catalog.pg_stat_user_tables s
        JOIN pg_class c ON c.oid = s.relid
        ORDER BY pg_total_relation_size(c.oid) DESC
        LIMIT 25;
    """))
    for r in res:
        print(f"TABLE: {r.table_name:<30} | SIZE: {r.total_size:<10} | ROWS: {r.row_count}")

async def run_cleanup() -> int:
    engine = get_engine()
    
    bloated_partitions = []
    
    async with async_session_maker() as session:
        try:
            await monitor_usage(session)
            
            # Identify bloat (Partitions with very few rows but > 1MB size)
            res = await session.execute(text("""
                SELECT relname 
                FROM pg_catalog.pg_stat_user_tables 
                WHERE relname LIKE 'cost_records_%' 
                AND n_live_tup < 100 
                AND pg_total_relation_size(relid) > 1024 * 1024;
            """))
            bloated_partitions = [r[0] for r in res]
            
            if bloated_partitions:
                print(f"\nDetected {len(bloated_partitions)} bloated partitions. Reclaiming space...")
            else:
                print("\nNo significant bloat detected in cost_records partitions.")

        except SUPABASE_CLEANUP_RECOVERABLE_EXCEPTIONS as exc:
            print(f"❌ ERROR: {exc}", file=sys.stderr)
            return 1
    
    # Run VACUUM FULL outside transaction to reclaim disk space
    if bloated_partitions:
        try:
            async with engine.connect() as conn:
                await conn.execution_options(isolation_level="AUTOCOMMIT")
                for part in bloated_partitions:
                    print(f"  VACUUM FULL {part}...")
                    await conn.execute(text(f"VACUUM FULL {part};"))
                print("✅ Aggressive reclamation (VACUUM FULL) completed.")
        except SUPABASE_CLEANUP_RECOVERABLE_EXCEPTIONS as vacuum_exc:
            print(f"⚠️ Vacuum failed: {vacuum_exc}", file=sys.stderr)
            return 1
    
    async with async_session_maker() as session:
        await monitor_usage(session)

    await engine.dispose()
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(run_cleanup()))
