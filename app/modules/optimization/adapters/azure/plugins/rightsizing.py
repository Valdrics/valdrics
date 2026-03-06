from __future__ import annotations

from typing import Any, Iterable

import structlog
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.monitor import MonitorManagementClient

from app.modules.optimization.adapters.common.credentials import resolve_azure_credentials
from app.modules.optimization.adapters.common.rightsizing_common import (
    build_rightsizing_finding,
    evaluate_max_samples,
    is_small_shape,
    utc_window,
)
from app.modules.optimization.adapters.common.sync_bridge import materialize_iterable, run_blocking
from app.modules.optimization.domain.cloud_api_budget import (
    allow_expensive_cloud_api_call,
)
from app.modules.optimization.domain.plugin import ZombiePlugin
from app.modules.optimization.domain.registry import registry
from app.modules.reporting.domain.pricing.service import PricingService

logger = structlog.get_logger()

def _resolve_azure_error_base() -> type[Exception]:
    try:
        from azure.core.exceptions import AzureError
    except ImportError:  # pragma: no cover - fallback for SDK-mocked test envs
        return Exception
    return AzureError

CPU_MAX_THRESHOLD_PERCENT = 10.0
SKIPPED_VM_SIZE_TOKENS: tuple[str, ...] = ("standard_b", "basic_a")
AZURE_RIGHTSIZING_SCAN_RECOVERABLE_EXCEPTIONS: tuple[type[Exception], ...] = (
    _resolve_azure_error_base(),
    OSError,
    TimeoutError,
    ValueError,
)


@registry.register("azure")
class OverprovisionedVmPlugin(ZombiePlugin):
    """Detect Azure VMs with persistently low maximum CPU utilization."""

    @property
    def category_key(self) -> str:
        return "overprovisioned_azure_vms"

    @staticmethod
    def _estimate_monthly_cost(vm_size: str, region: str) -> float:
        estimated = PricingService.estimate_monthly_waste(
            provider="azure",
            resource_type="instance",
            resource_size=vm_size,
            region=region,
        )
        return round(float(estimated), 2)

    async def scan(
        self,
        session: Any,
        region: str,
        credentials: dict[str, str] | Any | None = None,
        config: Any = None,
        inventory: Any = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        del config, inventory, kwargs
        subscription_id = str(session)
        findings: list[dict[str, Any]] = []

        try:
            az_creds = resolve_azure_credentials(credentials)
            compute_client = ComputeManagementClient(az_creds, subscription_id)
            monitor_client = MonitorManagementClient(az_creds, subscription_id)
            virtual_machines = await materialize_iterable(
                compute_client.virtual_machines.list_all
            )
            for vm in virtual_machines:
                finding = await self._scan_vm(
                    vm=vm,
                    monitor_client=monitor_client,
                    compute_client=compute_client,
                    region=region,
                )
                if finding is not None:
                    findings.append(finding)
        except AZURE_RIGHTSIZING_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.error(
                "azure_rightsizing_scan_error",
                error=str(exc),
                subscription_id=subscription_id,
                region=region,
            )

        return findings

    async def _scan_vm(
        self,
        *,
        vm: Any,
        monitor_client: MonitorManagementClient,
        compute_client: ComputeManagementClient,
        region: str,
    ) -> dict[str, Any] | None:
        resource_id = str(getattr(vm, "id", "") or "").strip()
        vm_name = str(getattr(vm, "name", "") or "").strip()
        if not resource_id or not vm_name:
            return None

        resource_group_name = self._extract_resource_group_name(resource_id)
        try:
            instance_view = await run_blocking(
                compute_client.virtual_machines.instance_view,
                resource_group_name=resource_group_name,
                vm_name=vm_name,
            )
        except AZURE_RIGHTSIZING_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.warning(
                "azure_rightsizing_vm_state_error",
                vm_name=vm_name,
                error=str(exc),
            )
            return None

        if not self._is_running(instance_view):
            return None

        vm_size = str(
            getattr(getattr(vm, "hardware_profile", None), "vm_size", "") or "unknown"
        )
        if is_small_shape(vm_size, tokens=SKIPPED_VM_SIZE_TOKENS):
            return None

        start_time, end_time = utc_window(7)
        allowed = await allow_expensive_cloud_api_call(
            "azure_monitor",
            operation="metrics.list",
        )
        if not allowed:
            logger.warning(
                "azure_monitor_budget_exhausted",
                plugin=self.category_key,
                vm_name=vm_name,
            )
            return None

        try:
            metrics_data = await run_blocking(
                monitor_client.metrics.list,
                resource_uri=resource_id,
                timespan=f"{start_time.isoformat()}/{end_time.isoformat()}",
                interval="P1D",
                metricnames="Percentage CPU",
                aggregation="Maximum",
            )
        except AZURE_RIGHTSIZING_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.warning(
                "azure_rightsizing_vm_metric_error",
                vm_name=vm_name,
                error=str(exc),
            )
            return None

        evaluation = evaluate_max_samples(
            self._iter_cpu_max_values(metrics_data),
            threshold=CPU_MAX_THRESHOLD_PERCENT,
        )
        if not evaluation.has_data or not evaluation.below_threshold:
            return None

        vm_region = str(getattr(vm, "location", "") or region)
        monthly_cost = self._estimate_monthly_cost(vm_size=vm_size, region=vm_region)
        if monthly_cost <= 0.0:
            logger.warning(
                "azure_rightsizing_pricing_unavailable",
                vm_name=vm_name,
                vm_size=vm_size,
                region=vm_region,
            )
            return None

        finding = build_rightsizing_finding(
            resource_id=resource_id,
            resource_type="Azure Virtual Machine",
            resource_name=vm_name,
            region=vm_region,
            monthly_cost=monthly_cost,
            current_size=vm_size,
            max_cpu_percent=evaluation.max_observed,
            threshold_percent=CPU_MAX_THRESHOLD_PERCENT,
            action="resize_azure_vm",
            confidence_score=0.85,
        )
        finding[
            "explainability_notes"
        ] = f"VM {vm_name} had Max CPU of {evaluation.max_observed:.1f}% over the last 7 days."
        return finding

    @staticmethod
    def _extract_resource_group_name(resource_id: str) -> str:
        parts = [part for part in resource_id.split("/") if part]
        try:
            rg_index = parts.index("resourceGroups")
        except ValueError as exc:
            raise ValueError(f"resource_id missing resourceGroups segment: {resource_id}") from exc
        if rg_index + 1 >= len(parts):
            raise ValueError(f"resource_id missing resource group value: {resource_id}")
        resource_group_name = parts[rg_index + 1].strip()
        if not resource_group_name:
            raise ValueError(f"resource group is empty in resource_id: {resource_id}")
        return resource_group_name

    @staticmethod
    def _is_running(instance_view: Any) -> bool:
        statuses = getattr(instance_view, "statuses", None) or []
        for status in statuses:
            status_code = str(getattr(status, "code", "") or "")
            if status_code == "PowerState/running":
                return True
        return False

    @staticmethod
    def _iter_cpu_max_values(metrics_data: Any) -> Iterable[float]:
        metric_values = getattr(metrics_data, "value", None) or []
        for metric in metric_values:
            metric_name_obj = getattr(metric, "name", None)
            metric_name = str(getattr(metric_name_obj, "value", "") or "")
            if metric_name != "Percentage CPU":
                continue
            for series in getattr(metric, "timeseries", None) or []:
                for point in getattr(series, "data", None) or []:
                    maximum = getattr(point, "maximum", None)
                    if maximum is None:
                        continue
                    yield float(maximum)
