"""
Cost Reconciliation Service

Detects discrepancies between "fast" API data (Explorer) and "slow" CUR data (S3 Parquet).
Ensures financial trust by flagging deltas >1%.
"""

import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Any, Dict
from uuid import UUID

import structlog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reporting.domain.reconciliation_close_package import (
    generate_close_package_impl,
)
from app.modules.reporting.domain.reconciliation_compare import (
    compare_explorer_vs_cur_impl,
)
from app.modules.reporting.domain.reconciliation_exports import (
    render_close_package_csv,
    render_restatement_runs_csv,
    render_restatements_csv,
)
from app.modules.reporting.domain.reconciliation_history import (
    get_restatement_history_impl,
    get_restatement_runs_impl,
)
from app.modules.reporting.domain.reconciliation_invoice import (
    delete_invoice_impl,
    get_invoice_impl,
    get_invoice_reconciliation_summary_impl,
    invoice_total_to_usd_impl,
    list_invoices_impl,
    update_invoice_status_impl,
    upsert_invoice_impl,
)
from app.shared.core.exceptions import ExternalAPIError

logger = structlog.get_logger()


RECON_ALERT_THRESHOLD_PCT = 1.0
SUPPORTED_RECON_PROVIDERS = {
    "aws",
    "azure",
    "gcp",
    "saas",
    "license",
    "platform",
    "hybrid",
}
INVOICE_EXCHANGE_RATE_IMPORT_EXCEPTIONS: tuple[type[Exception], ...] = (ImportError,)
RECON_ALERT_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    ExternalAPIError,
    SQLAlchemyError,
    AttributeError,
    RuntimeError,
    ValueError,
    TypeError,
)


