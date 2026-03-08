"""DB-backed cloud resource pricing catalog with safe default seeding."""

from __future__ import annotations

from collections.abc import Iterable
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.shared.core.cloud_pricing_aws_sync import collect_supported_aws_pricing_records
from app.shared.core.pricing_defaults import (
    AVERAGE_BILLING_MONTH_HOURS,
    DEFAULT_RATES,
    REGION_MULTIPLIERS,
)

logger = structlog.get_logger()

CLOUD_PRICING_REFRESH_RECOVERABLE_EXCEPTIONS = (
    SQLAlchemyError,
    RuntimeError,
    TypeError,
    ValueError,
    AttributeError,
    OSError,
    ImportError,
)

_CLOUD_PRICING_CACHE: dict[tuple[str, str, str, str], float] = {}
_CLOUD_PRICING_DETAILS_CACHE: dict[tuple[str, str, str, str], dict[str, Any]] = {}
def _normalize_key(value: Any, *, default: str = "") -> str:
    normalized = str(value or default).strip().lower()
    return normalized or default


def _normalize_size(value: Any) -> str:
    return _normalize_key(value, default="default")


def _safe_rate(value: Any) -> float:
    if isinstance(value, Decimal):
        return float(value)
    return float(value or 0.0)


def _cache_key(
    provider: str,
    resource_type: str,
    resource_size: str,
    region: str,
) -> tuple[str, str, str, str]:
    return (
        _normalize_key(provider),
        _normalize_key(resource_type),
        _normalize_size(resource_size),
        _normalize_key(region, default="global"),
    )


def get_cloud_hourly_rate(
    provider: str,
    resource_type: str,
    resource_size: str | None = None,
    region: str = "global",
) -> float:
    normalized_provider = _normalize_key(provider)
    normalized_type = _normalize_key(resource_type)
    normalized_size = _normalize_size(resource_size)
    normalized_region = _normalize_key(region, default="global")

    exact_key = _cache_key(
        normalized_provider, normalized_type, normalized_size, normalized_region
    )
    default_region_key = _cache_key(
        normalized_provider, normalized_type, "default", normalized_region
    )
    global_key = _cache_key(normalized_provider, normalized_type, normalized_size, "global")
    global_default_key = _cache_key(
        normalized_provider, normalized_type, "default", "global"
    )

    if exact_key in _CLOUD_PRICING_CACHE:
        return _CLOUD_PRICING_CACHE[exact_key]
    if default_region_key in _CLOUD_PRICING_CACHE:
        return _CLOUD_PRICING_CACHE[default_region_key]

    base_rate = _CLOUD_PRICING_CACHE.get(global_key)
    if base_rate is None:
        base_rate = _CLOUD_PRICING_CACHE.get(global_default_key)
    if base_rate is None:
        logger.debug(
            "cloud_pricing_missing",
            provider=provider,
            resource_type=resource_type,
            resource_size=resource_size,
            region=region,
        )
        return 0.0

    multiplier = REGION_MULTIPLIERS.get(normalized_region, 1.0)
    return float(base_rate) * float(multiplier)


