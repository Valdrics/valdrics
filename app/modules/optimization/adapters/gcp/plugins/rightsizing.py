from __future__ import annotations

from typing import Any, Iterable

import structlog
from google.cloud import compute_v1
from google.cloud import monitoring_v3

from app.modules.optimization.adapters.common import build_google_recoverable_exceptions
from app.modules.optimization.adapters.common.credentials import resolve_gcp_credentials
from app.modules.optimization.adapters.common.rightsizing_common import (
    build_rightsizing_finding,
    evaluate_max_samples,
    is_small_shape,
    utc_window,
)
from app.modules.optimization.adapters.common.sync_bridge import materialize_iterable
from app.modules.optimization.domain.cloud_api_budget import (
    allow_expensive_cloud_api_call,
)
from app.modules.optimization.domain.plugin import ZombiePlugin
from app.modules.optimization.domain.registry import registry
from app.modules.reporting.domain.pricing.service import PricingService

logger = structlog.get_logger()

CPU_MAX_THRESHOLD_RATIO = 0.1
SKIPPED_MACHINE_TYPE_TOKENS: tuple[str, ...] = ("micro", "small")
GCP_RIGHTSIZING_SCAN_RECOVERABLE_EXCEPTIONS = build_google_recoverable_exceptions()


@registry.register("gcp")
class OverprovisionedComputePlugin(ZombiePlugin):
    """Detect running GCP Compute instances with persistently low peak CPU."""

    @property
    def category_key(self) -> str:
        return "overprovisioned_gcp_instances"

    @staticmethod
    def _estimate_monthly_cost(machine_type: str, region: str) -> float:
        estimated = PricingService.estimate_monthly_waste(
            provider="gcp",
            resource_type="instance",
            resource_size=machine_type,
            region=region,
        )
        return round(float(estimated), 2)

    async def scan(
        self,
        session: Any,
        region: str,
        credentials: dict[str, Any] | Any | None = None,
        config: Any = None,
        inventory: Any = None,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        del config, inventory, kwargs
        project_id = str(session)
        findings: list[dict[str, Any]] = []

        try:
            gcp_creds = resolve_gcp_credentials(credentials)
            instances_client = compute_v1.InstancesClient(credentials=gcp_creds)
            monitor_client = monitoring_v3.MetricServiceClient(credentials=gcp_creds)
            aggregated_pages = await materialize_iterable(
                instances_client.aggregated_list,
                project=project_id,
            )
            for _zone_path, page in aggregated_pages:
                for instance in getattr(page, "instances", None) or []:
                    finding = await self._scan_instance(
                        monitor_client=monitor_client,
                        project_id=project_id,
                        instance=instance,
                        default_region=region,
                    )
                    if finding is not None:
                        findings.append(finding)
        except GCP_RIGHTSIZING_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.error(
                "gcp_rightsizing_scan_error",
                error=str(exc),
                project_id=project_id,
                region=region,
            )

        return findings

    async def _scan_instance(
        self,
        *,
        monitor_client: monitoring_v3.MetricServiceClient,
        project_id: str,
        instance: Any,
        default_region: str,
    ) -> dict[str, Any] | None:
        status = str(getattr(instance, "status", "") or "")
        if status != "RUNNING":
            return None

        machine_type_url = str(getattr(instance, "machine_type", "") or "")
        if not machine_type_url:
            return None
        if is_small_shape(machine_type_url, tokens=SKIPPED_MACHINE_TYPE_TOKENS):
            return None

        instance_id = str(getattr(instance, "id", "") or "")
        if not instance_id:
            return None

        start_time, end_time = utc_window(7)
        interval = monitoring_v3.TimeInterval(
            {
                "start_time": {"seconds": int(start_time.timestamp())},
                "end_time": {"seconds": int(end_time.timestamp())},
            }
        )
        aggregation = monitoring_v3.Aggregation(
            {
                "alignment_period": {"seconds": 86400},
                "per_series_aligner": monitoring_v3.Aggregation.Aligner.ALIGN_MAX,
            }
        )
        allowed = await allow_expensive_cloud_api_call(
            "gcp_monitoring",
            operation="list_time_series",
        )
        if not allowed:
            logger.warning(
                "gcp_monitoring_budget_exhausted",
                plugin=self.category_key,
                instance_id=instance_id,
            )
            return None

        try:
            result_series = await materialize_iterable(
                monitor_client.list_time_series,
                request={
                    "name": f"projects/{project_id}",
                    "filter": (
                        'metric.type="compute.googleapis.com/instance/cpu/utilization" '
                        f'AND resource.labels.instance_id="{instance_id}"'
                    ),
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                    "aggregation": aggregation,
                },
            )
        except GCP_RIGHTSIZING_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.warning(
                "gcp_rightsizing_instance_metric_error",
                instance_id=instance_id,
                error=str(exc),
            )
            return None

        evaluation = evaluate_max_samples(
            self._iter_cpu_ratio_samples(result_series),
            threshold=CPU_MAX_THRESHOLD_RATIO,
        )
        if not evaluation.has_data or not evaluation.below_threshold:
            return None

        machine_type_name = machine_type_url.split("/")[-1]
        instance_region = self._derive_region_from_zone(
            str(getattr(instance, "zone", "") or ""),
            fallback=default_region,
        )
        monthly_cost = self._estimate_monthly_cost(
            machine_type=machine_type_name,
            region=instance_region,
        )
        if monthly_cost <= 0.0:
            logger.warning(
                "gcp_rightsizing_pricing_unavailable",
                instance_id=instance_id,
                machine_type=machine_type_name,
                region=instance_region,
            )
            return None

        max_cpu_percent = evaluation.max_observed * 100.0
        finding = build_rightsizing_finding(
            resource_id=instance_id,
            resource_type="GCP Compute Instance",
            resource_name=str(getattr(instance, "name", "") or instance_id),
            region=instance_region,
            monthly_cost=monthly_cost,
            current_size=machine_type_name,
            max_cpu_percent=max_cpu_percent,
            threshold_percent=CPU_MAX_THRESHOLD_RATIO * 100.0,
            action="resize_gcp_instance",
            confidence_score=0.85,
        )
        finding[
            "explainability_notes"
        ] = f"Instance {machine_type_name} had Max CPU of {max_cpu_percent:.1f}% over the last 7 days."
        return finding

    @staticmethod
    def _iter_cpu_ratio_samples(series_list: list[Any]) -> Iterable[float]:
        for result in series_list:
            for point in getattr(result, "points", None) or []:
                value = getattr(getattr(point, "value", None), "double_value", None)
                if value is None:
                    continue
                yield float(value)

    @staticmethod
    def _derive_region_from_zone(zone: str, *, fallback: str) -> str:
        normalized = zone.strip()
        if not normalized:
            return fallback
        if "/" in normalized:
            normalized = normalized.split("/")[-1]
        parts = normalized.split("-")
        if len(parts) >= 2:
            return "-".join(parts[:-1])
        return fallback
