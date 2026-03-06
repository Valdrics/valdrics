"""Rule CRUD and lookup operations for attribution engine."""

from __future__ import annotations

from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribution import AttributionRule


async def list_rules(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    include_inactive: bool = False,
) -> list[AttributionRule]:
    """List tenant attribution rules ordered by priority."""
    query = select(AttributionRule).where(AttributionRule.tenant_id == tenant_id)
    if not include_inactive:
        query = query.where(AttributionRule.is_active)
    query = query.order_by(AttributionRule.priority.asc(), AttributionRule.name.asc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
) -> AttributionRule | None:
    """Fetch one attribution rule scoped to tenant."""
    query = (
        select(AttributionRule)
        .where(AttributionRule.tenant_id == tenant_id)
        .where(AttributionRule.id == rule_id)
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    *,
    name: str,
    priority: int,
    rule_type: str,
    conditions: dict[str, Any],
    allocation: Any,
    is_active: bool = True,
) -> AttributionRule:
    """Create and persist a tenant attribution rule."""
    rule = AttributionRule(
        tenant_id=tenant_id,
        name=name,
        priority=priority,
        rule_type=rule_type,
        conditions=conditions,
        allocation=allocation,
        is_active=is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule


async def update_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
    updates: dict[str, Any],
    *,
    normalize_rule_type_fn: Any,
) -> AttributionRule | None:
    """Update an existing attribution rule."""
    rule = await get_rule(db, tenant_id, rule_id)
    if not rule:
        return None

    if "rule_type" in updates and isinstance(updates["rule_type"], str):
        updates["rule_type"] = normalize_rule_type_fn(updates["rule_type"])

    for field in (
        "name",
        "priority",
        "rule_type",
        "conditions",
        "allocation",
        "is_active",
    ):
        if field in updates and updates[field] is not None:
            setattr(rule, field, updates[field])

    await db.commit()
    await db.refresh(rule)
    return rule


async def delete_rule(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    rule_id: uuid.UUID,
) -> bool:
    """Delete one tenant rule and return whether it existed."""
    rule = await get_rule(db, tenant_id, rule_id)
    if not rule:
        return False
    await db.delete(rule)
    await db.commit()
    return True


async def get_active_rules(db: AsyncSession, tenant_id: uuid.UUID) -> list[AttributionRule]:
    """
    Retrieve all active attribution rules for a tenant, ordered by priority.
    Lower priority numbers are evaluated first.
    """
    query = (
        select(AttributionRule)
        .where(AttributionRule.tenant_id == tenant_id)
        .where(AttributionRule.is_active)
        .order_by(AttributionRule.priority.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())