def get_cloud_pricing_quote(
    provider: str,
    resource_type: str,
    resource_size: str | None = None,
    region: str = "global",
) -> dict[str, Any]:
    normalized_provider = _normalize_key(provider)
    normalized_type = _normalize_key(resource_type)
    normalized_size = _normalize_size(resource_size)
    normalized_region = _normalize_key(region, default="global")

    key_candidates: tuple[tuple[str, tuple[str, str, str, str]], ...] = (
        (
            "exact_region_size",
            _cache_key(normalized_provider, normalized_type, normalized_size, normalized_region),
        ),
        (
            "exact_region_default_size",
            _cache_key(normalized_provider, normalized_type, "default", normalized_region),
        ),
        (
            "global_exact_size_regionalized",
            _cache_key(normalized_provider, normalized_type, normalized_size, "global"),
        ),
        (
            "global_default_regionalized",
            _cache_key(normalized_provider, normalized_type, "default", "global"),
        ),
    )
    selected = next(
        (
            (match_strategy, key)
            for match_strategy, key in key_candidates
            if key in _CLOUD_PRICING_DETAILS_CACHE
        ),
        None,
    )
    selected_match_strategy = selected[0] if selected is not None else None
    selected_key = selected[1] if selected is not None else None
    if selected_key is None:
        return {
            "provider": normalized_provider,
            "resource_type": normalized_type,
            "resource_size": normalized_size,
            "requested_region": normalized_region,
            "effective_region": "missing",
            "hourly_rate_usd": 0.0,
            "source": "missing",
            "pricing_metadata": {},
        }

    details = dict(_CLOUD_PRICING_DETAILS_CACHE[selected_key])
    pricing_metadata = dict(details.get("pricing_metadata") or {})
    hourly_rate = get_cloud_hourly_rate(
        provider=normalized_provider,
        resource_type=normalized_type,
        resource_size=normalized_size,
        region=normalized_region,
    )
    effective_region = str(details.get("effective_region") or "global")
    pricing_metadata.update(
        {
            "match_strategy": selected_match_strategy or "missing",
            "requested_region": normalized_region,
            "effective_region": effective_region,
            "region_multiplier_applied": (
                float(REGION_MULTIPLIERS.get(normalized_region, 1.0))
                if effective_region == "global" and normalized_region != "global"
                else 1.0
            ),
            "pricing_confidence": (
                "catalog_exact"
                if selected_match_strategy == "exact_region_size"
                else (
                    "catalog_size_fallback"
                    if selected_match_strategy == "exact_region_default_size"
                    else (
                        "regionalized_catalog_baseline"
                        if selected_match_strategy == "global_exact_size_regionalized"
                        else "regionalized_default_baseline"
                    )
                )
            ),
        }
    )
    details.update(
        {
            "provider": normalized_provider,
            "resource_type": normalized_type,
            "resource_size": normalized_size,
            "requested_region": normalized_region,
            "hourly_rate_usd": hourly_rate,
            "pricing_metadata": pricing_metadata,
        }
    )
    return details


def _flatten_default_rates() -> list[dict[str, Any]]:
    seed_records: list[dict[str, Any]] = []
    for provider, resource_map in DEFAULT_RATES.items():
        for resource_type, resource_value in resource_map.items():
            if isinstance(resource_value, dict):
                for resource_size, hourly_rate in resource_value.items():
                    seed_records.append(
                        {
                            "provider": _normalize_key(provider),
                            "resource_type": _normalize_key(resource_type),
                            "resource_size": _normalize_size(resource_size),
                            "region": "global",
                            "hourly_rate_usd": _safe_rate(hourly_rate),
                            "source": "default_catalog",
                            "pricing_metadata": {
                                "billing_period_hours": AVERAGE_BILLING_MONTH_HOURS,
                                "coverage_scope": "repo_default_catalog",
                                "pricing_basis": "hourly_normalized_default",
                                "coverage_limitations": (
                                    "Checked-in default pricing catalog; live provider catalog coverage may differ by region, size, and HA profile."
                                ),
                            },
                        }
                    )
            else:
                seed_records.append(
                    {
                        "provider": _normalize_key(provider),
                        "resource_type": _normalize_key(resource_type),
                        "resource_size": "default",
                        "region": "global",
                        "hourly_rate_usd": _safe_rate(resource_value),
                        "source": "default_catalog",
                        "pricing_metadata": {
                            "billing_period_hours": AVERAGE_BILLING_MONTH_HOURS,
                            "coverage_scope": "repo_default_catalog",
                            "pricing_basis": "hourly_default",
                            "coverage_limitations": (
                                "Checked-in default pricing catalog; live provider catalog coverage may differ by region, size, and HA profile."
                            ),
                        },
                    }
                )
    return seed_records


async def _upsert_catalog_records(*, db_session: Any, records: Iterable[dict[str, Any]]) -> int:
    from app.models.pricing import CloudResourcePricing

    updated = 0
    for record in records:
        stmt = select(CloudResourcePricing).where(
            CloudResourcePricing.provider == record["provider"],
            CloudResourcePricing.resource_type == record["resource_type"],
            CloudResourcePricing.resource_size == record["resource_size"],
            CloudResourcePricing.region == record["region"],
        )
        existing = (await db_session.execute(stmt)).scalar_one_or_none()
        if existing is None:
            db_session.add(CloudResourcePricing(**record))
            updated += 1
            continue
        existing.hourly_rate_usd = record["hourly_rate_usd"]
        existing.source = record["source"]
        existing.pricing_metadata = dict(record.get("pricing_metadata") or {})
        existing.is_active = True
        updated += 1
    return updated


