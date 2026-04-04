from __future__ import annotations

import asyncio
import sys
from uuid import uuid4

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from scripts.env_generation_common import repo_root_for

_REPO_ROOT = repo_root_for(__file__)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


async def seed_data() -> int:
    from app.models.tenant import Tenant, User, UserPersona, UserRole
    from app.shared.db.session import async_session_maker, get_engine

    print("🌱 Seeding test...", flush=True)
    engine = get_engine()
    try:
        async with async_session_maker() as db:
            async with db.begin():
                print("✅ Session created!", flush=True)

                # Check User query with raw SQL
                print("🔍 Checking User query (RAW)...", flush=True)
                res = await db.execute(text("SELECT id FROM users LIMIT 1"))
                print(
                    f"✅ RAW User Query executed! Count: {len(res.all())}", flush=True
                )

                # Check User query with ORM
                print("🔍 Checking User query (ORM)...", flush=True)
                res = await db.execute(select(User).limit(1))
                print(
                    f"✅ ORM User Query executed! Count: {len(res.scalars().all())}",
                    flush=True,
                )

                # Try insert Tenant
                print("🌱 Inserting Tenant...", flush=True)
                tenant_id = uuid4()
                t = Tenant(id=tenant_id, name="Test Tenant", plan="growth")
                db.add(t)
                print("✅ Tenant Added!", flush=True)

                # Try insert User
                print("🌱 Inserting User...", flush=True)
                user_id = uuid4()
                u = User(
                    id=user_id,
                    tenant_id=tenant_id,
                    email="admin@valdrics.com",
                    role=UserRole.OWNER.value,
                    persona=UserPersona.ENGINEERING.value,
                    is_active=True,
                )
                db.add(u)
                print("✅ User Added!", flush=True)

            print("✅ Commit successful!", flush=True)
            return 0
    except (SQLAlchemyError, OSError, RuntimeError, TypeError, ValueError) as e:
        print(f"❌ Tenant import failed: {e}", flush=True)
        return 1
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    del argv
    return asyncio.run(seed_data())


if __name__ == "__main__":
    raise SystemExit(main())
