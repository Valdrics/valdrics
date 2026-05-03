from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, AsyncIterator
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribution import CostAllocation
from app.models.aws_connection import AWSConnection
from app.models.azure_connection import AzureConnection
from app.models.cloud import CloudAccount, CostRecord
from app.models.gcp_connection import GCPConnection
from app.models.hybrid_connection import HybridConnection
from app.models.license_connection import LicenseConnection
from app.models.llm import LLMUsage
from app.models.platform_connection import PlatformConnection
from app.models.saas_connection import SaaSConnection
from app.modules.reporting.domain.focus_export_helpers import (
    _CLOUD_PROVIDER_DISPLAY,
    _focus_charge_category,
    _focus_charge_frequency,
    _focus_service_category,
    _humanize_vendor,
    _service_provider_display,
)
from app.modules.reporting.domain.focus_export_rows import (
    AI_FOCUS_PROVIDER,
    FOCUS_V13_CORE_COLUMNS,
    FocusAccountContext,
    FocusAllocation,
    FocusAllocationKey,
    FocusSyntheticAllocation,
    _allocation_bucket,
    _date_window_bounds,
    _format_cost,
    _format_currency,
    _format_optional_decimal,
    _next_month_start,
    _tags_json,
    _to_decimal,
    llm_usage_to_focus,
    row_to_focus,
)

logger = structlog.get_logger()
FOCUS_EXPORT_STREAM_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    SQLAlchemyError,
    RuntimeError,
    OSError,
    TimeoutError,
    TypeError,
    ValueError,
    AttributeError,
)
__all__ = (
    "FOCUS_V13_CORE_COLUMNS",
    "FocusV13ExportService",
    "_format_cost",
    "_format_currency",
    "_format_optional_decimal",
    "_humanize_vendor",
    "_next_month_start",
    "_service_provider_display",
    "_focus_charge_category",
    "_focus_charge_frequency",
    "_focus_service_category",
    "_tags_json",
)


