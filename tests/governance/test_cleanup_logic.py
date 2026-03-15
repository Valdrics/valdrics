import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from decimal import Decimal
from sqlalchemy import select, func
from app.models.cloud import CostRecord
from app.modules.reporting.domain.persistence import CostPersistenceService


@pytest.mark.asyncio
async def test_batched_cleanup(db):
    """Verify that cleanup_old_records deletes in batches and commits."""
    service = CostPersistenceService(db)

    from datetime import timezone

    old_date = datetime.now(timezone.utc) - timedelta(days=400)
    # Create dependencies to satisfy foreign keys
    from app.models.tenant import Tenant
    from app.models.cloud import CloudAccount

    tenant = Tenant(id=uuid4(), name="Cleanup Test Tenant")
    db.add(tenant)
    await db.flush()

    # Set tenant context to satisfy RLS
    from app.shared.db.session import set_session_tenant_id

    await set_session_tenant_id(db, tenant.id)

    account = CloudAccount(
        id=uuid4(),
        tenant_id=tenant.id,
        provider="aws",
        name="Cleanup Test Account",
    )
    db.add(account)
    await db.flush()  # Flush to DB but don't commit yet

    records = []
    for _ in range(10):
        records.append(
            CostRecord(
                tenant_id=tenant.id,
                account_id=account.id,
                service="EC2",
                cost_usd=Decimal("1.0"),
                recorded_at=old_date.date(),
                timestamp=old_date,
            )
        )

    db.add_all(records)
    await db.flush()

    # Verify records exist
    result = await db.execute(
        select(func.count())
        .select_from(CostRecord)
        .where(CostRecord.tenant_id == tenant.id)
    )
    count = result.scalar()
    assert count == 10

    # Run cleanup
    res = await service.cleanup_old_records(days_retention=365)

    # Verify records are gone
    result = await db.execute(
        select(func.count())
        .select_from(CostRecord)
        .where(CostRecord.tenant_id == tenant.id)
    )
    count_after = result.scalar()
    assert count_after == 0
    # deleted_count should be at least 10 (our records)
    assert res["deleted_count"] >= 10


@pytest.mark.asyncio
async def test_batched_cleanup_removes_legacy_null_timestamp_rows(db):
    service = CostPersistenceService(db)

    from datetime import timezone

    old_date = datetime.now(timezone.utc) - timedelta(days=400)
    from app.models.tenant import Tenant
    from app.models.cloud import CloudAccount
    from app.shared.db.session import set_session_tenant_id

    tenant = Tenant(id=uuid4(), name="Cleanup Null Timestamp Tenant")
    db.add(tenant)
    await db.flush()
    await set_session_tenant_id(db, tenant.id)

    account = CloudAccount(
        id=uuid4(),
        tenant_id=tenant.id,
        provider="aws",
        name="Cleanup Null Timestamp Account",
    )
    db.add(account)
    await db.flush()

    db.add(
        CostRecord(
            tenant_id=tenant.id,
            account_id=account.id,
            service="EC2",
            cost_usd=Decimal("1.0"),
            recorded_at=old_date.date(),
            timestamp=None,
        )
    )
    await db.flush()

    before_count = await db.execute(
        select(func.count())
        .select_from(CostRecord)
        .where(CostRecord.tenant_id == tenant.id)
    )
    assert before_count.scalar() == 1

    result = await service.cleanup_old_records(days_retention=365)

    after_count = await db.execute(
        select(func.count())
        .select_from(CostRecord)
        .where(CostRecord.tenant_id == tenant.id)
    )
    assert after_count.scalar() == 0
    assert result["deleted_count"] >= 1
