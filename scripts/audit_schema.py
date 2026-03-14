import asyncio

from sqlalchemy import text

from app.shared.db.session import get_engine
from scripts.rls_tooling import is_rls_exempt_table, requires_rls

async def audit_schema():
    engine = get_engine()
    
    async with engine.connect() as conn:
        print("\n--- GLOBAL SCHEMA AUDIT ---")
        
        # 1. List all user tables and their RLS status
        res = await conn.execute(text("""
            SELECT 
                relname as table_name,
                relrowsecurity as rls_enabled,
                relforcerowsecurity as rls_forced,
                pg_size_pretty(pg_total_relation_size(c.oid)) as total_size,
                (SELECT count(*) FROM pg_index WHERE indrelid = c.oid) as index_count
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
            AND relkind = 'r'
            AND relname NOT LIKE 'alembic_%'
            ORDER BY table_name;
        """))
        
        tables = res.fetchall()
        print(f"Total Tables found: {len(tables)}")
        
        audit_report = []
        for t in tables:
            # Check for tenant_id column
            col_res = await conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.columns 
                WHERE table_name = :table_name AND column_name = 'tenant_id'
            """), {"table_name": t.table_name})
            has_tenant_id = col_res.scalar() > 0
            
            status = "✅ READY"
            issues = []
            
            if has_tenant_id and is_rls_exempt_table(t.table_name):
                issues.append("RLS EXEMPT")
            elif requires_rls(table_name=t.table_name, has_tenant_id=has_tenant_id) and not t.rls_enabled:
                status = "❌ NOT READY"
                issues.append("RLS NOT ENABLED")
            
            if t.index_count == 0:
                issues.append("NO INDEXES")
                
            if "_old" in t.table_name or "_tmp" in t.table_name:
                status = "⚠️ WARNING"
                issues.append("POTENTIAL ORPHAN/DEVELOPMENT TABLE")

            audit_report.append({
                "table": t.table_name,
                "size": t.total_size,
                "rls": "ON" if t.rls_enabled else "OFF",
                "has_tenant_id": has_tenant_id,
                "indexes": t.index_count,
                "status": status,
                "issues": issues
            })

        # Print detailed report
        for item in audit_report:
            issue_str = f" | ISSUES: {', '.join(item['issues'])}" if item['issues'] else ""
            print(f"[{item['status']}] {item['table']:<30} | Size: {item['size']:<10} | RLS: {item['rls']:<3} | TenantID: {str(item['has_tenant_id']):<5}{issue_str}")

        # 2. Check for missing RLS policies
        print("\n--- RLS Policy Check ---")
        res = await conn.execute(text("""
            SELECT tablename, policyname, roles, cmd, qual
            FROM pg_policies
            WHERE schemaname = 'public';
        """))
        policies = res.fetchall()
        for p in policies:
             print(f"POLICY: {p.policyname:<40} on {p.tablename}")

    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(audit_schema())