class FocusV13ExportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_rows(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        provider: str | None = None,
        include_preliminary: bool = False,
    ) -> AsyncIterator[dict[str, str]]:
        include_origin_spend = provider != AI_FOCUS_PROVIDER
        include_ai_spend = provider in (None, AI_FOCUS_PROVIDER)

        if include_origin_spend:
            async for row in self._export_origin_rows(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
                provider=provider,
                include_preliminary=include_preliminary,
            ):
                yield row
        if include_ai_spend:
            async for row in self._export_ai_rows(
                tenant_id=tenant_id,
                start_date=start_date,
                end_date=end_date,
            ):
                yield row

    async def _export_origin_rows(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        provider: str | None,
        include_preliminary: bool,
    ) -> AsyncIterator[dict[str, str]]:
        contexts = await self._load_account_contexts(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            include_preliminary=include_preliminary,
        )
        filters: list[Any] = [
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
        ]
        if not include_preliminary:
            filters.append(CostRecord.cost_status == "FINAL")
        if provider:
            filters.append(CloudAccount.provider == provider)

        stmt = (
            select(CostRecord, CloudAccount, CostAllocation)
            .join(CloudAccount, CostRecord.account_id == CloudAccount.id)
            .outerjoin(
                CostAllocation,
                (CostAllocation.cost_record_id == CostRecord.id)
                & (CostAllocation.recorded_at == CostRecord.recorded_at),
            )
            .where(*filters)
            .order_by(
                CostRecord.recorded_at.asc(),
                CostRecord.timestamp.asc(),
                CostRecord.id.asc(),
                CostAllocation.timestamp.asc(),
                CostAllocation.id.asc(),
            )
            .execution_options(yield_per=500)
        )

        # Use streaming where supported; SQLite in tests still works with execute().
        try:
            result = await self.db.stream(stmt)
            current_key: FocusAllocationKey | None = None
            current_record: CostRecord | None = None
            current_account: CloudAccount | None = None
            current_allocations: list[CostAllocation] = []
            async for cost_record, account, allocation in result:
                record_key = self._allocation_key_for_record(cost_record)
                if current_key is not None and record_key != current_key:
                    if current_record is not None and current_account is not None:
                        for focus_row in self._rows_for_cost_record(
                            current_record,
                            current_account,
                            contexts,
                            {current_key: current_allocations},
                        ):
                            yield focus_row
                    current_allocations = []
                current_key = record_key
                current_record = cost_record
                current_account = account
                if allocation is not None:
                    current_allocations.append(allocation)

            if (
                current_key is not None
                and current_record is not None
                and current_account is not None
            ):
                for focus_row in self._rows_for_cost_record(
                    current_record,
                    current_account,
                    contexts,
                    {current_key: current_allocations},
                ):
                    yield focus_row
            return
        except FOCUS_EXPORT_STREAM_RECOVERABLE_EXCEPTIONS:
            logger.debug("focus_export_stream_fallback_to_execute")

        sync_result = await self.db.execute(stmt)
        for cost_record, account, allocations in self._group_origin_rows(sync_result):
            record_key = self._allocation_key_for_record(cost_record)
            for focus_row in self._rows_for_cost_record(
                cost_record,
                account,
                contexts,
                {record_key: allocations},
            ):
                yield focus_row

    async def _export_ai_rows(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
    ) -> AsyncIterator[dict[str, str]]:
        window_start, window_end = _date_window_bounds(start_date, end_date)
        stmt = (
            select(LLMUsage)
            .where(
                LLMUsage.tenant_id == tenant_id,
                LLMUsage.created_at >= window_start,
                LLMUsage.created_at < window_end,
            )
            .order_by(LLMUsage.created_at.asc(), LLMUsage.id.asc())
            .execution_options(stream_results=True)
        )
        try:
            result = await self.db.stream(stmt)
            async for usage in result.scalars():
                yield self._llm_usage_to_focus(usage)
            return
        except FOCUS_EXPORT_STREAM_RECOVERABLE_EXCEPTIONS:
            logger.debug("focus_export_ai_stream_fallback_to_execute")

        rows = (await self.db.execute(stmt)).scalars().all()
        for usage in rows:
            yield self._llm_usage_to_focus(usage)

    async def _load_account_contexts(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        provider: str | None,
        include_preliminary: bool,
    ) -> dict[UUID, FocusAccountContext]:
        filters: list[Any] = [
            CostRecord.tenant_id == tenant_id,
            CostRecord.recorded_at >= start_date,
            CostRecord.recorded_at <= end_date,
        ]
        if not include_preliminary:
            filters.append(CostRecord.cost_status == "FINAL")
        if provider:
            filters.append(CloudAccount.provider == provider)

        stmt = (
            select(CloudAccount.id, CloudAccount.provider, CloudAccount.name)
            .join(CostRecord, CostRecord.account_id == CloudAccount.id)
            .where(*filters)
            .distinct()
        )
        rows = (await self.db.execute(stmt)).all()

        contexts: dict[UUID, FocusAccountContext] = {}
        ids_by_provider: dict[str, list[UUID]] = {}
        for account_id, provider_key, name in rows:
            provider_key = str(provider_key or "").strip().lower()
            display = _service_provider_display(provider_key)
            contexts[account_id] = FocusAccountContext(
                provider_key=provider_key,
                billing_account_id=str(account_id),
                billing_account_name=str(name or ""),
                provider_name=display,
                publisher_name=display,
                service_provider_name=display,
                invoice_issuer_name=display,
            )
            ids_by_provider.setdefault(provider_key, []).append(account_id)

        # Enrich with provider-native identifiers and Cloud+ vendor names.
        await self._enrich_cloud_accounts(contexts, ids_by_provider.get("aws", []))
        await self._enrich_cloud_accounts(contexts, ids_by_provider.get("azure", []))
        await self._enrich_cloud_accounts(contexts, ids_by_provider.get("gcp", []))
        await self._enrich_cloud_plus_accounts(
            contexts, "saas", ids_by_provider.get("saas", [])
        )
        await self._enrich_cloud_plus_accounts(
            contexts, "license", ids_by_provider.get("license", [])
        )
        await self._enrich_cloud_plus_accounts(
            contexts, "platform", ids_by_provider.get("platform", [])
        )
        await self._enrich_cloud_plus_accounts(
            contexts, "hybrid", ids_by_provider.get("hybrid", [])
        )

        return contexts

    def _rows_for_cost_record(
        self,
        cost_record: CostRecord,
        account: CloudAccount,
        contexts: dict[UUID, FocusAccountContext],
        allocations_by_record_key: dict[FocusAllocationKey, list[CostAllocation]],
    ) -> list[dict[str, str]]:
        allocations = allocations_by_record_key.get(
            self._allocation_key_for_record(cost_record), []
        )
        if not allocations:
            return [self._row_to_focus(cost_record, account, contexts)]

        # A single synthetic Unallocated row from the attribution engine is not
        # a split allocation, so keep the export at the origin-charge level.
        if (
            len(allocations) == 1
            and allocations[0].rule_id is None
            and _allocation_bucket(allocations[0].allocated_to).lower()
            == "unallocated"
        ):
            return [self._row_to_focus(cost_record, account, contexts)]

        allocations_for_export: list[FocusAllocation] = [*allocations]
        origin_cost = _to_decimal(getattr(cost_record, "cost_usd", None), field_name="origin cost")
        allocated_cost = sum(
            (
                _to_decimal(allocation.amount, field_name="allocation amount")
                for allocation in allocations
            ),
            Decimal("0"),
        )
        unallocated_cost = origin_cost - allocated_cost
        if unallocated_cost > Decimal("0"):
            percentage = (
                Decimal("0")
                if origin_cost == Decimal("0")
                else (unallocated_cost / origin_cost) * Decimal("100")
            )
            allocations_for_export.append(
                FocusSyntheticAllocation(
                    id=(
                        f"{getattr(cost_record, 'id', 'unknown')}:"
                        f"{getattr(cost_record, 'recorded_at', 'unknown')}:"
                        "unallocated-remainder"
                    ),
                    rule_id=None,
                    allocated_to="Unallocated",
                    amount=unallocated_cost,
                    percentage=percentage,
                )
            )

        return [
            self._row_to_focus(cost_record, account, contexts, allocation=allocation)
            for allocation in allocations_for_export
        ]

    def _allocation_key_for_record(self, cost_record: CostRecord) -> FocusAllocationKey:
        record_id = getattr(cost_record, "id", None)
        recorded_at = getattr(cost_record, "recorded_at", None)
        if not isinstance(record_id, UUID) or not isinstance(recorded_at, date):
            raise ValueError("FOCUS export cost records require id and recorded_at")
        return (record_id, recorded_at)

    def _group_origin_rows(
        self,
        rows: Any,
    ) -> list[tuple[CostRecord, CloudAccount, list[CostAllocation]]]:
        grouped: list[tuple[CostRecord, CloudAccount, list[CostAllocation]]] = []
        current_key: FocusAllocationKey | None = None
        current_record: CostRecord | None = None
        current_account: CloudAccount | None = None
        current_allocations: list[CostAllocation] = []

        for cost_record, account, allocation in rows:
            record_key = self._allocation_key_for_record(cost_record)
            if current_key is not None and record_key != current_key:
                if current_record is not None and current_account is not None:
                    grouped.append((current_record, current_account, current_allocations))
                current_allocations = []
            current_key = record_key
            current_record = cost_record
            current_account = account
            if allocation is not None:
                current_allocations.append(allocation)

        if (
            current_key is not None
            and current_record is not None
            and current_account is not None
        ):
            grouped.append((current_record, current_account, current_allocations))
        return grouped

    async def _enrich_cloud_accounts(
        self,
        contexts: dict[UUID, FocusAccountContext],
        account_ids: list[UUID],
    ) -> None:
        if not account_ids:
            return

        # Note: each connection model stores its provider-native identifier in a different field.
        # We update BillingAccountId so exports can round-trip to provider invoices.
        aws_rows = (
            await self.db.execute(
                select(AWSConnection.id, AWSConnection.aws_account_id).where(
                    AWSConnection.id.in_(account_ids)
                )
            )
        ).all()
        for conn_id, aws_account_id in aws_rows:
            ctx = contexts.get(conn_id)
            if not ctx:
                continue
            display = _CLOUD_PROVIDER_DISPLAY["aws"]
            contexts[conn_id] = FocusAccountContext(
                provider_key=ctx.provider_key,
                billing_account_id=str(aws_account_id),
                billing_account_name=f"AWS {aws_account_id}",
                provider_name=display,
                publisher_name=display,
                service_provider_name=display,
                invoice_issuer_name=display,
            )

        azure_rows = (
            await self.db.execute(
                select(AzureConnection.id, AzureConnection.subscription_id).where(
                    AzureConnection.id.in_(account_ids)
                )
            )
        ).all()
        for conn_id, subscription_id in azure_rows:
            ctx = contexts.get(conn_id)
            if not ctx:
                continue
            display = _CLOUD_PROVIDER_DISPLAY["azure"]
            contexts[conn_id] = FocusAccountContext(
                provider_key=ctx.provider_key,
                billing_account_id=str(subscription_id),
                billing_account_name=ctx.billing_account_name or str(subscription_id),
                provider_name=display,
                publisher_name=display,
                service_provider_name=display,
                invoice_issuer_name=display,
            )

        gcp_rows = (
            await self.db.execute(
                select(GCPConnection.id, GCPConnection.project_id).where(
                    GCPConnection.id.in_(account_ids)
                )
            )
        ).all()
        for conn_id, project_id in gcp_rows:
            ctx = contexts.get(conn_id)
            if not ctx:
                continue
            display = _CLOUD_PROVIDER_DISPLAY["gcp"]
            contexts[conn_id] = FocusAccountContext(
                provider_key=ctx.provider_key,
                billing_account_id=str(project_id),
                billing_account_name=ctx.billing_account_name or str(project_id),
                provider_name=display,
                publisher_name=display,
                service_provider_name=display,
                invoice_issuer_name=display,
            )

    async def _enrich_cloud_plus_accounts(
        self,
        contexts: dict[UUID, FocusAccountContext],
        provider_key: str,
        account_ids: list[UUID],
    ) -> None:
        if not account_ids:
            return

        model = {
            "saas": SaaSConnection,
            "license": LicenseConnection,
            "platform": PlatformConnection,
            "hybrid": HybridConnection,
        }.get(provider_key)
        if model is None:
            return

        sync_result = await self.db.execute(
            select(getattr(model, "id"), getattr(model, "vendor")).where(
                getattr(model, "id").in_(account_ids)
            )
        )
        for conn_id, vendor in sync_result.all():
            ctx = contexts.get(conn_id)
            if not ctx:
                continue
            issuer = _service_provider_display(
                provider_key, str(vendor) if vendor else None
            )
            contexts[conn_id] = FocusAccountContext(
                provider_key=ctx.provider_key,
                billing_account_id=str(conn_id),
                billing_account_name=ctx.billing_account_name,
                provider_name=issuer,
                publisher_name=issuer,
                service_provider_name=issuer,
                invoice_issuer_name=issuer,
            )

    def _row_to_focus(
        self,
        cost_record: CostRecord,
        account: CloudAccount,
        contexts: dict[UUID, FocusAccountContext],
        allocation: FocusAllocation | None = None,
    ) -> dict[str, str]:
        return row_to_focus(cost_record, account, contexts, allocation=allocation)

    def _llm_usage_to_focus(self, usage: LLMUsage) -> dict[str, str]:
        return llm_usage_to_focus(usage)
