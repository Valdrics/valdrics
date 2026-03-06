"""Attribution engine for rule-based cost allocation (BE-FIN-ATTR-1)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribution import AttributionRule, CostAllocation
from app.models.cloud import CostRecord
from app.modules.reporting.domain.attribution_engine_allocation_ops import (
    apply_rules as _apply_rules_impl,
    apply_rules_to_tenant as _apply_rules_to_tenant_impl,
    get_allocation_coverage as _get_allocation_coverage_impl,
    get_allocation_summary as _get_allocation_summary_impl,
    get_unallocated_analysis as _get_unallocated_analysis_impl,
    match_conditions as _match_conditions_impl,
    process_cost_record as _process_cost_record_impl,
    simulate_rule as _simulate_rule_impl,
)
from app.modules.reporting.domain.attribution_engine_rule_crud import (
    create_rule as _create_rule_impl,
    get_active_rules as _get_active_rules_impl,
    get_rule as _get_rule_impl,
    list_rules as _list_rules_impl,
)
from app.modules.reporting.domain.attribution_engine_validation import (
    ATTRIBUTION_DECIMAL_PARSE_RECOVERABLE_EXCEPTIONS,
    VALID_RULE_TYPES,
    allocation_entries as _allocation_entries_impl,
    normalize_rule_type as _normalize_rule_type_impl,
    validate_rule_payload as _validate_rule_payload_impl,
)

logger = structlog.get_logger()


class AttributionEngine:
    """
    Applies attribution rules to cost records, creating CostAllocation records
    for percentage-based splits, direct allocations, and fixed allocations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def normalize_rule_type(self, rule_type: str) -> str:
        """Normalize rule type to uppercase for consistent matching."""
        return _normalize_rule_type_impl(rule_type)

    def validate_rule_payload(self, rule_type: str, allocation: Any) -> list[str]:
        """
        Validate allocation payload shape for a rule type.
        Returns a list of validation error messages; empty list means valid.
        """
        return _validate_rule_payload_impl(rule_type, allocation)

    def _allocation_entries(self, allocation: Any) -> list[dict[str, Any]]:
        """Normalize allocation payload to a list of dict entries."""
        return _allocation_entries_impl(allocation)

    async def list_rules(
        self,
        tenant_id: uuid.UUID,
        include_inactive: bool = False,
    ) -> list[AttributionRule]:
        """List tenant attribution rules ordered by priority."""
        return await _list_rules_impl(
            self.db,
            tenant_id,
            include_inactive=include_inactive,
        )

    async def get_rule(
        self,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID,
    ) -> AttributionRule | None:
        """Fetch one attribution rule scoped to tenant."""
        return await _get_rule_impl(self.db, tenant_id, rule_id)

    async def create_rule(
        self,
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
        normalized_type = self.normalize_rule_type(rule_type)
        return await _create_rule_impl(
            self.db,
            tenant_id,
            name=name,
            priority=priority,
            rule_type=normalized_type,
            conditions=conditions,
            allocation=allocation,
            is_active=is_active,
        )

    async def update_rule(
        self,
        tenant_id: uuid.UUID,
        rule_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> AttributionRule | None:
        """Update an existing attribution rule."""
        rule = await self.get_rule(tenant_id, rule_id)
        if not rule:
            return None

        if "rule_type" in updates and isinstance(updates["rule_type"], str):
            updates["rule_type"] = self.normalize_rule_type(updates["rule_type"])

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

        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def delete_rule(self, tenant_id: uuid.UUID, rule_id: uuid.UUID) -> bool:
        """Delete one tenant rule and return whether it existed."""
        rule = await self.get_rule(tenant_id, rule_id)
        if not rule:
            return False
        await self.db.delete(rule)
        await self.db.commit()
        return True

    async def get_active_rules(self, tenant_id: uuid.UUID) -> list[AttributionRule]:
        """
        Retrieve all active attribution rules for a tenant, ordered by priority.
        Lower priority numbers are evaluated first.
        """
        return await _get_active_rules_impl(self.db, tenant_id)

    def match_conditions(self, cost_record: CostRecord, conditions: dict[str, Any]) -> bool:
        """
        Check if a cost record matches rule conditions.
        Supports matching on: service, region, account_id, tags.
        """
        return _match_conditions_impl(cost_record, conditions)

    async def apply_rules(
        self,
        cost_record: CostRecord,
        rules: list[AttributionRule],
    ) -> list[CostAllocation]:
        """
        Apply attribution rules to a cost record and return allocations.
        First matching rule wins (rules are pre-sorted by priority).
        """
        return await _apply_rules_impl(
            cost_record,
            rules,
            match_conditions_fn=self.match_conditions,
            logger_obj=logger,
        )

    async def process_cost_record(
        self,
        cost_record: CostRecord,
        tenant_id: uuid.UUID,
    ) -> list[CostAllocation]:
        """
        Full pipeline: Get rules for tenant, apply to cost record, persist allocations.
        """
        return await _process_cost_record_impl(
            self.db,
            cost_record,
            tenant_id,
            get_active_rules_fn=self.get_active_rules,
            apply_rules_fn=self.apply_rules,
            logger_obj=logger,
        )

    async def apply_rules_to_tenant(
        self,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
        *,
        commit: bool = True,
    ) -> dict[str, int]:
        """
        Batch apply attribution rules to all cost records for tenant/date window.
        Used for recalculation or historical reconciliation.
        """
        return await _apply_rules_to_tenant_impl(
            self.db,
            tenant_id,
            start_date,
            end_date,
            get_active_rules_fn=self.get_active_rules,
            apply_rules_fn=self.apply_rules,
            logger_obj=logger,
            commit=commit,
        )

    async def get_allocation_summary(
        self,
        tenant_id: uuid.UUID,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
        bucket: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Get aggregated allocation summary by bucket for a tenant."""
        return await _get_allocation_summary_impl(
            self.db,
            tenant_id,
            start_date=start_date,
            end_date=end_date,
            bucket=bucket,
            limit=limit,
            offset=offset,
        )

    async def get_allocation_coverage(
        self,
        tenant_id: uuid.UUID,
        start_date: date | None = None,
        end_date: date | None = None,
        target_percentage: float = 90.0,
    ) -> dict[str, Any]:
        """
        Compute allocation coverage KPI for a tenant and date window.

        Coverage = allocated_cost / total_cost * 100
        """
        return await _get_allocation_coverage_impl(
            self.db,
            tenant_id,
            start_date=start_date,
            end_date=end_date,
            target_percentage=target_percentage,
        )

    async def get_unallocated_analysis(
        self,
        tenant_id: uuid.UUID,
        start_date: date,
        end_date: date,
    ) -> list[dict[str, Any]]:
        """
        Identify top services contributing to unallocated spend.
        Provides recommendations for attribution rules.
        """
        return await _get_unallocated_analysis_impl(
            self.db,
            tenant_id,
            start_date=start_date,
            end_date=end_date,
        )

    async def simulate_rule(
        self,
        tenant_id: uuid.UUID,
        *,
        rule_type: str,
        conditions: dict[str, Any],
        allocation: Any,
        start_date: date,
        end_date: date,
        sample_limit: int = 500,
    ) -> dict[str, Any]:
        """
        Run a dry-run simulation of one rule against tenant records in a range.
        """
        return await _simulate_rule_impl(
            self.db,
            tenant_id,
            rule_type=rule_type,
            conditions=conditions,
            allocation=allocation,
            start_date=start_date,
            end_date=end_date,
            normalize_rule_type_fn=self.normalize_rule_type,
            match_conditions_fn=self.match_conditions,
            apply_rules_fn=self.apply_rules,
            sample_limit=sample_limit,
        )


__all__ = [
    "AttributionEngine",
    "VALID_RULE_TYPES",
    "ATTRIBUTION_DECIMAL_PARSE_RECOVERABLE_EXCEPTIONS",
]
