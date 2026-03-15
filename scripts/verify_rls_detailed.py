import asyncio

from sqlalchemy import text

from app.shared.db.session import get_engine
from scripts.rls_tooling import is_rls_exempt_table, requires_rls


async def check() -> int:
    engine = get_engine()
    async with engine.connect() as conn:
        version_res = await conn.execute(text("SELECT version_num FROM alembic_version"))
        versions = [r[0] for r in version_res.fetchall()]
        print(f"Alembic Versions: {versions}")

        table_res = await conn.execute(
            text(
                """
                SELECT relname AS table_name, relrowsecurity AS rowsecurity
                FROM pg_class c
                JOIN pg_namespace n ON n.oid = c.relnamespace
                WHERE n.nspname = 'public'
                  AND relkind = 'r'
                  AND relname NOT LIKE 'alembic_%'
                ORDER BY relname
                """
            )
        )
        tenant_tables_res = await conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND column_name = 'tenant_id'
                """
            )
        )
        tenant_tables = {str(row[0]) for row in tenant_tables_res.fetchall()}

        missing_required: list[str] = []
        for row in table_res.fetchall():
            table_name_value = getattr(row, "table_name", None)
            if table_name_value is None and isinstance(row, (tuple, list)):
                table_name_value = row[0]
            rowsecurity_value = getattr(row, "rowsecurity", None)
            if rowsecurity_value is None and isinstance(row, (tuple, list)):
                rowsecurity_value = row[1]
            table_name = str(table_name_value)
            rls_enabled = bool(rowsecurity_value)
            has_tenant_id = table_name in tenant_tables
            if has_tenant_id and is_rls_exempt_table(table_name):
                print(f"Table {table_name}: RLS EXEMPT")
                continue
            if requires_rls(table_name=table_name, has_tenant_id=has_tenant_id):
                print(f"Table {table_name}: RLS Enabled = {rls_enabled}")
                if not rls_enabled:
                    missing_required.append(table_name)

        if missing_required:
            print(f"WARNING: Missing RLS on required tables: {missing_required}")
            exit_code = 1
        else:
            print("SUCCESS: All required tenant-scoped tables have RLS enabled.")
            exit_code = 0

    await engine.dispose()
    return exit_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(check()))
