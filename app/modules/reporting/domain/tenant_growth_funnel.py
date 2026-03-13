from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant_growth_funnel_snapshot import TenantGrowthFunnelSnapshot
from app.shared.core.pricing import PricingTier, normalize_tier

_TOKEN_SANITIZER = re.compile(r"[^a-z0-9_./:+-]+")
_PATH_SANITIZER = re.compile(r"[^a-z0-9_./?=&:%+-]+")

TenantGrowthFunnelStage = Literal[
    "tenant_onboarded",
    "connection_verified",
    "pricing_viewed",
    "checkout_started",
    "first_value_activated",
    "paid_activated",
]

_STAGE_FIELD_MAP: dict[TenantGrowthFunnelStage, str] = {
    "tenant_onboarded": "tenant_onboarded_at",
    "connection_verified": "first_connection_verified_at",
    "pricing_viewed": "pricing_viewed_at",
    "checkout_started": "checkout_started_at",
    "first_value_activated": "first_value_activated_at",
    "paid_activated": "paid_activated_at",
}

_SNAPSHOT_DATETIME_FIELDS: tuple[str, ...] = (
    "first_touch_at",
    "last_touch_at",
    "tenant_onboarded_at",
    "first_connection_verified_at",
    "pricing_viewed_at",
    "checkout_started_at",
    "first_value_activated_at",
    "pql_qualified_at",
    "paid_activated_at",
    "created_at",
    "updated_at",
)


@dataclass(frozen=True, slots=True)
class TenantGrowthFunnelAttribution:
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    utm_term: str | None = None
    utm_content: str | None = None
    persona: str | None = None
    intent: str | None = None
    page_path: str | None = None
    first_touch_at: datetime | None = None
    last_touch_at: datetime | None = None


def _normalize_token(value: str | None, *, max_length: int) -> str | None:
    if value is None:
        return None
    token = _TOKEN_SANITIZER.sub("_", str(value).strip().lower()).strip("_")
    if not token:
        return None
    return token[:max_length]


def _normalize_path(value: str | None, *, max_length: int = 256) -> str | None:
    if value is None:
        return None
    token = _PATH_SANITIZER.sub("", str(value).strip())
    if not token:
        return None
    return token[:max_length]


