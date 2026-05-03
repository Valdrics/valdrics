import pytest
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribution import CostAllocation
from app.models.cloud import CostRecord, CloudAccount
from app.modules.reporting.domain.aggregator import CostAggregator


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_cost_aggregator_basic_breakdown(db: AsyncSession):
    """
    Test that the cost aggregator correctly sums costs by service.
    (Issue R2: Unit tests for cost aggregation)
    """
    tenant_id = uuid4()

    # Setup Tenant for FK
    from app.models.tenant import Tenant

    db.add(Tenant(id=tenant_id, name="Test Tenant", plan="enterprise"))
    await db.flush()

    # Setup test accounts
    account = CloudAccount(
        id=uuid4(), tenant_id=tenant_id, provider="aws", name="Test AWS", is_active=True
    )
    db.add(account)

    # Setup cost records
    records = [
        CostRecord(
            tenant_id=tenant_id,
            account_id=account.id,
            service="EC2",
            cost_usd=Decimal("100.00"),
            carbon_kg=Decimal("10.0"),
            recorded_at=date(2026, 1, 1),
        ),
        CostRecord(
            tenant_id=tenant_id,
            account_id=account.id,
            service="EC2",
            cost_usd=Decimal("50.00"),
            carbon_kg=Decimal("5.0"),
            recorded_at=date(2026, 1, 2),
        ),
        CostRecord(
            tenant_id=tenant_id,
            account_id=account.id,
            service="S3",
            cost_usd=Decimal("25.00"),
            carbon_kg=Decimal("1.0"),
            recorded_at=date(2026, 1, 1),
        ),
    ]
    for r in records:
        db.add(r)

    await db.commit()

    # Execute aggregation
    breakdown = await CostAggregator.get_basic_breakdown(
        db,
        tenant_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        provider="aws",
    )

    # Assert total costs
    assert breakdown["total_cost"] == 175.0
    assert breakdown["total_carbon_kg"] == 16.0

    # Assert individual services
    services = {s["service"]: s for s in breakdown["breakdown"]}
    assert services["EC2"]["cost"] == 150.0
    assert services["S3"]["cost"] == 25.0
    assert len(breakdown["breakdown"]) == 2


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_cost_aggregator_tenant_isolation(db: AsyncSession):
    """
    Verify that aggregator only returns data for the specified tenant.
    """
    tenant_a = uuid4()
    tenant_b = uuid4()

    # Setup Tenants for FK
    from app.models.tenant import Tenant

    db.add_all(
        [
            Tenant(id=tenant_a, name="Tenant A", plan="pro"),
            Tenant(id=tenant_b, name="Tenant B", plan="starter"),
        ]
    )
    await db.flush()

    account_a = CloudAccount(
        tenant_id=tenant_a,
        provider="aws",
        name="A",
    )
    account_b = CloudAccount(
        tenant_id=tenant_b,
        provider="aws",
        name="B",
    )
    db.add_all([account_a, account_b])
    await db.flush()

    db.add(
        CostRecord(
            tenant_id=tenant_a,
            account_id=account_a.id,
            service="EC2",
            cost_usd=Decimal("10.00"),
            recorded_at=date(2026, 1, 1),
        )
    )
    db.add(
        CostRecord(
            tenant_id=tenant_b,
            account_id=account_b.id,
            service="EC2",
            cost_usd=Decimal("20.00"),
            recorded_at=date(2026, 1, 1),
        )
    )
    await db.commit()

    # Check Tenant A
    breakdown_a = await CostAggregator.get_basic_breakdown(
        db, tenant_a, date(2026, 1, 1), date(2026, 1, 1), provider="aws"
    )
    assert breakdown_a["total_cost"] == 10.0

    # Check Tenant B
    breakdown_b = await CostAggregator.get_basic_breakdown(
        db, tenant_b, date(2026, 1, 1), date(2026, 1, 1), provider="aws"
    )
    assert breakdown_b["total_cost"] == 20.0


@pytest.mark.asyncio
async def test_governance_report_uses_cost_allocations_as_canonical_source(
    db: AsyncSession,
) -> None:
    from app.models.tenant import Tenant

    tenant_id = uuid4()
    db.add(Tenant(id=tenant_id, name="Canonical Allocation Tenant", plan="enterprise"))
    await db.flush()

    account = CloudAccount(
        id=uuid4(),
        tenant_id=tenant_id,
        provider="aws",
        name="Production AWS",
        is_active=True,
    )
    db.add(account)
    await db.flush()

    allocated_record = CostRecord(
        id=uuid4(),
        tenant_id=tenant_id,
        account_id=account.id,
        service="EC2",
        cost_usd=Decimal("100.00"),
        recorded_at=date(2026, 1, 1),
        allocated_to=None,
    )
    unallocated_record = CostRecord(
        id=uuid4(),
        tenant_id=tenant_id,
        account_id=account.id,
        service="S3",
        cost_usd=Decimal("50.00"),
        recorded_at=date(2026, 1, 1),
        allocated_to="Team-That-Should-Be-Ignored",
    )
    db.add_all([allocated_record, unallocated_record])
    await db.flush()

    db.add(
        CostAllocation(
            cost_record_id=allocated_record.id,
            recorded_at=allocated_record.recorded_at,
            rule_id=None,
            allocated_to="Platform",
            amount=Decimal("100.00"),
            percentage=Decimal("100.00"),
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
    )
    await db.commit()

    report = await CostAggregator.get_governance_report(
        db,
        tenant_id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
    )

    assert report["total_cost"] == 150.0
    assert report["unallocated_cost"] == 50.0
    assert report["resource_count"] == 1
    assert report["insights"][0]["service"] == "S3"
    assert report["insights"][0]["amount"] == 50.0
