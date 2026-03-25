from __future__ import annotations

import asyncio
import sys
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from scripts.env_generation_common import repo_root_for

_REPO_ROOT = repo_root_for(__file__)
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from app.models.tenant import Tenant, User, UserRole, UserPersona
from app.shared.db.session import async_session_maker, get_engine

async def seed_data() -> int:
    """Seed initial development data (Tenant + User)."""
    print("🌱 Seeding development data...", flush=True)
    engine = get_engine()
    try:
        async with async_session_maker() as db:
            async with db.begin():
                # Check for existing user (using simple limit query to avoid blind index complexity)
                res = await db.execute(select(User).limit(1))
                existing_user = res.scalars().first()

                if not existing_user:
                    print("  + Creating initial Tenant and User...", flush=True)

                    # Create Tenant
                    tenant_id = uuid4()
                    tenant = Tenant(
                        id=tenant_id,
                        name="Valdrics Dev",
                        plan="growth",
                    )
                    db.add(tenant)

                    # Create User
                    user_id = uuid4()
                    user = User(
                        id=user_id,
                        tenant_id=tenant_id,
                        email="admin@valdrics.com",
                        role=UserRole.OWNER.value,
                        persona=UserPersona.ENGINEERING.value,
                        is_active=True,
                    )
                    db.add(user)

                    print(f"  + Created Tenant: Valdrics Dev ({tenant_id})", flush=True)
                    print(f"  + Created User: admin@valdrics.com ({user_id})", flush=True)
                    print("  ! NOTE: Create this user in Supabase Auth with this UUID!", flush=True)
                    print(f"  ! User ID: {user_id}", flush=True)
                else:
                    print("  ~ Users already exist, skipping seed.", flush=True)

        print("✅ Dev data seeding complete!", flush=True)
        return 0
    except (SQLAlchemyError, OSError, RuntimeError, TypeError, ValueError) as exc:
        print(f"❌ Dev data seed failed: {exc}", flush=True)
        return 1
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    del argv
    return asyncio.run(seed_data())

if __name__ == "__main__":
    raise SystemExit(main())
