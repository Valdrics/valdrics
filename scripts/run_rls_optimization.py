from __future__ import annotations

import asyncio
import time
from pathlib import Path

from app.shared.db.session import async_session_maker


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sql_script_path() -> Path:
    path = (_repo_root() / "scripts" / "optimize_performance_and_security.sql").resolve()
    if not path.exists():
        raise RuntimeError(f"SQL script not found: {path}")
    if not path.is_file():
        raise RuntimeError(f"SQL script must be a file: {path}")
    return path


async def run_optimization() -> int:
    print("⚡ Starting Database Performance & Security Hardening...")
    start_total = time.time()

    sql = _sql_script_path().read_text(encoding="utf-8")

    try:
        async with async_session_maker() as db:
            # Get the underlying asyncpg connection
            conn = await db.connection()
            raw_conn = await conn.get_raw_connection()

            # Execute the entire script as one multi-statement string
            # We use the internal driver connection to support this directly
            await raw_conn.driver_connection.execute(sql)

            print(f"🏁 Total hardening time: {time.time() - start_total:.2f}s")
            print("✅ Database Performance & Security Hardening applied successfully!")
            return 0
    except (OSError, RuntimeError, TypeError, ValueError) as e:
        # The transaction is handled by the SQL script itself (BEGIN/COMMIT)
        # but we should still log the error properly.
        print(f"❌ Error during hardening: {e}")
        return 1


def main(argv: list[str] | None = None) -> int:
    del argv
    return asyncio.run(run_optimization())

if __name__ == "__main__":
    raise SystemExit(main())
