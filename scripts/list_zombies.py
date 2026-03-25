import asyncio
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.remediation import RemediationRequest
from app.shared.db.session import async_session_maker


async def check_zombies() -> int:
    async with async_session_maker() as session:
        try:
            res = await session.execute(select(RemediationRequest))
            zombies = res.scalars().all()
            print(f"Found {len(zombies)} zombies")
            for z in zombies:
                print(
                    f"- {z.resource_id} ({z.resource_type}): Estimated ${z.estimated_monthly_savings}/mo waste"
                )
            return 0
        except (SQLAlchemyError, OSError, RuntimeError, TypeError, ValueError) as e:
            print(f"Error checking zombies: {str(e)}")
            return 1


def main(argv: list[str] | None = None) -> int:
    del argv
    return asyncio.run(check_zombies())


if __name__ == "__main__":
    raise SystemExit(main())
