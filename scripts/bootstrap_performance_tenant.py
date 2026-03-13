#!/usr/bin/env python3
"""Bootstrap a local authenticated tenant for performance smoke runs."""

from __future__ import annotations

import argparse
import asyncio
from datetime import timedelta
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from sqlalchemy import select

from app.shared.core.auth import create_access_token
from app.shared.core.pricing_types import PricingTier
from app.shared.db.session import async_session_maker, mark_session_system_context
from app.models.tenant import Tenant, User


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a signed bearer token and onboard a tenant for load-test runs."
    )
    parser.add_argument("--url", required=True, help="Base URL for the running API.")
    parser.add_argument(
        "--tenant-name",
        default="Performance Validation Tenant",
        help="Tenant name to onboard.",
    )
    parser.add_argument(
        "--email",
        default="performance.owner@valdrics.ai",
        help="Owner email used for the bootstrap token and onboarding.",
    )
    parser.add_argument(
        "--hours",
        type=float,
        default=2.0,
        help="Bearer token TTL in hours.",
    )
    parser.add_argument(
        "--tier",
        choices=[tier.value for tier in PricingTier],
        default=PricingTier.FREE.value,
        help="Local tenant tier to assign after onboarding.",
    )
    return parser.parse_args()


def _is_local_target(base_url: str) -> bool:
    hostname = (urlparse(str(base_url)).hostname or "").strip().lower()
    return hostname in {"127.0.0.1", "localhost"}


async def _apply_local_tenant_tier(*, user_id: UUID, tier: PricingTier) -> None:
    if tier == PricingTier.FREE:
        return

    async with async_session_maker() as session:
        await mark_session_system_context(session)
        tenant = (
            await session.execute(
                select(Tenant)
                .join(User, User.tenant_id == Tenant.id)
                .where(User.id == user_id)
                .limit(1)
            )
        ).scalar_one_or_none()
        if tenant is None:
            raise SystemExit("Unable to locate bootstrapped tenant for local tier upgrade")
        tenant.plan = tier.value
        await session.commit()


async def _onboard_tenant(*, base_url: str, token: str, tenant_name: str, email: str) -> None:
    payload = {"tenant_name": tenant_name, "admin_email": email}
    timeout = httpx.Timeout(15.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(
            f"{base_url.rstrip('/')}/api/v1/settings/onboard",
            headers={"Authorization": f"Bearer {token}"},
            json=payload,
        )
    if response.status_code == 200:
        return
    if response.status_code == 400 and "Already onboarded" in response.text:
        return
    raise SystemExit(
        f"Tenant bootstrap failed ({response.status_code}): {response.text}"
    )


async def main() -> None:
    args = _parse_args()
    user_id = uuid4()
    token = create_access_token(
        {"sub": str(user_id), "email": str(args.email).strip()},
        timedelta(hours=float(args.hours)),
    )
    await _onboard_tenant(
        base_url=str(args.url),
        token=token,
        tenant_name=str(args.tenant_name).strip(),
        email=str(args.email).strip(),
    )
    requested_tier = PricingTier(str(args.tier).strip().lower())
    if requested_tier != PricingTier.FREE:
        if not _is_local_target(str(args.url)):
            raise SystemExit("Tier promotion is only supported for local performance targets")
        await _apply_local_tenant_tier(user_id=user_id, tier=requested_tier)
    print(token)


if __name__ == "__main__":
    asyncio.run(main())
