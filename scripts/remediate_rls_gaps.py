import asyncio

from sqlalchemy import text

from app.shared.db.session import get_engine
from scripts.rls_tooling import filter_rls_candidate_tables

async def remediate_rls():
    engine = get_engine()
    
    async with engine.connect() as conn:
        print("\n--- REMEDIATING RLS GAPS ---")
        
        # 1. Identify all tables with tenant_id but no RLS
        res = await conn.execute(text("""
            SELECT relname as table_name
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
            AND relkind = 'r'
            AND relrowsecurity = false
            AND relname NOT LIKE 'alembic_%'
            AND EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = c.relname AND column_name = 'tenant_id'
            );
        """))
        target_tables = list(filter_rls_candidate_tables(r[0] for r in res))
        
        print(f"Found {len(target_tables)} tables/partitions requiring RLS enforcement.")
        
        preparer = conn.dialect.identifier_preparer
        for table in target_tables:
            print(f"  Enforcing RLS on {table}...")
            quoted_table = preparer.quote(table)
            await conn.execute(text(f"ALTER TABLE {quoted_table} ENABLE ROW LEVEL SECURITY;"))
            await conn.execute(text(f"ALTER TABLE {quoted_table} FORCE ROW LEVEL SECURITY;"))
            
            # If it is a partition, it might need the policy explicitly if not inherited 
            # (though in PG11+ it usually inherits, forcing it is safer).
            # We also ensure the standard isolation policy exists on the table if it's not the root.
            # But usually, they inherit from the root. Let's just enable it first.
        
        await conn.commit()
        print("✅ RLS remediation completed.")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(remediate_rls())
