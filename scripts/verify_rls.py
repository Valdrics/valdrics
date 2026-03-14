import asyncio

from sqlalchemy import text

from app.shared.db.session import get_engine
from scripts.rls_tooling import requires_rls

async def check():
    engine = get_engine()
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND rowsecurity = true"
            )
        )
        rls_tables = [r[0] for r in result.fetchall()]
        print(f"RLS Enabled Tables: {rls_tables}")
        
        all_tables_result = await conn.execute(text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'"))
        all_tables = [r[0] for r in all_tables_result.fetchall()]
        tenant_tables_result = await conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND column_name = 'tenant_id'
                """
            )
        )
        tenant_tables = {str(row[0]) for row in tenant_tables_result.fetchall()}
        
        missing_rls = [
            t
            for t in all_tables
            if t not in rls_tables
            and t not in ["alembic_version"]
            and requires_rls(table_name=t, has_tenant_id=t in tenant_tables)
        ]
        if missing_rls:
            print(f"WARNING: No RLS on: {missing_rls}")
        else:
            print("SUCCESS: All application tables have RLS enabled.")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check())