class CostReconciliationService:
    INVOICE_EXCHANGE_RATE_IMPORT_EXCEPTIONS = INVOICE_EXCHANGE_RATE_IMPORT_EXCEPTIONS

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _normalize_source(source: str | None) -> str:
        source_key = (source or "unknown").strip().lower()
        if source_key in {"unknown", "", "null"}:
            return "unknown"

        if any(token in source_key for token in ("cur", "parquet", "s3")):
            return "cur"
        if any(
            token in source_key
            for token in ("explorer", "cost_explorer", "ce_api", "cost_management")
        ):
            return "explorer"
        return source_key

    @staticmethod
    def _normalize_provider(provider: str | None) -> str | None:
        if provider is None:
            return None
        provider_key = provider.strip().lower()
        if not provider_key:
            return None
        if provider_key not in SUPPORTED_RECON_PROVIDERS:
            raise ValueError(
                f"Unsupported provider '{provider}'. Supported providers: "
                f"{', '.join(sorted(SUPPORTED_RECON_PROVIDERS))}"
            )
        return provider_key

    @staticmethod
    def _normalize_cloud_plus_source(source: str | None, provider: str) -> str:
        source_key = (source or "unknown").strip().lower()
        if provider in {"saas", "license", "platform", "hybrid"}:
            if source_key in {f"{provider}_feed", "feed"}:
                return "feed"
            if source_key in {"native", f"{provider}_native"}:
                return "native"
            if source_key.startswith(f"{provider}_"):
                return "native"
            return "unknown"

        return "unknown"

    @staticmethod
    def _compute_confidence(
        total_service_count: int,
        comparable_service_count: int,
        comparable_record_count: int,
    ) -> float:
        if total_service_count <= 0 or comparable_service_count <= 0:
            return 0.0
        coverage_ratio = comparable_service_count / total_service_count
        volume_factor = min(comparable_record_count / 1000.0, 1.0)
        return round(min(1.0, 0.6 * coverage_ratio + 0.4 * volume_factor), 2)

    @staticmethod
    def _to_float(value: Any) -> float:
        return float(value or 0)

    @staticmethod
    def _to_int(value: Any) -> int:
        return int(value or 0)

    @staticmethod
    def _stable_hash(payload: Dict[str, Any]) -> str:
        canonical = json.dumps(
            payload, sort_keys=True, separators=(",", ":"), default=str
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _render_close_package_csv(
        tenant_id: str,
        start_date: date,
        end_date: date,
        close_status: str,
        lifecycle_summary: Dict[str, Any],
        reconciliation_summary: Dict[str, Any],
        invoice_reconciliation: Dict[str, Any] | None,
        restatement_entries: list[Dict[str, Any]],
    ) -> str:
        return render_close_package_csv(
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            close_status=close_status,
            lifecycle_summary=lifecycle_summary,
            reconciliation_summary=reconciliation_summary,
            invoice_reconciliation=invoice_reconciliation,
            restatement_entries=restatement_entries,
        )

    @staticmethod
    def _render_restatements_csv(entries: list[Dict[str, Any]]) -> str:
        return render_restatements_csv(entries)

    @staticmethod
    def _render_restatement_runs_csv(runs: list[Dict[str, Any]]) -> str:
        return render_restatement_runs_csv(runs)

    async def get_restatement_history(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        export_csv: bool = False,
        provider: str | None = None,
    ) -> Dict[str, Any]:
        return await get_restatement_history_impl(
            self,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            export_csv=export_csv,
            provider=provider,
        )

    async def get_restatement_runs(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        export_csv: bool = False,
        provider: str | None = None,
    ) -> Dict[str, Any]:
        return await get_restatement_runs_impl(
            self,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            export_csv=export_csv,
            provider=provider,
        )

    async def generate_close_package(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        enforce_finalized: bool = True,
        provider: str | None = None,
        max_restatement_entries: int | None = None,
    ) -> Dict[str, Any]:
        return await generate_close_package_impl(
            self,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            enforce_finalized=enforce_finalized,
            provider=provider,
            max_restatement_entries=max_restatement_entries,
        )

    async def list_invoices(
        self,
        tenant_id: UUID,
        provider: str | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[Any]:
        return await list_invoices_impl(
            self,
            tenant_id=tenant_id,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
        )

    async def get_invoice(
        self,
        tenant_id: UUID,
        invoice_id: UUID,
    ) -> Any | None:
        return await get_invoice_impl(self, tenant_id=tenant_id, invoice_id=invoice_id)

    async def upsert_invoice(
        self,
        tenant_id: UUID,
        *,
        provider: str,
        start_date: date,
        end_date: date,
        currency: str,
        total_amount: Decimal,
        invoice_number: str | None = None,
        status: str | None = None,
        notes: str | None = None,
    ) -> Any:
        return await upsert_invoice_impl(
            self,
            tenant_id=tenant_id,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
            currency=currency,
            total_amount=total_amount,
            invoice_number=invoice_number,
            status=status,
            notes=notes,
        )

    async def delete_invoice(self, tenant_id: UUID, invoice_id: UUID) -> bool:
        return await delete_invoice_impl(self, tenant_id=tenant_id, invoice_id=invoice_id)

    async def update_invoice_status(
        self,
        tenant_id: UUID,
        invoice_id: UUID,
        *,
        status: str,
        notes: str | None = None,
    ) -> Any | None:
        return await update_invoice_status_impl(
            self,
            tenant_id=tenant_id,
            invoice_id=invoice_id,
            status=status,
            notes=notes,
        )

    async def _invoice_total_to_usd(self, amount: Decimal, currency: str) -> Decimal:
        return await invoice_total_to_usd_impl(self, amount=amount, currency=currency)

    async def get_invoice_reconciliation_summary(
        self,
        *,
        tenant_id: UUID,
        provider: str,
        start_date: date,
        end_date: date,
        ledger_final_cost_usd: float,
        threshold_percent: float = 1.0,
    ) -> Dict[str, Any]:
        return await get_invoice_reconciliation_summary_impl(
            self,
            tenant_id=tenant_id,
            provider=provider,
            start_date=start_date,
            end_date=end_date,
            ledger_final_cost_usd=ledger_final_cost_usd,
            threshold_percent=threshold_percent,
        )

    async def compare_explorer_vs_cur(
        self,
        tenant_id: UUID,
        start_date: date,
        end_date: date,
        alert_threshold_pct: float = RECON_ALERT_THRESHOLD_PCT,
        provider: str | None = None,
    ) -> Dict[str, Any]:
        return await compare_explorer_vs_cur_impl(
            self,
            tenant_id=tenant_id,
            start_date=start_date,
            end_date=end_date,
            alert_threshold_pct=alert_threshold_pct,
            provider=provider,
            recoverable_alert_errors=RECON_ALERT_RECOVERABLE_EXCEPTIONS,
            log=logger,
        )