def _normalize_timestamp(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def normalize_growth_funnel_attribution(
    *,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
    utm_term: str | None = None,
    utm_content: str | None = None,
    persona: str | None = None,
    intent: str | None = None,
    page_path: str | None = None,
    first_touch_at: datetime | None = None,
    last_touch_at: datetime | None = None,
) -> TenantGrowthFunnelAttribution:
    return TenantGrowthFunnelAttribution(
        utm_source=_normalize_token(utm_source, max_length=96),
        utm_medium=_normalize_token(utm_medium, max_length=96),
        utm_campaign=_normalize_token(utm_campaign, max_length=96),
        utm_term=_normalize_token(utm_term, max_length=96),
        utm_content=_normalize_token(utm_content, max_length=96),
        persona=_normalize_token(persona, max_length=64),
        intent=_normalize_token(intent, max_length=64),
        page_path=_normalize_path(page_path),
        first_touch_at=_normalize_timestamp(first_touch_at),
        last_touch_at=_normalize_timestamp(last_touch_at),
    )


async def _ensure_snapshot_row(db: AsyncSession, tenant_id: UUID) -> None:
    bind = getattr(db, "bind", None)
    dialect_name = str(getattr(getattr(bind, "dialect", None), "name", "") or "").lower()
    insert_values = {
        "tenant_id": tenant_id,
        "current_tier": PricingTier.FREE.value,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        await db.execute(
            pg_insert(TenantGrowthFunnelSnapshot)
            .values(**insert_values)
            .on_conflict_do_nothing(
                index_elements=[TenantGrowthFunnelSnapshot.tenant_id]
            )
        )
        return

    if dialect_name == "sqlite":
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        await db.execute(
            sqlite_insert(TenantGrowthFunnelSnapshot)
            .values(**insert_values)
            .on_conflict_do_nothing(
                index_elements=[TenantGrowthFunnelSnapshot.tenant_id]
            )
        )
        return

    existing = await db.execute(
        select(TenantGrowthFunnelSnapshot.id).where(
            TenantGrowthFunnelSnapshot.tenant_id == tenant_id
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(TenantGrowthFunnelSnapshot(**insert_values))
        await db.flush()


def _build_update_values(
    *,
    stage: TenantGrowthFunnelStage,
    occurred_at: datetime,
    current_tier: PricingTier,
    attribution: TenantGrowthFunnelAttribution | None,
    provider: str | None,
    source: str | None,
) -> dict[str, object]:
    stage_field = _STAGE_FIELD_MAP[stage]
    values: dict[str, object] = {
        "updated_at": datetime.now(timezone.utc),
        "current_tier": current_tier.value,
        stage_field: func.coalesce(
            getattr(TenantGrowthFunnelSnapshot, stage_field),
            occurred_at,
        ),
    }
    if attribution is not None:
        values.update(
            {
                "utm_source": func.coalesce(
                    TenantGrowthFunnelSnapshot.utm_source,
                    attribution.utm_source,
                ),
                "utm_medium": func.coalesce(
                    TenantGrowthFunnelSnapshot.utm_medium,
                    attribution.utm_medium,
                ),
                "utm_campaign": func.coalesce(
                    TenantGrowthFunnelSnapshot.utm_campaign,
                    attribution.utm_campaign,
                ),
                "utm_term": func.coalesce(
                    TenantGrowthFunnelSnapshot.utm_term,
                    attribution.utm_term,
                ),
                "utm_content": func.coalesce(
                    TenantGrowthFunnelSnapshot.utm_content,
                    attribution.utm_content,
                ),
                "persona": func.coalesce(
                    TenantGrowthFunnelSnapshot.persona,
                    attribution.persona,
                ),
                "acquisition_intent": func.coalesce(
                    TenantGrowthFunnelSnapshot.acquisition_intent,
                    attribution.intent,
                ),
                "first_path": func.coalesce(
                    TenantGrowthFunnelSnapshot.first_path,
                    attribution.page_path,
                ),
                "first_touch_at": func.coalesce(
                    TenantGrowthFunnelSnapshot.first_touch_at,
                    attribution.first_touch_at,
                ),
                "last_touch_at": func.coalesce(
                    TenantGrowthFunnelSnapshot.last_touch_at,
                    attribution.last_touch_at,
                ),
            }
        )
    normalized_provider = _normalize_token(provider, max_length=32)
    normalized_source = _normalize_token(source, max_length=64)
    if stage == "connection_verified":
        values["first_connection_provider"] = func.coalesce(
            TenantGrowthFunnelSnapshot.first_connection_provider,
            normalized_provider,
        )
    if stage == "first_value_activated":
        values["first_value_source"] = func.coalesce(
            TenantGrowthFunnelSnapshot.first_value_source,
            normalized_source,
        )
    return values


def _normalize_snapshot_datetimes(
    snapshot: TenantGrowthFunnelSnapshot,
) -> TenantGrowthFunnelSnapshot:
    for field_name in _SNAPSHOT_DATETIME_FIELDS:
        setattr(
            snapshot,
            field_name,
            _normalize_timestamp(getattr(snapshot, field_name, None)),
        )
    return snapshot


async def record_tenant_growth_funnel_stage(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    stage: TenantGrowthFunnelStage,
    occurred_at: datetime | None = None,
    current_tier: PricingTier | str | None = None,
    attribution: TenantGrowthFunnelAttribution | None = None,
    provider: str | None = None,
    source: str | None = None,
    commit: bool = False,
) -> TenantGrowthFunnelSnapshot:
    normalized_time = _normalize_timestamp(occurred_at) or datetime.now(timezone.utc)
    normalized_tier = normalize_tier(current_tier)

    await _ensure_snapshot_row(db, tenant_id)

    update_values = _build_update_values(
        stage=stage,
        occurred_at=normalized_time,
        current_tier=normalized_tier,
        attribution=attribution,
        provider=provider,
        source=source,
    )

    await db.execute(
        update(TenantGrowthFunnelSnapshot)
        .where(TenantGrowthFunnelSnapshot.tenant_id == tenant_id)
        .values(**update_values)
    )

    await db.execute(
        update(TenantGrowthFunnelSnapshot)
        .where(TenantGrowthFunnelSnapshot.tenant_id == tenant_id)
        .where(TenantGrowthFunnelSnapshot.pql_qualified_at.is_(None))
        .where(TenantGrowthFunnelSnapshot.tenant_onboarded_at.is_not(None))
        .where(TenantGrowthFunnelSnapshot.first_connection_verified_at.is_not(None))
        .where(TenantGrowthFunnelSnapshot.first_value_activated_at.is_not(None))
        .values(
            pql_qualified_at=func.coalesce(
                TenantGrowthFunnelSnapshot.pql_qualified_at,
                TenantGrowthFunnelSnapshot.first_value_activated_at,
            ),
            updated_at=datetime.now(timezone.utc),
        )
    )

    await db.flush()

    snapshot = (
        await db.execute(
            select(TenantGrowthFunnelSnapshot).where(
                TenantGrowthFunnelSnapshot.tenant_id == tenant_id
            )
        )
    ).scalar_one()
    if commit:
        await db.commit()
    return _normalize_snapshot_datetimes(snapshot)
