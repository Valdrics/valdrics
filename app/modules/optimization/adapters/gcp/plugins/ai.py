from __future__ import annotations

import time
from typing import Any

import structlog
from google.cloud import aiplatform_v1
from google.cloud import monitoring_v3
from google.oauth2 import service_account  # noqa: F401

from app.modules.optimization.adapters.common import build_google_recoverable_exceptions
from app.modules.optimization.adapters.common.credentials import resolve_gcp_credentials
from app.modules.optimization.adapters.common.sync_bridge import materialize_iterable
from app.modules.optimization.domain.cloud_api_budget import (
    allow_expensive_cloud_api_call,
)
from app.modules.optimization.domain.plugin import ZombiePlugin
from app.modules.optimization.domain.registry import registry
from app.modules.reporting.domain.pricing.service import PricingService

logger = structlog.get_logger()
GCP_VERTEX_SCAN_RECOVERABLE_EXCEPTIONS = build_google_recoverable_exceptions()


@registry.register("gcp")
class IdleVertexEndpointsPlugin(ZombiePlugin):
    @property
    def category_key(self) -> str:
        return "idle_vertex_ai_endpoints"

    @staticmethod
    def _estimate_monthly_cost(endpoint: Any, region: str) -> float:
        deployed_models = list(getattr(endpoint, "deployed_models", []) or [])
        if not deployed_models:
            estimated = PricingService.estimate_monthly_waste(
                provider="gcp",
                resource_type="instance",
                resource_size=None,
                region=region,
                quantity=1.0,
            )
            return round(float(estimated), 2)

        total = 0.0
        for deployed_model in deployed_models:
            dedicated = getattr(deployed_model, "dedicated_resources", None)
            machine_spec = getattr(dedicated, "machine_spec", None)
            machine_type = str(getattr(machine_spec, "machine_type", "") or "").strip()
            replica_count = float(getattr(dedicated, "min_replica_count", 1) or 1)
            if replica_count <= 0:
                replica_count = 1.0
            total += PricingService.estimate_monthly_waste(
                provider="gcp",
                resource_type="instance",
                resource_size=machine_type or None,
                region=region,
                quantity=replica_count,
            )
        return round(float(total), 2)

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
        target_region = region if region != "global" else "us-central1"

        try:
            gcp_creds = resolve_gcp_credentials(credentials)
            endpoint_client = aiplatform_v1.EndpointServiceClient(
                client_options={"api_endpoint": f"{target_region}-aiplatform.googleapis.com"},
                credentials=gcp_creds,
            )
            monitor_client = monitoring_v3.MetricServiceClient(credentials=gcp_creds)
            endpoints = await materialize_iterable(
                endpoint_client.list_endpoints,
                parent=f"projects/{project_id}/locations/{target_region}",
            )

            for endpoint in endpoints:
                finding = await self._scan_endpoint(
                    endpoint=endpoint,
                    monitor_client=monitor_client,
                    project_id=project_id,
                    target_region=target_region,
                )
                if finding is not None:
                    findings.append(finding)

        except GCP_VERTEX_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.error(
                "gcp_vertex_scan_error",
                error=str(exc),
                project_id=project_id,
                region=target_region,
            )

        return findings

    async def _scan_endpoint(
        self,
        *,
        endpoint: Any,
        monitor_client: monitoring_v3.MetricServiceClient,
        project_id: str,
        target_region: str,
    ) -> dict[str, Any] | None:
        if not getattr(endpoint, "traffic_split", None):
            return None

        endpoint_name = str(getattr(endpoint, "name", "") or "").strip()
        if not endpoint_name:
            return None
        endpoint_id = endpoint_name.split("/")[-1]

        allowed = await allow_expensive_cloud_api_call(
            "gcp_monitoring",
            operation="list_time_series",
        )
        if not allowed:
            logger.warning(
                "gcp_monitoring_budget_exhausted",
                plugin=self.category_key,
                endpoint_id=endpoint_id,
            )
            return None

        now = int(time.time())
        interval = monitoring_v3.TimeInterval(
            {
                "start_time": {"seconds": now - (7 * 86400)},
                "end_time": {"seconds": now},
            }
        )

        try:
            results = await materialize_iterable(
                monitor_client.list_time_series,
                request={
                    "name": f"projects/{project_id}",
                    "filter": (
                        'metric.type="aiplatform.googleapis.com/endpoint/prediction_count" '
                        f'AND resource.labels.endpoint_id="{endpoint_id}"'
                    ),
                    "interval": interval,
                    "view": monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL,
                },
            )
        except GCP_VERTEX_SCAN_RECOVERABLE_EXCEPTIONS as exc:
            logger.warning(
                "gcp_vertex_endpoint_metric_error",
                endpoint_id=endpoint_id,
                error=str(exc),
            )
            return None

        has_predictions = any(getattr(result, "points", None) for result in results)
        if has_predictions:
            return None

        monthly_cost = self._estimate_monthly_cost(endpoint=endpoint, region=target_region)
        if monthly_cost <= 0.0:
            logger.warning(
                "gcp_vertex_pricing_unavailable",
                endpoint_id=endpoint_id,
                endpoint_name=getattr(endpoint, "display_name", None),
                region=target_region,
            )
            return None

        endpoint_display_name = str(getattr(endpoint, "display_name", "") or endpoint_id)
        return {
            "resource_id": endpoint_name,
            "resource_type": "Vertex AI Endpoint",
            "resource_name": endpoint_display_name,
            "region": target_region,
            "monthly_cost": monthly_cost,
            "recommendation": "Undeploy models from idle endpoint",
            "action": "undeploy_vertex_endpoint",
            "confidence_score": 0.95,
            "explainability_notes": (
                f"Endpoint '{endpoint_display_name}' had 0 predictions in the last 7 days."
            ),
        }
