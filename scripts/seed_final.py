import asyncio
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import text

from app.shared.core.security import encrypt_string, generate_blind_index
from app.shared.db.session import async_session_maker, get_engine

async def seed_data():
    """Seed initial development data (Tenant + User) using Raw SQL."""
    print("🌱 Seeding development data (RAW SQL)...", flush=True)

    async with async_session_maker() as db:
        async with db.begin():
            # Check for existing user
            print("🔍 Checking existing users...", flush=True)
            res = await db.execute(text("SELECT id FROM users LIMIT 1"))
            existing_user = res.first()
            
            if not existing_user:
                print("  + Creating initial Tenant and User...", flush=True)
                
                # Prepare Data
                tenant_id = uuid4()
                tenant_name = "Valdrics Dev"
                tenant_name_enc = encrypt_string(tenant_name)
                tenant_name_bidx = generate_blind_index(tenant_name, tenant_id=tenant_id)
                
                user_id = uuid4()
                user_email = "admin@valdrics.com"
                user_email_enc = encrypt_string(user_email)
                user_email_bidx = generate_blind_index(user_email, tenant_id=tenant_id)
                
                now = datetime.now(timezone.utc)

                # Insert Tenant through ORM logic? No, raw SQL.
                print("🌱 Inserting Tenant...", flush=True)
                await db.execute(
                    text("""
                        INSERT INTO tenants (id, name, name_bidx, plan, trial_started_at)
                        VALUES (:id, :name, :name_bidx, :plan, :trial_started_at)
                    """),
                    {
                        "id": tenant_id,
                        "name": tenant_name_enc,
                        "name_bidx": tenant_name_bidx,
                        "plan": "growth",
                        "trial_started_at": now
                    }
                )
                
                # Insert User
                print("🌱 Inserting User...", flush=True)
                await db.execute(
                    text("""
                        INSERT INTO users (id, tenant_id, email, email_bidx, role, persona, is_active)
                        VALUES (:id, :tenant_id, :email, :email_bidx, :role, :persona, :is_active)
                    """),
                    {
                        "id": user_id,
                        "tenant_id": tenant_id,
                        "email": user_email_enc,
                        "email_bidx": user_email_bidx,
                        "role": "owner",
                        "persona": "engineering",
                        "is_active": True
                    }
                )
                
                print(f"  + Created Tenant: Valdrics Dev ({tenant_id})", flush=True)
                print(f"  + Created User: admin@valdrics.com ({user_id})", flush=True)
                print("  ! NOTE: Create this user in Supabase Auth with this UUID!", flush=True)
                print(f"  ! User ID: {user_id}", flush=True)
            else:
                 print("  ~ Users already exist, skipping seed.", flush=True)

    print("✅ Dev data seeding complete!", flush=True)
    await get_engine().dispose()

if __name__ == "__main__":
    asyncio.run(seed_data())