async def seed_default_cloud_pricing_catalog(db_session: Any = None) -> int:
    """Persist the checked-in default cloud pricing catalog to the database."""
    from app.shared.db.session import async_session_maker, mark_session_system_context

    async def _seed(session: Any, *, commit: bool) -> int:
        updated = await _upsert_catalog_records(
            db_session=session,
            records=_flatten_default_rates(),
        )
        if commit:
            await session.commit()
        else:
            await session.flush()
        return updated

    if db_session is None:
        async with async_session_maker() as session:
            await mark_session_system_context(session)
            return await _seed(session, commit=True)
    return await _seed(db_session, commit=False)


def _refresh_cache_from_rows(rows: Iterable[Any]) -> int:
    _CLOUD_PRICING_CACHE.clear()
    _CLOUD_PRICING_DETAILS_CACHE.clear()
    count = 0
    for row in rows:
        key = _cache_key(
            getattr(row, "provider", None),
            getattr(row, "resource_type", None),
            getattr(row, "resource_size", None),
            getattr(row, "region", None),
        )
        _CLOUD_PRICING_CACHE[key] = _safe_rate(getattr(row, "hourly_rate_usd", 0.0))
        _CLOUD_PRICING_DETAILS_CACHE[key] = {
            "effective_region": _normalize_key(getattr(row, "region", None), default="global"),
            "source": _normalize_key(getattr(row, "source", None), default="default_catalog"),
            "pricing_metadata": dict(getattr(row, "pricing_metadata", {}) or {}),
        }
        count += 1
    return count


async def refresh_cloud_resource_pricing(db_session: Any = None) -> int:
    """Refresh the in-memory pricing cache from the persisted catalog, seeding defaults if empty."""
    from app.models.pricing import CloudResourcePricing
    from app.shared.db.session import async_session_maker, mark_session_system_context

    async def _refresh(session: Any) -> int:
        stmt = select(CloudResourcePricing).where(CloudResourcePricing.is_active.is_(True))
        rows = (await session.execute(stmt)).scalars().all()
        if not rows:
            await seed_default_cloud_pricing_catalog(session)
            rows = (await session.execute(stmt)).scalars().all()
        refreshed = _refresh_cache_from_rows(rows)
        logger.info("cloud_pricing_cache_refreshed", record_count=refreshed)
        return refreshed

    try:
        if db_session is None:
            async with async_session_maker() as session:
                await mark_session_system_context(session)
                return await _refresh(session)
        return await _refresh(db_session)
    except CLOUD_PRICING_REFRESH_RECOVERABLE_EXCEPTIONS as exc:
        logger.error("cloud_pricing_refresh_failed", error=str(exc))
        return 0


async def sync_supported_aws_pricing(db_session: Any = None, *, client: Any = None) -> int:
    """
    Persist supported AWS Pricing API observations into the catalog.

    The repository synchronizes a curated set of verified AWS catalog probes for the
    resource classes that are priced directly by the optimization engine.
    """
    from app.shared.db.session import async_session_maker, mark_session_system_context

    try:
        import boto3
        from botocore.exceptions import BotoCoreError
    except ImportError as exc:
        logger.error("aws_pricing_sync_failed", error=str(exc))
        return 0

    pricing_client = client or boto3.client("pricing", region_name="us-east-1")
    try:
        records = collect_supported_aws_pricing_records(pricing_client)
    except (BotoCoreError, OSError, RuntimeError, ValueError, TypeError) as exc:
        logger.warning("aws_pricing_sync_unavailable", error=str(exc))
        return 0
    if not records:
        logger.warning("aws_pricing_sync_no_supported_rates_found")
        return 0

    async def _sync(session: Any, *, commit: bool) -> int:
        updated = await _upsert_catalog_records(db_session=session, records=records)
        if commit:
            await session.commit()
        else:
            await session.flush()
        await refresh_cloud_resource_pricing(session)
        logger.info(
            "aws_pricing_sync_completed",
            supported_records=updated,
        )
        return updated

    try:
        if db_session is None:
            async with async_session_maker() as session:
                await mark_session_system_context(session)
                return await _sync(session, commit=True)
        return await _sync(db_session, commit=False)
    except CLOUD_PRICING_REFRESH_RECOVERABLE_EXCEPTIONS as exc:
        logger.error("aws_pricing_sync_failed", error=str(exc))
        return 0


__all__ = [
    "CLOUD_PRICING_REFRESH_RECOVERABLE_EXCEPTIONS",
    "get_cloud_hourly_rate",
    "get_cloud_pricing_quote",
    "refresh_cloud_resource_pricing",
    "seed_default_cloud_pricing_catalog",
    "sync_supported_aws_pricing",
]
